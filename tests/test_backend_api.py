import pytest
from httpx import AsyncClient, ASGITransport
from aidbg.backend.main import app
from aidbg.backend.database import init_db


@pytest.mark.asyncio
async def test_backend_e2e_flow():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        h_resp = await client.get("/api/v1/health")
        assert h_resp.status_code == 200
        assert h_resp.json()["status"] == "ok"

        # 2. Ingest an error event
        event_payload = {
            "error_type": "AttributeError",
            "error_message": "'NoneType' object has no attribute 'password'",
            "culprit": "app.py:login:42",
            "frames": [
                {"filename": "app.py", "function": "login", "lineno": 42, "code_line": "return user.password"}
            ],
            "tags": {"service": "auth-service"},
            "request": {"method": "POST", "path": "/api/login"},
            "breadcrumbs": [{"message": "Attempting user lookup", "category": "auth"}]
        }

        resp1 = await client.post("/api/v1/incidents/ingest", json=event_payload)
        assert resp1.status_code == 202
        data1 = resp1.json()
        assert data1["status"] == "accepted"
        inc_id = data1["incident_id"]
        assert len(inc_id) == 6

        # Ingest identical event again to test deduplication
        resp2 = await client.post("/api/v1/incidents/ingest", json=event_payload)
        assert resp2.status_code == 202
        data2 = resp2.json()
        assert data2["incident_id"] == inc_id
        assert data2["occurrences"] >= 2

        # 3. List incidents
        list_resp = await client.get("/api/v1/incidents")
        assert list_resp.status_code == 200
        incidents = list_resp.json()
        assert any(i["id"] == inc_id for i in incidents)

        # 4. Detail endpoint
        det_resp = await client.get(f"/api/v1/incidents/{inc_id}")
        assert det_resp.status_code == 200
        assert det_resp.json()["error_type"] == "AttributeError"
