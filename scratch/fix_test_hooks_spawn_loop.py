#!/usr/bin/env python3
"""
Fix for test_hooks_background.py spawn loop

Problem: start_new_session=True may trigger recursive SessionStart events
Solution: Add spawn guard with file-based locking and cooldown

Strategy:
1. Check if test already running (lock file)
2. Check cooldown (60s minimum between spawns)
3. Remove start_new_session=True (keep parent attached)
4. Add cleanup on completion
"""

fix_code = '''#!/usr/bin/env python3
"""
SessionStart hook: Run hook test suite in background (non-blocking).

Launches test_hooks.py in background process and returns immediately.
Results are persisted to .claude/memory/hook_test_results.json for
later consumption by report_hook_issues.py.

SPAWN GUARD: Prevents recursive spawning via lock file + cooldown.
"""
import json
import sys
import subprocess
import os
import time
from pathlib import Path

def main(event):
    """Launch hook tests in background with spawn protection."""
    try:
        # Find project root
        current = Path(__file__).parent
        while current != Path("/"):
            if (current / "scripts" / "ops" / "test_hooks.py").exists():
                project_root = current
                break
            current = current.parent
        else:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": "⚠️  Hook test suite: Could not find project root"
                }
            }

        test_script = project_root / "scripts" / "ops" / "test_hooks.py"
        lock_file = project_root / ".claude" / "memory" / "test_hooks.lock"

        # SPAWN GUARD 1: Check if already running
        if lock_file.exists():
            try:
                lock_age = time.time() - lock_file.stat().st_mtime
                if lock_age < 60:  # Less than 60s old
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": "SessionStart",
                            "additionalContext": f"🧪 Hook tests already running (started {lock_age:.0f}s ago)"
                        }
                    }
                else:
                    # Stale lock (>60s), remove it
                    lock_file.unlink()
            except:
                pass

        # SPAWN GUARD 2: Cooldown check
        cooldown_file = project_root / ".claude" / "memory" / "test_hooks_last_run.txt"
        if cooldown_file.exists():
            try:
                last_run = float(cooldown_file.read_text().strip())
                elapsed = time.time() - last_run
                if elapsed < 60:  # 60s cooldown
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": "SessionStart",
                            "additionalContext": f"🧪 Hook tests on cooldown ({60-elapsed:.0f}s remaining)"
                        }
                    }
            except:
                pass

        # Create lock file
        lock_file.write_text(str(os.getpid()))

        # Record spawn time
        cooldown_file.write_text(str(time.time()))

        # Launch in background WITHOUT start_new_session
        # (keep attached to prevent recursive session detection)
        process = subprocess.Popen(
            [sys.executable, str(test_script), "--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(project_root)
        )

        # Cleanup lock file after a delay (async)
        # The test script itself will remove the lock when done
        def cleanup_lock():
            import time
            time.sleep(5)  # Give process time to start
            try:
                if lock_file.exists():
                    # Check if process still running
                    try:
                        os.kill(process.pid, 0)  # Signal 0 = check if alive
                        # Still running, don't remove lock
                    except:
                        # Process finished, remove lock
                        lock_file.unlink()
            except:
                pass

        # Start cleanup thread (non-blocking)
        import threading
        threading.Thread(target=cleanup_lock, daemon=True).start()

        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": f"🧪 Hook test suite launched (PID {process.pid})"
            }
        }

    except Exception as e:
        # Clean up lock on error
        try:
            if lock_file.exists():
                lock_file.unlink()
        except:
            pass

        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": f"⚠️  Hook test suite error: {e}"
            }
        }

if __name__ == "__main__":
    try:
        event_data = json.load(sys.stdin)
        result = main(event_data)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": f"Hook execution error: {e}"
            }
        }))
'''

print("Fixed test_hooks_background.py code:")
print("=" * 70)
print(fix_code)
print("=" * 70)

print("\nChanges:")
print("1. Added file-based lock (.claude/memory/test_hooks.lock)")
print("2. Added 60s cooldown (.claude/memory/test_hooks_last_run.txt)")
print("3. Removed start_new_session=True (prevent recursive sessions)")
print("4. Added cleanup thread to remove lock after completion")
print("5. Added PID tracking in lock file")

print("\nApply fix? (Write to .claude/hooks/test_hooks_background.py)")
