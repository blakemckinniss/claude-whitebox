#!/usr/bin/env python3
"""Test all PreToolUse:Bash hooks to find the broken one"""

import json
import subprocess
import sys
from pathlib import Path

hooks = [
    "root_pollution_gate.py",
    "scratch_flat_enforcer.py",
    "detect_install.py",
    "performance_gate.py",
    "command_prerequisite_gate.py",
    "risk_gate.py",
    "pre_delegation.py",
    "tier_gate.py",
    "force_playwright.py",
    "detect_background_opportunity.py",
    "detect_parallel_bash.py",
    "auto_playwright_setup.py",
]

# Sample Bash tool context
context = {
    "toolName": "Bash",
    "toolParams": {
        "command": "find .claude/hooks -type f -name '*.py' | wc -l"
    }
}

project_dir = Path(__file__).parent.parent
hooks_dir = project_dir / ".claude" / "hooks"

print("Testing PreToolUse:Bash hooks...")
print("=" * 60)

failures = []

for hook_name in hooks:
    hook_path = hooks_dir / hook_name

    try:
        result = subprocess.run(
            ["python3", str(hook_path)],
            input=json.dumps(context),
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(project_dir),
            env={
                **subprocess.os.environ,
                "CLAUDE_PROJECT_DIR": str(project_dir)
            }
        )

        if result.returncode != 0:
            failures.append({
                "hook": hook_name,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            })
            print(f"❌ {hook_name}: EXIT {result.returncode}")
            print(f"   STDERR: {result.stderr[:200]}")
        else:
            # Check for valid JSON output
            try:
                output = json.loads(result.stdout) if result.stdout.strip() else {}
                print(f"✅ {hook_name}: OK")
            except json.JSONDecodeError as e:
                failures.append({
                    "hook": hook_name,
                    "exit_code": 0,
                    "stdout": result.stdout,
                    "stderr": f"Invalid JSON: {e}",
                })
                print(f"⚠️  {hook_name}: Invalid JSON output")
                print(f"   OUTPUT: {result.stdout[:200]}")

    except subprocess.TimeoutExpired:
        failures.append({
            "hook": hook_name,
            "exit_code": -1,
            "stdout": "",
            "stderr": "Timeout after 5s",
        })
        print(f"⏱️  {hook_name}: TIMEOUT")
    except Exception as e:
        failures.append({
            "hook": hook_name,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
        })
        print(f"💥 {hook_name}: {e}")

print("\n" + "=" * 60)
print(f"\nRESULTS: {len(hooks) - len(failures)}/{len(hooks)} passing")

if failures:
    print(f"\nFAILURES ({len(failures)}):")
    for failure in failures:
        print(f"\n{failure['hook']}:")
        print(f"  Exit code: {failure['exit_code']}")
        if failure['stderr']:
            print(f"  Error: {failure['stderr']}")
        if failure['stdout']:
            print(f"  Output: {failure['stdout'][:300]}")

    sys.exit(1)
else:
    print("\n✅ All PreToolUse:Bash hooks working correctly")
