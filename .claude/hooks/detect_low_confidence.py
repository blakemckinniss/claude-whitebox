#!/usr/bin/env python3
"""
Detect Low Confidence Hook: Warns when coding requests occur at insufficient confidence
Triggers on: write, implement, refactor, fix, modify, edit
"""
import sys
import json
from pathlib import Path

# Load confidence state
MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
STATE_FILE = MEMORY_DIR / "confidence_state.json"


def load_confidence():
    """Load current confidence level"""
    if not STATE_FILE.exists():
        return 0
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
            return data.get("current_confidence", 0)
    except Exception:
        return 0


# Load input
try:
    input_data = json.load(sys.stdin)
except Exception:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

prompt = input_data.get("prompt", "")
if not prompt:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

prompt_lower = prompt.lower()

# Detect coding/action requests - FIXED: Use regex word boundaries
import re

coding_patterns = [
    r"\bwrite\b",      # Won't match "rewrite" prefix
    r"\bimplement\b",
    r"\bcreate\b",
    r"\bbuild\b",
    r"\bmake\s+(?:a|the|this|me)\b",  # "make a/the" not "Makefile"
    r"\brefactor\b",
    r"\bfix\b",        # Won't match "prefix", "suffix"
    r"\bmodify\b",
    r"\bedit\b",       # Won't match "credit"
    r"\bupdate\b",
    r"\badd\s+(?:a|the|an)\b",  # "add a/the" specifically
    r"\bgenerate\b",
    r"\bscaffold\b",
]

# Detect if this is a coding request - using regex for precision
is_coding_request = any(re.search(pattern, prompt_lower) for pattern in coding_patterns)

if is_coding_request:
    confidence = load_confidence()

    if confidence < 31:
        # Ignorance tier - blocked from coding
        additional_context = f"""
📉 EPISTEMOLOGICAL PROTOCOL: CONFIDENCE TOO LOW

Current Confidence: {confidence}% (IGNORANCE TIER)

⛔ CODING PROHIBITED AT <31% CONFIDENCE

You are attempting a coding task without sufficient evidence.

ALLOWED ACTIONS:
  • Ask questions
  • /research "<query>" - Gather documentation (+20%)
  • /xray --type <type> --name <Name> - Find code structure (+10%)
  • /probe "<object>" - Inspect runtime APIs (+30%)

FORBIDDEN ACTIONS:
  ❌ Writing code
  ❌ Proposing solutions
  ❌ Making changes

NEXT STEPS:
  1. Gather evidence using allowed tools
  2. Build context to 31%+ before attempting solutions
  3. Track: python3 scripts/ops/confidence.py status

**The Dunning-Kruger Checkpoint: Peak ignorance is not a license to code.**
"""
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": additional_context,
                    }
                }
            )
        )
        sys.exit(0)

    elif confidence < 71:
        # Hypothesis tier - can scratch, not production
        additional_context = f"""
📉 EPISTEMOLOGICAL PROTOCOL: LIMITED CONFIDENCE

Current Confidence: {confidence}% (HYPOTHESIS TIER)

⚠️ PRODUCTION CODE BLOCKED - SCRATCH ONLY

You have documentation/context but no runtime verification.

ALLOWED ACTIONS:
  • /think "<problem>" - Decompose the task (+5%)
  • /skeptic "<proposal>" - Check for risks (+5%)
  • Write to scratch/ directory (experimentation)
  • /probe "<object>" - Verify APIs (+30%)
  • /verify <check> <target> - Confirm state (+40%)

FORBIDDEN ACTIONS:
  ❌ Modifying scripts/ or production files
  ❌ Claiming "I know how to do this"
  ❌ Committing code

THRESHOLD FOR PRODUCTION: 71%+

NEXT STEPS:
  1. Test your hypothesis in scratch/
  2. Run verification commands
  3. Reach 71%+ before modifying production code
"""
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": additional_context,
                    }
                }
            )
        )
        sys.exit(0)

# Confidence sufficient or not a coding request
print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "",
            }
        }
    )
)
sys.exit(0)
