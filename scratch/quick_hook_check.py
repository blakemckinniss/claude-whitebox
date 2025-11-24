#!/usr/bin/env python3
"""Quick hook safety check - look for obvious issues only"""
import os
from pathlib import Path
import json

def check_file(filepath):
    """Quick check for obvious issues"""
    with open(filepath, 'r') as f:
        content = f.read()

    issues = []

    # Check for while True without any break
    if 'while True:' in content or 'while 1:' in content:
        # Check if there's a break statement nearby
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'while True:' in line or 'while 1:' in line:
                # Check next 20 lines for break
                has_break = any('break' in lines[j] for j in range(i, min(i+20, len(lines))))
                if not has_break:
                    issues.append(f"Line {i+1}: while True without visible break")

    # Check for unbounded list/dict accumulation
    if '.append(' in content and 'clear()' not in content and 'del ' not in content:
        if content.count('.append(') > 5:
            issues.append(f"Multiple append operations ({content.count('.append(')}) without cleanup")

    # Check for readlines() - reads entire file into memory
    if '.readlines()' in content:
        issues.append("Uses .readlines() - loads entire file into memory")

    # Check for requests without timeout
    if 'requests.' in content and 'timeout=' not in content:
        issues.append("HTTP requests without timeout parameter")

    return issues

def check_state_files():
    """Check size of state files"""
    memory_dir = Path(".claude/memory")
    if not memory_dir.exists():
        return {}

    large_files = {}
    for f in memory_dir.rglob("*"):
        if f.is_file():
            size = f.stat().st_size
            if size > 100000:  # >100KB
                large_files[str(f)] = size

    return large_files

def main():
    hooks_dir = Path(".claude/hooks")

    print("🔍 Quick Hook Safety Check\n")

    # Check each hook
    problems = {}
    for hook_file in sorted(hooks_dir.glob("*.py")):
        issues = check_file(hook_file)
        if issues:
            problems[hook_file.name] = issues

    # Report
    if problems:
        print(f"⚠️  Found {len(problems)} hooks with potential issues:\n")
        for filename, issues in problems.items():
            print(f"  {filename}:")
            for issue in issues:
                print(f"    - {issue}")
            print()
    else:
        print("✅ No obvious issues found in hooks\n")

    # Check state files
    large_files = check_state_files()
    if large_files:
        print("📊 Large state files (>100KB):")
        for filepath, size in sorted(large_files.items(), key=lambda x: -x[1]):
            print(f"  {filepath}: {size:,} bytes ({size/1024/1024:.2f} MB)")
        print()
    else:
        print("✅ No large state files found\n")

    # Count hooks
    hook_count = len(list(hooks_dir.glob("*.py")))
    print(f"📈 Total hooks: {hook_count}")

    return len(problems)

if __name__ == "__main__":
    exit(main())
