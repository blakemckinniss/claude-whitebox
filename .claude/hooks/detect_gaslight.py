#!/usr/bin/env python3
"""
Detect Gaslight Hook: Detects user frustration indicating AI gaslighting
Triggers when user disputes Claude's claims or reports persistent failures
"""
import sys
import json

# Load input
try:
    input_data = json.load(sys.stdin)
except Exception:
    # If parsing fails, exit silently
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

# User frustration indicators - they're disputing Claude's claims
frustration_triggers = [
    "you said",
    "you claimed",
    "you just told me",
    "still not working",
    "still doesn't work",
    "didn't work",
    "no it doesn't",
    "no it isn't",
    "stop lying",
    "that's not true",
    "check again",
    "same error",
    "still broken",
    "still failing",
    "you're wrong",
    "i already tried that",
    "that didn't fix it",
    "nothing changed",
    "it's still",
]

# Escalation indicators - repeated failures
escalation_triggers = [
    "third time",
    "fourth time",
    "again and again",
    "keep saying",
    "every time",
    "repeatedly",
]

# Detect frustration
frustration_detected = any(trigger in prompt_lower for trigger in frustration_triggers)
escalation_detected = any(trigger in prompt_lower for trigger in escalation_triggers)

if frustration_detected or escalation_detected:
    severity = "CRITICAL" if escalation_detected else "WARNING"

    warnings = []

    if frustration_detected:
        warnings.append("🚨 USER FRUSTRATION: Claims being disputed")

    if escalation_detected:
        warnings.append("🔥 ESCALATION: Repeated failures detected")

    warning_text = "\n".join(warnings)

    additional_context = f"""
⚠️ TRUST ERROR DETECTED - {severity}

{warning_text}

🤥 GASLIGHTING PROTOCOL ACTIVE:

The user suspects you are making false claims or hallucinating fixes.

IMMEDIATE ACTIONS REQUIRED:
  1. STOP apologizing. Apologies without proof are meaningless.
  2. STOP guessing. Do not suggest fixes without verification.
  3. RUN VERIFICATION: Use scripts/ops/verify.py to prove system state
  4. ESTABLISH GROUND TRUTH: Show evidence before making claims

MANDATORY VERIFICATION LOOP:
  • Before claiming "I fixed X" → Verify with verify.py
  • Before claiming "File contains Y" → Verify with verify.py grep_text
  • Before claiming "Port is open" → Verify with verify.py port_open
  • Before claiming "Command works" → Verify with verify.py command_success

If verification shows the problem persists:
  • Admit: "The verification tool confirms the issue persists"
  • Investigate: Use ls -l, cat, grep to understand ACTUAL state
  • Explain: What you found vs what you expected
  • Fix: Address the ROOT CAUSE, not symptoms

Consider switching to Sherlock agent (/use sherlock) for evidence-based investigation.

REMEMBER: The system state is the source of truth, not your internal model.
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
    # No intervention needed
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
