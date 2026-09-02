"""
Execution and request context tracking for aidbg.
Maintains breadcrumbs, active spans, tags, and request-level telemetry.
"""

from __future__ import annotations
import contextvars
import time
from collections import deque
from typing import Any, Dict, List, Optional
from aidbg.agent.redaction import sanitize_data

_MAX_BREADCRUMBS = 50

# Request-scoped context
_current_request: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    "aidbg_current_request", default=None
)

# Active trace/span IDs
_current_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "aidbg_current_trace_id", default=None
)
_current_span_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "aidbg_current_span_id", default=None
)

# Global / service tags
_global_tags: Dict[str, Any] = {
    "service": "default-service",
    "environment": "development"
}

# Request-scoped breadcrumb deque
_current_breadcrumbs: contextvars.ContextVar[Optional[deque]] = contextvars.ContextVar(
    "aidbg_current_breadcrumbs", default=None
)


def set_tag(key: str, value: Any) -> None:
    """Set a global metadata tag for the application."""
    _global_tags[key] = sanitize_data(value)


def get_tags() -> Dict[str, Any]:
    """Retrieve a copy of global tags."""
    return dict(_global_tags)


def _get_breadcrumb_queue() -> deque:
    q = _current_breadcrumbs.get()
    if q is None:
        q = deque(maxlen=_MAX_BREADCRUMBS)
        _current_breadcrumbs.set(q)
    return q


def add_breadcrumb(message: str, category: str = "custom", level: str = "info", data: Optional[Dict[str, Any]] = None) -> None:
    """Add a breadcrumb event leading up to an error."""
    q = _get_breadcrumb_queue()
    entry = {
        "timestamp": time.time(),
        "category": category,
        "level": level,
        "message": sanitize_data(message),
        "data": sanitize_data(data) if data else {}
    }
    q.append(entry)


def get_breadcrumbs() -> List[Dict[str, Any]]:
    """Retrieve collected breadcrumbs."""
    q = _get_breadcrumb_queue()
    return list(q)


def set_request_context(method: str, path: str, headers: Optional[Dict[str, str]] = None,
                        client_ip: Optional[str] = None, query_params: Optional[Dict[str, Any]] = None) -> None:
    """Store current HTTP request context."""
    sanitized_headers = sanitize_data(headers) if headers else {}
    sanitized_params = sanitize_data(query_params) if query_params else {}
    _current_request.set({
        "method": method,
        "path": path,
        "headers": sanitized_headers,
        "client_ip": client_ip,
        "query_params": sanitized_params,
        "timestamp": time.time()
    })


def get_request_context() -> Optional[Dict[str, Any]]:
    """Retrieve current HTTP request context."""
    return _current_request.get()


def set_trace_ids(trace_id: Optional[str], span_id: Optional[str]) -> None:
    """Set active OpenTelemetry trace and span IDs."""
    _current_trace_id.set(trace_id)
    _current_span_id.set(span_id)


def get_trace_ids() -> tuple[Optional[str], Optional[str]]:
    """Get active (trace_id, span_id)."""
    return _current_trace_id.get(), _current_span_id.get()


def clear_context() -> None:
    """Reset request-scoped context variables."""
    _current_request.set(None)
    _current_trace_id.set(None)
    _current_span_id.set(None)
    _current_breadcrumbs.set(None)
