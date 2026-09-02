"""
Fail-open background transport for aidbg agent.
Guarantees that telemetry ingestion failure NEVER affects the host application.
"""

from __future__ import annotations
import atexit
import json
import logging
import queue
import threading
import time
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger("aidbg.agent.transport")


class CircuitBreaker:
    """Simple circuit breaker to avoid hammering backend if down."""
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 10.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def allow_request(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True  # HALF_OPEN allows trial


class Transport:
    """
    Asynchronous, non-blocking fail-open event transport.
    Events are enqueued into an in-memory bounded queue and dispatched
    by a dedicated background worker thread.
    """
    def __init__(self, endpoint_url: str = "http://127.0.0.1:8765/api/v1/incidents/ingest",
                 max_queue_size: int = 1000, timeout: float = 1.5):
        self.endpoint_url = endpoint_url
        self.queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self.timeout = timeout
        self.circuit_breaker = CircuitBreaker()
        self.running = True
        self.dropped_events = 0
        self.thread = threading.Thread(target=self._worker_loop, daemon=True, name="aidbg-transport")
        self.thread.start()
        atexit.register(self.shutdown)

    def send_event(self, event: Dict[str, Any]) -> bool:
        """
        Enqueue an event. Returns True if queued, False if dropped due to full queue.
        Guaranteed to never raise an exception.
        """
        try:
            self.queue.put_nowait(event)
            return True
        except queue.Full:
            self.dropped_events += 1
            return False
        except Exception:
            return False

    def _worker_loop(self) -> None:
        # Create a dedicated HTTP client with short timeouts
        with httpx.Client(timeout=self.timeout) as client:
            while self.running:
                try:
                    try:
                        event = self.queue.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    if not self.circuit_breaker.allow_request():
                        # Backend down; drop event safely
                        self.dropped_events += 1
                        self.queue.task_done()
                        continue

                    try:
                        resp = client.post(self.endpoint_url, json=event)
                        if resp.status_code in (200, 201, 202):
                            self.circuit_breaker.record_success()
                        else:
                            self.circuit_breaker.record_failure()
                    except Exception:
                        self.circuit_breaker.record_failure()
                    finally:
                        self.queue.task_done()

                except Exception:
                    # Absolute fail-open safety
                    pass

    def flush(self, timeout: float = 1.0) -> None:
        """Attempt to flush remaining items within timeout."""
        start = time.time()
        while not self.queue.empty() and (time.time() - start) < timeout:
            time.sleep(0.05)

    def shutdown(self) -> None:
        """Gracefully stop background worker."""
        self.flush(timeout=0.5)
        self.running = False


# Global default transport singleton
_default_transport: Optional[Transport] = None


def get_transport() -> Transport:
    global _default_transport
    if _default_transport is None:
        _default_transport = Transport()
    return _default_transport


def set_transport(transport: Transport) -> None:
    global _default_transport
    _default_transport = transport
