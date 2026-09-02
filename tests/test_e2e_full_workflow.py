import pytest
import os
from httpx import AsyncClient, ASGITransport
from aidbg.backend.main import app
from aidbg.backend.database import init_db, AsyncSessionLocal, Incident
from aidbg.backend.api.incidents import analyze_incident_async


@pytest.mark.asyncio
async def test_full_rca_and_fix_workflow():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Ingest an incident simulating Bug 1 from examples/buggy_app/app.py
        payload = {
            "error_type": "AttributeError",
            "error_message": "'NoneType' object has no attribute 'password'",
            "culprit": "examples/buggy_app/app.py:login:57",
            "frames": [
                {
                    "filename": os.path.abspath("examples/buggy_app/app.py"),
                    "lineno": 57,
                    "function": "login",
                    "code_line": "if user.password == req.password:"
                }
            ],
            "tags": {"service": "payment-auth-service"},
            "request": {"method": "POST", "path": "/api/login"},
            "breadcrumbs": [{"message": "Attempting login for username: ghost_user", "category": "auth"}]
        }

        resp = await client.post("/api/v1/incidents/ingest", json=payload)
        assert resp.status_code == 202
        data = resp.json()
        incident_id = data["incident_id"]

        # Run the asynchronous analyzer directly
        await analyze_incident_async(
            incident_id=incident_id,
            event_data=payload,
            culprit_file=os.path.abspath("examples/buggy_app/app.py"),
            culprit_line=57
        )

        # 2. Query explain endpoint
        explain_resp = await client.get(f"/api/v1/incidents/{incident_id}/explain")
        assert explain_resp.status_code == 200
        explanation = explain_resp.json()
        assert explanation["confidence"] >= 0.80
        assert "user" in explanation["root_cause"].lower() or "none" in explanation["root_cause"].lower()
        assert len(explanation["evidence"]) > 0

        # 3. Query fix endpoint
        fix_resp = await client.get(f"/api/v1/incidents/{incident_id}/fix")
        assert fix_resp.status_code == 200
        fix_data = fix_resp.json()
        assert fix_data["proposed_patch"] is not None
        assert "---" in fix_data["proposed_patch"]
        assert fix_data["generated_test"] is not None
        assert "def test_" in fix_data["generated_test"]
