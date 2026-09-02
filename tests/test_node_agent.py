import subprocess
import sys
import time
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from aidbg.backend.main import app

def test_node_agent_file_exists():
    agent_path = Path("aidbg/agent/node_agent.cjs")
    assert agent_path.exists(), "aidbg/agent/node_agent.cjs must exist"

def test_node_agent_syntax():
    res = subprocess.run(["node", "-c", "aidbg/agent/node_agent.cjs"], capture_output=True)
    assert res.returncode == 0, f"Node agent syntax check failed: {res.stderr.decode()}"

def test_node_agent_execution_interception(tmp_path):
    # Create a small buggy Node.js script
    buggy_js = tmp_path / "buggy.js"
    buggy_js.write_text("""
    const secretPassword = 'my_secret_123';
    let user = null;
    console.log("Before crash");
    // Trigger TypeError
    console.log(user.password);
    """)

    agent_path = Path("aidbg/agent/node_agent.cjs").resolve()
    env = {
        "NODE_OPTIONS": f"--require {agent_path}",
        "AIDBG_ENDPOINT": "http://127.0.0.1:8765/api/v1/incidents/ingest",
        "AIDBG_SERVICE": "test-node-service",
        "PATH": "/usr/local/bin:/usr/bin:/bin"
    }

    res = subprocess.run(["node", str(buggy_js)], env=env, capture_output=True, text=True)
    assert "Before crash" in res.stdout
    assert "TypeError" in res.stderr
