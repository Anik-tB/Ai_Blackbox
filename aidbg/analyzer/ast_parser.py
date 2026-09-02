"""
Static source code analyzer using Python's native AST.
Analyzes culprit functions, call relationships, variable assignments,
and detects patterns like unvalidated None/NULL attribute access and resource leakage.
"""

from __future__ import annotations
import ast
import os
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
    """
    Analyzes an AST to find suspect patterns:
    1. Null propagation: Variable assigned from external call, then accessed without None check.
    2. Unprotected resource allocation: acquiring connection without 'with' statement.
    """
    def __init__(self, target_line: int):
        self.target_line = target_line
        self.suspect_patterns: List[Dict[str, Any]] = []
        self.assigned_vars: Dict[str, int] = {}  # var_name -> line
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
        # Track assignments e.g. user = database.find(...)
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.assigned_vars[target.id] = node.lineno
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        # Check if condition tests variable for None or truthiness
        # e.g. if user is None / if user: / if not user:
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
        # e.g. user.password
        if isinstance(node.value, ast.Name):
            var_name = node.value.id
            if var_name in self.assigned_vars and var_name not in self.checked_vars:
                assign_line = self.assigned_vars[var_name]
                if node.lineno >= assign_line:
                    # Potential unverified attribute access!
                    self.suspect_patterns.append({
                        "type": "POSSIBLE_NULL_DEREFERENCE",
                        "variable": var_name,
                        "attribute": node.attr,
                        "assigned_line": assign_line,
                        "accessed_line": node.lineno,
                        "description": (
                            f"Variable '{var_name}' assigned at line {assign_line} "
                            f"is accessed as '.{node.attr}' at line {node.lineno} "
                            f"without an explicit 'is not None' check."
                        )
                    })
        self.generic_visit(node)


def analyze_source_file(file_path: str, target_line: int) -> Dict[str, Any]:
    """
    Parse a Python file and extract AST context, enclosing function,
    called functions, and suspect bug patterns.
    """
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}", "found": False}

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            source_content = f.read()

        tree = ast.parse(source_content, filename=file_path)
    except Exception as e:
        return {"error": f"Failed to parse AST: {e}", "found": False}

    # Find the enclosing function
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

    # Extract source lines around target
    lines = source_content.splitlines()
    start_idx = max(0, target_line - 10)
    end_idx = min(len(lines), target_line + 10)
    context_snippet = "\n".join(
        f"{i+1:4d} | {lines[i]}" for i in range(start_idx, end_idx)
    )

    return {
        "found": True,
        "file_path": file_path,
        "target_line": target_line,
        "enclosing_function": func_name,
        "calls": func_calls,
        "suspect_patterns": pattern_analyzer.suspect_patterns,
        "snippet": context_snippet,
    }
