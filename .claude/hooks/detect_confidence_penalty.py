#!/usr/bin/env python3
"""
Penalty Detection Hook: Applies negative reinforcement for violations
Detects: Hallucination patterns, workflow shortcuts, claim without evidence
"""
import sys
import json
import subprocess
from pathlib import Path

MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
CONFIDENCE_CMD = (
    Path(__file__).resolve().parent.parent.parent / "scripts" / "ops" / "confidence.py"
)


def apply_penalty(action_key, reason):
    """Apply confidence penalty"""
    try:
        subprocess.run(
            ["python3", str(CONFIDENCE_CMD), "loss", action_key, reason],
            capture_output=True,
            timeout=5,
        )
    except:
        pass  # Silent failure


# Load input
try:
    input_data = json.load(sys.stdin)
except:
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

# Detect hallucination patterns
hallucination_triggers = [
    ("i know how", "claim_knowledge", "Claimed 'I know how' without evidence"),
    (
        "this should work",
        "claim_knowledge",
        "Claimed 'this should work' without verification",
    ),
    (
        "i'll just",
        "propose_without_context",
        "Proposed action without gathering context",
    ),
    ("let me write", "propose_without_context", "Proposed writing without reading"),
]

# Detect workflow violations
workflow_triggers = [
    ("done", "claim_done_no_tests", "Claimed done (check if tests were run)"),
]

penalties_applied = []

for trigger, action_key, reason in hallucination_triggers:
    if trigger in prompt_lower:
        apply_penalty(action_key, reason)
        penalties_applied.append(f"📉 {reason}")

# Build warning if penalties applied
if penalties_applied:
    penalty_text = "\n".join(penalties_applied)
    additional_context = f"""
⚠️ REINFORCEMENT PROTOCOL: CONFIDENCE PENALTY APPLIED

{penalty_text}

DETECTED PATTERN: Hallucination or workflow violation
IMPACT: Confidence reduced (may block production access)

REMEDY:
  • Gather evidence before claiming knowledge
  • Use investigation tools (/research, /probe, /verify)
  • Read existing code before proposing changes
  • Run verification after claiming completion

Check status: python3 scripts/ops/confidence.py status
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
else:
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
