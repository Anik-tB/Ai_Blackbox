import sys
import pytest
from aidbg.agent.collector import capture_exception, build_error_payload
from aidbg.agent.transport import Transport, set_transport
from aidbg.agent.context import add_breadcrumb, set_request_context, set_tag


class DummyTransport:
    def __init__(self):
        self.events = []
    
    def send_event(self, event):
        self.events.append(event)
        return True


def test_capture_exception_flow():
    dummy = DummyTransport()
    set_transport(dummy)

    set_tag("env", "testing")
    add_breadcrumb("Pre-failure step 1")
    set_request_context("POST", "/api/test", {"user-agent": "test-client"})

    try:
        raise ValueError("Simulated computation failure")
    except ValueError:
        success = capture_exception()
        assert success is True

    assert len(dummy.events) == 1
    event = dummy.events[0]
    assert event["error_type"] == "ValueError"
    assert "Simulated computation failure" in event["error_message"]
    assert len(event["frames"]) > 0
    assert event["tags"]["env"] == "testing"
    assert event["request"]["path"] == "/api/test"
    assert len(event["breadcrumbs"]) >= 1


def test_fail_open_when_transport_fails():
    class FailingTransport:
        def send_event(self, event):
            raise RuntimeError("Network is completely dead")

    set_transport(FailingTransport())

    # Even if transport explodes with an exception, capture_exception must return False without raising
    try:
        raise KeyError("missing_key")
    except KeyError:
        result = capture_exception()
        assert result is False
