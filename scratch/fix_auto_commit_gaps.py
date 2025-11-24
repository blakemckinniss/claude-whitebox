#!/usr/bin/env python3
"""
Fix critical gaps in auto-commit protocol files
Addresses all void.py findings
"""
from pathlib import Path

# File paths
ENFORCEMENT_LIB = Path("scratch/auto_commit_enforcement.py")
TELEMETRY_HOOK = Path(".claude/hooks/auto_commit_telemetry.py")
PROMPT_HOOK = Path(".claude/hooks/auto_commit_prompt_check.py")
MANAGER_TOOL = Path("scratch/auto_commit_manager.py")

def fix_enforcement_library():
    """Fix enforcement library gaps"""
    content = ENFORCEMENT_LIB.read_text()

    # Fix 1: Add commit history pruning (keep last 100)
    old_record = '        state["commit_history"].append(datetime.now().isoformat())'
    new_record = '''        state["commit_history"].append(datetime.now().isoformat())
        # Prune old history (keep last 100 commits)
        if len(state["commit_history"]) > 100:
            state["commit_history"] = state["commit_history"][-100:]'''
    content = content.replace(old_record, new_record)

    # Fix 2: Better error handling in get_uncommitted_stats
    old_except = '''    except Exception as e:
        return 0, 0, []'''
    new_except = '''    except subprocess.TimeoutExpired:
        # Git timeout - likely large repo
        import sys
        print("⚠️ Git timeout - repo too large for quick stats", file=sys.stderr)
        return 0, 0, []
    except FileNotFoundError:
        # Git not installed or not in PATH
        import sys
        print("⚠️ Git not found - auto-commit monitoring disabled", file=sys.stderr)
        return 0, 0, []
    except Exception as e:
        # Other errors - log but don't crash
        import sys
        print(f"⚠️ Git stats error: {e}", file=sys.stderr)
        return 0, 0, []'''
    content = content.replace(old_except, new_except)

    # Fix 3: Protected save_state
    old_save = '''def save_state(state: Dict) -> None:
    """Save auto-commit state"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)'''
    new_save = '''def save_state(state: Dict) -> None:
    """Save auto-commit state"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except (IOError, OSError) as e:
        # Disk full, permissions, readonly filesystem
        import sys
        print(f"⚠️ Failed to save auto-commit state: {e}", file=sys.stderr)
        # Continue without saving - don't crash'''
    content = content.replace(old_save, new_save)

    # Fix 4: Better exception handling in load_state
    old_load_except = '''    except:
        return {'''
    new_load_except = '''    except (json.JSONDecodeError, IOError, OSError):
        # Corrupted state or I/O error - reset to default
        return {'''
    content = content.replace(old_load_except, new_load_except)

    ENFORCEMENT_LIB.write_text(content)
    print(f"✅ Fixed {ENFORCEMENT_LIB}")


def fix_telemetry_hook():
    """Fix telemetry hook gaps"""
    content = TELEMETRY_HOOK.read_text()

    # Fix 1: Better JSON exception handling
    old_json_except = '''except:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ""
        }
    }))
    sys.exit(0)'''
    new_json_except = '''except (json.JSONDecodeError, ValueError) as e:
    # Malformed JSON input
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": f"⚠️ Hook input parse error: {type(e).__name__}"
        }
    }), file=sys.stderr)
    sys.exit(0)'''
    content = content.replace(old_json_except, new_json_except)

    # Fix 2: Better import error messaging
    old_import = '''except ImportError:
    # Library not available yet
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ""
        }
    }))
    sys.exit(0)'''
    new_import = '''except ImportError as e:
    # Library not available - expected during initial setup
    import sys
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ""  # Silent - expected during setup
        }
    }))
    sys.exit(0)'''
    content = content.replace(old_import, new_import)

    TELEMETRY_HOOK.write_text(content)
    print(f"✅ Fixed {TELEMETRY_HOOK}")


