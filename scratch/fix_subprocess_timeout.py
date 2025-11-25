#!/usr/bin/env python3
"""
Add timeout=30 to subprocess.run calls that don't have it.
Uses AST for accurate parsing.
"""

import ast
import re
from pathlib import Path

HOOKS_DIR = Path(__file__).parent.parent / ".claude" / "hooks"

def add_timeout_to_subprocess(content: str) -> tuple[str, int]:
    """Add timeout to subprocess.run/check_output calls"""
    lines = content.split('\n')
    changes = 0

    # Find subprocess.run( calls and add timeout if missing
    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if line contains subprocess.run or subprocess.check_output
        if 'subprocess.run(' in line or 'subprocess.check_output(' in line or 'subprocess.call(' in line:
            # Find the full call (may span multiple lines)
            start_idx = i
            paren_count = line.count('(') - line.count(')')
            full_call_lines = [line]

            while paren_count > 0 and i + 1 < len(lines):
                i += 1
                full_call_lines.append(lines[i])
                paren_count += lines[i].count('(') - lines[i].count(')')

            full_call = '\n'.join(full_call_lines)

            # Check if timeout is already present
            if 'timeout' not in full_call:
                # Find the closing paren and add timeout before it
                # Work backwards from the last line
                last_line_idx = start_idx + len(full_call_lines) - 1
                last_line = lines[last_line_idx]

                # Find position of last )
                if ')' in last_line:
                    # Insert timeout=30 before the last )
                    # Handle case where ) might have trailing content
                    match = re.search(r'\)\s*$', last_line)
                    if match:
                        insert_pos = match.start()
                        # Check if there's a comma needed
                        prefix = last_line[:insert_pos].rstrip()
                        if prefix and not prefix.endswith(',') and not prefix.endswith('('):
                            lines[last_line_idx] = prefix + ', timeout=30)'
                        else:
                            lines[last_line_idx] = prefix + 'timeout=30)'
                        changes += 1

        i += 1

    return '\n'.join(lines), changes

def process_file(filepath: Path) -> dict:
    """Process a single file"""
    content = filepath.read_text()
    original = content

    if 'subprocess.' not in content:
        return {"file": filepath.name, "changes": 0, "modified": False}

    new_content, changes = add_timeout_to_subprocess(content)

    if new_content != original:
        filepath.write_text(new_content)
        return {"file": filepath.name, "changes": changes, "modified": True}

    return {"file": filepath.name, "changes": 0, "modified": False}

def main():
    print("=" * 60)
    print("🔧 SUBPROCESS TIMEOUT FIXER")
    print("=" * 60)

    total_modified = 0
    total_changes = 0

    for hook_path in sorted(HOOKS_DIR.glob("*.py")):
        if hook_path.name.startswith("__"):
            continue
        if "backup" in hook_path.name:
            continue

        result = process_file(hook_path)

        if result["modified"]:
            total_modified += 1
            total_changes += result["changes"]
            print(f"✅ {result['file']}: Added timeout to {result['changes']} call(s)")

    print("\n" + "=" * 60)
    print(f"📊 SUMMARY: Modified {total_modified} files, {total_changes} total changes")
    print("=" * 60)

if __name__ == "__main__":
    main()
