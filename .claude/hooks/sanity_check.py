#!/usr/bin/env python3
"""
Sanity Check Hook: Detects when Claude is about to write code for complex libraries
without first verifying the runtime API.
"""
import sys
import json

# Load input
data = json.load(sys.stdin)
prompt = data.get("prompt", "").lower()

# Words that indicate Claude is about to write code using external libs
code_intent = [
    "write a script",
    "create a tool",
    "implement",
    "code",
    "build",
    "add a function",
]
risky_libs = [
    "pandas",
    "numpy",
    "aws",
    "boto3",
    "azure",
    "openai",
    "anthropic",
    "requests",
    "django",
    "flask",
    "fastapi",
    "sqlalchemy",
    "pydantic",
    "tensorflow",
    "pytorch",
    "sklearn",
]

is_coding = any(x in prompt for x in code_intent)
using_risky_lib = any(x in prompt for x in risky_libs)

if is_coding and using_risky_lib:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": (
                        "⚠️ SANITY CHECK: You are about to write code for a complex library.\n"
                        "STOP. Do not guess methods.\n"
                        "1. Have you run `scripts/ops/research.py` to get current docs?\n"
                        "2. Have you run `scripts/ops/probe.py` to verify the runtime API?\n"
                        "If not, do that FIRST before writing any code."
                    ),
                }
            }
        )
    )
    sys.exit(0)

# No warning needed
print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit"}}))
sys.exit(0)
