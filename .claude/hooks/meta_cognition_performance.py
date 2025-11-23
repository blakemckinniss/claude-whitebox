#!/usr/bin/env python3
"""
Meta-Cognition Performance Reminder
Triggers on: UserPromptSubmit
Injects questions to check before acting
"""
import sys
import json

input_data = json.load(sys.stdin)

# Meta-cognition checklist injected into context
reminder = """
⚡ META-COGNITION PERFORMANCE CHECKLIST (Before responding):

1. Multiple tool calls planned?
   → Can they run in PARALLEL? (single message, multiple <invoke> blocks)

2. Operation repeated >2 times?
   → Should I write a SCRIPT to scratch/ instead?

3. File iteration detected?
   → Should I use parallel.py with max_workers=50?

4. Multiple agents needed?
   → Can I delegate in PARALLEL? (single message, multiple Task calls)

5. Bash loop planned?
   → BLOCK YOURSELF - write script with parallel.py

Remember: You have UNLIMITED bandwidth. Sequential = wasting resources = -20% confidence.
"""

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": reminder
    }
}))
