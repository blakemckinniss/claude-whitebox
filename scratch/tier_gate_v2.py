#!/usr/bin/env python3
"""
Tier Gate V2: WITH AUTO-TUNING
PreToolUse Hook: Enforces confidence tier restrictions

EVOLUTION:
- Phase 1 (OBSERVE): Track tier violations silently
- Phase 2 (WARN): Suggest evidence gathering
- Phase 3 (ENFORCE): Block actions below required tier

AUTO-TUNING:
- Learns optimal tier thresholds from success/failure patterns
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
from meta_learning import record_manual_bypass, check_exception_rule
from epistemology import load_session_state, get_confidence_tier

# Pattern definitions
TIER_PATTERNS = {'ignorance_coding': {'threshold': 1, 'suggested_action': 'Gather evidence (Read/Research/Probe) to reach HYPOTHESIS tier (31%+)'}, 'hypothesis_production': {'threshold': 1, 'suggested_action': 'Reach CERTAINTY tier (71%+) before modifying production code'}}

# Initialize auto-tuner
MEMORY_DIR = PROJECT_DIR / ".claude" / "memory"
STATE_FILE = MEMORY_DIR / "tier_gate_state.json"

tuner = AutoTuner(
    system_name="tier_enforcement",
    state_file=STATE_FILE,
    patterns=TIER_PATTERNS,
    default_phase="observe",
)


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
        # Allow if no state (fail open)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}))
        sys.exit(0)

    current_confidence = state.get("confidence", 0)
    tier_name, tier_desc = get_confidence_tier(current_confidence)

    # Pattern 1: Coding at IGNORANCE tier (0-30%)
    if current_confidence < 31 and tool_name in ["Write", "Edit"]:
        pattern_name = "ignorance_coding"

        # Check exception rules
        should_bypass, rule = check_exception_rule(
            "tier_gate",
            {"tool": tool_name, "confidence": current_confidence, "tier": tier_name}
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
                hook_name="tier_gate",
                context={"tool": tool_name, "confidence": current_confidence, "tier": tier_name},
                turn=turn,
                reason="Manual bypass of tier enforcement"
            )

        # Update metrics
        tuner.update_metrics(
            pattern_name,
            turns_wasted=3,  # Estimate for fixing hallucinated code
            script_written=False,
            bypassed="MANUAL" in prompt or "SUDO MANUAL" in prompt
        )

        # Phase transition
        transition_msg = tuner.check_phase_transition(turn)
        if transition_msg:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "additionalContext": transition_msg}}))
            sys.exit(0)

        # Auto-tune
        tuner.auto_tune_thresholds(turn)

        # Report
        report = tuner.generate_report(turn)
        if report:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "additionalContext": report}}))
            sys.exit(0)

        # Enforcement
        if action == "block" and message:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": message}}))
            sys.exit(0)
        elif action == "warn" and message:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "additionalContext": message}}))
            sys.exit(0)

    # Pattern 2: Production code at HYPOTHESIS tier (31-70%)
    if 31 <= current_confidence < 71 and tool_name in ["Write", "Edit"]:
        file_path = tool_params.get("file_path", "")
        is_production = "scripts/" in file_path or "src/" in file_path or file_path.endswith(".py") and "scratch/" not in file_path

        if is_production:
            pattern_name = "hypothesis_production"

            # Check exception rules
            should_bypass, rule = check_exception_rule(
                "tier_gate",
                {"tool": tool_name, "confidence": current_confidence, "tier": tier_name, "file": file_path}
            )

            if should_bypass:
                print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "additionalContext": f"🎓 Exception: {rule['reason']}"}}))
                sys.exit(0)

            # Check if should enforce
            action, message = tuner.should_enforce(pattern_name, prompt)

            # Track bypass
            if "MANUAL" in prompt:
                record_manual_bypass(
                    hook_name="tier_gate",
                    context={"tool": tool_name, "confidence": current_confidence, "tier": tier_name, "file": file_path},
                    turn=turn,
                    reason="Manual bypass for production code"
                )

            # Update metrics
            tuner.update_metrics(
                pattern_name,
                turns_wasted=5,  # High cost for buggy production code
                script_written=False,
                bypassed="MANUAL" in prompt or "SUDO MANUAL" in prompt
            )

            # Phase transition
            transition_msg = tuner.check_phase_transition(turn)
            if transition_msg:
                print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "additionalContext": transition_msg}}))
                sys.exit(0)

            # Auto-tune
            tuner.auto_tune_thresholds(turn)

            # Report
            report = tuner.generate_report(turn)
            if report:
                print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "additionalContext": report}}))
                sys.exit(0)

            # Enforcement
            if action == "block" and message:
                print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": message}}))
                sys.exit(0)
            elif action == "warn" and message:
                print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "additionalContext": message}}))
                sys.exit(0)

    # Allow execution (default)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
