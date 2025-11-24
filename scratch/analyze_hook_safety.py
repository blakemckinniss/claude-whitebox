#!/usr/bin/env python3
"""
Hook Safety Analyzer - Detect memory leaks and runaway loops in hooks
"""
import os
import re
import json
from pathlib import Path
from collections import defaultdict

# Pattern definitions for safety issues
SAFETY_PATTERNS = {
    "infinite_loop": [
        (r"while\s+True\s*:", "Unconditional while True loop"),
        (r"while\s+1\s*:", "Unconditional while 1 loop"),
        (r"for\s+\w+\s+in\s+itertools\.count\(", "Unbounded itertools.count()"),
    ],
    "memory_leak": [
        (r"(\w+)\s*=\s*\[\]\s*\n.*\1\.append\(", "List accumulation without cleanup"),
        (r"(\w+)\s*=\s*\{\}\s*\n.*\1\[", "Dict accumulation without cleanup"),
        (r"global\s+\w+.*\n.*\.append\(", "Global accumulation"),
        (r"cache\s*=\s*\{\}", "Manual cache without size limit"),
    ],
    "unbounded_io": [
        (r"\.readlines\(\)", "Reading all lines into memory"),
        (r"\.read\(\)", "Reading entire file into memory without size check"),
        (r"with\s+open\([^)]+\).*\.read\(\)", "Full file read without size limit"),
    ],
    "recursive_risk": [
        (r"def\s+(\w+).*\n(?:.*\n)*?.*\1\(", "Potential recursive call"),
    ],
    "blocking_ops": [
        (r"requests\.(get|post)\((?![^)]*timeout)", "HTTP request without timeout"),
        (r"subprocess\.run\((?![^)]*timeout)", "Subprocess without timeout"),
        (r"time\.sleep\((\d+)", "Long sleep detected"),
    ]
}

# Good patterns that indicate safety measures
SAFETY_MEASURES = {
    "size_limits": [
        r"if\s+len\([^)]+\)\s*>\s*\d+",
        r"maxlen\s*=",
        r"[:]\s*-\d+",  # List slicing
        r"\.tail\(\d+\)",
    ],
    "timeouts": [
        r"timeout\s*=",
        r"max_age\s*=",
        r"expire",
    ],
    "cleanup": [
        r"\.clear\(\)",
        r"del\s+\w+",
        r"gc\.collect\(",
    ],
    "bounds_checking": [
        r"if\s+.*\s+>\s+\d+.*break",
        r"for.*:\s*\n\s+if.*break",
        r"max_iterations",
    ]
}

def analyze_file(filepath):
    """Analyze a single hook file for safety issues"""
    with open(filepath, 'r') as f:
        content = f.read()

    issues = defaultdict(list)
    protections = defaultdict(list)

    # Check for problematic patterns
    for category, patterns in SAFETY_PATTERNS.items():
        for pattern, description in patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues[category].append({
                    "line": line_num,
                    "description": description,
                    "code": match.group(0)[:80]  # First 80 chars
                })

    # Check for safety measures
    for category, patterns in SAFETY_MEASURES.items():
        for pattern in patterns:
            if re.search(pattern, content):
                protections[category].append(pattern)

    # Special checks
    file_size = os.path.getsize(filepath)
    lines = content.count('\n') + 1

    # Check for state files that grow unbounded
    state_files = re.findall(r'["\']([^"\']*\.json[l]?)["\']', content)
    state_writes = len(re.findall(r'json\.dump|\.write\(', content))

    # Check for append-only logs
    append_ops = len(re.findall(r'\.append\(|\.extend\(|\+=', content))

    return {
        "file": os.path.basename(filepath),
        "size": file_size,
        "lines": lines,
        "issues": dict(issues),
        "protections": dict(protections),
        "state_files": state_files,
        "state_writes": state_writes,
        "append_ops": append_ops,
        "has_cleanup": bool(protections.get("cleanup")),
        "has_size_limits": bool(protections.get("size_limits")),
    }

