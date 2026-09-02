"""
Async database layer for AIBD.
Fully compatible with Supabase PostgreSQL (via asyncpg) and SQLite (via aiosqlite).
"""

from __future__ import annotations
import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
from sqlalchemy import Column, Float, Integer, String, Text, JSON, BigInteger, ForeignKey, desc
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship

from aidbg.backend.config import settings

Base = declarative_base()


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(16), primary_key=True)  # Fingerprint e.g. A7F82C
    error_type = Column(String(128), nullable=False)
    error_message = Column(Text, nullable=True)
    service = Column(String(128), default="default-service")
    culprit = Column(String(256), nullable=True)
    severity = Column(String(32), default="HIGH")
    occurrences = Column(Integer, default=1)
    first_seen = Column(Float, default=time.time)
    last_seen = Column(Float, default=time.time)
    status = Column(String(32), default="open")  # open, analyzing, resolved

    # Root Cause Analysis results
    root_cause = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    causal_chain = Column(JSON, default=list)
    evidence = Column(JSON, default=list)
    hypotheses = Column(JSON, default=list)

    # Actionable Fixes
    suggested_fix = Column(Text, nullable=True)
    proposed_patch = Column(Text, nullable=True)
    generated_test = Column(Text, nullable=True)
    risk = Column(String(32), nullable=True)  # low, medium, high

    # Relationships
    events = relationship("Event", back_populates="incident", cascade="all, delete-orphan", lazy="selectin")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "service": self.service,
            "culprit": self.culprit,
            "severity": self.severity,
            "occurrences": self.occurrences,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "status": self.status,
            "root_cause": self.root_cause,
            "confidence": self.confidence,
            "causal_chain": self.causal_chain or [],
            "evidence": self.evidence or [],
            "hypotheses": self.hypotheses or [],
            "suggested_fix": self.suggested_fix,
            "proposed_patch": self.proposed_patch,
            "generated_test": self.generated_test,
            "risk": self.risk,
        }


class Event(Base):
    __tablename__ = "events"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    incident_id = Column(String(16), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    trace_id = Column(String(64), nullable=True)
    span_id = Column(String(64), nullable=True)
    frames = Column(JSON, default=list)
    request_context = Column(JSON, default=dict)
    breadcrumbs = Column(JSON, default=list)
    system_metadata = Column(JSON, default=dict)
    extra = Column(JSON, default=dict)
    timestamp = Column(Float, default=time.time)

    incident = relationship("Incident", back_populates="events")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "frames": self.frames or [],
            "request_context": self.request_context or {},
            "breadcrumbs": self.breadcrumbs or [],
            "system_metadata": self.system_metadata or {},
            "extra": self.extra or {},
            "timestamp": self.timestamp,
        }


# Database engine and session factory
effective_db_url = settings.get_effective_db_url()
connect_args = {}
if "asyncpg" in effective_db_url:
    connect_args = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }

engine = create_async_engine(
    effective_db_url,
    connect_args=connect_args,
    echo=False,
    future=True,
    pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def init_db() -> None:
    """Create tables if not existing (useful for SQLite or initial Postgres setup)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to yield an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
