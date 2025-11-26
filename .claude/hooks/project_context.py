#!/usr/bin/env python3
"""
Project Context Hook v3: Provide git/folder/file awareness.

Hook Type: UserPromptSubmit
Latency Target: <50ms (fast git/filesystem checks)

Problem: Claude lacks awareness of project structure, git state, key files
Solution: Gather project context on each prompt, inject relevant info
"""

import sys
import json
import subprocess
import os
from pathlib import Path

# =============================================================================
# CONFIG
# =============================================================================

# Key files that indicate project type/structure
KEY_FILES = {
    "package.json": "Node.js project",
    "pyproject.toml": "Python project (modern)",
    "setup.py": "Python project (legacy)",
    "Cargo.toml": "Rust project",
    "go.mod": "Go project",
    "Makefile": "Has Makefile",
    "Dockerfile": "Has Docker",
    "docker-compose.yml": "Has Docker Compose",
    ".env": "Has .env file",
    "CLAUDE.md": "Has Claude instructions",
}

# Directories that matter
KEY_DIRS = ["src", "lib", "scripts", "tests", "docs", ".claude", "projects", "scratch"]

# =============================================================================
# CONTEXT GATHERING
# =============================================================================

def run_git_command(cmd: list, cwd: str = None, timeout: float = 2.0) -> str:
    """Run git command and return output."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=cwd or os.getcwd()
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def get_git_context() -> dict:
    """Get current git state."""
    context = {}

    # Current branch
    branch = run_git_command(["git", "branch", "--show-current"])
    if branch:
        context["branch"] = branch

    # Uncommitted changes count
    status = run_git_command(["git", "status", "--porcelain"])
    if status:
        lines = [l for l in status.split('\n') if l.strip()]
        # Modified in worktree (not staged): ' M' or 'MM' second char
        modified = len([l for l in lines if len(l) > 1 and l[1] == 'M'])
        untracked = len([l for l in lines if l.startswith('??')])
        # Staged: first char in MADRC (but not '?' or ' ')
        staged = len([l for l in lines if len(l) > 0 and l[0] in 'MADRC'])
        if modified or untracked or staged:
            context["uncommitted"] = {"modified": modified, "untracked": untracked, "staged": staged}

    # Recent commit (just hash + subject)
    last_commit = run_git_command(["git", "log", "-1", "--format=%h %s"])
    if last_commit:
        context["last_commit"] = last_commit[:60]

    return context


def get_project_structure() -> dict:
    """Get project structure info."""
    cwd = Path.cwd()
    structure = {}

    # Check key files
    found_files = []
    for filename, desc in KEY_FILES.items():
        if (cwd / filename).exists():
            found_files.append(filename)
    if found_files:
        structure["key_files"] = found_files

    # Check key directories
    found_dirs = []
    for dirname in KEY_DIRS:
        if (cwd / dirname).is_dir():
            found_dirs.append(dirname)
    if found_dirs:
        structure["directories"] = found_dirs

    return structure


def format_context(git: dict, structure: dict) -> str:
    """Format context for injection."""
    parts = []

    # Git info
    if git:
        git_line = []
        if "branch" in git:
            git_line.append(f"branch: {git['branch']}")
        if "uncommitted" in git:
            u = git["uncommitted"]
            changes = []
            if u.get("modified"):
                changes.append(f"{u['modified']} modified")
            if u.get("untracked"):
                changes.append(f"{u['untracked']} untracked")
            if u.get("staged"):
                changes.append(f"{u['staged']} staged")
            if changes:
                git_line.append(f"changes: {', '.join(changes)}")
        if git_line:
            parts.append(f"Git: {' | '.join(git_line)}")

    # Structure info
    if structure.get("directories"):
        parts.append(f"Dirs: {', '.join(structure['directories'])}")

    return " | ".join(parts) if parts else ""


def main():
    """UserPromptSubmit hook entry point."""
    try:
        json.load(sys.stdin)  # Consume stdin (hook interface requirement)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({}))
        sys.exit(0)

    # Gather context
    git_context = get_git_context()
    project_structure = get_project_structure()

    # Format output
    context_str = format_context(git_context, project_structure)

    if context_str:
        output = {
            "additionalContext": f"📁 PROJECT: {context_str}"
        }
    else:
        output = {}

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
