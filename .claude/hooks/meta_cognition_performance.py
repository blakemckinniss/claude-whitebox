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
   → 🚀 AGENT CONTEXT IS FREE - each agent = separate context window!

5. Large research/analysis across modules?
   → Use PARALLEL AGENTS as free workers (no token cost to main thread)
   → Example: "Analyze auth, API, database modules" → 3 agents in ONE message

6. Bash loop planned?
   → BLOCK YOURSELF - write script with parallel.py

7. Major decision needed?
   → Use ORACLE.PY IN PARALLEL (3s vs 90s for council.py)
   → "Run oracle judge, critic, skeptic in parallel"
   → 30x faster, 95% context savings

Remember:
- You have UNLIMITED bandwidth
- Agent context is FREE (separate windows)
- Oracle.py is 30x faster than council.py (2-3s vs 90s)
- Sequential = wasting resources = -20% confidence
- Parallel agents = free parallelism + free context = +20% confidence
- Parallel oracles = 3 expert perspectives in 3 seconds
"""

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": reminder
    }
}))
