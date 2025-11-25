#!/usr/bin/env python3
"""
Scratch Prompt Analyzer Hook (UserPromptSubmit)

Detects iteration language in user prompts ("for each file", "all files", etc.)
Warns immediately when file_iteration pattern detected.
"""

import sys
import json
from pathlib import Path

# Add scripts/lib to path
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

sys.path.insert(0, str(PROJECT_DIR / "scripts" / "lib"))

from scratch_enforcement import (
    detect_pattern_in_prompt,
    should_enforce,
    get_enforcement_state,
    log_telemetry,
    PATTERNS,
)


def main():
    """Main hook logic"""
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    prompt = data.get("prompt", "")
    turn = data.get("turn", 0)

    if not prompt:
        sys.exit(0)

    # Detect pattern in prompt
    pattern_name = detect_pattern_in_prompt(prompt)

    if pattern_name:
        # Load state
        state = get_enforcement_state()

        # Check if should warn/enforce
        action, message = should_enforce(pattern_name, state, prompt)

        if message:  # WARN or ENFORCE phase
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": message
                }
            }
            print(json.dumps(output))
            log_telemetry(turn, pattern_name, f"prompt_{action}", [], {"prompt_snippet": prompt[:100]})
            sys.exit(0)

    # Default output (no context)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ""
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
