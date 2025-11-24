#!/usr/bin/env python3
"""
SessionStart hook: Run hook test suite in background (non-blocking).

Launches test_hooks.py in background process and returns immediately.
Results are persisted to .claude/memory/hook_test_results.json for
later consumption by report_hook_issues.py.
"""
import json
import sys
import subprocess
import os
from pathlib import Path

def main(event):
    """Launch hook tests in background, return immediately."""
    try:
        # Find project root
        current = Path(__file__).parent
        while current != Path("/"):
            if (current / "scripts" / "ops" / "test_hooks.py").exists():
                project_root = current
                break
            current = current.parent
        else:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": "⚠️  Hook test suite: Could not find project root"
                }
            }

        test_script = project_root / "scripts" / "ops" / "test_hooks.py"

        # Launch in background (detached from parent process)
        # Use Popen instead of run() to avoid blocking
        subprocess.Popen(
            [sys.executable, str(test_script), "--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Detach from parent
            cwd=str(project_root)
        )

        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "🧪 Hook test suite running in background..."
            }
        }

    except Exception as e:
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": f"⚠️  Hook test suite failed to launch: {str(e)}"
            }
        }


if __name__ == "__main__":
    event = json.load(sys.stdin)
    result = main(event)
    print(json.dumps(result))
