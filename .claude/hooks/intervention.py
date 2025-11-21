#!/usr/bin/env python3
"""
Intervention Hook: Detects bikeshedding and "Not Invented Here" syndrome
Warns user before proceeding with potentially wasteful work
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

# Signs of bikeshedding - focusing on trivial details
bikeshed_triggers = [
    "prettier config",
    "linting rules",
    "lint config",
    "color scheme",
    "folder structure",
    "naming convention",
    "switch to",
    "migrate to",
    "replace with",
    "instead of",
    "code style",
    "formatting",
    "indentation",
    "spacing",
    "eslint",
    "prettier",
]

# Signs of "Not Invented Here" syndrome - reinventing wheels
nih_triggers = [
    "custom framework",
    "my own version",
    "from scratch",
    "build our own",
    "write our own",
    "custom implementation",
    "roll our own",
]

# Signs of YAGNI - building for future that hasn't happened
yagni_triggers = [
    "might need",
    "could need",
    "in case we",
    "future proof",
    "eventually",
    "scalability",
    "when we grow",
    "for later",
]

# Detect triggers
bikeshed_detected = any(trigger in prompt_lower for trigger in bikeshed_triggers)
nih_detected = any(trigger in prompt_lower for trigger in nih_triggers)
yagni_detected = any(trigger in prompt_lower for trigger in yagni_triggers)

# Build warning message if any trigger detected
if bikeshed_detected or nih_detected or yagni_detected:
    warnings = []

    if bikeshed_detected:
        warnings.append("🚲 BIKESHEDDING: This looks like trivial configuration/style work")

    if nih_detected:
        warnings.append("🔧 NOT INVENTED HERE: You might be reinventing an existing solution")

    if yagni_detected:
        warnings.append("🔮 YAGNI: You might be building for a future that hasn't happened")

    warning_text = "\n".join(warnings)

    additional_context = f"""
⚖️ COURT IN SESSION - The Judge has flagged this topic

{warning_text}

MANDATORY CHECK - Ask yourself:
  • Does this DIRECTLY help ship to production TODAY?
  • Is there an existing tool/library that does this?
  • Am I solving a problem I actually have, or one I MIGHT have?

RECOMMENDED: Run The Judge before proceeding:
  python3 scripts/ops/judge.py "your proposal"

If The Judge says STOP, you drop the task.
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
