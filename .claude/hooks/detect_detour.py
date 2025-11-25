#!/usr/bin/env python3
"""
Detour Detection Hook: Detect blocking issues and suggest alternative approaches
Triggers on: PostToolUse
Purpose: Automatically detect when an error blocks progress and suggest detour strategies
"""
import sys
import json
from pathlib import Path

# Add scripts/lib to path
# Navigate from .claude/hooks/ -> project root -> scripts
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

# Import detour detection functions
try:
    from lib.detour import detect_detour, generate_detour_suggestion
except ImportError:
    # Fail silently if detour.py not available
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

# Load input
try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
    sys.exit(1)
except Exception:
    # Any other error - return empty context
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

# Extract input parameters
tool_name = input_data.get("tool_name", "")
tool_input = input_data.get("tool_input", {})
tool_result = input_data.get("tool_response") or input_data.get("toolResult", {})
turn = input_data.get("turn", 0)

# Only process Bash tool (most errors come from shell commands)
if tool_name != "Bash":
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

# Extract tool output from result
# toolResult can have "content" (stdout) and/or "error" (stderr)
tool_output = ""
if isinstance(tool_result, dict):
    content = tool_result.get("content", "")
    error = tool_result.get("error", "")
    # Combine both content and error for analysis
    tool_output = f"{content}\n{error}".strip()
elif isinstance(tool_result, str):
    tool_output = tool_result
else:
    # No output to analyze
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

# Skip if no output
if not tool_output:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

# Detect detour
try:
    detection_result = detect_detour(tool_output, tool_name, tool_input)

    if detection_result:
        pattern, matched_text = detection_result

        # Only trigger suggestion if severity >= 6 (medium-high or higher)
        if pattern.severity >= 6:
            # Generate suggestion
            # Use placeholder for original_task since we don't have task context
            original_task = "Current task (check TodoWrite or recent context)"
            suggestion = generate_detour_suggestion(pattern, matched_text, original_task)

            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PostToolUse",
                            "additionalContext": suggestion,
                        }
                    }
                )
            )
        else:
            # Severity too low, don't spam
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PostToolUse",
                            "additionalContext": "",
                        }
                    }
                )
            )
    else:
        # No detour detected
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": "",
                    }
                }
            )
        )

except Exception as e:
    # Hook failure - return empty context to avoid blocking Claude
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

sys.exit(0)
