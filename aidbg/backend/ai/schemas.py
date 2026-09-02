"""
Pydantic schemas for AI output validation.
Enforces strict structured responses to ensure high reliability and zero hallucinations.
"""

from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class Hypothesis(BaseModel):
    description: str = Field(..., description="Probable explanation inferred from the evidence")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")


class CausalStep(BaseModel):
    source: str = Field(..., description="Source state or event")
    target: str = Field(..., description="Resulting state or event")
    reason: str = Field(..., description="Why this transition occurred")


class RootCauseExplanation(BaseModel):
    root_cause: str = Field(..., description="Concise explanation of why the application failed")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    evidence: List[str] = Field(default_factory=list, description="Direct facts observed in telemetry, AST, and git")
    hypotheses: List[Hypothesis] = Field(default_factory=list, description="Probable hypotheses")
    recommended_fix: str = Field(..., description="Actionable recommendation for the engineer")
    proposed_patch: Optional[str] = Field(None, description="Unified git diff representing the proposed fix")
    generated_test: Optional[str] = Field(None, description="Pytest regression test verifying the bug is fixed")
    risk: Literal["low", "medium", "high"] = Field("low", description="Risk assessment of applying the proposed fix")
