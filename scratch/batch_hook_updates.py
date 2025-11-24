#!/usr/bin/env python3
"""
Batch update hooks with meta-learning integration.

Updates:
1. scratch_enforcer_gate.py - Add meta-learning tracking
2. native_batching_enforcer.py - Add meta-learning tracking (already done in v2)
3. command_prerequisite_gate.py - Full auto-tuning upgrade

This script generates the updated versions for manual review.
"""

import sys
from pathlib import Path

PROJECT_DIR = Path.cwd()
HOOKS_DIR = PROJECT_DIR / ".claude" / "hooks"
SCRATCH_DIR = PROJECT_DIR / "scratch"

# Update 1: scratch_enforcer_gate.py integration
SCRATCH_GATE_META_LEARNING_PATCH = '''
# After line 11 (from scratch_enforcement import ...)
# Add:
from meta_learning import record_manual_bypass, record_sudo_bypass

# In main(), after bypass detection (around line 54):
        if action == "observe":
            # Bypass triggered - track as potential false positive
            if "MANUAL" in prompt:
                record_manual_bypass(
                    hook_name="scratch_enforcer",
                    context={"pattern": pattern_name, "tools": [tool_name]},
                    turn=turn,
                    reason="Manual override of scratch-first enforcement"
                )
                update_pattern_detection(pattern_name, 0, script_written=False, bypassed=True)
                log_telemetry(turn, pattern_name, "bypassed_manual", [tool_name])
            elif "SUDO MANUAL" in prompt:
                record_sudo_bypass(
                    hook_name="scratch_enforcer",
                    context={"pattern": pattern_name, "tools": [tool_name]},
                    turn=turn,
                    reason="SUDO override of scratch-first enforcement"
                )
'''

# Update 2: command_prerequisite_gate.py full upgrade
COMMAND_PREREQ_AUTO_TUNING = '''
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
                "allowExecution": True,
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
                "allowExecution": True,
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
                "allowExecution": True,
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
                    "allowExecution": True,
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
                    "allowExecution": True,
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
                        "allowExecution": True,
                        "additionalContext": message.replace("BLOCKED", "⚠️ RECOMMENDED"),
                    }
                }
            else:
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "allowExecution": False,
                        "blockMessage": message,
                    }
                }
            print(json.dumps(output))
            sys.exit(0)

        elif action == "warn" and message:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "allowExecution": True,
                    "additionalContext": message,
                }
            }
            print(json.dumps(output))
            sys.exit(0)

    # Allow execution (default)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "allowExecution": True,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
'''

def main():
    """Generate updated hook files"""

    print("📝 Generating updated hook files...\n")

    # Write command_prerequisite_gate v2
    output_file = SCRATCH_DIR / "command_prerequisite_gate_v2.py"
    with open(output_file, "w") as f:
        f.write(COMMAND_PREREQ_AUTO_TUNING)

    print(f"✅ Generated: {output_file}")
    print(f"   - Full auto-tuning integration")
    print(f"   - Meta-learning support")
    print(f"   - 3-phase evolution\n")

    # Write patch notes for scratch_enforcer_gate
    patch_file = SCRATCH_DIR / "scratch_enforcer_gate_meta_learning_patch.txt"
    with open(patch_file, "w") as f:
        f.write(SCRATCH_GATE_META_LEARNING_PATCH)

    print(f"✅ Generated: {patch_file}")
    print(f"   - Meta-learning integration patch")
    print(f"   - Manual application required\n")

    print("💡 NEXT STEPS:")
    print("1. Review scratch/command_prerequisite_gate_v2.py")
    print("2. Test in isolation")
    print("3. Backup original and deploy")
    print("4. Apply patch to scratch_enforcer_gate.py")

if __name__ == "__main__":
    main()
