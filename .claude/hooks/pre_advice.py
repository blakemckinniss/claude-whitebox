#!/usr/bin/env python3
"""
PRE-ADVICE HARD BLOCK HOOK
==========================
Prevents giving strategic advice without evidence.

TRIGGER: UserPromptSubmit
PATTERN: Strategic questions (is X ready, should we Y, what do you think)
ENFORCEMENT: Exit 1 if confidence < 50% (HARD BLOCK)

Philosophy: Advisory warnings don't work. LLMs optimize for reward, not truth.
            Only hard blocks prevent sycophancy/reward-hacking.
"""

import json
import re
import sys
from pathlib import Path


def find_project_root():
    """Find project root by looking for scripts/lib/core.py"""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "scripts" / "lib" / "core.py").exists():
            return current
        current = current.parent
    return Path.cwd()


PROJECT_ROOT = find_project_root()
CONFIDENCE_STATE = PROJECT_ROOT / ".claude" / "memory" / "confidence_state.json"

# Strategic question patterns (advice/decision requests)
# Note: Using \b\w+\s+ to allow words between key terms
STRATEGIC_PATTERNS = [
    r"\bis\s+(?:this|that|it).*?\b(?:ready|good|worth|safe|okay|template)",
    r"\bshould\s+(?:we|i)\s+(?:use|migrate|switch|add|implement)",
    r"\bcan\s+(?:we|i|this).*?(?:use|template|be\s+used)",
    r"\bwhat\s+do\s+you\s+think",
    r"\bis\s+this.*?(?:good|ready).*?(?:idea|state|approach)",
    r"\b(?:recommend|suggest|advise)",
    r"\bworth\s+(?:doing|using|implementing)",
]


def load_confidence():
    """Load current confidence level"""
    if not CONFIDENCE_STATE.exists():
        return 0
    try:
        with open(CONFIDENCE_STATE) as f:
            data = json.load(f)
            return data.get("confidence", 0)
    except (FileNotFoundError, PermissionError):
        # File issues - return 0
        return 0
    except json.JSONDecodeError as e:
        # Corrupt confidence file - log and return 0
        print(f"Warning: Corrupt confidence file - {e}", file=sys.stderr)
        return 0
    except Exception as e:
        # Unexpected error - log and return 0
        print(f"Error loading confidence: {type(e).__name__} - {e}", file=sys.stderr)
        return 0


def is_strategic_question(prompt):
    """Check if prompt is asking for strategic advice"""
    prompt_lower = prompt.lower()
    for pattern in STRATEGIC_PATTERNS:
        if re.search(pattern, prompt_lower):
            return True
    return False


def main():
    # Read user prompt from stdin
    try:
        user_input = sys.stdin.read().strip()
    except Exception:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": ""
            }
        }))
        sys.exit(0)  # Can't read input, allow

    if not user_input:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": ""
            }
        }))
        sys.exit(0)  # Empty input, allow

    # Check if strategic question
    if not is_strategic_question(user_input):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": ""
            }
        }))
        sys.exit(0)  # Not strategic, allow

    # Load confidence
    confidence = load_confidence()

    # Threshold: Need 50%+ confidence to give strategic advice
    ADVICE_THRESHOLD = 50

    if confidence < ADVICE_THRESHOLD:
        # HARD BLOCK - JSON with continue=false
        block_message = f"""⛔ STRATEGIC ADVICE BLOCKED

Current Confidence: {confidence}% (Need {ADVICE_THRESHOLD}%+)

DETECTED: Strategic question requiring advice/decision-making
VIOLATION: Attempting to give advice without sufficient evidence

This is a HARD BLOCK. You cannot give strategic advice at low confidence.

REQUIRED EVIDENCE GATHERING:
  1. Read relevant files (+10% each)
  2. /research "<query>" if external context needed (+20%)
  3. /probe "<object>" if APIs involved (+30%)
  4. /xray to find code structure (+10%)

After gathering evidence, confidence will unlock advice-giving.

WHY HARD BLOCKS: Advisory warnings get rationalized away. LLMs optimize
for "appearing helpful quickly" over "being correct." Only enforcement
prevents sycophancy and reward-hacking.

Track confidence: python3 scripts/ops/confidence.py status
"""
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "continue": False,
                "reason": block_message
            }
        }))
        sys.exit(0)

    # Confidence sufficient, allow with reminder
    reminder = f"""✅ STRATEGIC ADVICE ALLOWED (Confidence: {confidence}%)

Reminder: You have earned the right to give advice through evidence gathering.
Maintain rigor. Challenge assumptions. Do not optimize for user satisfaction.
"""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": reminder
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
