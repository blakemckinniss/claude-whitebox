#!/usr/bin/env python3
"""
Confidence Initialization Hook: Assesses initial confidence on first prompt
Triggers on: UserPromptSubmit
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
    assess_initial_confidence,
    save_session_state,
    get_confidence_tier,
)

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

session_id = input_data.get("sessionId", "unknown")
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

# Load or initialize session state
state = load_session_state(session_id)
if not state:
    state = initialize_session_state(session_id)

# Check if this is the first prompt (turn 0)
turn = state.get("turn_count", 0)

# On first turn, assess initial confidence
if turn == 0:
    initial_confidence = assess_initial_confidence(prompt)
    state["confidence"] = initial_confidence

    # Record in history
    state["confidence_history"].append(
        {
            "turn": 1,
            "confidence": initial_confidence,
            "reason": "initial_assessment",
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
    )

# Increment turn counter
state["turn_count"] = turn + 1

# Save state
save_session_state(session_id, state)

# Get tier information
current_confidence = state["confidence"]
tier_name, tier_desc = get_confidence_tier(current_confidence)

# Get token info
tokens = state.get('tokens_estimated', 0)
token_pct = state.get('context_window_percent', 0)

# Inject current state as context
context = f"""
📊 EPISTEMOLOGICAL STATE (Turn {state['turn_count']}):
   • Confidence: {current_confidence}% ({tier_name} TIER)
   • Risk: {state.get('risk', 0)}%
   • Tokens: {token_pct}% ({tokens:,} / 200,000)
   • {tier_desc}

Evidence Gathered:
   • Files Read: {len(state.get('read_files', {}))}
   • Total Evidence Items: {len(state.get('evidence_ledger', []))}
"""

print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context,
            }
        }
    )
)
sys.exit(0)
