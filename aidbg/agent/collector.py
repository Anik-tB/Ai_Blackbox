"""
Exception collector for aidbg.
Intercepts unhandled exceptions via sys.excepthook, threading, and asyncio,
safely extracts stack frames, local variables, and context, and forwards to transport.
Guarantees FAIL-OPEN behavior: NEVER crashes the monitored application.
"""

from __future__ import annotations
import asyncio
import functools
import linecache
import os
import platform
import socket
import sys
import threading
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from aidbg.agent.context import (
    get_breadcrumbs,
    get_request_context,
    get_tags,
    get_trace_ids,
    set_tag,
)
from aidbg.agent.redaction import sanitize_data
from aidbg.agent.transport import get_transport

_original_excepthook = sys.excepthook
_original_threading_excepthook = getattr(threading, "excepthook", None)
_is_initialized = False


def extract_stack_frames(tb: Any) -> List[Dict[str, Any]]:
    """
    Extract structured stack frames from a traceback, including
    code context and local variables.
    """
    frames: List[Dict[str, Any]] = []
    curr = tb
    while curr is not None:
        frame = curr.tb_frame
        lineno = curr.tb_lineno
        code = frame.f_code
        filename = code.co_filename
        func_name = code.co_name

        # Extract local variables with redaction and size limits
        locals_dict: Dict[str, Any] = {}
        try:
            for k, v in frame.f_locals.items():
                if k.startswith("__") and k.endswith("__"):
                    continue
                locals_dict[k] = sanitize_data(v, max_depth=3)
        except Exception:
            locals_dict["[ERROR]"] = "Failed to inspect locals"

        # Surrounding source code context
        pre_context: List[str] = []
        context_line: str = ""
        post_context: List[str] = []
        try:
            for i in range(max(1, lineno - 5), lineno):
                line = linecache.getline(filename, i)
                if line:
                    pre_context.append(line.rstrip())
            context_line = linecache.getline(filename, lineno).rstrip()
            for i in range(lineno + 1, lineno + 6):
                line = linecache.getline(filename, i)
                if line:
                    post_context.append(line.rstrip())
        except Exception:
            pass

        frames.append({
            "filename": filename,
            "lineno": lineno,
            "function": func_name,
            "code_line": context_line,
            "pre_context": pre_context,
            "post_context": post_context,
            "locals": locals_dict,
        })
        curr = curr.tb_next

    return frames


def build_error_payload(exc_type: Type[BaseException], exc_value: BaseException,
                        exc_traceback: Any, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Construct a clean, sanitized error event dictionary."""
    trace_id, span_id = get_trace_ids()
    frames = extract_stack_frames(exc_traceback)

    # Culprit source location (the innermost frame)
    culprit_file = frames[-1]["filename"] if frames else "unknown"
    culprit_func = frames[-1]["function"] if frames else "unknown"
    culprit_line = frames[-1]["lineno"] if frames else 0

    return {
        "error_type": exc_type.__name__ if hasattr(exc_type, "__name__") else str(exc_type),
        "error_message": sanitize_data(str(exc_value)),
        "culprit": f"{culprit_file}:{culprit_func}:{culprit_line}",
        "timestamp": time.time(),
        "frames": frames,
        "trace_id": trace_id,
        "span_id": span_id,
        "tags": get_tags(),
        "request": get_request_context(),
        "breadcrumbs": get_breadcrumbs(),
        "extra": sanitize_data(extra) if extra else {},
        "system": {
            "hostname": socket.gethostname(),
            "os": platform.system(),
            "python_version": platform.python_version(),
            "pid": os.getpid(),
        }
    }


def capture_exception(exc_info: Optional[Tuple[Type[BaseException], BaseException, Any]] = None,
                      extra: Optional[Dict[str, Any]] = None) -> bool:
    """
    Capture an exception manually or from sys.exc_info().
    Returns True if captured and dispatched, False otherwise.
    Guaranteed FAIL-OPEN: Will never raise an exception.
    """
    try:
        if exc_info is None:
            exc_info = sys.exc_info()
        exc_type, exc_value, exc_tb = exc_info

        if exc_type is None or exc_value is None:
            return False

        # Ignore SystemExit and KeyboardInterrupt
        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            return False

        payload = build_error_payload(exc_type, exc_value, exc_tb, extra)
        return get_transport().send_event(payload)
    except Exception:
        # Fail-open guarantee
        return False


def _aidbg_excepthook(exc_type: Type[BaseException], exc_value: BaseException, exc_traceback: Any) -> None:
    """sys.excepthook override that reports to aidbg then delegates to original hook."""
    try:
        capture_exception((exc_type, exc_value, exc_traceback))
    except Exception:
        pass
    if _original_excepthook:
        _original_excepthook(exc_type, exc_value, exc_traceback)


def _aidbg_threading_excepthook(args: Any) -> None:
    """threading.excepthook override."""
    try:
        capture_exception((args.exc_type, args.exc_value, args.exc_traceback))
    except Exception:
        pass
    if _original_threading_excepthook:
        _original_threading_excepthook(args)


def observe(func: Callable) -> Callable:
    """
    Decorator to monitor a function for uncaught errors while re-raising them cleanly.
    """
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                capture_exception()
                raise e
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                capture_exception()
                raise e
        return sync_wrapper


def init(endpoint_url: Optional[str] = None, service_name: str = "default-service",
         environment: str = "development") -> None:
    """
    Initialize aidbg agent, register global exception hooks, and configure transport.
    """
    global _is_initialized
    if _is_initialized:
        return

    set_tag("service", service_name)
    set_tag("environment", environment)

    if endpoint_url:
        from aidbg.agent.transport import Transport, set_transport
        set_transport(Transport(endpoint_url=endpoint_url))

    sys.excepthook = _aidbg_excepthook
    if hasattr(threading, "excepthook"):
        threading.excepthook = _aidbg_threading_excepthook

    _is_initialized = True
