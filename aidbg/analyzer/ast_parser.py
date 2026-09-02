"""
Polyglot Source Code & AST Analyzer.
Supports Python (native AST), JavaScript/TypeScript (static inspection),
and Universal Source Reader for all other languages (Go, Rust, Java, C++, Ruby, PHP).
"""

from __future__ import annotations
import ast
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class FunctionCallVisitor(ast.NodeVisitor):
    """Collects all function calls within a node."""
    def __init__(self):
        self.calls: List[str] = []

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            self.calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            val_name = ""
            if isinstance(node.func.value, ast.Name):
                val_name = f"{node.func.value.id}."
            self.calls.append(f"{val_name}{node.func.attr}")
        self.generic_visit(node)


class CodePatternAnalyzer(ast.NodeVisitor):
    """Analyzes a Python AST to find suspect bug patterns."""
    def __init__(self, target_line: int):
        self.target_line = target_line
        self.suspect_patterns: List[Dict[str, Any]] = []
        self.assigned_vars: Dict[str, int] = {}
        self.checked_vars: Set[str] = set()
        self.current_function: Optional[str] = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev_func

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        prev_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev_func

    def visit_Assign(self, node: ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.assigned_vars[target.id] = node.lineno
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        self._record_checked_vars(node.test)
        self.generic_visit(node)

    def _record_checked_vars(self, test_node: ast.AST):
        if isinstance(test_node, ast.Name):
            self.checked_vars.add(test_node.id)
        elif isinstance(test_node, ast.UnaryOp) and isinstance(test_node.operand, ast.Name):
            self.checked_vars.add(test_node.operand.id)
        elif isinstance(test_node, ast.Compare):
            if isinstance(test_node.left, ast.Name):
                self.checked_vars.add(test_node.left.id)
            for comparator in test_node.comparators:
                if isinstance(comparator, ast.Name):
                    self.checked_vars.add(comparator.id)

    def visit_Attribute(self, node: ast.Attribute):
        if isinstance(node.value, ast.Name):
            var_name = node.value.id
            if var_name in self.assigned_vars and var_name not in self.checked_vars:
                assign_line = self.assigned_vars[var_name]
                if node.lineno >= assign_line:
                    self.suspect_patterns.append({
                        "type": "POSSIBLE_NULL_DEREFERENCE",
                        "variable": var_name,
                        "attribute": node.attr,
                        "assigned_line": assign_line,
                        "accessed_line": node.lineno,
                        "description": (
                            f"Variable '{var_name}' assigned at line {assign_line} is accessed as "
                            f"'.{node.attr}' at line {node.lineno} without an explicit 'is not None' check."
                        )
                    })
        self.generic_visit(node)


def analyze_javascript_file(file_path: str, target_line: int) -> Dict[str, Any]:
    """Static inspection for JavaScript/TypeScript files."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        return {"error": str(e), "found": False}

    suspect_patterns = []
    enclosing_func = "module_scope"
    func_calls = []

    # Find surrounding context
    target_idx = target_line - 1
    if 0 <= target_idx < len(lines):
        failing_line = lines[target_idx].strip()

        # Check for property dereferences without optional chaining
        matches = re.findall(r"([a-zA-Z0-9_\$]+)\.([a-zA-Z0-9_\$]+)", failing_line)
        for obj, prop in matches:
            if obj not in ["console", "process", "Math", "JSON", "Object", "Array", "Promise", "this", "res", "req"]:
                suspect_patterns.append({
                    "type": "POSSIBLE_UNDEFINED_DEREFERENCE",
                    "variable": obj,
                    "property": prop,
                    "description": f"Object '{obj}' accessed property '.{prop}' without null check or optional chaining (?.)."
                })

        # Check for unhandled Promise / await
        if "await" in failing_line:
            suspect_patterns.append({
                "type": "ASYNC_AWAIT_EXECUTION",
                "description": "Asynchronous operation with await; check for rejected Promise without try/catch."
            })

    # Search upwards for enclosing function or Express route
    for i in range(min(target_line, len(lines)) - 1, -1, -1):
        line = lines[i].strip()
        route_match = re.search(r"\b(app|router)\.(get|post|put|delete|patch|use)\s*\(\s*['\"]([^'\"]+)['\"]", line)
        if route_match:
            enclosing_func = f"{route_match.group(2).upper()} {route_match.group(3)}"
            break
        fn_match = re.search(r"(?:function\s+([a-zA-Z0-9_\$]+)|(?:const|let|var)\s+([a-zA-Z0-9_\$]+)\s*=\s*(?:async\s*)?\()", line)
        if fn_match:
            enclosing_func = fn_match.group(1) or fn_match.group(2)
            break

    start_idx = max(0, target_line - 10)
    end_idx = min(len(lines), target_line + 10)
    context_snippet = "\n".join(f"{i+1:4d} | {lines[i].rstrip()}" for i in range(start_idx, end_idx))

    return {
        "found": True,
        "language": "javascript",
        "file_path": file_path,
        "target_line": target_line,
        "enclosing_function": enclosing_func,
        "calls": func_calls,
        "suspect_patterns": suspect_patterns,
        "snippet": context_snippet,
    }


def analyze_generic_source_file(file_path: str, target_line: int) -> Dict[str, Any]:
    """Universal source snippet reader for Go, Rust, Java, C++, Ruby, PHP."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        return {"error": str(e), "found": False}

    start_idx = max(0, target_line - 10)
    end_idx = min(len(lines), target_line + 10)
    context_snippet = "\n".join(f"{i+1:4d} | {lines[i].rstrip()}" for i in range(start_idx, end_idx))

    return {
        "found": True,
        "language": Path(file_path).suffix.lstrip("."),
        "file_path": file_path,
        "target_line": target_line,
        "enclosing_function": "main_or_enclosing_block",
        "calls": [],
        "suspect_patterns": [],
        "snippet": context_snippet,
    }


def analyze_source_file(file_path: str, target_line: int) -> Dict[str, Any]:
    """
    Polyglot source file analyzer.
    Delegates to Python AST, JavaScript inspector, or Universal source reader based on extension.
    """
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}", "found": False}

    ext = Path(file_path).suffix.lower()

    # 1. JavaScript & TypeScript
    if ext in [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]:
        return analyze_javascript_file(file_path, target_line)

    # 2. Non-Python Generic Languages
    if ext not in [".py", ".pyw"]:
        return analyze_generic_source_file(file_path, target_line)

    # 3. Python native AST
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            source_content = f.read()
        tree = ast.parse(source_content, filename=file_path)
    except Exception as e:
        return {"error": f"Failed to parse AST: {e}", "found": False}

    enclosing_func: Optional[ast.FunctionDef] = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                if node.lineno <= target_line <= (node.end_lineno or target_line):
                    enclosing_func = node
                    break

    func_name = enclosing_func.name if enclosing_func else "module_level"
    func_calls: List[str] = []
    if enclosing_func:
        visitor = FunctionCallVisitor()
        visitor.visit(enclosing_func)
        func_calls = visitor.calls

    pattern_analyzer = CodePatternAnalyzer(target_line)
    if enclosing_func:
        pattern_analyzer.visit(enclosing_func)
    else:
        pattern_analyzer.visit(tree)

    lines = source_content.splitlines()
    start_idx = max(0, target_line - 10)
    end_idx = min(len(lines), target_line + 10)
    context_snippet = "\n".join(
        f"{i+1:4d} | {lines[i]}" for i in range(start_idx, end_idx)
    )

    return {
        "found": True,
        "language": "python",
        "file_path": file_path,
        "target_line": target_line,
        "enclosing_function": func_name,
        "calls": func_calls,
        "suspect_patterns": pattern_analyzer.suspect_patterns,
        "snippet": context_snippet,
    }
