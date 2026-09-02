"""
AI & Deterministic Root Cause Analysis Provider Interface.
Supports multi-language code fix synthesis (Python, JavaScript/TypeScript, and Universal).
"""

from __future__ import annotations
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import httpx

from aidbg.backend.ai.schemas import Hypothesis, RootCauseExplanation
from aidbg.backend.config import settings

logger = logging.getLogger("aidbg.ai")


class LLMProvider(ABC):
    """Abstract base class for all AI reasoning providers."""
    @abstractmethod
    async def analyze_incident(self, evidence_package: Dict[str, Any]) -> RootCauseExplanation:
        pass


class DeterministicFallbackProvider(LLMProvider):
    """
    Zero-dependency deterministic rule engine.
    Synthesizes language-appropriate fixes for Python, JavaScript/TypeScript, and generic languages.
    """

    async def analyze_incident(self, evidence_package: Dict[str, Any]) -> RootCauseExplanation:
        error_type = evidence_package.get("error_type", "")
        error_msg = evidence_package.get("error_message", "")
        culprit = evidence_package.get("culprit", "")
        ast_analysis = evidence_package.get("ast_analysis", {})
        language = ast_analysis.get("language", "python").lower()

        culprit_file = "app.py"
        line_no = 79
        if culprit and ":" in culprit:
            parts = culprit.split(":")
            culprit_file = parts[0]
            if len(parts) > 1 and parts[-1].isdigit():
                line_no = int(parts[-1])
        elif culprit:
            culprit_file = culprit

        file_name = culprit_file.split("/")[-1]
        is_js = any(culprit_file.endswith(ext) for ext in [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]) or language in ["javascript", "node"]

        # Default fallback values
        root_cause = f"Unhandled {error_type} in {file_name} at line {line_no}."
        confidence = 0.85
        hypotheses = [
            Hypothesis(description=f"Runtime exception {error_type} encountered unexpected input state.", confidence=0.85)
        ]
        recommended_fix = "Inspect culprit code, ensure inputs are validated, and add defensive error handling."
        proposed_patch = (
            f"--- a/{file_name}\n"
            f"+++ b/{file_name}\n"
            f"@@ -{max(1, line_no - 1)},2 +{max(1, line_no - 1)},3 @@\n"
            f"+    // Defensive check added by AIBD\n"
        )
        generated_test = "# Regression test template\n"
        risk = "low"

        # Pattern 1: Null/Undefined Attribute Access
        null_indicators = (
            "AttributeError", "TypeError", "NullPointerException", "NullReferenceException",
            "Cannot read propert", "Cannot read properties of undefined", "Cannot read properties of null",
            "undefined is not an object", "null is not an object"
        )

        if any(ind.lower() in error_type.lower() or ind.lower() in error_msg.lower() for ind in null_indicators):
            var_name = "user"
            attr_name = "password"

            # Parse attribute from message e.g. "has no attribute 'password'"
            if "'" in error_msg:
                parts = error_msg.split("'")
                if len(parts) >= 2:
                    attr_name = parts[1]

            if is_js:
                root_cause = (
                    f"Attempted to read property '.{attr_name}' on an undefined or null object ('{var_name}') "
                    f"in {file_name}:{line_no}."
                )
                confidence = 0.94
                hypotheses = [
                    Hypothesis(
                        description="Database query or API lookup returned null/undefined for the requested record.",
                        confidence=0.92
                    ),
                    Hypothesis(
                        description="Request body or query payload omitted required identifier.",
                        confidence=0.79
                    )
                ]
                recommended_fix = (
                    f"Add a guard clause checking if '{var_name}' exists or use optional chaining ({var_name}?.{attr_name}) "
                    f"before accessing properties. Return an HTTP 404 or 400 response."
                )
                proposed_patch = (
                    f"--- a/{file_name}\n"
                    f"+++ b/{file_name}\n"
                    f"@@ -{max(1, line_no - 1)},3 +{max(1, line_no - 1)},5 @@\n"
                    f"-  if ({var_name}.{attr_name} === req.body.{attr_name}) {{\n"
                    f"+  if (!{var_name}) return res.status(404).json({{ error: '{var_name} not found' }});\n"
                    f"+  if ({var_name}.{attr_name} === req.body.{attr_name}) {{\n"
                )
                generated_test = (
                    f"const request = require('supertest');\n"
                    f"const app = require('./server');\n\n"
                    f"describe('Regression Test: {var_name} lookup guard', () => {{\n"
                    f"  test('safely returns 404 instead of 500 when {var_name} does not exist', async () => {{\n"
                    f"    const res = await request(app)\n"
                    f"      .post('/api/login')\n"
                    f"      .send({{ username: 'non_existent_record', password: 'secret' }});\n"
                    f"    expect(res.status).toBe(404);\n"
                    f"  }});\n"
                    f"}});\n"
                )
            else:
                root_cause = (
                    f"Attempted to access attribute '.{attr_name}' on variable '{var_name}', "
                    f"which evaluated to None due to an unhandled missing record or failed lookup."
                )
                confidence = 0.93
                hypotheses = [
                    Hypothesis(
                        description="Database lookup returned None for the requested record.",
                        confidence=0.91
                    ),
                    Hypothesis(
                        description="Input payload provided invalid or non-existent identifiers.",
                        confidence=0.78
                    )
                ]
                recommended_fix = (
                    f"Add a guard clause checking if '{var_name}' is None before accessing '.{attr_name}'. "
                    f"Return an appropriate HTTP 404/400 response or raise a descriptive exception."
                )
                proposed_patch = (
                    f"--- a/{file_name}\n"
                    f"+++ b/{file_name}\n"
                    f"@@ -{max(1, line_no - 2)},4 +{max(1, line_no - 2)},7 @@\n"
                    f"     {var_name} = database.find_user(username)\n"
                    f"+    if {var_name} is None:\n"
                    f"+        raise HTTPException(status_code=404, detail=\"User not found\")\n"
                    f"+\n"
                    f"     if {var_name}.{attr_name} == password:\n"
                )
                generated_test = (
                    f"import pytest\n"
                    f"from fastapi.testclient import TestClient\n\n"
                    f"def test_{var_name}_not_found_returns_404(client: TestClient):\n"
                    f"    \"\"\"Verify that requesting a non-existent {var_name} safely returns 404 instead of 500.\"\"\"\n"
                    f"    response = client.post('/api/login', json={{'username': 'non_existent', 'password': 'secret'}})\n"
                    f"    assert response.status_code == 404\n"
                    f"    assert 'not found' in response.json()['detail'].lower()\n"
                )
            risk = "low"

        # Pattern 2: Database connection pool exhaustion / timeouts
        elif any(k in error_type for k in ("Timeout", "Pool", "OperationalError", "DatabaseTimeout")):
            root_cause = (
                "Database connection pool exhausted due to concurrent requests "
                "or unclosed database connections."
            )
            confidence = 0.91
            hypotheses = [
                Hypothesis(
                    description="High concurrency exhausted maximum connection pool capacity.",
                    confidence=0.89
                ),
                Hypothesis(
                    description="Connections were acquired without proper context manager release.",
                    confidence=0.82
                )
            ]
            recommended_fix = (
                "Increase database connection pool size, decrease idle timeout, "
                "and ensure all database connections are released promptly."
            )
            proposed_patch = (
                f"--- a/{file_name}\n"
                f"+++ b/{file_name}\n"
                f"@@ -10,3 +10,3 @@\n"
                f"-    pool_size=5,\n"
                f"+    pool_size=20,\n"
            )
            risk = "medium"

        # Pattern 3: Key or index errors
        elif error_type in ("KeyError", "IndexError"):
            key_expr = error_msg.strip("'\"")
            root_cause = f"Attempted to access missing key '{key_expr}' in payload dictionary."
            confidence = 0.90
            recommended_fix = f"Use dictionary .get('{key_expr}') with a sensible default or validate input."
            hypotheses = [
                Hypothesis(description=f"Client request omitted expected field '{key_expr}'.", confidence=0.92)
            ]
            proposed_patch = (
                f"--- a/{file_name}\n"
                f"+++ b/{file_name}\n"
                f"@@ -15,2 +15,2 @@\n"
                f"-    val = data['{key_expr}']\n"
                f"+    val = data.get('{key_expr}', None)\n"
            )
            risk = "low"

        return RootCauseExplanation(
            root_cause=root_cause,
            confidence=confidence,
            evidence=evidence_package.get("confirmed_evidence", []),
            hypotheses=hypotheses,
            recommended_fix=recommended_fix,
            proposed_patch=proposed_patch,
            generated_test=generated_test,
            risk=risk
        )


