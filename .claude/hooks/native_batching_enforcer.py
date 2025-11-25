#!/usr/bin/env python3
"""
Native Tool Batching Enforcer V2 (PreToolUse Hook)
WITH AUTO-TUNING

Uses auto_tuning.py framework for self-tuning enforcement.

EVOLUTION:
- Phase 1 (OBSERVE): Track patterns silently for 20 turns
- Phase 2 (WARN): Suggest parallel invocation patterns
- Phase 3 (ENFORCE): Hard block sequential operations

AUTO-TUNING:
- Adjusts thresholds based on MANUAL bypass usage (FP rate)
- Backtrack to WARN if FP rate >15%
- Tighten thresholds if FP rate <3% and ROI >5x
- Auto-report every 50 turns
"""

import sys
import json
from pathlib import Path

# Add scripts/lib to path
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

sys.path.insert(0, str(PROJECT_DIR / "scripts" / "lib"))

from auto_tuning import AutoTuner

# Pattern definitions for batching
BATCHING_PATTERNS = {
    "sequential_reads": {
        "tools": ["Read"],
        "threshold": 2,  # 2+ Read calls in same turn
        "suggested_action": "Use parallel Read invocation (single message, multiple <invoke> blocks)",
    },
    "sequential_greps": {
        "tools": ["Grep"],
        "threshold": 3,  # 3+ Grep calls
        "suggested_action": "Use parallel Grep invocation",
    },
    "sequential_web": {
        "tools": ["WebFetch", "WebSearch"],
        "threshold": 2,  # 2+ web ops
        "suggested_action": "Use parallel WebFetch/WebSearch invocation",
    },
}

# Initialize auto-tuner
MEMORY_DIR = PROJECT_DIR / ".claude" / "memory"
STATE_FILE = MEMORY_DIR / "batching_enforcement_state.json"

tuner = AutoTuner(
    system_name="batching",
    state_file=STATE_FILE,
    patterns=BATCHING_PATTERNS,
    default_phase="observe",  # Start passive
)


def load_session_state(session_id: str):
    """Load session state for tool call tracking"""
    session_file = MEMORY_DIR / f"session_{session_id}_state.json"
    if not session_file.exists():
        return {"tool_calls": []}

    try:
        with open(session_file) as f:
            return json.load(f)
    except:
        return {"tool_calls": []}


def save_session_state(session_id: str, state: dict):
    """Save session state"""
    session_file = MEMORY_DIR / f"session_{session_id}_state.json"
    session_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(session_file, "w") as f:
            json.dump(state, f, indent=2)
    except:
        pass


def get_tool_calls_in_turn(session_state: dict, turn: int):
    """Get all tool calls in current turn"""
    return [
        call
        for call in session_state.get("tool_calls", [])
        if call["turn"] == turn
    ]


def record_tool_call(session_state: dict, tool_name: str, turn: int):
    """Record tool call"""
    if "tool_calls" not in session_state:
        session_state["tool_calls"] = []

    session_state["tool_calls"].append(
        {"tool": tool_name, "turn": turn, "timestamp": __import__("time").time()}
    )

    # Keep only last 10 turns
    min_turn = turn - 10
    session_state["tool_calls"] = [
        call for call in session_state["tool_calls"] if call["turn"] >= min_turn
    ]


def detect_batching_pattern(tool_name: str, session_state: dict, turn: int):
    """
    Detect if current tool call matches a batching anti-pattern.

    Returns: (pattern_name, count) or None
    """
    current_turn_calls = get_tool_calls_in_turn(session_state, turn)

    # Check each pattern
    for pattern_name, pattern_config in BATCHING_PATTERNS.items():
        pattern_tools = pattern_config["tools"]

        if tool_name in pattern_tools:
            # Count how many times pattern tools were called this turn
            count = sum(1 for call in current_turn_calls if call["tool"] in pattern_tools)

            # +1 for current call
            count += 1

            if count >= pattern_config["threshold"]:
                return (pattern_name, count)

    return None


def main():
    """Main enforcement logic"""
    try:
        data = json.load(sys.stdin)
    except:
        sys.exit(0)

    tool_name = data.get("toolName", "")
    turn = int(data.get("turnNumber", 0))
    session_id = data.get("sessionId", "unknown")
    prompt = data.get("userPrompt", "")

    # Only track batchable tools
    batchable_tools = ["Read", "Grep", "Glob", "WebFetch", "WebSearch"]
    if tool_name not in batchable_tools:
        sys.exit(0)

    # Load session state
    session_state = load_session_state(session_id)

    # Detect pattern
    detection = detect_batching_pattern(tool_name, session_state, turn)

    if detection:
        pattern_name, count = detection

        # Check if should enforce
        action, message = tuner.should_enforce(pattern_name, prompt)

        # Record tool call
        record_tool_call(session_state, tool_name, turn)
        save_session_state(session_id, session_state)

        # Update metrics (estimate turns wasted = count - 1)
        turns_wasted = count - 1
        script_written = False  # Can't detect this in PreToolUse
        bypassed = "MANUAL" in prompt or "SUDO MANUAL" in prompt

        tuner.update_metrics(pattern_name, turns_wasted, script_written, bypassed)

        # Check phase transition
        transition_msg = tuner.check_phase_transition(turn)
        if transition_msg:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",  # Don't block on transitions
                    "additionalContext": transition_msg,
                }
            }
            print(json.dumps(output))
            sys.exit(0)

        # Auto-tune thresholds
        adjustments = tuner.auto_tune_thresholds(turn)
        if adjustments:
            # Log but don't show to user (happens in background)
            pass

        # Generate report
        report = tuner.generate_report(turn)
        if report:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": report,
                }
            }
            print(json.dumps(output))
            sys.exit(0)

        # Enforcement logic
        if action == "block" and message:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": message,
                }
            }
            print(json.dumps(output))
            sys.exit(0)

        elif action == "warn" and message:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": message,
                }
            }
            print(json.dumps(output))
            sys.exit(0)

    # Allow execution (default)
    record_tool_call(session_state, tool_name, turn)
    save_session_state(session_id, session_state)

    output = {
        "hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
