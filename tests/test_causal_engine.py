import pytest
from aidbg.analyzer.causal_engine import CausalGraphBuilder, build_evidence_package, synthesize_causal_chain


def test_causal_graph_builder():
    builder = CausalGraphBuilder()
    builder.add_event("evt1", "Traffic Increase +38%", node_type="anomaly")
    builder.add_event("evt2", "DB Queries +51%", node_type="anomaly")
    builder.add_event("evt3", "Connection Pool 100%", node_type="anomaly")
    builder.add_causal_edge("evt1", "evt2", reason="Higher request rate triggered more queries", confidence=0.92)
    builder.add_causal_edge("evt2", "evt3", reason="Queries exhausted pool", confidence=0.95)

    graph_dict = builder.to_dict()
    assert len(graph_dict["nodes"]) == 3
    assert len(graph_dict["edges"]) == 2
    assert graph_dict["edges"][0]["from"] == "evt1"
    assert graph_dict["edges"][0]["confidence"] == 0.92


def test_synthesize_causal_chain():
    evidence = {
        "error_type": "AttributeError",
        "error_message": "'NoneType' object has no attribute 'password'",
        "request": {"method": "POST", "path": "/api/login"},
        "ast_analysis": {
            "suspect_patterns": [{
                "variable": "user",
                "attribute": "password",
                "assigned_line": 3,
                "accessed_line": 4
            }]
        },
        "git_correlation": []
    }
    graph_dict, steps = synthesize_causal_chain(evidence)
    assert len(graph_dict["nodes"]) >= 3
    assert len(steps) >= 2
    # Verify chain flow contains the null check and exception
    step_texts = " ".join(s["to"] for s in steps)
    assert "user is None" in step_texts or "Access" in step_texts
