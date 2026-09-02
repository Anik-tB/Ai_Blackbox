import pytest
from aidbg.agent.redaction import redact_string, sanitize_data, is_sensitive_key, REDACTED_STR


def test_sensitive_keys():
    assert is_sensitive_key("password")
    assert is_sensitive_key("db_password")
    assert is_sensitive_key("auth_token")
    assert is_sensitive_key("api_key")
    assert is_sensitive_key("STRIPE_SECRET")
    assert not is_sensitive_key("username")
    assert not is_sensitive_key("status_code")


def test_sanitize_dict_keys():
    payload = {
        "user_id": 123,
        "username": "alice",
        "password": "super_secret_password_123",
        "nested": {
            "token": "secret_jwt_xyz",
            "normal_field": "visible_value"
        }
    }
    sanitized = sanitize_data(payload)
    assert sanitized["user_id"] == 123
    assert sanitized["username"] == "alice"
    assert sanitized["password"] == REDACTED_STR
    assert sanitized["nested"]["token"] == REDACTED_STR
    assert sanitized["nested"]["normal_field"] == "visible_value"


def test_redact_patterns_in_string():
    bearer = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeak"
    redacted = redact_string(bearer)
    assert REDACTED_STR in redacted
    assert "eyJhbGciOiJIUzI1Ni" not in redacted

    sk_key = "Using key sk-1234567890abcdef1234567890 for API"
    assert redact_string(sk_key) == f"Using key {REDACTED_STR} for API"


def test_sanitize_depth_limit():
    deep = {}
    curr = deep
    for i in range(10):
        curr["next"] = {}
        curr = curr["next"]
    
    sanitized = sanitize_data(deep, max_depth=4)
    assert isinstance(sanitized, dict)