def get_state_file_sizes():
    """Check actual size of state files"""
    memory_dir = Path(".claude/memory")
    if not memory_dir.exists():
        return {}

    sizes = {}
    for filepath in memory_dir.rglob("*"):
        if filepath.is_file():
            sizes[str(filepath)] = filepath.stat().st_size

    return sizes

def main():
    hooks_dir = Path(".claude/hooks")
    results = []

    print("🔍 Analyzing hook files for memory leaks and runaway loops...\n")

    # Analyze each hook
    for hook_file in sorted(hooks_dir.glob("*.py")):
        result = analyze_file(hook_file)
        results.append(result)

    # Report findings
    critical = []
    warnings = []
    clean = []

    for result in results:
        issue_count = sum(len(v) for v in result["issues"].values())
        protection_count = sum(len(v) for v in result["protections"].values())

        if issue_count > 0 and protection_count == 0:
            critical.append(result)
        elif issue_count > 0:
            warnings.append(result)
        else:
            clean.append(result)

    # Print critical issues
    if critical:
        print("🚨 CRITICAL - Hooks with issues and no protections:\n")
        for result in critical:
            print(f"  {result['file']} ({result['lines']} lines)")
            for category, items in result["issues"].items():
                print(f"    ⚠️  {category}: {len(items)} issue(s)")
                for issue in items[:3]:  # Show first 3
                    print(f"       Line {issue['line']}: {issue['description']}")
            print()

    # Print warnings
    if warnings:
        print("⚠️  WARNINGS - Hooks with potential issues (but have some protections):\n")
        for result in warnings:
            print(f"  {result['file']} ({result['lines']} lines)")
            for category, items in result["issues"].items():
                print(f"    ⚠️  {category}: {len(items)} issue(s)")
            if result["protections"]:
                print(f"    ✅ Protections: {', '.join(result['protections'].keys())}")
            print()

    # State file growth analysis
    print("\n📊 STATE FILE GROWTH ANALYSIS:\n")
    state_sizes = get_state_file_sizes()
    large_files = {k: v for k, v in state_sizes.items() if v > 100000}  # >100KB

    if large_files:
        print("  Large state files (>100KB):")
        for filepath, size in sorted(large_files.items(), key=lambda x: -x[1]):
            print(f"    {filepath}: {size:,} bytes ({size/1024:.1f} KB)")
    else:
        print("  ✅ No state files >100KB")

    # Hooks writing to state files
    print("\n📝 HOOKS WITH STATE FILE WRITES:\n")
    state_writers = [(r["file"], len(r["state_files"]), r["has_cleanup"])
                     for r in results if r["state_writes"] > 0]

    for hook, num_files, has_cleanup in sorted(state_writers, key=lambda x: -x[1]):
        status = "✅" if has_cleanup else "⚠️ "
        print(f"  {status} {hook}: writes to {num_files} state file(s)")

    # Summary statistics
    print(f"\n\n📈 SUMMARY:")
    print(f"  Total hooks analyzed: {len(results)}")
    print(f"  Critical issues: {len(critical)}")
    print(f"  Warnings: {len(warnings)}")
    print(f"  Clean: {len(clean)}")
    print(f"  Total state file size: {sum(state_sizes.values()):,} bytes")

    # Check for hooks with high append operations
    high_append = [r for r in results if r["append_ops"] > 10]
    if high_append:
        print(f"\n⚠️  Hooks with high append operations (>10):")
        for r in high_append:
            print(f"    {r['file']}: {r['append_ops']} append operations")

    # Save detailed report
    report_file = "scratch/hook_safety_report.json"
    with open(report_file, 'w') as f:
        json.dump({
            "critical": critical,
            "warnings": warnings,
            "clean": clean,
            "state_sizes": state_sizes,
            "summary": {
                "total_hooks": len(results),
                "critical_count": len(critical),
                "warning_count": len(warnings),
                "clean_count": len(clean),
            }
        }, f, indent=2)

    print(f"\n💾 Detailed report saved to: {report_file}")

    return len(critical)

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
