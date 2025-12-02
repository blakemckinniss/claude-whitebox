#!/usr/bin/env python3
"""
Beads Integration Hook: Surface ready work and maintain agent memory.

SUDO SECURITY

Runs on SessionStart to:
1. Check if beads is installed and initialized
2. Show ready (unblocked) issues for the current project
3. Surface context from previous sessions

Zero config - just works when beads is available and initialized.
"""

import _lib_path  # noqa: F401
import sys
import json
import subprocess
from pathlib import Path

try:
    from project_detector import get_current_project
    PROJECT_AWARE = True
except ImportError:
    PROJECT_AWARE = False


# =============================================================================
# BEADS DETECTION
# =============================================================================

def check_beads_installed() -> bool:
    """Check if beads CLI (bd) is available."""
    try:
        result = subprocess.run(
            ["bd", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def check_beads_initialized(root: str) -> bool:
    """Check if beads is initialized in the project."""
    beads_dir = Path(root) / ".beads"
    return beads_dir.exists() and (beads_dir / "issues.jsonl").exists()


# =============================================================================
# BEADS QUERIES
# =============================================================================

def get_ready_issues(root: str, limit: int = 3) -> list[dict]:
    """Get ready (unblocked) issues from beads."""
    try:
        result = subprocess.run(
            ["bd", "ready", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=root,
        )
        if result.returncode == 0 and result.stdout.strip():
            issues = json.loads(result.stdout)
            return issues[:limit] if isinstance(issues, list) else []
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, json.JSONDecodeError):
        pass
    return []


def get_in_progress_issues(root: str) -> list[dict]:
    """Get issues currently in progress."""
    try:
        result = subprocess.run(
            ["bd", "list", "--status", "in_progress", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=root,
        )
        if result.returncode == 0 and result.stdout.strip():
            issues = json.loads(result.stdout)
            return issues if isinstance(issues, list) else []
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, json.JSONDecodeError):
        pass
    return []


def format_issue_summary(issues: list[dict], prefix: str = "") -> str:
    """Format issues for display."""
    if not issues:
        return ""

    lines = []
    for issue in issues[:3]:
        issue_id = issue.get("id", "?")[:10]
        title = issue.get("title", "")[:50]
        priority = issue.get("priority", "")
        priority_str = f"P{priority}" if priority else ""
        lines.append(f"  {prefix}{issue_id}: {title} {priority_str}".strip())

    return "\n".join(lines)


# =============================================================================
# MAIN HOOK
# =============================================================================

def main():
    """SessionStart hook entry point."""
    # Consume stdin
    try:
        json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        pass

    output = {}
    messages = []

    # Skip if project detection not available
    if not PROJECT_AWARE:
        print(json.dumps(output))
        sys.exit(0)

    try:
        # Get project context
        project = get_current_project()

        # Skip ephemeral sessions
        if project.project_type == "ephemeral":
            print(json.dumps(output))
            sys.exit(0)

        # Check if beads is installed
        if not check_beads_installed():
            # Beads not installed - skip silently
            print(json.dumps(output))
            sys.exit(0)

        # Check if beads is initialized in this project
        if not check_beads_initialized(project.root_path):
            # Not initialized - skip silently
            print(json.dumps(output))
            sys.exit(0)

        # Get in-progress issues (highest priority)
        in_progress = get_in_progress_issues(project.root_path)
        if in_progress:
            messages.append(f"🔄 **IN PROGRESS** ({len(in_progress)}):")
            messages.append(format_issue_summary(in_progress))

        # Get ready issues
        ready = get_ready_issues(project.root_path)
        if ready and not in_progress:
            messages.append(f"📋 **READY WORK** ({len(ready)}):")
            messages.append(format_issue_summary(ready))
        elif ready:
            # Just show count if there's already in-progress work
            messages.append(f"📋 {len(ready)} more ready")

        if messages:
            output["message"] = "\n".join(messages)

    except Exception as e:
        # Don't fail session start - beads is optional
        import sys as _sys
        print(f"beads hook error: {e}", file=_sys.stderr)

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
