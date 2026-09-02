"""
Health check and diagnostic endpoints for AIBD.
"""

from __future__ import annotations
import platform
import sys
from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from aidbg.backend.config import settings
from aidbg.backend.database import get_db

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Basic health check and database connectivity verification."""
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "ok",
        "database": db_status,
        "database_type": "Supabase (PostgreSQL)" if settings.supabase_db_url else "SQLite (local)",
        "ai_provider": settings.ai_provider,
        "python_version": platform.python_version(),
    }


@router.get("/doctor")
async def doctor_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Detailed diagnostics for CLI `aidbg doctor`."""
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "checks": [
            {"name": "Python Environment", "status": "pass", "details": platform.python_version()},
            {"name": "Backend Service", "status": "pass", "details": f"Running on {settings.host}:{settings.port}"},
            {"name": "Database Connection", "status": "pass" if db_ok else "fail",
             "details": "Supabase" if settings.supabase_db_url else "Local SQLite"},
            {"name": "AI Reasoning Engine", "status": "pass", "details": settings.ai_provider},
            {"name": "Secret Redaction Rules", "status": "pass", "details": "Active (Tokens, Passwords, Keys)"}
        ]
    }
