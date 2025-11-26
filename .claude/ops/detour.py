#!/usr/bin/env python3
"""
CLI management tool for the Detour Protocol - status tracking, resolution, and testing

The Detour Protocol CLI provides command-line access to the detour stack:
- View current detour status (active/resolved)
- Resolve detours when blocking issues are fixed
- Abandon detours when user chooses not to fix
- Test detour detection patterns
- Clear detour state

Usage Examples:
    # Show current detour status
    python3 .claude/ops/detour.py status

    # Resolve most recent detour
    python3 .claude/ops/detour.py resolve

    # Resolve specific detour by ID
    python3 .claude/ops/detour.py resolve abc123

    # Abandon a detour
    python3 .claude/ops/detour.py abandon abc123 "Will fix in next sprint"

    # Peek at current detour without resolving
    python3 .claude/ops/detour.py peek

    # Test detour detection on sample errors
    python3 .claude/ops/detour.py test

    # Clear detour state
    python3 .claude/ops/detour.py clear
"""
import sys
import os

# Add .claude/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
# Find project root by looking for '.claude' directory
_current = _script_dir
while _current != '/':
    if os.path.exists(os.path.join(_current, '.claude', 'lib', 'core.py')):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with .claude/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, '.claude', 'lib'))
from core import setup_script, finalize, logger, handle_debug  # noqa: E402

# Import detour library
from detour import (  # noqa: E402
    get_detour_status_report,
    pop_detour,
    abandon_detour,
    get_resume_prompt,
    peek_detour,
    detect_detour,
    DETOUR_STACK_FILE,
    load_detour_stack
)


def action_status():
    """Show current detour status"""
    report = get_detour_status_report()
    print("\n" + report + "\n")
    return True


def action_resolve(detour_id=None):
    """Resolve a detour (mark as fixed)"""
    resolved = pop_detour(detour_id)

    if not resolved:
        if detour_id:
            logger.error(f"Detour {detour_id} not found in active stack")
        else:
            logger.error("No active detours to resolve")
        return False

    print("\n" + "=" * 70)
    print("✅ DETOUR RESOLVED")
    print("=" * 70)
    print(f"ID: {resolved['id']}")
    print(f"Type: {resolved['detour_type']}")
    print(f"Issue: {resolved['blocking_issue'][:80]}...")
    print(f"\nOriginal Task: {resolved['original_task'][:80]}...")
    print("=" * 70)

    resume_prompt = get_resume_prompt(resolved)
    print(resume_prompt)

    logger.info(f"Detour {resolved['id']} resolved successfully")
    return True


def action_abandon(detour_id, reason):
    """Abandon a detour (user chose not to fix)"""
    if not detour_id:
        logger.error("Detour ID required for abandon action")
        return False

    if not reason:
        logger.error("Reason required for abandoning detour")
        return False

    success = abandon_detour(detour_id, reason)

    if not success:
        logger.error(f"Detour {detour_id} not found in active stack")
        return False

    print("\n" + "=" * 70)
    print("🚫 DETOUR ABANDONED")
    print("=" * 70)
    print(f"ID: {detour_id}")
    print(f"Reason: {reason}")
    print("=" * 70 + "\n")

    logger.info(f"Detour {detour_id} abandoned: {reason}")
    return True


def action_peek():
    """Show current detour without resolving"""
    detour = peek_detour()

    if not detour:
        print("\n📊 No active detours\n")
        return True

    print("\n" + "=" * 70)
    print("👀 CURRENT DETOUR (peek)")
    print("=" * 70)
    print(f"ID: {detour['id']}")
    print(f"Type: {detour['detour_type']}")
    print(f"Severity: {detour['severity']}/10")
    print(f"Status: {detour['status']}")
    print("\nBlocking Issue:")
    print(f"  {detour['blocking_issue'][:150]}...")
    print("\nOriginal Task:")
    print(f"  {detour['original_task'][:150]}...")
    print(f"\nSuggested Agent: {detour['suggested_agent']}")
    print(f"Detected: Turn {detour['detected_at_turn']} ({detour['detected_at_time'][:19]})")

    if detour.get('subagent_id'):
        print(f"Subagent ID: {detour['subagent_id']}")

    print("=" * 70 + "\n")

    return True


