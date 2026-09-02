"""
Incidents REST API for AIBD.
Handles ingestion, deduplication, root cause analysis, fix generation, and retrieval.
"""

from __future__ import annotations
import asyncio
import os
import subprocess
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from aidbg.analyzer.ast_parser import analyze_source_file
from aidbg.analyzer.causal_engine import build_evidence_package, synthesize_causal_chain
from aidbg.analyzer.fingerprint import calculate_severity, compute_fingerprint
from aidbg.backend.ai.provider import get_llm_provider
from aidbg.backend.api.ws import manager
from aidbg.backend.config import settings
from aidbg.backend.database import Event, Incident, get_db
from aidbg.backend.git.git_analyzer import correlate_changes
from aidbg.backend.supabase_client import broadcast_incident_event

router = APIRouter(prefix="/api/v1/incidents", tags=["Incidents"])


async def analyze_incident_async(incident_id: str, event_data: Dict[str, Any],
                                 culprit_file: str, culprit_line: int):
    """
    Background task to perform AST analysis, Git correlation, and AI reasoning.
    Updates the database with the synthesized evidence, causal chain, and safe patch.
    """
    from aidbg.backend.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        inc = await session.get(Incident, incident_id)
        if not inc:
            return

        inc.status = "analyzing"
        await session.commit()

        # 1. Static AST Analysis
        ast_info = analyze_source_file(culprit_file, culprit_line)

        # 2. Git History & Blame Correlation
        git_info = correlate_changes(inc.first_seen, culprit_file, culprit_line, repo_path=settings.repo_path)

        # 3. Build Evidence Package & Causal Graph
        evidence_pkg = build_evidence_package(inc.to_dict(), event_data, ast_info, git_info)
        causal_graph, causal_steps = synthesize_causal_chain(evidence_pkg)

        # 4. AI Reasoning (or Deterministic Fallback)
        provider = get_llm_provider()
        try:
            rca = await provider.analyze_incident(evidence_pkg)
            inc.root_cause = rca.root_cause
            inc.confidence = rca.confidence
            inc.evidence = [e for e in rca.evidence]
            inc.hypotheses = [h.model_dump() for h in rca.hypotheses]
            inc.suggested_fix = rca.recommended_fix
            inc.proposed_patch = rca.proposed_patch
            inc.generated_test = rca.generated_test
            inc.risk = rca.risk
        except Exception as e:
            inc.root_cause = f"Analysis completed via heuristic engine (AI notice: {str(e)})"
            inc.confidence = 0.85
            inc.evidence = evidence_pkg.get("confirmed_evidence", [])

        # Store graph into causal_chain field
        inc.causal_chain = causal_graph
        inc.status = "open"
        await session.commit()

        # Broadcast update to web dashboard and Supabase Realtime
        await manager.broadcast({
            "type": "INCIDENT_UPDATED",
            "incident": inc.to_dict()
        })
        await broadcast_incident_event(incident_id, "UPDATE", inc.to_dict())


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(payload: Dict[str, Any], background_tasks: BackgroundTasks,
                       db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Ingest a telemetry event from the aidbg agent.
    Deduplicates errors by fingerprint and triggers background analysis.
    """
    error_type = payload.get("error_type", "UnknownError")
    error_message = payload.get("error_message", "")
    frames = payload.get("frames", [])
    culprit = payload.get("culprit", "")
    service = payload.get("tags", {}).get("service", "default-service")

    # Compute stable incident fingerprint e.g. A7F82C
    incident_id = compute_fingerprint(error_type, frames, error_message)

    # Culprit file & line parsing
    culprit_file = ""
    culprit_line = 0
    if frames:
        culprit_file = frames[-1].get("filename", "")
        culprit_line = frames[-1].get("lineno", 0)

    # Upsert Incident
    query = select(Incident).where(Incident.id == incident_id)
    res = await db.execute(query)
    incident = res.scalar_one_or_none()

    now = time.time()
    if incident:
        incident.occurrences += 1
        incident.last_seen = now
        incident.severity = calculate_severity(error_type, incident.occurrences)
    else:
        incident = Incident(
            id=incident_id,
            error_type=error_type,
            error_message=error_message,
            service=service,
            culprit=culprit,
            severity=calculate_severity(error_type, 1),
            occurrences=1,
            first_seen=now,
            last_seen=now,
            status="open"
        )
        db.add(incident)

    # Create raw Event record
    event = Event(
        incident_id=incident_id,
        trace_id=payload.get("trace_id"),
        span_id=payload.get("span_id"),
        frames=frames,
        request_context=payload.get("request") or {},
        breadcrumbs=payload.get("breadcrumbs") or [],
        system_metadata=payload.get("system") or {},
        extra=payload.get("extra") or {},
        timestamp=now
    )
    db.add(event)
    await db.commit()

    # Trigger async background RCA & AST analysis
    background_tasks.add_task(
        analyze_incident_async,
        incident_id,
        event.to_dict(),
        culprit_file,
        culprit_line
    )

    return {
        "status": "accepted",
        "incident_id": incident_id,
        "occurrences": incident.occurrences
    }


@router.get("")
async def list_incidents(severity: Optional[str] = None, status: Optional[str] = None,
                         limit: int = 50, db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    """List recent incidents with optional severity and status filters."""
    query = select(Incident).order_by(desc(Incident.last_seen)).limit(limit)
    if severity:
        query = query.where(Incident.severity == severity.upper())
    if status:
        query = query.where(Incident.status == status)

    result = await db.execute(query)
    incidents = result.scalars().all()
    return [inc.to_dict() for inc in incidents]


@router.get("/{incident_id}")
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve complete incident details, causal graph, and latest event."""
    query = select(Incident).where(Incident.id == incident_id)
    res = await db.execute(query)
    incident = res.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    data = incident.to_dict()
    # Include the most recent event data
    if incident.events:
        data["latest_event"] = incident.events[-1].to_dict()
    return data


@router.get("/{incident_id}/explain")
async def explain_incident(incident_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve formatted explanation for CLI and reports."""
    incident = await db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    return {
        "incident_id": incident.id,
        "error_type": incident.error_type,
        "root_cause": incident.root_cause or "Analysis pending or unavailable.",
        "confidence": incident.confidence or 0.0,
        "causal_chain": incident.causal_chain or {},
        "evidence": incident.evidence or [],
        "hypotheses": incident.hypotheses or [],
        "recommended_fix": incident.suggested_fix or "No fix recommendation available.",
        "risk": incident.risk or "low",
    }


@router.get("/{incident_id}/fix")
async def get_fix(incident_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve proposed unified patch diff and generated test suite."""
    incident = await db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    return {
        "incident_id": incident.id,
        "proposed_patch": incident.proposed_patch,
        "generated_test": incident.generated_test,
        "risk": incident.risk,
        "instructions": "Never automatically applied to production. Review before merging."
    }


@router.post("/{incident_id}/branch")
async def create_fix_branch(incident_id: str, repo_path: str = ".") -> Dict[str, Any]:
    """Create a new Git branch for the proposed fix."""
    branch_name = f"fix/aidbg-{incident_id.lower()}"
    try:
        res = subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5.0
        )
        if res.returncode == 0:
            return {"status": "success", "branch": branch_name}
        return {"status": "error", "detail": res.stderr}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/{incident_id}/logs")
async def get_incident_logs(incident_id: str, db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    """Retrieve chronological breadcrumbs leading up to the incident."""
    incident = await db.get(Incident, incident_id)
    if not incident or not incident.events:
        return []
    return incident.events[-1].breadcrumbs or []


@router.get("/{incident_id}/trace")
async def get_incident_trace(incident_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve stack frames and execution trace."""
    incident = await db.get(Incident, incident_id)
    if not incident or not incident.events:
        return {"trace": []}
    return {
        "incident_id": incident.id,
        "trace_id": incident.events[-1].trace_id,
        "frames": incident.events[-1].frames
    }
