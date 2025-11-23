#!/usr/bin/env python3
"""
Post-Tool-Use Hook: Detects tool failures and triggers auto-fix system
Runs after any tool execution to check for errors
"""
import sys
import json
import os
from pathlib import Path
from typing import Optional

# Add scripts/lib to path
_hooks_dir = Path(__file__).parent
_project_root = _hooks_dir.parent.parent
sys.path.insert(0, str(_project_root / "scripts" / "lib"))

try:
    from error_detection import (
        classify_tool_error,
        calculate_risk,
        calculate_effort,
        decide_action,
        generate_fix_suggestions,
        should_auto_fix,
        ErrorReport,
        ActionDecision,
    )
    from auto_fixes import apply_auto_fix, find_applicable_fixes, AUTO_FIX_REGISTRY
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
    except (OSError, IOError) as e:
        # Logging failed - don't crash the hook, but note the failure
        pass  # Silently fail - hook must continue


def log_auto_fix(error: ErrorReport, fix_id: str, success: bool, turn: int, error_msg: Optional[str] = None):
    """Log auto-fix attempt to fix ledger"""
    try:
        ledger_path = _project_root / ".claude" / "memory" / "fix_ledger.jsonl"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)

        log_entry = {
            'turn': turn,
            'error_id': error.error_id,
            'fix_id': fix_id,
            'file_path': error.file_path,
            'success': success,
            'error_message': error_msg,
            'timestamp': __import__('datetime').datetime.now().isoformat(),
        }

        with open(ledger_path, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except (OSError, IOError) as e:
        # Logging failed - don't crash the hook
        pass


def main():
    try:
        # Load input
        input_data = json.load(sys.stdin)
    except:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "",
            }
        }))
        sys.exit(0)

    # Extract tool info
    tool_name = input_data.get('toolName', '')
    tool_input = input_data.get('toolInput', {})
    tool_result = input_data.get('toolResult', {})
    turn = input_data.get('turn', 0)

    # Check if tool failed
    if 'error' not in tool_result or not tool_result['error']:
        # Tool succeeded, no action needed
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "",
            }
        }))
        sys.exit(0)

    # Tool failed - classify error
    error_message = tool_result.get('error', '')
    error_report = classify_tool_error(tool_name, error_message, tool_input)

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

    # Check if should auto-fix
    should_fix, reason = should_auto_fix(error_report, action)

    additional_context = ""

    if should_fix and action == ActionDecision.AUTO_FIX:
        # Attempt auto-fix
        if error_report.file_path and Path(error_report.file_path).exists():
            # Check if any auto-fixes apply
            with open(error_report.file_path, 'r') as f:
                content = f.read()

            applicable_fixes = find_applicable_fixes(content)

            if applicable_fixes:
                auto_fix, match = applicable_fixes[0]  # Take first applicable fix

                # Apply fix
                success, error_msg = apply_auto_fix(error_report.file_path, auto_fix)

                # Log fix attempt
                log_auto_fix(error_report, auto_fix.fix_id, success, turn, error_msg)

                if success:
                    additional_context = f"""
🔧 AUTO-FIX APPLIED

Error: {error_report.description}
File: {error_report.file_path}
Fix: {auto_fix.name}
Risk: {auto_fix.risk}% → {error_report.risk}%
Effort: {auto_fix.effort}%

✅ Fix applied successfully
Backup created at: {error_report.file_path}.autofix.backup

MANDATORY: Run verify.py to confirm fix worked
"""
                else:
                    additional_context = f"""
⚠️ AUTO-FIX FAILED

Error: {error_report.description}
File: {error_report.file_path}
Fix: {auto_fix.name}
Failure reason: {error_msg}

Manual intervention required.
"""
            else:
                # No applicable auto-fixes
                additional_context = f"""
🔍 ERROR DETECTED (No Auto-Fix Available)

Error: {error_report.description}
Category: {error_report.category.value}
Risk: {error_report.risk}%
Effort: {error_report.effort}%
Action: {action.value}

Fix suggestions:
{chr(10).join(f"  {i+1}. {s.approach}" for i, s in enumerate(suggestions))}

Manual investigation required.
"""
    elif action == ActionDecision.CONSULT:
        # Present suggestions to user
        additional_context = f"""
⚠️ ERROR REQUIRES CONSULTATION

Error: {error_report.description}
Category: {error_report.category.value}
Risk: {error_report.risk}%
Effort: {error_report.effort}%

Fix suggestions:
{chr(10).join(f"  {i+1}. {s.approach} (Risk after: {s.risk_after_fix}%, One-click: {s.one_click})" for i, s in enumerate(suggestions))}

Please select fix approach or defer to scope.
"""
    elif action == ActionDecision.DEFER:
        additional_context = f"""
📋 ERROR DEFERRED TO PUNCH LIST

Error: {error_report.description}
Category: {error_report.category.value}
Risk: {error_report.risk}%
Effort: {error_report.effort}% (too high for immediate fix)

Action: Added to scope.py punch list for later review.

Consider running: scope init "Fix {error_report.description}"
"""
    elif action == ActionDecision.BLOCK:
        additional_context = f"""
🚨 CRITICAL ERROR - BLOCKED

Error: {error_report.description}
Category: {error_report.category.value}
Risk: {error_report.risk}% (CRITICAL)

This error is too risky for autonomous or immediate action.

MANDATORY: Convene council for review
Command: python3 scripts/ops/council.py "{error_report.description}"
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
