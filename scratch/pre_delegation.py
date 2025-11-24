#!/usr/bin/env python3
"""
PRE-DELEGATION VALIDATION HOOK
===============================
Prevents delegating to council/critic/advisors without evidence.

TRIGGER: PreToolUse (Bash)
PATTERN: Calls to council.py, critic.py, judge.py, skeptic.py, think.py
ENFORCEMENT: Block if confidence < 40%

Philosophy: "Garbage in, garbage out" - If you don't understand the problem,
            advisors can't help. Must gather context before delegation.
"""

import json
import sys
import re
from pathlib import Path


def find_project_root():
    """Find project root by looking for scripts/lib/core.py"""
    current = Path(__file__).resolve().parent
    for _ in range (10):
        if (current / "scripts" / "lib" / "core.py").exists():
            return current
        current = current.parent
    return Path.cwd()


PROJECT_ROOT = find_project_root()
CONFIDENCE_STATE = PROJECT_ROOT / ".claude" / "memory" / "confidence_state.json"

# Advisory scripts that require context
ADVISORS = [
    "council.py",
    "critic.py",
    "judge.py",
    "skeptic.py",
    "think.py",
    "consult.py",
]


def load_confidence():
    """Load current confidence level"""
    if not CONFIDENCE_STATE.exists():
        return 0
    try:
        with open(CONFIDENCE_STATE) as f:
            data = json.load(f)
            return data.get("confidence", 0)
    except:
        return 0


def is_advisor_call(command):
    """Check if command is calling an advisor script"""
    for advisor in ADVISORS:
        if advisor in command:
            return advisor
    return None


def main():
    # Load input
    try:
        input_data = json.load(sys.stdin)
    except:
        # Can't parse, allow
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "action": "allow"
            }
        }))
        sys.exit(0)

    tool_name = input_data.get("toolName", "")
    tool_params = input_data.get("toolParams", {})

    # Only intercept Bash tool
    if tool_name != "Bash":
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "action": "allow"
            }
        }))
        sys.exit(0)

    # Check if it's an advisor call
    command = tool_params.get("command", "")
    advisor = is_advisor_call(command)

    if not advisor:
        # Not an advisor call, allow
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "action": "allow"
            }
        }))
        sys.exit(0)

    # Check confidence
    confidence = load_confidence()
    DELEGATION_THRESHOLD = 40

    if confidence < DELEGATION_THRESHOLD:
        # BLOCK delegation
        denial_message = f"""
⛔ DELEGATION BLOCKED: INSUFFICIENT CONTEXT

Current Confidence: {confidence}% (Need {DELEGATION_THRESHOLD}%+)
Attempting to call: {advisor}

VIOLATION: "Garbage In, Garbage Out"

You are trying to delegate to advisors without understanding the problem yourself.
The advisors cannot help if you feed them bad assumptions or incomplete context.

Example of what went wrong in this session:
  1. User asked about templates
  2. You had 0% confidence (hadn't read codebase)
  3. You delegated to Critic with wrong assumptions
  4. Critic attacked the wrong target
  5. User had to correct you multiple times

REQUIRED BEFORE DELEGATION:
  ✅ Read relevant files to understand the problem (+10% each)
  ✅ Research external context if needed (/research, +20%)
  ✅ Probe APIs if complex libraries involved (/probe, +30%)
  ✅ Understand what you're actually asking about

MINIMUM {DELEGATION_THRESHOLD}% confidence required to delegate.

WHY THIS MATTERS:
  • Council/Critic are expensive (external API calls)
  • Bad questions → bad advice → wasted user time
  • You must understand the problem to frame it correctly

NEXT STEPS:
  1. Gather evidence about the problem domain
  2. Reach {DELEGATION_THRESHOLD}%+ confidence
  3. Then delegate with proper context

Track: python3 scripts/ops/confidence.py status
"""
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "action": "deny",
                "denyReason": denial_message
            }
        }))
        sys.exit(0)

    # Confidence sufficient, allow delegation
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "action": "allow"
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
