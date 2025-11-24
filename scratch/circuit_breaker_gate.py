#!/usr/bin/env python3
"""
Circuit Breaker Gate (PreToolUse Hook)

Blocks tool execution if circuit breaker is OPEN.
Runs BEFORE tool execution to enforce circuit breakers.
"""

import sys
import json
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from circuit_breaker import (
        check_circuit_state,
        load_circuit_state,
        save_circuit_state,
        load_config,
        initialize_circuit,
        add_event_to_window,
    )
except ImportError:
    # Fallback if library not available
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "shouldBlock": False,
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
                    "hookEventName": "PreToolUse",
                    "shouldBlock": False,
                }
            }
        )
    )
    sys.exit(0)

# Extract data
tool_name = input_data.get("tool_name", "unknown")
tool_input = input_data.get("tool_input", {})
session_id = input_data.get("session_id", "unknown")
turn_count = input_data.get("turn_count", 0)
prompt = input_data.get("user_prompt", "")

# Check for bypass keyword
if "SUDO BYPASS" in prompt:
    # Allow bypass
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "shouldBlock": False,
            "additionalContext": "\n⚠️ Circuit breaker bypassed (SUDO BYPASS keyword detected)",
        }
    }
    print(json.dumps(output))
    sys.exit(0)

# Initialize state
config = load_config()
state = load_circuit_state()

# Check tool_failure circuit breaker
circuit_name = "tool_failure"
if circuit_name not in state["circuits"]:
    state["circuits"][circuit_name] = initialize_circuit(circuit_name, config)

action, message = check_circuit_state(
    circuit_name=circuit_name, session_id=session_id, turn=turn_count
)

if action == "block":
    # Circuit breaker OPEN - block execution
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "shouldBlock": True,
            "systemMessage": message,
        }
    }
    print(json.dumps(output))
    sys.exit(0)

elif action == "probe":
    # Circuit breaker HALF_OPEN - allow but warn
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "shouldBlock": False,
            "additionalContext": f"\n{message}",
        }
    }
    print(json.dumps(output))
    sys.exit(0)

# Pattern: sequential_tools (detect same tool called multiple times in same turn)
# Track tool uses in current turn
circuit_name_seq = "sequential_tools"
if circuit_name_seq not in state["circuits"]:
    state["circuits"][circuit_name_seq] = initialize_circuit(circuit_name_seq, config)

circuit_seq = state["circuits"][circuit_name_seq]

# Add current tool use to window
add_event_to_window(
    circuit_seq,
    turn=turn_count,
    event_type="tool_use",
    metadata={"tool": tool_name},
)

# Count same tool in current turn
same_tool_count = sum(
    1
    for e in circuit_seq["window"]
    if e["turn"] == turn_count and e["metadata"].get("tool") == tool_name
)

threshold = circuit_seq["config"].get("threshold", 10)

if same_tool_count > threshold:
    # Too many sequential calls - suggest script
    message = f"""⚠️ SEQUENTIAL TOOL ABUSE DETECTED

Tool: {tool_name}
Count: {same_tool_count} calls in current turn
Threshold: {threshold}

RECOMMENDATION: Write a scratch script instead of manual iteration.

Example:
  scratch/batch_{tool_name.lower()}.py

This is a warning (not a block). Consider using scratch/ for better efficiency.
Bypass: Include "SUDO BYPASS" to suppress this warning.
"""

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "shouldBlock": False,
            "additionalContext": f"\n{message}",
        }
    }
    print(json.dumps(output))
    sys.exit(0)

# Save state after tracking
save_circuit_state(state)

# Allow execution
output = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "shouldBlock": False,
    }
}
print(json.dumps(output))
sys.exit(0)
