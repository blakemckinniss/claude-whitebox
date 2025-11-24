#!/usr/bin/env python3
"""
Auto-fix: Add timeout parameters to subprocess calls

Analyzes Python files and adds timeout=10 to subprocess calls that are missing it.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).parent.parent


def find_subprocess_calls_without_timeout(content: str) -> List[Tuple[int, str]]:
    """
    Find subprocess calls missing timeout parameter

    Returns: List of (line_number, line_content)
    """
    lines = content.split('\n')
    issues = []

    for i, line in enumerate(lines, 1):
        # Match subprocess.run/call/Popen/check_output
        if re.search(r'subprocess\.(run|call|Popen|check_output)\(', line):
            # Check if timeout is already present
            if 'timeout=' not in line:
                # Check next few lines (multiline calls)
                window = '\n'.join(lines[i-1:min(i+5, len(lines))])
                if 'timeout=' not in window:
                    issues.append((i, line))

    return issues


def add_timeout_to_line(line: str, indent: int = 0) -> str:
    """
    Add timeout parameter to a subprocess call

    Handles both single-line and start of multi-line calls
    """

    # If line ends with ), add timeout before )
    if line.rstrip().endswith(')'):
        # Single-line call
        return line.rstrip()[:-1] + ', timeout=10)'

    # If line ends with comma, add timeout on next line (will be handled by multiline logic)
    # For now, just note that timeout should be added
    return line


def fix_file(filepath: Path, dry_run: bool = True) -> int:
    """
    Fix subprocess calls in a file

    Returns: Number of fixes applied
    """
    content = filepath.read_text()
    issues = find_subprocess_calls_without_timeout(content)

    if not issues:
        return 0

    print(f"\n{filepath.relative_to(PROJECT_ROOT)}")

    lines = content.split('\n')
    fixes_applied = 0

    for line_num, line_content in issues:
        idx = line_num - 1

        # Determine proper timeout value based on context
        timeout = 10  # Default 10s

        # Longer timeouts for specific commands
        if 'git' in line_content and 'push' in line_content:
            timeout = 30  # Git push can be slow
        elif 'pytest' in line_content or 'test' in line_content:
            timeout = 60  # Tests can take time
        elif 'npm' in line_content or 'pip' in line_content:
            timeout = 120  # Package managers can be slow

        # Find where to add timeout
        # Strategy: Look for the closing ) of the subprocess call

        # Check if single-line call
        if ')' in line_content:
            # Single-line: insert before closing )
            original = lines[idx]
            # Find last )
            paren_pos = original.rfind(')')
            fixed = original[:paren_pos] + f', timeout={timeout}' + original[paren_pos:]
            lines[idx] = fixed

            print(f"  Line {line_num}:")
            print(f"    - {original.strip()}")
            print(f"    + {fixed.strip()}")

            fixes_applied += 1

        else:
            # Multi-line call: find closing ) in next few lines
            for j in range(idx, min(idx + 10, len(lines))):
                if ')' in lines[j]:
                    # Found closing paren
                    original = lines[j]
                    paren_pos = original.rfind(')')
                    indent = len(original) - len(original.lstrip())
                    fixed = original[:paren_pos] + f',\n{" " * indent}timeout={timeout}' + original[paren_pos:]
                    lines[j] = fixed

                    print(f"  Lines {line_num}-{j+1}:")
                    print(f"    Added: timeout={timeout}")

                    fixes_applied += 1
                    break

    if fixes_applied > 0 and not dry_run:
        # Write back to file
        filepath.write_text('\n'.join(lines))
        print(f"  ✓ Applied {fixes_applied} fix(es)")
    elif fixes_applied > 0:
        print(f"  [DRY RUN] Would apply {fixes_applied} fix(es)")

    return fixes_applied


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Add timeout to subprocess calls')
    parser.add_argument('--apply', action='store_true', help='Apply fixes (default: dry run)')
    parser.add_argument('--files', nargs='*', help='Specific files to fix (default: all)')
    args = parser.parse_args()

    dry_run = not args.apply

    if dry_run:
        print("="*80)
        print("DRY RUN MODE (use --apply to make changes)")
        print("="*80)

    # Find files to fix
    if args.files:
        files_to_fix = [Path(f) for f in args.files]
    else:
        # Scan all Python files
        files_to_fix = []
        for directory in ['.claude/hooks', 'scripts/ops', 'scripts/lib']:
            dir_path = PROJECT_ROOT / directory
            if dir_path.exists():
                files_to_fix.extend(dir_path.glob('*.py'))

    print(f"\nScanning {len(files_to_fix)} files...")

    total_fixes = 0
    files_fixed = 0

    for filepath in files_to_fix:
        fixes = fix_file(filepath, dry_run=dry_run)
        if fixes > 0:
            total_fixes += fixes
            files_fixed += 1

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Files scanned: {len(files_to_fix)}")
    print(f"Files with issues: {files_fixed}")
    print(f"Total fixes: {total_fixes}")

    if dry_run and total_fixes > 0:
        print("\nTo apply fixes, run:")
        print("  python3 scratch/add_subprocess_timeouts.py --apply")
    elif total_fixes > 0:
        print("\n✓ All fixes applied successfully")


if __name__ == '__main__':
    main()
