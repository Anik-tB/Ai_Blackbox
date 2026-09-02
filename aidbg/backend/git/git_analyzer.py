"""
Git repository analyzer for AIBD.
Inspects recent commits, blame history, diffs, and correlates changes with incidents.
"""

from __future__ import annotations
import os
import subprocess
from typing import Any, Dict, List, Optional


def run_git(args: List[str], repo_path: str = ".") -> Optional[str]:
    """Execute a git command safely within repo_path."""
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5.0
        )
        if res.returncode == 0:
            return res.stdout.strip()
        return None
    except Exception:
        return None


def get_recent_commits(repo_path: str = ".", limit: int = 5, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve recent commits, optionally filtered by a specific file."""
    cmd = ["log", f"-n{limit}", "--pretty=format:%H|%an|%ae|%at|%s"]
    if file_path:
        rel_path = os.path.relpath(file_path, repo_path) if os.path.isabs(file_path) else file_path
        cmd.extend(["--", rel_path])

    out = run_git(cmd, repo_path=repo_path)
    if not out:
        return []

    commits: List[Dict[str, Any]] = []
    for line in out.splitlines():
        parts = line.split("|", 4)
        if len(parts) == 5:
            c_hash, author, email, timestamp, msg = parts
            commits.append({
                "hash": c_hash[:8],
                "full_hash": c_hash,
                "author": author,
                "email": email,
                "timestamp": float(timestamp) if timestamp.isdigit() else 0.0,
                "message": msg,
            })
    return commits


def get_line_blame(file_path: str, line_no: int, repo_path: str = ".") -> Optional[Dict[str, Any]]:
    """Inspect git blame for a specific line number in a file."""
    if not os.path.exists(file_path):
        return None

    rel_path = os.path.relpath(file_path, repo_path) if os.path.isabs(file_path) else file_path
    out = run_git(["blame", "-L", f"{line_no},{line_no}", "--porcelain", rel_path], repo_path=repo_path)
    if not out:
        return None

    lines = out.splitlines()
    if not lines:
        return None

    commit_hash = lines[0].split()[0][:8]
    author = "unknown"
    summary = ""
    for l in lines[1:]:
        if l.startswith("author "):
            author = l.replace("author ", "", 1)
        elif l.startswith("summary "):
            summary = l.replace("summary ", "", 1)

    return {
        "commit": commit_hash,
        "author": author,
        "summary": summary,
        "line": line_no,
        "file": rel_path
    }


def get_commit_diff(commit_hash: str, repo_path: str = ".") -> Optional[str]:
    """Get the diff patch of a given commit."""
    return run_git(["show", "--stat", "-p", commit_hash], repo_path=repo_path)


def correlate_changes(incident_time: float, culprit_file: str, culprit_line: int,
                      repo_path: str = ".") -> List[Dict[str, Any]]:
    """
    Find commits potentially related to the incident and score confidence.
    """
    related: List[Dict[str, Any]] = []

    # 1. Check line blame
    blame = get_line_blame(culprit_file, culprit_line, repo_path=repo_path)
    if blame:
        diff_text = get_commit_diff(blame["commit"], repo_path=repo_path)
        related.append({
            "commit": blame["commit"],
            "message": blame["summary"],
            "author": blame["author"],
            "relation": "Last modified the failing line directly",
            "confidence": 0.88,
            "diff": diff_text[:1500] if diff_text else ""
        })

    # 2. Check recent commits touching the file
    recent = get_recent_commits(repo_path=repo_path, limit=3, file_path=culprit_file)
    for c in recent:
        if blame and c["hash"] == blame["commit"]:
            continue
        diff_text = get_commit_diff(c["hash"], repo_path=repo_path)
        related.append({
            "commit": c["hash"],
            "message": c["message"],
            "author": c["author"],
            "relation": f"Modified {os.path.basename(culprit_file)} recently",
            "confidence": 0.65,
            "diff": diff_text[:1500] if diff_text else ""
        })

    return related
