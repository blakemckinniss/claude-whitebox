#!/usr/bin/env python3
"""
Performance Gate V2: WITH AUTO-TUNING
PreToolUse Hook: Enforces performance best practices (parallelism, background execution)

EVOLUTION:
- Phase 1 (OBSERVE): Track sequential vs parallel patterns silently
- Phase 2 (WARN): Suggest performance improvements
- Phase 3 (ENFORCE): Block inefficient patterns

AUTO-TUNING:
- Learns optimal parallelism thresholds from task type
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
from meta_learning import record_manual_bypass, record_sudo_bypass, check_exception_rule

# Pattern definitions
PERFORMANCE_PATTERNS = {'sequential_bash': {'threshold': 3, 'suggested_action': 'Use parallel background execution (run_in_background=true)'}, 'blocking_on_slow': {'threshold': 1, 'suggested_action': 'Use background execution for slow operations (>5s)'}}

# Initialize auto-tuner
MEMORY_DIR = PROJECT_DIR / ".claude" / "memory"
STATE_FILE = MEMORY_DIR / "performance_gate_state.json"

tuner = AutoTuner(
    system_name="performance_enforcement",
    state_file=STATE_FILE,
    patterns=PERFORMANCE_PATTERNS,
    default_phase="observe",
    default_thresholds={}
)


def main():
    """Main enforcement logic"""
    try:
        data = json.load(sys.stdin)
    except Exception:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_params = data.get("tool_input", {})
    turn = data.get("turn", 0)
    prompt = data.get("prompt", "")

    # Only track Bash tool for performance patterns
    if tool_name != "Bash":
        sys.exit(0)

    command = tool_params.get("command", "")
    run_in_background = tool_params.get("run_in_background", False)

    # Detect slow operations not using background
    slow_keywords = ["pytest", "npm test", "npm run build", "cargo build", "docker build"]
    is_slow = any(kw in command for kw in slow_keywords)

    if is_slow and not run_in_background:
        pattern_name = "blocking_on_slow"

        # Check exception rules
        should_bypass, rule = check_exception_rule(
            "performance_gate",
            {"tool": tool_name, "command": command}
        )

        if should_bypass:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": f"🎓 Exception: {rule['reason']}",
                }
            }
            print(json.dumps(output))
            sys.exit(0)

        # Check if should enforce
        action, message = tuner.should_enforce(pattern_name, prompt)

        # Track bypass
        if "MANUAL" in prompt:
            record_manual_bypass(
                hook_name="performance_gate",
                context={"tool": tool_name, "pattern": pattern_name, "command": command[:100]},
                turn=turn,
                reason="Manual bypass of performance enforcement"
            )

        # Update metrics (estimate slow command = 30s blocked)
        tuner.update_metrics(
            pattern_name,
            turns_wasted=1,  # Could have worked during that time
            script_written=False,
            bypassed="MANUAL" in prompt or "SUDO MANUAL" in prompt
        )

        # Phase transition
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

        # Auto-tune
        tuner.auto_tune_thresholds(turn)

        # Report
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

