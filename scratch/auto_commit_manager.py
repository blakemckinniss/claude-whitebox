#!/usr/bin/env python3
"""
Auto-Commit Management Tool
View stats, reset state, manually trigger commits
"""
import sys
from pathlib import Path

# Add scratch to path
scratch_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(scratch_dir))

import auto_commit_enforcement


def show_stats():
    """Show detailed auto-commit statistics"""
    stats = auto_commit_enforcement.get_stats()

    print("=" * 70)
    print("AUTO-COMMIT STATISTICS (AGGRESSIVE MODE)")
    print("=" * 70)
    print()

    # Status
    print(f"Status: {'✅ ENABLED' if stats['enabled'] else '❌ DISABLED'}")
    print(f"Total Auto-Commits: {stats['total_auto_commits']}")
    print(f"Commit History Count: {stats['commit_history_count']}")
    print()

    # Current state
    print("CURRENT UNCOMMITTED:")
    print(f"  Files: {stats['current_file_count']}")
    print(f"  LOC Changed: {stats['current_loc_changed']}")
    print()

    # Thresholds
    print("THRESHOLDS (AGGRESSIVE):")
    print(f"  File Count: {stats['thresholds']['file_count_min']}-{stats['thresholds']['file_count_max']}")
    print(f"  LOC Changed: {stats['thresholds']['loc_threshold']}")
    print(f"  Mode: {'COMBINED (both must trigger)' if stats['thresholds']['combined_mode'] else 'INDIVIDUAL (either can trigger)'}")
    print()

    # Trigger status
    print(f"WILL COMMIT NEXT: {'🔴 YES' if stats['will_commit_next'] else '🟢 NO'}")
    print(f"Reason: {stats['commit_reason']}")
    print()

    # Progress bars (ZeroDivisionError protection)
    file_min = stats['thresholds']['file_count_min']
    loc_thresh = stats['thresholds']['loc_threshold']
    file_percent = min(100, int((stats['current_file_count'] / file_min) * 100)) if file_min > 0 else 0
    loc_percent = min(100, int((stats['current_loc_changed'] / loc_thresh) * 100)) if loc_thresh > 0 else 0

    print(f"File Progress: [{'█' * (file_percent // 10)}{'░' * (10 - file_percent // 10)}] {file_percent}%")
    print(f"LOC Progress:  [{'█' * (loc_percent // 10)}{'░' * (10 - loc_percent // 10)}] {loc_percent}%")
    print()

    # Last failure
    if stats['last_failure']:
        print(f"⚠️ Last Failure: {stats['last_failure']}")
        print()

    # Initialized
    print(f"Initialized: {stats['initialized_at']}")
    print()


def force_commit():
    """Force a commit regardless of thresholds"""
    print("🔧 FORCING AUTO-COMMIT...")
    print()

    result = auto_commit_enforcement.execute_auto_commit(
        auto_commit_enforcement.load_state()
    )

    success, message = result
    print(message)

    # Exit with proper code for automation
    sys.exit(0 if success else 1)


def reset():
    """Reset auto-commit state"""
    print("🔄 RESETTING AUTO-COMMIT STATE...")
    print()

    message = auto_commit_enforcement.reset_state()
    print(message)


def check():
    """Check if commit is needed and execute"""
    result = auto_commit_enforcement.check_and_commit()

    if result:
        print(result)
    else:
        print("✅ No auto-commit needed (below thresholds)")


def enable():
    """Enable auto-commit enforcement"""
    state = auto_commit_enforcement.load_state()
    state["enabled"] = True
    auto_commit_enforcement.save_state(state)
    print("✅ Auto-commit ENABLED")
    sys.exit(0)


def disable():
    """Disable auto-commit enforcement"""
    state = auto_commit_enforcement.load_state()
    state["enabled"] = False
    auto_commit_enforcement.save_state(state)
    print("⏸️ Auto-commit DISABLED")
    sys.exit(0)


def main():
    """Main CLI"""
    if len(sys.argv) < 2:
        print("Auto-Commit Manager")
        print()
        print("Usage:")
        print("  python3 auto_commit_manager.py stats      # Show statistics")
        print("  python3 auto_commit_manager.py check      # Check and commit if needed")
        print("  python3 auto_commit_manager.py force      # Force commit now")
        print("  python3 auto_commit_manager.py reset      # Reset state")
        print("  python3 auto_commit_manager.py enable     # Enable enforcement")
        print("  python3 auto_commit_manager.py disable    # Disable enforcement")
        print()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "stats":
        show_stats()
        sys.exit(0)
    elif cmd == "check":
        check()
        sys.exit(0)
    elif cmd == "force":
        force_commit()  # Has own exit code
    elif cmd == "reset":
        reset()
        sys.exit(0)
    elif cmd == "enable":
        enable()
    elif cmd == "disable":
        disable()
    else:
        print(f"Unknown command: {cmd}")
        print("Use: stats, check, force, reset, enable, or disable")
        sys.exit(1)


if __name__ == "__main__":
    main()
