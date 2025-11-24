
#!/usr/bin/env python3
"""
Command Prerequisite Gate V2: WITH AUTO-TUNING
PreToolUse Hook: Enforces workflow command prerequisites

EVOLUTION:
- Phase 1 (OBSERVE): Track actual command timings for 20 turns
- Phase 2 (WARN): Suggest prerequisites when windows violated
- Phase 3 (ENFORCE): Hard block until prerequisites met

AUTO-TUNING:
- Learns optimal windows from actual usage (e.g., if upkeep runs every 15 turns, adjust window from 20→18)
- Adapts to different task types (research-only sessions may not need commit prereqs)
- Auto-exempts certain patterns (test runs, documentation updates)
"""

import sys
import json
from pathlib import Path

# Add scripts/lib to path
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

sys.path.insert(0, str(PROJECT_DIR / "scripts" / "lib"))

from epistemology import (
    load_session_state,
    initialize_session_state,
    check_command_prerequisite,
    get_confidence_tier,
    get_tier_privileges,
)
from auto_tuning import AutoTuner
from meta_learning import record_manual_bypass, check_exception_rule

# Prerequisite patterns
PREREQUISITE_PATTERNS = {
    "commit_needs_upkeep": {
        "trigger": "git commit",
        "prerequisite": "upkeep",
        "default_window": 20,
        "threshold": 1,  # Always required
        "suggested_action": "Run /upkeep to sync requirements and check for drift",
    },
    "claim_needs_verify": {
        "trigger": ["Fixed", "Done", "completed"],
        "prerequisite": "verify",
        "default_window": 3,
        "threshold": 1,
        "suggested_action": "Run /verify to prove the claim with objective evidence",
    },
}

# Initialize auto-tuner
MEMORY_DIR = PROJECT_DIR / ".claude" / "memory"
STATE_FILE = MEMORY_DIR / "command_prerequisite_state.json"

tuner = AutoTuner(
    system_name="command_prerequisites",
    state_file=STATE_FILE,
    patterns=PREREQUISITE_PATTERNS,
    default_phase="observe",
    default_thresholds={
        "auto_tune_interval": 100,  # Tune every 100 turns (less frequent)
        "phase_transition_confidence": 0.50,  # Lower bar - these are critical
    },
)


def detect_prerequisite_violation(tool_name, tool_params, session_state, turn):
    """
    Detect if prerequisite is violated.

    Returns: (pattern_name, window_used, last_run_turn) or None
    """
    # Check git commit
    if tool_name == "Bash":
        command = tool_params.get("command", "")

        if "git commit" in command:
            commands_run = session_state.get("commands_run", {})
            upkeep_runs = commands_run.get("upkeep", [])

            if not upkeep_runs:
                return ("commit_needs_upkeep", 20, None)

            last_upkeep = max(upkeep_runs)
            turns_ago = turn - last_upkeep

            if turns_ago > 20:
                return ("commit_needs_upkeep", 20, last_upkeep)

    # Check claim keywords (simplified - would need more context)
    # This is a placeholder - actual implementation would check message content

    return None


def main():
    """Main enforcement logic"""
    try:
        data = json.load(sys.stdin)
    except:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    session_id = data.get("sessionId", "unknown")
    tool_name = data.get("toolName", "")
    tool_params = data.get("toolParams", {})
    turn = data.get("turn", 0)
    prompt = data.get("prompt", "")

    # Load session state
    state = load_session_state(session_id)
    if not state:
        state = initialize_session_state(session_id)

    current_confidence = state.get("confidence", 0)
    tier_name, tier_desc = get_confidence_tier(current_confidence)
    privileges = get_tier_privileges(current_confidence)
    enforcement_mode = privileges.get("prerequisite_mode", "enforce")

    # EXPERT TIER: Bypass all checks
    if enforcement_mode == "disabled":
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": f"""✨ EXPERT TIER ({current_confidence}%) - Prerequisite checks bypassed

Maximum autonomy earned through consistent evidence gathering.""",
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Check for exception rules (meta-learning)
    should_bypass, rule = check_exception_rule(
        "command_prerequisite_gate",
        {"tool": tool_name, "params": tool_params}
    )

    if should_bypass:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": f"""🎓 Exception rule applied: {rule['reason']}""",
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Detect prerequisite violation
    detection = detect_prerequisite_violation(tool_name, tool_params, state, turn)

    if detection:
        pattern_name, window, last_run = detection

        # Check if should enforce
        action, message = tuner.should_enforce(pattern_name, prompt)

        # Track bypass if MANUAL used
        if "MANUAL" in prompt:
            record_manual_bypass(
                hook_name="command_prerequisite_gate",
                context={"tool": tool_name, "pattern": pattern_name},
                turn=turn,
                reason="Manual bypass of prerequisite check"
            )

        # Update metrics
        turns_wasted = window if last_run is None else (turn - last_run - window)
        tuner.update_metrics(
            pattern_name,
            max(0, turns_wasted),
            script_written=False,
            bypassed="MANUAL" in prompt or "SUDO MANUAL" in prompt
        )

        # Check phase transition
        transition_msg = tuner.check_phase_transition(turn)
        if transition_msg:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": transition_msg,
                }
            }
            print(json.dumps(output))
            sys.exit(0)

        # Auto-tune (every 100 turns)
        tuner.auto_tune_thresholds(turn)

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

        # Enforcement
        if action == "block" and message:
            # TRUSTED tier: Warn instead of block
            if enforcement_mode == "warn":
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "additionalContext": message.replace("BLOCKED", "⚠️ RECOMMENDED"),
                    }
                }
            else:
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
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
