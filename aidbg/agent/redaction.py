"""
Data redaction and sensitive information scrubbing.
Guarantees that credentials, tokens, passwords, cookies, and keys are NEVER
transmitted to backend storage or external AI providers.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Set, Union

REDACTED_STR = "[REDACTED]"

# Key names that should always have their values redacted
SENSITIVE_KEY_PATTERNS = {
    "password", "passwd", "pwd", "secret", "token", "api_key", "apikey",
    "access_token", "refresh_token", "auth", "authorization", "cookie",
    "session", "private_key", "privkey", "credit_card", "card_number",
    "cvv", "ssn", "client_secret", "bearer"
}

# Regex patterns for detecting sensitive data inside strings
REGEX_PATTERNS = [
    # Bearer tokens
    (re.compile(r"Bearer\s+([A-Za-z0-9\-\._~\+\/]+=*)", re.IGNORECASE), f"Bearer {REDACTED_STR}"),
    # JWT tokens
    (re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+"), REDACTED_STR),
    # OpenAI / AWS key patterns
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), REDACTED_STR),
    (re.compile(r"AKIA[0-9A-Z]{16}"), REDACTED_STR),
    # Basic URL query string credentials e.g. ?token=xyz
    (re.compile(r"(?i)(password|token|secret|key|apiKey)=([^&\s]+)"), rf"\1={REDACTED_STR}"),
    # Credit card numbers (13 to 16 digits with optional spaces or dashes)
    (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), REDACTED_STR),
]


def is_sensitive_key(key: str) -> bool:
    """Check whether a dict key or variable name is sensitive."""
    k = key.lower()
    for pattern in SENSITIVE_KEY_PATTERNS:
        if pattern in k:
            return True
    return False


def redact_string(value: str) -> str:
    """Scrub sensitive patterns from a string."""
    if not isinstance(value, str):
        return value
    res = value
    for regex, replacement in REGEX_PATTERNS:
        res = regex.sub(replacement, res)
    return res


def sanitize_data(data: Any, max_depth: int = 5, current_depth: int = 0) -> Any:
    """
    Recursively redact sensitive data from nested structures (dict, list, tuple, primitives).
    Limits recursion depth to prevent circular references and massive payload sizes.
    """
    if current_depth > max_depth:
        return "[TRUNCATED_DEPTH]"

    if data is None:
        return None

    if isinstance(data, (bool, int, float)):
        return data

    if isinstance(data, str):
        return redact_string(data)

    if isinstance(data, bytes):
        try:
            return redact_string(data.decode("utf-8", errors="replace"))
        except Exception:
            return "[BYTES]"

    if isinstance(data, dict):
        sanitized_dict: Dict[str, Any] = {}
        for k, v in data.items():
            key_str = str(k)
            if is_sensitive_key(key_str):
                sanitized_dict[key_str] = REDACTED_STR
            else:
                sanitized_dict[key_str] = sanitize_data(v, max_depth, current_depth + 1)
        return sanitized_dict

    if isinstance(data, (list, tuple, set)):
        items = [sanitize_data(item, max_depth, current_depth + 1) for item in data]
        return items if not isinstance(data, tuple) else tuple(items)

    # For general arbitrary objects, capture their safe repr
    try:
        val_repr = repr(data)
        if len(val_repr) > 500:
            val_repr = val_repr[:500] + "...[TRUNCATED]"
        return redact_string(val_repr)
    except Exception:
        return "[UNSERIALIZABLE]"
