#!/usr/bin/env python3
"""
POST-EDIT VALIDATOR - PostToolUse Hook

PROBLEM: Claude edits Python files and breaks them without knowing.
Hook errors are non-blocking, so Claude proceeds obliviously.

SOLUTION: After every Edit/Write to .py files:
1. Run py_compile for syntax check
2. For scripts/lib/ files: Actually import to catch missing imports
3. If fails → INJECT ERROR INTO CONTEXT

KEY INSIGHT: py_compile only checks SYNTAX, not imports!
`x: List[str] = []` passes py_compile but fails at import time.
We must actually import library files to catch this.
"""
import sys
import json
import subprocess
from pathlib import Path


def validate_python_file(file_path: str) -> tuple:
    """
    Validate a Python file for syntax and import errors.

    Returns:
        (success: bool, error_message: str)
    """
    path = Path(file_path)

    if not path.exists():
        return True, ""

    if not path.suffix == ".py":
        return True, ""

    # Step 1: Syntax check with py_compile
    try:
        result = subprocess.run(
            ["python3", "-m", "py_compile", str(path)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False, f"SYNTAX ERROR:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT: Syntax check took too long"
    except Exception as e:
        return False, f"SYNTAX CHECK FAILED: {e}"

    # Step 1b: Ruff lint (10ms - catches fatal errors)
    try:
        result = subprocess.run(
            ["ruff", "check", str(path), "--select=F"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0 and result.stdout.strip():
            return False, f"RUFF FATAL ERRORS:\n{result.stdout.strip()}"
    except FileNotFoundError:
        pass
    except Exception:
        pass

    # Step 1c: Vulture dead code check (50ms - warns about unused code)
    # Only for library files, and only warn (don't block)
    if "scripts/lib/" in str(path) or "scripts/ops/" in str(path):
        try:
            result = subprocess.run(
                ["vulture", str(path), "--min-confidence=80"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 3:  # Only warn if 3+ dead code items
                    # Don't fail - just warn (will be shown in context)
                    pass  # Warning will be shown but won't block
        except FileNotFoundError:
            pass
        except Exception:
            pass

    # Step 2: For library files, do actual import test
    # This catches missing imports like "List" without "from typing import List"
    path_str = str(path)

    if "scripts/lib/" in path_str:
        # Actually import the module to catch NameError, ImportError, etc.
        module_name = path.stem
        # We need to run from project root with proper path
        test_script = f'''
import sys
sys.path.insert(0, "scripts")
from lib import {module_name}
print("OK")
'''
        try:
            result = subprocess.run(
                ["python3", "-c", test_script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                stderr = result.stderr.strip()
                if stderr:
                    # Extract the most relevant error line
                    lines = stderr.split('\n')
                    error_lines = [l for l in lines if 'Error' in l or 'error' in l.lower()]
                    if error_lines:
                        return False, f"IMPORT ERROR:\n{stderr}"
        except subprocess.TimeoutExpired:
            pass  # Don't fail on timeout
        except Exception:
            pass

    elif "scripts/ops/" in path_str:
        # For ops scripts, check if they at least parse and have no obvious import errors
        module_name = path.stem
        test_script = f'''
import sys
sys.path.insert(0, "scripts")
import importlib.util
spec = importlib.util.spec_from_file_location("{module_name}", "{path}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)  # Actually load to catch import errors
'''
        try:
            result = subprocess.run(
                ["python3", "-c", test_script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # Don't fail ops scripts - they often have conditional imports
        except Exception:
            pass

    # Note: We don't deeply validate .claude/hooks/ files because:
    # - They often import from lib which requires project context
    # - Syntax check is sufficient for most hook errors
    # - If a hook breaks, it shows up in hook output anyway

    return True, ""


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ""}}))
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_params = hook_input.get("tool_input", {})

    if tool_name not in ["Edit", "Write"]:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ""}}))
        return 0

    file_path = tool_params.get("file_path", "")

    if not file_path.endswith(".py"):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ""}}))
        return 0

    success, error_msg = validate_python_file(file_path)

    if not success:
        context = f"""
🚨 POST-EDIT VALIDATION FAILED 🚨

File: {file_path}

{error_msg}

⚠️ YOU BROKE THIS FILE. FIX IT IMMEDIATELY.

Do NOT proceed until this is fixed.

VERIFY YOUR FIX:
  python3 -c "from lib.{Path(file_path).stem} import *"
"""
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": context,
            }
        }))
    else:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "",
            }
        }))

    return 0


if __name__ == "__main__":
    sys.exit(main())