def action_test():
    """Test detour detection on sample error outputs"""
    test_cases = [
        ("ModuleNotFoundError: No module named 'pandas'", "Missing module"),
        ("Permission denied: /etc/passwd", "Permission error"),
        ("FileNotFoundError: [Errno 2] No such file or directory: 'config.yaml'", "File not found"),
        ("FAILED tests/test_auth.py::test_login - AssertionError", "Test failure"),
        ("npm ERR! peer dep missing: react@^18.0.0", "npm error"),
        ("Address already in use: 0.0.0.0:8080", "Port conflict"),
        ("ImportError: cannot import name 'validate'", "Import name error"),
        ("SyntaxError: invalid syntax", "Syntax error"),
        ("ConnectionRefusedError: [Errno 111] Connection refused", "Connection refused"),
        ("This is normal output with no errors", "Normal output"),
    ]

    print("\n" + "=" * 70)
    print("🧪 DETOUR DETECTION TEST SUITE")
    print("=" * 70 + "\n")

    detected_count = 0

    for output, description in test_cases:
        print(f"Test: {description}")
        print(f"  Input: {output[:60]}...")

        result = detect_detour(output, "Bash", {"command": "test"})

        if result:
            pattern, matched = result
            detected_count += 1
            print("  ✅ DETECTED")
            print(f"     Type: {pattern.detour_type.value}")
            print(f"     Matched: '{matched[:50]}...'")
            print(f"     Agent: {pattern.suggested_agent}")
            print(f"     Severity: {pattern.severity}/10")
        else:
            print("  ❌ NOT DETECTED")

        print()

    print("=" * 70)
    print(f"Results: {detected_count}/{len(test_cases)} patterns detected")
    print("=" * 70 + "\n")

    return True


def action_clear():
    """Remove detour stack file after confirmation"""
    if not DETOUR_STACK_FILE.exists():
        print("\n📊 No detour stack to clear\n")
        return True

    stack = load_detour_stack()
    active_count = len(stack.get("detours", []))
    resolved_count = len(stack.get("resolved", []))

    if active_count > 0:
        print(f"\n⚠️  WARNING: {active_count} active detour(s) will be lost!")

    print("About to clear detour stack:")
    print(f"  - {active_count} active detours")
    print(f"  - {resolved_count} resolved detours")

    user_input = input("\nContinue? (yes/no): ")
    if user_input.lower() != "yes":
        print("Cancelled")
        return True

    DETOUR_STACK_FILE.unlink()
    print("\n✅ Detour stack cleared\n")
    logger.info("Detour stack cleared")

    return True


def main():
    parser = setup_script("CLI management tool for the Detour Protocol - status tracking, resolution, and testing")

    parser.add_argument(
        "action",
        choices=["status", "resolve", "abandon", "peek", "test", "clear"],
        help="Action to perform"
    )
    parser.add_argument(
        "detour_id",
        nargs="?",
        help="Detour ID (for resolve/abandon actions)"
    )
    parser.add_argument(
        "reason",
        nargs="?",
        help="Reason for abandoning (required for abandon action)"
    )

    args = parser.parse_args()
    handle_debug(args)

    if args.dry_run:
        logger.warning("⚠️  DRY RUN MODE: No changes will be made")

    try:
        success = False

        if args.action == "status":
            success = action_status()

        elif args.action == "resolve":
            if args.dry_run:
                logger.warning("⚠️  DRY RUN: Would resolve detour")
                success = True
            else:
                success = action_resolve(args.detour_id)

        elif args.action == "abandon":
            if not args.detour_id:
                logger.error("Detour ID required for abandon action")
                logger.error("Usage: detour.py abandon <detour_id> <reason>")
                finalize(success=False)
                return

            if not args.reason:
                logger.error("Reason required for abandon action")
                logger.error("Usage: detour.py abandon <detour_id> <reason>")
                finalize(success=False)
                return

            if args.dry_run:
                logger.warning(f"⚠️  DRY RUN: Would abandon detour {args.detour_id}")
                success = True
            else:
                success = action_abandon(args.detour_id, args.reason)

        elif args.action == "peek":
            success = action_peek()

        elif args.action == "test":
            success = action_test()

        elif args.action == "clear":
            if args.dry_run:
                logger.warning("⚠️  DRY RUN: Would clear detour stack")
                success = True
            else:
                success = action_clear()

        finalize(success=success)

    except Exception as e:
        logger.error(f"Operation failed: {e}")
        finalize(success=False)


if __name__ == "__main__":
    main()
