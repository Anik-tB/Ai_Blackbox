"""
Incident fingerprinting and error deduplication.
Normalizes stack traces, strips dynamic elements (memory addresses, timestamps, UUIDs),
and computes a stable 6-character uppercase hex hash (e.g. A7F82C).
"""

from __future__ import annotations
import hashlib
import os
import re
from typing import Any, Dict, List

# Regex to strip dynamic identifiers from error messages
HEX_ADDR_RE = re.compile(r"0x[0-9a-fA-F]+")
UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
NUMBER_RE = re.compile(r"\b\d+\b")
QUOTED_STR_RE = re.compile(r"['\"][^'\"]*['\"]")


def normalize_error_message(message: str) -> str:
    """Normalize dynamic values out of an error message."""
    if not message:
        return ""
    norm = HEX_ADDR_RE.sub("0xADDR", message)
    norm = UUID_RE.sub("UUID", norm)
    # Don't strip single digits if they are part of common messages, but normalize numbers
    norm = NUMBER_RE.sub("N", norm)
    return norm.strip()


def normalize_path(path: str) -> str:
    """Extract relative module filename, stripping absolute directories."""
    if not path or path.startswith("<"):
        return path
    parts = path.replace("\\", "/").split("/")
    # Keep last 2 components e.g. "api/auth.py"
    if len(parts) >= 2:
        return "/".join(parts[-2:])
    return parts[-1]


def compute_fingerprint(error_type: str, frames: List[Dict[str, Any]], error_message: str = "") -> str:
    """
    Generate a deterministic, normalized fingerprint for an incident.
    Returns a 6-character uppercase hex string e.g. 'A7F82C'.
    """
    hasher = hashlib.sha256()
    hasher.update(error_type.strip().encode("utf-8"))

    # Include normalized frames
    for frame in frames:
        norm_file = normalize_path(frame.get("filename", ""))
        func = frame.get("function", "")
        # Omit line numbers to ensure line shifts do not fragment incidents
        frame_sig = f"{norm_file}:{func}"
        hasher.update(frame_sig.encode("utf-8"))

    # Include normalized error message pattern
    norm_msg = normalize_error_message(error_message)
    hasher.update(norm_msg.encode("utf-8"))

    digest = hasher.hexdigest().upper()
    return digest[:6]


def calculate_severity(error_type: str, occurrence_count: int = 1) -> str:
    """
    Determine incident severity based on error characteristics and frequency.
    Options: CRITICAL, HIGH, MEDIUM, LOW
    """
    critical_types = {"DatabaseTimeout", "ConnectionRefusedError", "OperationalError",
                      "MemoryError", "SystemError", "CriticalError"}
    high_types = {"NullPointerException", "AttributeError", "KeyError", "TypeError",
                  "ZeroDivisionError", "IndexError"}

    if error_type in critical_types or occurrence_count > 500:
        return "CRITICAL"
    if error_type in high_types or occurrence_count > 50:
        return "HIGH"
    if occurrence_count > 10:
        return "MEDIUM"
    return "LOW"
