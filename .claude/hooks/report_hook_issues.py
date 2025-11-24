#!/usr/bin/env python3
"""
SessionStart hook: Report hook test failures to user and Claude.

Reads hook_test_results.json (if exists) and surfaces critical issues
via additionalContext. Runs AFTER test_hooks_background.py has completed.
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta


def main(event):
    """Check for hook test failures and report them."""
    try:
        # Find project root
        current = Path(__file__).parent
        while current != Path("/"):
            if (current / ".claude" / "memory").exists():
                project_root = current
                break
            current = current.parent
        else:
            return {"hookSpecificOutput": {"hookEventName": "SessionStart"}}

        results_path = project_root / ".claude" / "memory" / "hook_test_results.json"

        # Check if results exist and are recent (< 5 minutes old)
        if not results_path.exists():
            return {"hookSpecificOutput": {"hookEventName": "SessionStart"}}

        # Check file age
        file_mtime = datetime.fromtimestamp(results_path.stat().st_mtime)
        age = datetime.now() - file_mtime

        if age > timedelta(minutes=5):
            # Results are stale, skip reporting
            return {"hookSpecificOutput": {"hookEventName": "SessionStart"}}

        # Load results
        try:
            with open(results_path, 'r') as f:
                results = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            # File is being written or corrupted, skip this round
            return {"hookSpecificOutput": {"hookEventName": "SessionStart"}}

        health = results.get("health_summary", {})
        failing = health.get("failing", 0)
        failed_hooks = health.get("failed_hooks", [])

        if failing == 0:
            # All hooks healthy
            return {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": f"✅ Hook health check: {results['total_hooks']} hooks OK"
                }
            }

        # Build failure report
        failure_list = []
        for hook_info in failed_hooks[:3]:  # First 3 failures
            filename = hook_info["filename"]
            errors = hook_info.get("errors", [])
            if errors:
                # Get first error, truncate
                error_msg = errors[0].split('\n')[0][:60]
                failure_list.append(f"  - {filename}: {error_msg}")

        context = f"""⚠️  HOOK HEALTH CHECK: {failing} hook(s) failing

{chr(10).join(failure_list)}

Run: python3 scripts/ops/test_hooks.py
for full details."""

        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context
            }
        }

    except Exception as e:
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": f"⚠️  Hook issue reporter error: {str(e)}"
            }
        }


if __name__ == "__main__":
    event = json.load(sys.stdin)
    result = main(event)
    print(json.dumps(result))
