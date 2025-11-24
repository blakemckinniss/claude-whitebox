#!/usr/bin/env python3
"""
Diagnose Auto-Commit Issues
Tests why auto-commit hooks aren't triggering
"""

import subprocess
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

print("🔍 AUTO-COMMIT DIAGNOSTIC\n")
print("=" * 60)

# 1. Check git status
print("\n1. GIT STATUS:")
result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
uncommitted = result.stdout.strip().split('\n') if result.stdout.strip() else []
print(f"   Uncommitted files: {len(uncommitted)}")
if uncommitted[:5]:
    for line in uncommitted[:5]:
        print(f"      {line}")
    if len(uncommitted) > 5:
        print(f"      ... and {len(uncommitted) - 5} more")

# 2. Check hook registration
print("\n2. HOOK REGISTRATION:")
settings_file = ROOT / ".claude/settings.json"
with open(settings_file) as f:
    settings = json.load(f)

session_end_hooks = settings.get("hooks", {}).get("SessionEnd", [])
stop_hooks = settings.get("hooks", {}).get("Stop", [])

session_end_cmds = []
for hook_group in session_end_hooks:
    for hook in hook_group.get("hooks", []):
        cmd = hook.get("command", "")
        if "commit" in cmd:
            session_end_cmds.append(cmd)

print(f"   SessionEnd hooks with 'commit': {len(session_end_cmds)}")
for cmd in session_end_cmds:
    hook_name = cmd.split("/")[-1]
    print(f"      • {hook_name}")

# 3. Test auto_commit_on_end.py manually
print("\n3. TEST auto_commit_on_end.py:")
hook_file = ROOT / ".claude/hooks/auto_commit_on_end.py"

if not hook_file.exists():
    print("   ❌ Hook file not found!")
else:
    print(f"   ✅ Hook file exists: {hook_file}")

    # Test execution
    try:
        result = subprocess.run(
            ["python3", str(hook_file)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=ROOT
        )

        print(f"   Exit code: {result.returncode}")
        print(f"   Output: {result.stdout.strip()}")
        if result.stderr:
            print(f"   Stderr: {result.stderr.strip()}")

    except Exception as e:
        print(f"   ❌ Execution failed: {e}")

# 4. Check auto_janitor.py
print("\n4. TEST auto_janitor.py:")
janitor_file = ROOT / ".claude/hooks/auto_janitor.py"

if not janitor_file.exists():
    print("   ❌ Hook file not found!")
else:
    print(f"   ✅ Hook file exists: {janitor_file}")

    # Test execution
    try:
        result = subprocess.run(
            ["python3", str(janitor_file)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=ROOT
        )

        print(f"   Exit code: {result.returncode}")
        print(f"   Output: {result.stdout[:200] if result.stdout else 'None'}")
        if result.stderr:
            print(f"   Stderr: {result.stderr[:200]}")

    except Exception as e:
        print(f"   ❌ Execution failed: {e}")

# 5. Check if hooks have execute permissions
print("\n5. FILE PERMISSIONS:")
for hook_name in ["auto_commit_on_end.py", "auto_commit_on_complete.py", "auto_janitor.py"]:
    hook_path = ROOT / ".claude/hooks" / hook_name
    if hook_path.exists():
        import stat
        mode = hook_path.stat().st_mode
        is_executable = bool(mode & stat.S_IXUSR)
        print(f"   {hook_name}: {'✅ Executable' if is_executable else '❌ Not executable'}")
    else:
        print(f"   {hook_name}: ❌ Not found")

# 6. Check SessionEnd vs Stop events
print("\n6. HOOK EVENT TYPES:")
print("   SessionEnd: Triggered when Claude Code session ends gracefully")
print("   Stop: Triggered when user explicitly stops operation")
print("")
print("   Note: These events may not fire in all contexts (e.g., IDE close, crash)")

# 7. Recommendations
print("\n7. RECOMMENDATIONS:")

if len(uncommitted) > 0:
    print("   ⚠️  You have uncommitted changes")
    print("   ⚠️  SessionEnd hook should trigger on session close")
    print("")
    print("   Possible reasons auto-commit didn't work:")
    print("   1. Session didn't end gracefully (IDE closed, crash)")
    print("   2. Hook execution failed silently")
    print("   3. Hook is running but not committing due to quality gates")
    print("   4. SessionEnd event not firing in this context")
    print("")
    print("   Manual commit available:")
    print("   1. python3 scripts/ops/upkeep.py")
    print("   2. git add .")
    print("   3. git commit -m 'your message'")
else:
    print("   ✅ No uncommitted changes - hooks would have nothing to commit")

print("\n" + "=" * 60)
print("Diagnostic complete")
