#!/usr/bin/env python3
"""
Error Review Tool: View and manage errors detected by auto-fix system
"""
import sys
import os
import json
from pathlib import Path

# Add scripts/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
_current = _script_dir
while _current != "/":
    if os.path.exists(os.path.join(_current, "scripts", "lib", "core.py")):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root")
sys.path.insert(0, os.path.join(_project_root, "scripts", "lib"))

from core import setup_script, finalize, logger
from error_detection import ErrorReport, ActionDecision, generate_fix_suggestions


def load_errors(ledger_path: Path):
    """Load all errors from ledger"""
    if not ledger_path.exists():
        return []

    errors = []
    with open(ledger_path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    errors.append(json.loads(line))
                except:
                    pass
    return errors


def load_fixes(ledger_path: Path):
    """Load all fix attempts from ledger"""
    if not ledger_path.exists():
        return []

    fixes = []
    with open(ledger_path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    fixes.append(json.loads(line))
                except:
                    pass
    return fixes


def display_error_summary(errors):
    """Display summary of all errors"""
    print("\n" + "=" * 70)
    print("📊 ERROR SUMMARY")
    print("=" * 70)

    if not errors:
        print("  No errors detected")
        return

    # Group by category
    by_category = {}
    by_action = {}
    for error in errors:
        category = error.get('category', 'unknown')
        action = error.get('action_decision', 'unknown')

        by_category[category] = by_category.get(category, 0) + 1
        by_action[action] = by_action.get(action, 0) + 1

    print(f"\n  Total Errors: {len(errors)}")
    print(f"\n  By Category:")
    for category, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
        print(f"    {category}: {count}")

    print(f"\n  By Action:")
    for action, count in sorted(by_action.items(), key=lambda x: x[1], reverse=True):
        print(f"    {action}: {count}")

    # Recent errors
    print(f"\n  Recent Errors (last 5):")
    for error in errors[-5:]:
        error_id = error.get('error_id', 'unknown')
        description = error.get('description', 'No description')
        severity = error.get('severity', 'UNKNOWN')
        risk = error.get('risk', 0)
        print(f"    [{severity}] {error_id}: {description[:60]} (Risk: {risk}%)")


def display_error_detail(error):
    """Display detailed error information"""
    print("\n" + "=" * 70)
    print("🔍 ERROR DETAILS")
    print("=" * 70)

    print(f"\n  Error ID: {error.get('error_id')}")
    print(f"  Category: {error.get('category')}")
    print(f"  Severity: {error.get('severity')}")
    print(f"  Description: {error.get('description')}")

    if error.get('file_path'):
        print(f"  File: {error.get('file_path')}")
        if error.get('line_number'):
            print(f"  Line: {error.get('line_number')}")

    print(f"\n  Risk Assessment:")
    print(f"    Risk Score: {error.get('risk')}%")
    print(f"    Effort Score: {error.get('effort')}%")
    print(f"    Reversible: {error.get('reversible')}")
    print(f"    Affects Production: {error.get('affects_production')}")
    print(f"    Has Tests: {error.get('has_tests')}")

    print(f"\n  Action Decision: {error.get('action_decision')}")
    print(f"  Detected at Turn: {error.get('turn')}")

    if error.get('tool_name'):
        print(f"  Tool: {error.get('tool_name')}")
    if error.get('command'):
        print(f"  Command: {error.get('command')}")


def display_fix_history(error_id, fixes):
    """Display fix attempts for error"""
    error_fixes = [f for f in fixes if f.get('error_id') == error_id]

    if not error_fixes:
        print("\n  No fix attempts recorded")
        return

    print("\n" + "=" * 70)
    print(f"🔧 FIX HISTORY ({len(error_fixes)} attempts)")
    print("=" * 70)

    for i, fix in enumerate(error_fixes, 1):
        status = "✅ SUCCESS" if fix.get('success') else "❌ FAILED"
        print(f"\n  Attempt {i}: {status}")
        print(f"    Fix ID: {fix.get('fix_id')}")
        print(f"    Turn: {fix.get('turn')}")
        print(f"    Timestamp: {fix.get('timestamp')}")
        if fix.get('error_message'):
            print(f"    Error: {fix.get('error_message')}")


def main():
    parser = setup_script("Error Review Tool: View and manage detected errors")

    parser.add_argument(
        '--error-id',
        help="Show details for specific error ID"
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help="List all errors"
    )
    parser.add_argument(
        '--recent',
        type=int,
        default=10,
        help="Show N most recent errors (default: 10)"
    )
    parser.add_argument(
        '--category',
        help="Filter by category"
    )
    parser.add_argument(
        '--action',
        choices=['auto_fix', 'consult', 'defer', 'block'],
        help="Filter by action decision"
    )
    parser.add_argument(
        '--fix-history',
        help="Show fix history for error ID"
    )

    args = parser.parse_args()

    # Paths
    error_ledger = Path(_project_root) / ".claude" / "memory" / "error_ledger.jsonl"
    fix_ledger = Path(_project_root) / ".claude" / "memory" / "fix_ledger.jsonl"

    # Load data
    errors = load_errors(error_ledger)
    fixes = load_fixes(fix_ledger)

    # Handle commands
    if args.fix_history:
        display_fix_history(args.fix_history, fixes)
        finalize(success=True)

    if args.error_id:
        # Find specific error
        error = next((e for e in errors if e.get('error_id') == args.error_id), None)
        if not error:
            logger.error(f"Error ID not found: {args.error_id}")
            finalize(success=False)

        display_error_detail(error)
        display_fix_history(args.error_id, fixes)
        finalize(success=True)

    # Filter errors
    filtered = errors

    if args.category:
        filtered = [e for e in filtered if e.get('category') == args.category]

    if args.action:
        filtered = [e for e in filtered if e.get('action_decision') == args.action]

    # Display
    if args.list:
        display_error_summary(filtered)

        print("\n" + "=" * 70)
        print(f"📋 ALL ERRORS ({len(filtered)})")
        print("=" * 70)

        for error in filtered:
            error_id = error.get('error_id', 'unknown')
            description = error.get('description', 'No description')
            severity = error.get('severity', 'UNKNOWN')
            action = error.get('action_decision', 'UNKNOWN')
            print(f"  [{severity}] {error_id}")
            print(f"    {description}")
            print(f"    Action: {action} | Risk: {error.get('risk')}% | Effort: {error.get('effort')}%")
            print()
    else:
        # Show recent errors
        recent = filtered[-args.recent:]
        display_error_summary(filtered)

        print("\n" + "=" * 70)
        print(f"📋 RECENT ERRORS ({len(recent)})")
        print("=" * 70)

        for error in recent:
            error_id = error.get('error_id', 'unknown')
            description = error.get('description', 'No description')
            severity = error.get('severity', 'UNKNOWN')
            action = error.get('action_decision', 'UNKNOWN')
            print(f"\n  [{severity}] {error_id}")
            print(f"    {description}")
            print(f"    Action: {action} | Risk: {error.get('risk')}% | Effort: {error.get('effort')}%")

    print("\n" + "=" * 70)
    print("\nUse --error-id <ID> to see full details")
    print("Use --fix-history <ID> to see fix attempts")
    print("=" * 70 + "\n")

    finalize(success=True)


if __name__ == "__main__":
    main()
