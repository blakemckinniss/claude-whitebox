#!/usr/bin/env python3
"""
Tier Gate Hook: Enforces confidence tier requirements before tool usage
Triggers on: PreToolUse
"""
import sys
import json
from pathlib import Path

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import (
    load_session_state,
    initialize_session_state,
    check_tier_gate,
    apply_penalty,
    get_confidence_tier,
)

# Load input
try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    # SECURITY: Fail CLOSED on malformed input
    error_msg = f"Tier gate: Malformed JSON input - {type(e).__name__}: {str(e)[:100]}"
    print(error_msg, file=sys.stderr)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"Security: Cannot validate tier without valid input. {error_msg}"
        }
    }))
    sys.exit(0)
except Exception as e:
    # SECURITY: Fail CLOSED on unexpected errors
    error_msg = f"Tier gate: Unexpected error - {type(e).__name__}: {str(e)[:100]}"
    print(error_msg, file=sys.stderr)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"Security: System error in tier gate. {error_msg}"
        }
    }))
    sys.exit(0)

session_id = input_data.get("session_id", "unknown")
tool_name = input_data.get("tool_name", "")
tool_params = input_data.get("tool_input", {})

if not tool_name:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow"
        }
    }))
    sys.exit(0)

# Load session state
state = load_session_state(session_id)
if not state:
    state = initialize_session_state(session_id)

current_confidence = state.get("confidence", 0)
turn = state.get("turn_count", 0)

# Check tier gate (graduated system - returns 4 values now)
allowed, block_message, penalty_type, enforcement_mode = check_tier_gate(
    tool_name, tool_params, current_confidence, session_id
)

if not allowed:
    # Apply specific penalty (tier_violation, edit_before_read, modify_unexamined, etc.)
    penalty_type = penalty_type or "tier_violation"  # Default fallback
    new_confidence = apply_penalty(
        session_id=session_id,
        penalty_type=penalty_type,
        turn=turn,
        reason=f"Attempted {tool_name} - {penalty_type}",
    )

    # Block the action
    tier_name, _ = get_confidence_tier(new_confidence)
    full_message = f"""{block_message}

New Confidence: {new_confidence}% ({tier_name} TIER)

Next Steps:
  1. Gather evidence using allowed tools
  2. Build confidence to required tier
  3. Then retry this action
"""

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": full_message
        }
    }))
    sys.exit(0)

# Handle warning mode (TRUSTED tier - allow with penalty)
if allowed and block_message and enforcement_mode == "warn":
    # Action allowed but with warning + penalty
    penalty_type = penalty_type or "tier_violation"
    new_confidence = apply_penalty(
        session_id=session_id,
        penalty_type=penalty_type,
        turn=turn,
        reason=f"Warning: {tool_name} - {penalty_type}",
    )

    tier_name, _ = get_confidence_tier(new_confidence)
    warning_context = f"""{block_message}

New Confidence: {new_confidence}% ({tier_name} TIER)

Action proceeding (TRUSTED tier allows this with penalty).
"""

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "additionalContext": warning_context
        }
    }))
    sys.exit(0)

# Allow the action
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow"
    }
}))
sys.exit(0)
