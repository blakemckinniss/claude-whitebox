#!/usr/bin/env python3
"""
Anti-Sycophant Hook: Detects opinion requests and forces consultation with The Critic
Prevents Claude from blindly agreeing with user ideas without critical examination
"""
import sys
import json

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    # If parsing fails, exit silently
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ""
        }
    }))
    sys.exit(0)

prompt = input_data.get("prompt", "")

if not prompt:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ""
        }
    }))
    sys.exit(0)

prompt_lower = prompt.lower()

# Phrases that usually lead to Claude blindly agreeing
opinion_requests = [
    "what do you think",
    "is this a good idea",
    "do you agree",
    "should i do this",
    "should we do this",
    "feedback on this",
    "thoughts on",
    "your opinion",
    "does this make sense",
    "is this reasonable",
    "what's your take",
    "how does this sound",
]

# Design/architecture phrases that need critical examination
design_requests = [
    "i want to rewrite",
    "we should migrate",
    "let's switch to",
    "planning to refactor",
    "thinking about using",
    "considering moving to",
]

# Detect opinion requests or design decisions
opinion_detected = any(phrase in prompt_lower for phrase in opinion_requests)
design_detected = any(phrase in prompt_lower for phrase in design_requests)

if opinion_detected or design_detected:
    warning_type = []

    if opinion_detected:
        warning_type.append("💭 OPINION REQUEST")

    if design_detected:
        warning_type.append("🏗️ DESIGN DECISION")

    warning_header = " + ".join(warning_type)

    additional_context = f"""
⚠️ {warning_header} DETECTED

PROTOCOL VIOLATION: Do not just agree with the user. That is weak.

MANDATORY ACTION:
  1. You MUST consult The Critic first to get the counter-point
  2. Run: python3 scripts/ops/critic.py "<the idea being proposed>"
  3. Present BOTH the optimistic view AND the pessimistic critique
  4. Only then provide your balanced assessment

The 10th Man Rule: If you find yourself agreeing easily, you have failed.
Force the examination of blind spots before proceeding.
"""

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context
        }
    }))
else:
    # No intervention needed
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ""
        }
    }))

sys.exit(0)