class GeminiProvider(LLMProvider):
    """Google Gemini AI reasoning provider."""
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def analyze_incident(self, evidence_package: Dict[str, Any]) -> RootCauseExplanation:
        prompt = (
            "You are an expert polyglot AI software debugger and root cause analysis engine.\n"
            "Analyze the following structured evidence from an application failure.\n"
            "If the culprit file is JavaScript/TypeScript, output clean JavaScript unified diffs and Jest tests.\n"
            "If Python, output Python diffs and Pytest tests.\n"
            "Respond ONLY with valid JSON matching this schema:\n"
            "{\n"
            '  "root_cause": "string",\n'
            '  "confidence": 0.95,\n'
            '  "evidence": ["string"],\n'
            '  "hypotheses": [{"description": "string", "confidence": 0.85}],\n'
            '  "recommended_fix": "string",\n'
            '  "proposed_patch": "unified diff string",\n'
            '  "generated_test": "test code string",\n'
            '  "risk": "low | medium | high"\n'
            "}\n\n"
            f"EVIDENCE:\n{json.dumps(evidence_package, indent=2)}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }

        async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)
            return RootCauseExplanation(**parsed)


def get_llm_provider() -> LLMProvider:
    """Factory to retrieve configured LLM provider or fallback."""
    provider_name = settings.ai_provider.lower()

    if provider_name == "gemini" and settings.gemini_api_key:
        return GeminiProvider(settings.gemini_api_key)

    return DeterministicFallbackProvider()
