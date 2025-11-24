#!/usr/bin/env python3
"""
Memory Janitor (SessionStart Hook)

Automatically cleans up memory on session start:
- Rotates large telemetry files
- Prunes old session files
- Truncates evidence ledgers

Runs silently - only outputs if cleanup performed.
"""

import sys
import json
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from memory_cleanup import auto_cleanup_on_startup
except ImportError:
    # Fallback if library not available
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

# Run auto cleanup
try:
    cleanup_message = auto_cleanup_on_startup()

    # Only show message if cleanup performed
    if "No action needed" not in cleanup_message:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": f"\n{cleanup_message}\n",
            }
        }
    else:
        # Silent success
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "",
            }
        }

    print(json.dumps(output))
    sys.exit(0)

except Exception as e:
    # Log error but don't fail hook
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"\n⚠️ Memory cleanup failed: {str(e)[:100]}\n",
        }
    }
    print(json.dumps(output))
    sys.exit(0)
