#!/usr/bin/env python3
"""
System Usage Profiler - Detect zombie processes and resource leaks

Checks:
1. Zombie processes (defunct subprocesses from hooks)
2. Memory usage by Python processes
3. CPU usage patterns
4. Open file descriptors (hook scripts holding files)
5. Process tree analysis (orphaned hook children)

Expected: Clean process tree, no zombies, minimal memory footprint
Red flags: >10 zombie processes, >500MB hook memory, >100 orphaned processes
"""

import subprocess
import json
import time
from pathlib import Path
from collections import defaultdict

def get_process_tree():
    """Get full process tree focused on Python processes"""
    result = subprocess.run(
        ["ps", "auxf"],
        capture_output=True,
        text=True
    )
    return result.stdout

def get_zombie_processes():
    """Find zombie (defunct) processes"""
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )

    zombies = []
    for line in result.stdout.split('\n')[1:]:  # Skip header
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 8:
            # Check for <defunct> or Z state
            if '<defunct>' in line or (len(parts[7]) > 0 and 'Z' in parts[7]):
                zombies.append(line)

    return zombies

def get_python_processes():
    """Get all Python processes with resource usage"""
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )

    python_procs = []
    for line in result.stdout.split('\n')[1:]:
        if 'python' in line.lower():
            parts = line.split()
            if len(parts) >= 11:
                python_procs.append({
                    'user': parts[0],
                    'pid': parts[1],
                    'cpu': parts[2],
                    'mem': parts[3],
                    'vsz': parts[4],
                    'rss': parts[5],
                    'state': parts[7],
                    'command': ' '.join(parts[10:])[:100],
                })

    return python_procs

def get_hook_processes():
    """Find processes running hook scripts"""
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )

    hook_procs = []
    for line in result.stdout.split('\n')[1:]:
        if '.claude/hooks/' in line:
            parts = line.split()
            if len(parts) >= 11:
                hook_procs.append({
                    'pid': parts[1],
                    'cpu': parts[2],
                    'mem': parts[3],
                    'state': parts[7],
                    'command': ' '.join(parts[10:])[:100],
                })

    return hook_procs

def get_open_files():
    """Count open file descriptors for current process"""
    try:
        result = subprocess.run(
            ["lsof", "-p", str(subprocess.os.getpid())],
            capture_output=True,
            text=True
        )
        return len(result.stdout.split('\n')) - 1  # Subtract header
    except:
        return "N/A (lsof not available)"

def get_memory_usage():
    """Get memory usage statistics"""
    result = subprocess.run(
        ["free", "-h"],
        capture_output=True,
        text=True
    )
    return result.stdout

def analyze_hook_lifecycle():
    """Analyze hook execution patterns from performance telemetry"""
    telemetry_file = Path(__file__).parent.parent / ".claude" / "memory" / "performance_telemetry.jsonl"

    if not telemetry_file.exists():
        return None

    hook_stats = defaultdict(lambda: {'count': 0, 'total_time': 0})

    try:
        with open(telemetry_file) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if 'tool_name' in entry and entry.get('tool_name') in ['Read', 'Write', 'Edit', 'Bash']:
                        # This represents hook executions
                        hook_stats['total']['count'] += 1
                except:
                    continue
    except Exception as e:
        return {"error": str(e)}

    return dict(hook_stats)

def main():
    print("=" * 70)
    print("SYSTEM RESOURCE PROFILING - Hook Process Analysis")
    print("=" * 70)

    # 1. Zombie Process Check
    print("\n[1] ZOMBIE PROCESS CHECK")
    print("-" * 70)
    zombies = get_zombie_processes()
    if zombies:
        print(f"⚠️  FOUND {len(zombies)} ZOMBIE PROCESSES:")
        for zombie in zombies[:10]:  # Show first 10
            print(f"  {zombie}")
    else:
        print("✅ No zombie processes detected")

    # 2. Python Process Analysis
    print("\n[2] PYTHON PROCESS ANALYSIS")
    print("-" * 70)
    python_procs = get_python_processes()

    total_mem_mb = sum(int(p['rss']) for p in python_procs) / 1024
    print(f"Total Python processes: {len(python_procs)}")
    print(f"Total memory usage: {total_mem_mb:.1f} MB")

    # Sort by memory
    python_procs.sort(key=lambda p: int(p['rss']), reverse=True)
    print(f"\nTop 10 by memory:")
    for proc in python_procs[:10]:
        mem_mb = int(proc['rss']) / 1024
        print(f"  PID {proc['pid']}: {mem_mb:>6.1f} MB | CPU {proc['cpu']:>5}% | {proc['command'][:60]}")

    # 3. Hook Process Check
    print("\n[3] ACTIVE HOOK PROCESSES")
    print("-" * 70)
    hook_procs = get_hook_processes()
    if hook_procs:
        print(f"⚠️  FOUND {len(hook_procs)} RUNNING HOOK PROCESSES:")
        for proc in hook_procs:
            print(f"  PID {proc['pid']}: {proc['state']} | CPU {proc['cpu']}% | {proc['command'][:60]}")
    else:
        print("✅ No hook processes currently running (expected)")

    # 4. File Descriptor Check
    print("\n[4] FILE DESCRIPTOR USAGE")
    print("-" * 70)
    open_fds = get_open_files()
    print(f"Open file descriptors (this process): {open_fds}")
    if isinstance(open_fds, int):
        if open_fds > 1000:
            print("⚠️  High file descriptor count - possible leak")
        else:
            print("✅ File descriptor count normal")

    # 5. Memory Overview
    print("\n[5] SYSTEM MEMORY OVERVIEW")
    print("-" * 70)
    print(get_memory_usage())

    # 6. Process Tree Sample
    print("\n[6] PROCESS TREE (Python processes only)")
    print("-" * 70)
    tree = get_process_tree()
    python_lines = [line for line in tree.split('\n') if 'python' in line.lower()]
    for line in python_lines[:20]:  # Show first 20
        print(line)

    # 7. Summary & Recommendations
    print("\n" + "=" * 70)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 70)

    issues = []

    if zombies:
        issues.append(f"❌ {len(zombies)} zombie processes detected")

    if hook_procs:
        issues.append(f"⚠️  {len(hook_procs)} hook processes still running (may be stuck)")

    if isinstance(open_fds, int) and open_fds > 1000:
        issues.append(f"⚠️  High file descriptor usage ({open_fds})")

    if total_mem_mb > 500:
        issues.append(f"⚠️  High Python memory usage ({total_mem_mb:.1f} MB)")

    if not issues:
        print("✅ SYSTEM HEALTHY - No resource leaks detected")
        print("\nMetrics:")
        print(f"  • Python processes: {len(python_procs)}")
        print(f"  • Total Python memory: {total_mem_mb:.1f} MB")
        print(f"  • Zombie processes: 0")
        print(f"  • Active hooks: 0")
    else:
        print("⚠️  ISSUES DETECTED:\n")
        for issue in issues:
            print(f"  {issue}")

        print("\nRecommended Actions:")
        if zombies:
            print("  1. Kill zombie processes: kill -9 <pid>")
            print("  2. Check parent process for proper wait() calls")

        if hook_procs:
            print("  3. Investigate stuck hooks: ps -p <pid> -o etime,cmd")
            print("  4. Kill stuck hooks: kill <pid>")

        if isinstance(open_fds, int) and open_fds > 1000:
            print("  5. Check for file descriptor leaks in hooks")
            print("  6. Run: lsof -p $$ | wc -l")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
