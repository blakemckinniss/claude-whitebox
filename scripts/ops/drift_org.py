#!/usr/bin/env python3
"""
Organizational Drift Management Tool
View drift reports, record false positives, and manage thresholds
"""

import sys
import argparse
from pathlib import Path

# Add scripts/lib to path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root / "scripts" / "lib"))

from org_drift import (
    get_drift_report,
    record_false_positive,
    revoke_false_positive,
    reset_state,
    load_state,
    save_state,
    DEFAULT_THRESHOLDS,
)


def report():
    """Show drift detection report"""
    print(get_drift_report())
    return 0  # Success exit code


def record_fp(violation_type: str):
    """Record a false positive"""
    valid_types = [
        "recursion",
        "root_pollution",
        "prod_pollution",
        "filename_collision",
        "hook_explosion",
        "scratch_bloat",
        "memory_fragmentation",
        "deep_nesting",
    ]

    if violation_type not in valid_types:
        print(f"❌ Invalid violation type: {violation_type}")
        print(f"Valid types: {', '.join(valid_types)}")
        return 1

    result = record_false_positive(violation_type)

    if result["success"]:
        print(f"✅ Recorded false positive for: {violation_type}")
        print(f"   • FP Count: {result['fp_count']}")
        print(f"   • Total Checks: {result['total_checks']}")
        print(f"   • FP Rate: {result['fp_rate']:.1f}%")
        print("Next auto-tuning will adjust thresholds accordingly.")
        return 0
    else:
        print(f"❌ Failed to record false positive")
        return 1


def revoke_fp(violation_type: str):
    """Revoke a false positive (undo accidental marking)"""
    result = revoke_false_positive(violation_type)

    if result.get("success"):
        print(f"✅ Revoked false positive for: {violation_type}")
        print(f"   • FP Count: {result['fp_count']}")
        print(f"   • Total Checks: {result['total_checks']}")
        print(f"   • FP Rate: {result['fp_rate']:.1f}%")
        return 0
    else:
        print(f"❌ {result.get('error', 'Failed to revoke false positive')}")
        return 1


def reset(full: bool = False, threshold: str = None, violation_type: str = None, force: bool = False):
    """Reset drift state (granular or full)"""
    if full and not force:
        confirmation = input("⚠️  This will reset all drift detection state. Continue? (yes/no): ")
        if confirmation.lower() != "yes":
            print("Cancelled.")
            return 1

    success = reset_state(full=full, threshold=threshold, violation_type=violation_type)

    if success:
        print("✅ Reset complete")
        return 0
    else:
        print("❌ Reset failed")
        return 1


def set_threshold(threshold_name: str, value: int):
    """Manually set a threshold with validation"""
    valid_thresholds = {
        "max_hooks": "Maximum number of hooks",
        "max_scratch_files": "Maximum scratch files",
        "max_memory_sessions": "Maximum session state files",
        "max_depth": "Maximum directory depth",
    }

    if threshold_name not in valid_thresholds:
        print(f"❌ Invalid threshold: {threshold_name}")
        print("Valid thresholds:")
        for name, desc in valid_thresholds.items():
            print(f"  • {name}: {desc}")
        return 1

    # Validate value
    if value < 0:
        print(f"❌ Threshold value must be non-negative")
        return 1

    if threshold_name in ["max_hooks", "max_scratch_files", "max_memory_sessions"] and value < 5:
        print(f"❌ {threshold_name} too low (minimum 5)")
        return 1

    if threshold_name == "max_depth" and value < 3:
        print(f"❌ max_depth too low (minimum 3)")
        return 1

    state = load_state()
    old_value = state["thresholds"].get(threshold_name, "unknown")
    state["thresholds"][threshold_name] = value

    if save_state(state):
        print(f"✅ Updated {threshold_name}: {old_value} → {value}")
        return 0
    else:
        print(f"❌ Failed to save state")
        return 1


def get_threshold(threshold_name: str = None):
    """Get current threshold value(s)"""
    state = load_state()

    if threshold_name:
        if threshold_name in state["thresholds"]:
            print(f"{threshold_name}: {state['thresholds'][threshold_name]}")
            return 0
        else:
            print(f"❌ Unknown threshold: {threshold_name}")
            return 1
    else:
        # Show all thresholds
        print("Current thresholds:")
        for name, value in state["thresholds"].items():
            default = DEFAULT_THRESHOLDS.get(name, "?")
            marker = " (modified)" if value != default else " (default)"
            print(f"  • {name}: {value}{marker}")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Organizational Drift Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View drift report
  drift_org.py report

  # Get threshold values
  drift_org.py get
  drift_org.py get max_hooks

  # Record a false positive
  drift_org.py fp hook_explosion

  # Revoke a false positive
  drift_org.py revoke hook_explosion

  # Manually set threshold
  drift_org.py set max_hooks 40

  # Reset all state
  drift_org.py reset --force

  # Reset specific threshold
  drift_org.py reset --threshold max_hooks

  # Reset specific violation stats
  drift_org.py reset --violation hook_explosion
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Report command
    subparsers.add_parser("report", help="Show drift detection report")

    # Get command
    get_parser = subparsers.add_parser("get", help="Get threshold value(s)")
    get_parser.add_argument("threshold", nargs="?", help="Threshold name (optional)")

    # False positive command
    fp_parser = subparsers.add_parser("fp", help="Record a false positive")
    fp_parser.add_argument("type", help="Violation type (e.g., hook_explosion)")

    # Revoke false positive command
    revoke_parser = subparsers.add_parser("revoke", help="Revoke a false positive")
    revoke_parser.add_argument("type", help="Violation type (e.g., hook_explosion)")

    # Set command
    set_parser = subparsers.add_parser("set", help="Manually set a threshold")
    set_parser.add_argument("threshold", help="Threshold name (e.g., max_hooks)")
    set_parser.add_argument("value", type=int, help="New value")

    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset drift state")
    reset_parser.add_argument("--force", action="store_true", help="Skip confirmation")
    reset_parser.add_argument("--threshold", help="Reset specific threshold to default")
    reset_parser.add_argument("--violation", help="Clear stats for specific violation type")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "report":
        return report()
    elif args.command == "get":
        return get_threshold(args.threshold)
    elif args.command == "fp":
        return record_fp(args.type)
    elif args.command == "revoke":
        return revoke_fp(args.type)
    elif args.command == "set":
        return set_threshold(args.threshold, args.value)
    elif args.command == "reset":
        # Determine reset mode
        full = not (args.threshold or args.violation)
        return reset(full=full, threshold=args.threshold, violation_type=args.violation, force=args.force)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
