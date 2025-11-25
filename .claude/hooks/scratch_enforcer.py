#!/usr/bin/env python3
"""
Scratch Enforcer Hook (PostToolUse)

Detects iteration patterns and enforces scratch-first philosophy.
Auto-tunes thresholds based on false positive rate and ROI.

THREE-PHASE AUTO-EVOLUTION:
1. OBSERVE (Turns 1-20): Silent data collection
2. WARN (Auto-triggers at 70% confidence): Suggestions only
3. ENFORCE (Auto-triggers at 3x proven ROI): Hard blocks
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
    get_enforcement_state,
    save_enforcement_state,
    detect_pattern_in_history,
    should_enforce,
    update_pattern_detection,
    auto_tune_thresholds,
    check_phase_transition,
    generate_auto_report,
    log_telemetry,
)


def main():
    """Main hook logic"""
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = data.get("toolName", "")
    turn = int(data.get("turnNumber", 0))
    session_id = data.get("sessionId", "unknown")

    # Only track file operation tools
    if tool_name not in ["Read", "Grep", "Glob", "Edit"]:
        sys.exit(0)

    # Load state
    state = get_enforcement_state()
    state["total_turns"] = turn

    # Build tool history from telemetry (last 10 turns)
    # For now, simplified: just track current tool
    tool_history = [{"tool": tool_name, "turn": turn}]

    # Detect pattern in history
    detection = detect_pattern_in_history(tool_name, tool_history, turn)

    if detection:
        pattern_name, count = detection

        # Estimate turns wasted (based on count)
        turns_wasted = count - 1  # First use is legitimate

        # Update pattern statistics
        update_pattern_detection(pattern_name, turns_wasted)

        # Log telemetry
        log_telemetry(turn, pattern_name, "detected", [tool_name])

        # Check if should enforce
        action, message = should_enforce(pattern_name, state)

        if action == "warn" and message:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": message
                }
            }
            print(json.dumps(output))
            log_telemetry(turn, pattern_name, "warned", [tool_name])

        elif action == "block" and message:
            # BLOCK via additionalContext (user sees warning, not hard block)
            # Hard blocking requires PreToolUse hook
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": message
                }
            }
            print(json.dumps(output))
            log_telemetry(turn, pattern_name, "blocked", [tool_name])

    # Auto-tune thresholds every 50 turns
    if turn > 0 and turn % 50 == 0:
        adjustments = auto_tune_thresholds(state, turn)
        if adjustments:
            log_telemetry(turn, "auto_tune", "threshold_adjusted", [], {"adjustments": adjustments})

    # Check phase transition
    transition_msg = check_phase_transition(state, turn)
    if transition_msg:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": transition_msg
            }
        }
        print(json.dumps(output))
        log_telemetry(turn, "phase_transition", state["phase"], [])

    # Generate auto-report every 50 turns (in WARN or ENFORCE phase)
    if turn > 0 and turn % 50 == 0 and state["phase"] != "observe":
        report = generate_auto_report(state, turn)
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": report
            }
        }
        print(json.dumps(output))

    # Save state
    save_enforcement_state(state)

    # Default output (no context)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ""
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
