#!/usr/bin/env python3
"""
Confidence Gate Hook: Blocks Write/Edit to production files at <71% confidence
Allows scratch/ writes at any level (experimentation)
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
    except:
        return 0

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "action": "allow"
        }
    }))
    sys.exit(0)

tool_name = input_data.get("toolName", "")
tool_params = input_data.get("toolParams", {})

# Only intercept Write/Edit operations
if tool_name not in ["Write", "Edit"]:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "action": "allow"
        }
    }))
    sys.exit(0)

# Get file path
file_path = tool_params.get("file_path", "")
if not file_path:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "action": "allow"
        }
    }))
    sys.exit(0)

# Allow scratch/ writes at any confidence (experimentation)
if "/scratch/" in file_path or file_path.startswith("scratch/"):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "action": "allow"
        }
    }))
    sys.exit(0)

# Check confidence for production files
confidence = load_confidence()

if confidence < 71:
    additional_context = f"""
🚨 CONFIDENCE GATE: PRODUCTION WRITE BLOCKED

Current Confidence: {confidence}% (INSUFFICIENT)
Target File: {file_path}

⛔ PRODUCTION CODE MODIFICATION REQUIRES 71%+ CONFIDENCE

You are attempting to modify production code without runtime verification.

CURRENT TIER: {"IGNORANCE (0-30%)" if confidence < 31 else "HYPOTHESIS (31-70%)"}

REQUIRED EVIDENCE FOR 71%+:
  1. Read relevant code files (+10% each)
  2. Research documentation (/research, +20%)
  3. Inspect runtime APIs (/probe, +30%)
  4. Verify system state (/verify, +40%)

ALLOWED RIGHT NOW:
  ✅ Write to scratch/ (experimentation allowed)
  ✅ Gather evidence using investigation tools
  ✅ Test hypotheses in throwaway code

FORBIDDEN:
  ❌ Modify scripts/ at <71%
  ❌ Edit production files at <71%
  ❌ Commit unverified changes

NEXT STEPS:
  1. python3 scripts/ops/confidence.py status (check current state)
  2. Gather evidence to reach 71%
  3. Retry this operation after threshold met

**Earn the right to code. Evidence > Intuition.**
"""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "action": "deny",
            "denyReason": additional_context
        }
    }))
    sys.exit(0)

# Confidence sufficient, allow operation
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "action": "allow"
    }
}))
sys.exit(0)
