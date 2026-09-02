import os
import tempfile
import pytest
from aidbg.analyzer.ast_parser import analyze_source_file


def test_ast_null_dereference_detection():
    # Sample buggy code with NULL return followed by attribute access
    code = """
def login(username, password):
    user = database.find_user(username)
    if user.password == password:
        return create_token(user)
    return None
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_path = f.name

    try:
        result = analyze_source_file(temp_path, target_line=4)
        assert result["found"] is True
        assert result["enclosing_function"] == "login"
        assert len(result["suspect_patterns"]) > 0
        p = result["suspect_patterns"][0]
        assert p["type"] == "POSSIBLE_NULL_DEREFERENCE"
        assert p["variable"] == "user"
        assert p["attribute"] == "password"
    finally:
        os.remove(temp_path)


def test_ast_safe_code_no_false_positive():
    # Safe code with guard check
    code = """
def login(username, password):
    user = database.find_user(username)
    if user is None:
        return None
    if user.password == password:
        return create_token(user)
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_path = f.name

    try:
        result = analyze_source_file(temp_path, target_line=6)
        assert result["found"] is True
        # Since 'user' is checked via 'if user is None', no suspect pattern should be flagged
        assert len(result["suspect_patterns"]) == 0
    finally:
        os.remove(temp_path)
