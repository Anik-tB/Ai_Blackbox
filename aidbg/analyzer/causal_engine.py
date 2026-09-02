"""
Causal Graph Engine and Structured Evidence Synthesis.
Combines runtime telemetry, static AST findings, and Git history into a
directed causal event graph with confirmed evidence vs hypotheses.
"""

from __future__ import annotations
import time
from typing import Any, Dict, List, Optional
import networkx as nx


class CausalGraphBuilder:
    """Builds and serializes a causal Directed Acyclic Graph (DAG)."""
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_event(self, node_id: str, label: str, node_type: str = "fact",
                  metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a node to the graph.
        node_type: 'fact' (observed), 'hypothesis' (inferred), 'anomaly' (metric spike), 'action'
        """
        self.graph.add_node(
            node_id,
            label=label,
            node_type=node_type,
            metadata=metadata or {}
        )

    def add_causal_edge(self, from_id: str, to_id: str, reason: str,
                         confidence: float = 1.0, evidence: str = "") -> None:
        """Add a directed causal edge between two events."""
        self.graph.add_edge(
            from_id,
            to_id,
            reason=reason,
            confidence=confidence,
            evidence=evidence
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the causal graph for UI and API consumers."""
        nodes = []
        for n, d in self.graph.nodes(data=True):
            nodes.append({
                "id": n,
                "label": d.get("label", n),
                "type": d.get("node_type", "fact"),
                "metadata": d.get("metadata", {})
            })

        edges = []
        for u, v, d in self.graph.edges(data=True):
            edges.append({
                "from": u,
                "to": v,
                "reason": d.get("reason", ""),
                "confidence": d.get("confidence", 1.0),
                "evidence": d.get("evidence", "")
            })

        return {
            "nodes": nodes,
            "edges": edges
        }


def build_evidence_package(incident: Dict[str, Any], event: Optional[Dict[str, Any]],
                           ast_info: Dict[str, Any], git_info: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Construct structured evidence payload before invoking the AI reasoning engine.
    Never sends unstructured walls of logs.
    """
    error_type = incident.get("error_type", "")
    error_msg = incident.get("error_message", "")
    culprit = incident.get("culprit", "")

    req = event.get("request_context", {}) if event else {}
    breadcrumbs = event.get("breadcrumbs", []) if event else []
    frames = event.get("frames", []) if event else []
    extra = event.get("extra", {}) if event else {}

    # Extract execution call stack string
    call_trace = []
    if req and req.get("path"):
        call_trace.append(f"{req.get('method', 'GET')} {req.get('path')}")
    for f in frames[-4:]:
        call_trace.append(f"{f.get('filename', '').split('/')[-1]}:{f.get('function', '')}:{f.get('lineno', '')}")

    # Gather verified facts
    confirmed_evidence: List[str] = []
    if error_type:
        confirmed_evidence.append(f"Uncaught {error_type}: {error_msg}")
    if req and req.get("path"):
        confirmed_evidence.append(f"Occurred during {req.get('method')} {req.get('path')}")
    if culprit:
        confirmed_evidence.append(f"Culprit location: {culprit}")
    if incident.get("occurrences", 1) > 1:
        confirmed_evidence.append(f"Reproduced {incident['occurrences']} times across requests")
    if extra.get("duration_ms"):
        confirmed_evidence.append(f"Request execution latency was {extra['duration_ms']:.1f}ms")

    # AST findings
    for pattern in ast_info.get("suspect_patterns", []):
        confirmed_evidence.append(f"AST Analysis: {pattern.get('description', '')}")

    # Git findings
    for g in git_info:
        confirmed_evidence.append(f"Recent commit {g.get('commit')}: '{g.get('message')}' ({g.get('relation')})")

    return {
        "incident_id": incident.get("id"),
        "error_type": error_type,
        "error_message": error_msg,
        "culprit": culprit,
        "occurrences": incident.get("occurrences", 1),
        "request": req,
        "call_trace": call_trace,
        "ast_analysis": ast_info,
        "git_correlation": git_info,
        "confirmed_evidence": confirmed_evidence,
        "breadcrumbs": breadcrumbs[-10:],
    }


def synthesize_causal_chain(evidence: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, str]]]:
    """
    Generate graph nodes, edges, and step-by-step causal chain.
    """
    builder = CausalGraphBuilder()
    causal_steps: List[Dict[str, str]] = []

    req = evidence.get("request", {})
    error_type = evidence.get("error_type", "Error")
    ast_info = evidence.get("ast_analysis", {})
    git_info = evidence.get("git_correlation", [])
    suspects = ast_info.get("suspect_patterns", [])

    # Start node: Request or entrypoint
    entry_id = "request_entry"
    entry_label = f"HTTP {req.get('method', 'GET')} {req.get('path', '/api')}" if req else "Execution Trigger"
    builder.add_event(entry_id, entry_label, node_type="fact")
    prev_id = entry_id

    # Git change node if relevant
    if git_info:
        top_git = git_info[0]
        git_id = "git_change"
        builder.add_event(git_id, f"Commit {top_git.get('commit')}: {top_git.get('message', '')}", node_type="fact")
        builder.add_causal_edge(git_id, entry_id, reason="Code deployment altered runtime behavior", confidence=top_git.get("confidence", 0.8))

    # AST suspect pattern node (e.g. NULL return or Pool exhaustion)
    if suspects:
        s = suspects[0]
        ast_id = "null_dereference"
        builder.add_event(ast_id, f"Variable '{s.get('variable')}' returned None", node_type="anomaly")
        builder.add_causal_edge(prev_id, ast_id, reason=f"Function called at line {s.get('assigned_line')}", confidence=0.92)
        causal_steps.append({"from": entry_label, "to": f"{s.get('variable')} is None", "reason": "Lookup returned empty result"})
        prev_id = ast_id

        # Access node
        access_id = "attribute_access"
        builder.add_event(access_id, f"Accessed .{s.get('attribute')} on None", node_type="anomaly")
        builder.add_causal_edge(prev_id, access_id, reason="Missing guard check", confidence=0.95)
        causal_steps.append({"from": f"{s.get('variable')} is None", "to": f"Access .{s.get('attribute')}", "reason": "No None check"})
        prev_id = access_id

    elif "Timeout" in error_type or "Pool" in error_type or "OperationalError" in error_type:
        pool_id = "pool_saturation"
        builder.add_event(pool_id, "Connection pool utilization 100%", node_type="anomaly")
        builder.add_causal_edge(prev_id, pool_id, reason="High concurrency without connection release", confidence=0.91)
        causal_steps.append({"from": entry_label, "to": "Connection Pool Exhaustion", "reason": "Concurrent workers saturated pool"})
        prev_id = pool_id

        wait_id = "requests_waiting"
        builder.add_event(wait_id, "Requests waiting for free connection", node_type="anomaly")
        builder.add_causal_edge(prev_id, wait_id, reason="All connections occupied", confidence=0.94)
        causal_steps.append({"from": "Connection Pool Exhaustion", "to": "Requests Waiting", "reason": "Timeout waiting for available socket"})
        prev_id = wait_id

    # Terminal node: The Exception
    err_id = "runtime_exception"
    builder.add_event(err_id, f"{error_type} Raised", node_type="anomaly")
    builder.add_causal_edge(prev_id, err_id, reason="Unrecoverable runtime error", confidence=0.99)
    causal_steps.append({"from": "Culprit operation", "to": f"{error_type} Raised", "reason": "Unhandled exception"})

    # HTTP 500 node
    resp_id = "http_500"
    builder.add_event(resp_id, "HTTP 500 Response", node_type="fact")
    builder.add_causal_edge(err_id, resp_id, reason="Exception propagated to web framework", confidence=1.0)
    causal_steps.append({"from": f"{error_type} Raised", "to": "HTTP 500 Response", "reason": "Internal server error sent to client"})

    return builder.to_dict(), causal_steps
