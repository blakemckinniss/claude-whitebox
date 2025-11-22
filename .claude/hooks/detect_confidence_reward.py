#!/usr/bin/env python3
"""
Reward Detection Hook: DEPRECATED - evidence_tracker.py handles this now
Keeping as pass-through for backward compatibility
"""
import sys
import json

# NOTE: This hook is deprecated. evidence_tracker.py (PostToolUse) handles
# all confidence updates directly via epistemology.py library.
# This hook kept as pass-through to avoid breaking existing settings.json.


# Pass-through hook - evidence_tracker.py handles all confidence updates
print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "",
            }
        }
    )
)
sys.exit(0)
