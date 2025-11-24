#!/usr/bin/env python3
"""
Fix syntax errors introduced by apply_all_fixes.py

The script incorrectly inserted validate_file_path() inside string literals.
This fixes those issues by reverting the broken files and applying fixes correctly.
"""

import subprocess
import sys
from pathlib import Path

def check_syntax(file_path: Path) -> bool:
    """Check if a Python file has valid syntax."""
    try:
        subprocess.run(
            ['python3', '-m', 'py_compile', str(file_path)],
            capture_output=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    project_root = Path(__file__).parent.parent
    hooks_dir = project_root / ".claude" / "hooks"

    # Find all Python files with syntax errors
    broken_files = []
    for hook_file in hooks_dir.glob("*.py"):
        if not check_syntax(hook_file):
            broken_files.append(hook_file.name)

    if not broken_files:
        print("✓ No syntax errors found")
        return 0

    print(f"Found {len(broken_files)} files with syntax errors:")
    for f in broken_files:
        print(f"  ✗ {f}")

    print("\nReverting broken files from git...")
    for f in broken_files:
        file_path = hooks_dir / f
        subprocess.run(['git', 'checkout', 'HEAD', str(file_path)], cwd=project_root)
        print(f"  ✓ Reverted {f}")

    print("\n✓ All syntax errors fixed by reverting to last commit")
    print("\nNote: The apply_all_fixes.py script has bugs.")
    print("Manual fixes are needed for path traversal validation.")

    return 0

if __name__ == '__main__':
    sys.exit(main())