def fix_prompt_hook():
    """Fix prompt hook gaps"""
    content = PROMPT_HOOK.read_text()

    # Fix 1: ZeroDivisionError protection
    old_percent = '''        file_percent = int((file_count / stats['thresholds']['file_count_min']) * 100)
        loc_percent = int((loc_changed / stats['thresholds']['loc_threshold']) * 100)'''
    new_percent = '''        # ZeroDivisionError protection
        file_min = stats['thresholds']['file_count_min']
        loc_thresh = stats['thresholds']['loc_threshold']
        file_percent = int((file_count / file_min) * 100) if file_min > 0 else 0
        loc_percent = int((loc_changed / loc_thresh) * 100) if loc_thresh > 0 else 0'''
    content = content.replace(old_percent, new_percent)

    # Fix 2: Better JSON exception handling
    old_json_except = '''except:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ""
        }
    }))
    sys.exit(0)'''
    new_json_except = '''except (json.JSONDecodeError, ValueError):
    # Malformed JSON - silent failure
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ""
        }
    }))
    sys.exit(0)'''
    content = content.replace(old_json_except, new_json_except)

    PROMPT_HOOK.write_text(content)
    print(f"✅ Fixed {PROMPT_HOOK}")


def fix_manager_tool():
    """Fix manager tool gaps"""
    content = MANAGER_TOOL.read_text()

    # Fix 1: ZeroDivisionError protection in show_stats
    old_progress = '''    # Progress bars
    file_percent = min(100, int((stats['current_file_count'] / stats['thresholds']['file_count_min']) * 100))
    loc_percent = min(100, int((stats['current_loc_changed'] / stats['thresholds']['loc_threshold']) * 100))'''
    new_progress = '''    # Progress bars (ZeroDivisionError protection)
    file_min = stats['thresholds']['file_count_min']
    loc_thresh = stats['thresholds']['loc_threshold']
    file_percent = min(100, int((stats['current_file_count'] / file_min) * 100)) if file_min > 0 else 0
    loc_percent = min(100, int((stats['current_loc_changed'] / loc_thresh) * 100)) if loc_thresh > 0 else 0'''
    content = content.replace(old_progress, new_progress)

    # Fix 2: Add exit codes
    # Replace force_commit function
    old_force = '''def force_commit():
    """Force a commit regardless of thresholds"""
    print("🔧 FORCING AUTO-COMMIT...")
    print()

    result = auto_commit_enforcement.execute_auto_commit(
        auto_commit_enforcement.load_state()
    )

    success, message = result
    print(message)'''
    new_force = '''def force_commit():
    """Force a commit regardless of thresholds"""
    print("🔧 FORCING AUTO-COMMIT...")
    print()

    result = auto_commit_enforcement.execute_auto_commit(
        auto_commit_enforcement.load_state()
    )

    success, message = result
    print(message)

    # Exit with proper code for automation
    sys.exit(0 if success else 1)'''
    content = content.replace(old_force, new_force)

    # Fix 3: Add enable/disable commands
    old_main = '''def main():
    """Main CLI"""
    if len(sys.argv) < 2:
        print("Auto-Commit Manager")
        print()
        print("Usage:")
        print("  python3 auto_commit_manager.py stats      # Show statistics")
        print("  python3 auto_commit_manager.py check      # Check and commit if needed")
        print("  python3 auto_commit_manager.py force      # Force commit now")
        print("  python3 auto_commit_manager.py reset      # Reset state")
        print()
        return

    cmd = sys.argv[1]

    if cmd == "stats":
        show_stats()
    elif cmd == "check":
        check()
    elif cmd == "force":
        force_commit()
    elif cmd == "reset":
        reset()
    else:
        print(f"Unknown command: {cmd}")
        print("Use: stats, check, force, or reset")'''
    new_main = '''def enable():
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
        sys.exit(1)'''
    content = content.replace(old_main, new_main)

    MANAGER_TOOL.write_text(content)
    print(f"✅ Fixed {MANAGER_TOOL}")


if __name__ == "__main__":
    print("=" * 70)
    print("FIXING AUTO-COMMIT PROTOCOL GAPS")
    print("=" * 70)
    print()

    fix_enforcement_library()
    fix_telemetry_hook()
    fix_prompt_hook()
    fix_manager_tool()

    print()
    print("=" * 70)
    print("✅ ALL FIXES APPLIED")
    print("=" * 70)
    print()
    print("Fixed issues:")
    print("  1. ✅ Commit history pruning (prevent unbounded growth)")
    print("  2. ✅ Better git error handling (timeout, missing git, etc.)")
    print("  3. ✅ Protected save_state (disk full, permissions)")
    print("  4. ✅ Better exception types (no bare except)")
    print("  5. ✅ ZeroDivisionError protection (both hooks + manager)")
    print("  6. ✅ Exit codes in manager (automation-friendly)")
    print("  7. ✅ Enable/disable commands added")
    print()
