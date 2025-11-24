#!/usr/bin/env python3
"""
Auto-Commit Telemetry Hook (PostToolUse)
Monitors file operations and checks commit thresholds after each tool use
"""
import sys
import json
from pathlib import Path

# Add scripts/lib to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "lib"))

try:
    # Import enforcement library from scratch
    scratch_dir = Path(__file__).resolve().parent.parent.parent / "scratch"
    sys.path.insert(0, str(scratch_dir))
    import auto_commit_enforcement
except ImportError:
    # Library not available yet
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ""
        }
    }))
    sys.exit(0)

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ""
        }
    }))
    sys.exit(0)

tool_name = input_data.get("toolName", "")

# Only check after file mutation tools
FILE_MUTATION_TOOLS = ["Write", "Edit", "Bash"]

if tool_name not in FILE_MUTATION_TOOLS:
    # Not a file mutation tool - skip check
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ""
        }
    }))
    sys.exit(0)

# Check if we should auto-commit
try:
    result = auto_commit_enforcement.check_and_commit()

    if result:
        # Commit was triggered
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"\n{result}"
            }
        }))
    else:
        # No commit needed
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": ""
            }
        }))

except Exception as e:
    # Error in enforcement - don't block tool
    error_msg = f"⚠️ Auto-commit check failed: {e}"
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": error_msg
        }
    }))

sys.exit(0)
