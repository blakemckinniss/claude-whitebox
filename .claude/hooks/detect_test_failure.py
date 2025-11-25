#!/usr/bin/env python3
"""
Post-Bash Hook: Detects test failures and triggers auto-fix system
Specifically monitors pytest/npm test/cargo test commands
"""
import sys
import json
import os
from pathlib import Path

# Add scripts/lib to path
_hooks_dir = Path(__file__).parent
_project_root = _hooks_dir.parent.parent
sys.path.insert(0, str(_project_root / "scripts" / "lib"))

try:
    from error_detection import (
        classify_bash_error,
        calculate_risk,
        calculate_effort,
        decide_action,
        generate_fix_suggestions,
        ErrorReport,
        ActionDecision,
    )
except ImportError:
    # Libraries not available, exit silently
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "",
        }
    }))
    sys.exit(0)


def log_error(error: ErrorReport, action: ActionDecision, turn: int):
    """Log error to error ledger"""
    try:
        ledger_path = _project_root / ".claude" / "memory" / "error_ledger.jsonl"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)

        log_entry = error.to_dict()
        log_entry['action_decision'] = action.value
        log_entry['turn'] = turn

        with open(ledger_path, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except (OSError, IOError):
        # Logging failed - don't crash the hook
        pass


def main():
    try:
        # Load input
        input_data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "",
            }
        }))
        sys.exit(0)

    # Check if this is Bash tool
    tool_name = input_data.get("tool_name", '')
    if tool_name != 'Bash':
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "",
            }
        }))
        sys.exit(0)

    # Extract command info
    tool_input = input_data.get("tool_input", {})
    tool_result = input_data.get('tool_response', input_data.get('toolResult', {}))
    turn = input_data.get('turn', 0)

    command = tool_input.get('command', '')

    # Extract exit code from result
    # Format may vary, try multiple approaches
    exit_code = None
    stdout = ""
    stderr = ""

    if isinstance(tool_result, dict):
        if 'exitCode' in tool_result:
            exit_code = tool_result['exitCode']
        elif 'exit_code' in tool_result:
            exit_code = tool_result['exit_code']

        stdout = tool_result.get('stdout', tool_result.get('output', ''))
        stderr = tool_result.get('stderr', '')

    # Only process failed commands
    if exit_code is None or exit_code == 0:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "",
            }
        }))
        sys.exit(0)

    # Classify bash error
    error_report = classify_bash_error(command, exit_code, stdout, stderr)

    if not error_report:
        # Error not classifiable
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "",
            }
        }))
        sys.exit(0)

    # Update error report with turn info
    error_report.detected_at_turn = turn

    # Calculate risk and effort
    error_report.risk = calculate_risk(error_report)
    error_report.effort = calculate_effort(error_report)

    # Decide action
    action = decide_action(error_report.risk, error_report.effort)

    # Log error
    log_error(error_report, action, turn)

    # Generate fix suggestions
    suggestions = generate_fix_suggestions(error_report)

    additional_context = ""

    # Test failures are special - always consult
    if "test" in command.lower():
        additional_context = f"""
🧪 TEST FAILURE DETECTED

Command: {command}
Exit Code: {exit_code}
Error: {error_report.description}

Test failures require investigation:
  1. Run with -v flag for details: pytest -v
  2. Identify failing assertion or error
  3. Fix implementation or update test
  4. Re-run to verify

MANDATORY: Fix tests before claiming task completion.
Risk: {error_report.risk}%
Effort: {error_report.effort}%

Test output (first 500 chars):
{stdout[:500]}
"""
    elif action == ActionDecision.CONSULT:
        additional_context = f"""
⚠️ COMMAND FAILURE - REQUIRES INVESTIGATION

Command: {command}
Exit Code: {exit_code}
Error: {error_report.description}
Risk: {error_report.risk}%
Effort: {error_report.effort}%

Fix suggestions:
{chr(10).join(f"  {i+1}. {s.approach}" for i, s in enumerate(suggestions))}

Error output:
{stderr[:500] if stderr else stdout[:500]}
"""
    elif action == ActionDecision.DEFER:
        additional_context = f"""
📋 COMMAND ERROR DEFERRED

Command: {command}
Exit Code: {exit_code}
Error: {error_report.description}
Effort: {error_report.effort}% (too high for immediate fix)

This error requires substantial effort to fix.
Consider adding to scope.py punch list.
"""
    elif action == ActionDecision.BLOCK:
        additional_context = f"""
🚨 CRITICAL COMMAND FAILURE

Command: {command}
Exit Code: {exit_code}
Error: {error_report.description}
Risk: {error_report.risk}% (CRITICAL)

This error may indicate serious system issues.
Recommend manual investigation before proceeding.
"""

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": additional_context,
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
