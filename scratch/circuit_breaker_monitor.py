#!/usr/bin/env python3
"""
Circuit Breaker Monitor (PostToolUse Hook)

Tracks tool usage patterns and records failures for circuit breaker system.
Runs AFTER tool execution to log outcomes.
"""

import sys
import json
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from circuit_breaker import (
        record_success,
        record_failure,
        add_event_to_window,
        load_circuit_state,
        save_circuit_state,
        load_config,
        initialize_circuit,
    )
except ImportError:
    # Fallback if library not available
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
except:
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

# Wrap main logic in try/except for crash protection
try:
    # Extract data with validation
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})
    tool_result = input_data.get("tool_result", {})
    session_id = input_data.get("session_id", "unknown")
    turn_count = input_data.get("turn_count", 0)

    # Validate tool_result is dict
    if not isinstance(tool_result, dict):
        tool_result = {}

    # Detect tool failure
    is_error = tool_result.get("isError", False)
    error_message = str(tool_result.get("content", ""))

    # Initialize state
    config = load_config()
    state = load_circuit_state()

    # Pattern: tool_failure (same tool failing repeatedly)
    circuit_name = "tool_failure"
    if circuit_name not in state["circuits"]:
        state["circuits"][circuit_name] = initialize_circuit(circuit_name, config)

    circuit = state["circuits"][circuit_name]

    if is_error:
        # Record failure
        message = record_failure(
            circuit_name=circuit_name,
            session_id=session_id,
            turn=turn_count,
            reason=f"{tool_name} failed: {error_message[:100]}",
            metadata={"tool": tool_name, "error": error_message[:200]},
        )

        if message:
            # Circuit tripped
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": f"\n{message}",
                }
            }
            print(json.dumps(output))
            sys.exit(0)
    else:
        # Record success
        message = record_success(circuit_name=circuit_name, session_id=session_id, turn=turn_count)

        if message:
            # Circuit state changed (e.g., HALF_OPEN → CLOSED)
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": f"\n{message}",
                }
            }
            print(json.dumps(output))
            sys.exit(0)

    # Pattern: sequential_tools (same tool called many times in same turn)
    # This is tracked in the gate hook (PreToolUse), not here

    # Pattern: hook_recursion (tracked separately in hook execution layer)

    # Output empty context (no message)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "",
        }
    }
    print(json.dumps(output))
    sys.exit(0)

except Exception as e:
    # Log error to stderr but return valid JSON to avoid hanging parent
    print(f"[circuit_breaker_monitor ERROR] {str(e)}", file=sys.stderr)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "",
        }
    }
    print(json.dumps(output))
    sys.exit(0)
