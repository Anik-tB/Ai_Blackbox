"""
OpenTelemetry and web framework instrumentation for aidbg.
Provides FastAPI middleware and OpenTelemetry span propagation.
"""

from __future__ import annotations
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

from aidbg.agent.collector import capture_exception
from aidbg.agent.context import (
    add_breadcrumb,
    clear_context,
    set_request_context,
    set_trace_ids,
)

# Try importing opentelemetry; if not installed, fail-open with stubs
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    HAS_OTEL = True
except ImportError:
    trace = None
    HAS_OTEL = False


@contextmanager
def span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Context manager to trace an execution block.
    Integrates with OpenTelemetry if available, else tracks local breadcrumbs.
    """
    start_time = time.time()
    add_breadcrumb(f"Started span: {name}", category="span", data=attributes)
    otel_span = None

    if HAS_OTEL and trace:
        tracer = trace.get_tracer("aidbg.agent")
        otel_span = tracer.start_span(name, attributes=attributes)
        ctx = otel_span.get_span_context()
        if ctx and ctx.is_valid:
            set_trace_ids(
                format(ctx.trace_id, "032x"),
                format(ctx.span_id, "016x")
            )

    try:
        yield otel_span
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000.0
        if otel_span:
            otel_span.record_exception(exc)
            otel_span.set_status(Status(StatusCode.ERROR, str(exc)))
        add_breadcrumb(
            f"Span failed: {name} ({str(exc)})",
            category="span_error",
            level="error",
            data={"duration_ms": duration_ms}
        )
        raise exc
    finally:
        duration_ms = (time.time() - start_time) * 1000.0
        if otel_span:
            otel_span.end()
        add_breadcrumb(f"Ended span: {name}", category="span", data={"duration_ms": duration_ms})


class AidbgFastAPIMiddleware:
    """
    ASGI middleware for FastAPI and Starlette.
    Automatically captures request context, latency, and any uncaught exceptions.
    """
    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        query_string = scope.get("query_string", b"").decode("utf-8", errors="replace")
        client = scope.get("client")
        client_ip = client[0] if client else None

        # Headers extraction
        headers_raw = scope.get("headers", [])
        headers = {}
        for k, v in headers_raw:
            try:
                headers[k.decode("latin1")] = v.decode("latin1")
            except Exception:
                pass

        set_request_context(
            method=method,
            path=path,
            headers=headers,
            client_ip=client_ip,
            query_params={"query": query_string} if query_string else {}
        )
        add_breadcrumb(f"HTTP {method} {path}", category="http_request")

        # Response tracking wrapper
        status_code = 200

        async def send_wrapper(message: Dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000.0
            capture_exception(extra={"duration_ms": duration_ms, "http_status": 500})
            raise exc
        finally:
            clear_context()
