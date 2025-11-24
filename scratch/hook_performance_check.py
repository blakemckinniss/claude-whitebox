#!/usr/bin/env python3
"""
Hook Performance Analysis
Checks telemetry data for hook performance issues
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT / ".claude/memory"

def load_jsonl(file_path):
    """Load JSONL file"""
    if not file_path.exists():
        return []

    entries = []
    with open(file_path) as f:
        for line in f:
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except:
                    pass
    return entries

def analyze_hook_performance():
    """Analyze hook execution performance"""
    perf_file = MEMORY_DIR / "hook_performance.jsonl"
    if not perf_file.exists():
        return None

    entries = load_jsonl(perf_file)
    if not entries:
        return None

    # Group by hook
    hook_stats = defaultdict(lambda: {
        "count": 0,
        "total_time": 0,
        "max_time": 0,
        "errors": 0
    })

    for entry in entries:
        hook = entry.get("hook", "unknown")
        duration = entry.get("duration_ms", 0)
        success = entry.get("success", True)

        hook_stats[hook]["count"] += 1
        hook_stats[hook]["total_time"] += duration
        hook_stats[hook]["max_time"] = max(hook_stats[hook]["max_time"], duration)
        if not success:
            hook_stats[hook]["errors"] += 1

    # Calculate averages
    for hook, stats in hook_stats.items():
        if stats["count"] > 0:
            stats["avg_time"] = stats["total_time"] / stats["count"]

    return hook_stats

def analyze_batching_telemetry():
    """Analyze batching enforcement telemetry"""
    batch_file = MEMORY_DIR / "batching_telemetry.jsonl"
    if not batch_file.exists():
        return None

    entries = load_jsonl(batch_file)
    if not entries:
        return None

    total_turns = len(entries)
    batched = sum(1 for e in entries if e.get("batched", False))
    sequential = sum(1 for e in entries if not e.get("batched", False) and e.get("tool_count", 0) > 1)

    return {
        "total_turns": total_turns,
        "batched_turns": batched,
        "sequential_turns": sequential,
        "batching_ratio": batched / total_turns if total_turns > 0 else 0,
        "total_time_saved_ms": sum(e.get("time_saved_ms", 0) for e in entries)
    }

def analyze_performance_telemetry():
    """Analyze general performance telemetry"""
    perf_file = MEMORY_DIR / "performance_telemetry.jsonl"
    if not perf_file.exists():
        return None

    entries = load_jsonl(perf_file)
    if not entries:
        return None

    # Count violations by type
    violations = Counter()
    for entry in entries:
        if entry.get("violation"):
            violations[entry.get("violation_type", "unknown")] += 1

    return {
        "total_checks": len(entries),
        "violations": dict(violations),
        "total_violations": sum(violations.values())
    }

def analyze_scratch_telemetry():
    """Analyze scratch-first enforcement"""
    scratch_file = MEMORY_DIR / "scratch_telemetry.jsonl"
    if not scratch_file.exists():
        return None

    entries = load_jsonl(scratch_file)
    if not entries:
        return None

    detections = sum(1 for e in entries if e.get("pattern_detected", False))
    scripts_written = sum(1 for e in entries if e.get("script_written", False))

    return {
        "total_turns": len(entries),
        "detections": detections,
        "scripts_written": scripts_written,
        "adoption_rate": scripts_written / detections if detections > 0 else 0
    }

def check_circuit_breaker():
    """Check circuit breaker state"""
    cb_file = MEMORY_DIR / "circuit_breaker_state.json"
    if not cb_file.exists():
        return None

    with open(cb_file) as f:
        return json.load(f)

def main():
    print("⚡ HOOK PERFORMANCE ANALYSIS\n")
    print("=" * 60)

    # 1. Hook execution performance
    print("\n🏃 HOOK EXECUTION PERFORMANCE:")
    hook_stats = analyze_hook_performance()

    if hook_stats:
        # Sort by total time
        sorted_hooks = sorted(
            hook_stats.items(),
            key=lambda x: x[1]["total_time"],
            reverse=True
        )

        print(f"   • Tracked hooks: {len(hook_stats)}")
        print(f"\n   Top 10 by total time:")
        for hook, stats in sorted_hooks[:10]:
            hook_name = hook.split("/")[-1] if "/" in hook else hook
            print(f"      {hook_name:40} {stats['avg_time']:6.1f}ms avg, {stats['count']:4d} calls")

        # Slow hooks (>100ms avg)
        slow = [(h, s) for h, s in hook_stats.items() if s["avg_time"] > 100]
        if slow:
            print(f"\n   ⚠️  Slow hooks (>100ms avg): {len(slow)}")
            for hook, stats in slow[:5]:
                hook_name = hook.split("/")[-1] if "/" in hook else hook
                print(f"      {hook_name}: {stats['avg_time']:.1f}ms avg")

        # Hooks with errors
        errored = [(h, s) for h, s in hook_stats.items() if s["errors"] > 0]
        if errored:
            print(f"\n   ❌ Hooks with errors: {len(errored)}")
            for hook, stats in errored[:5]:
                hook_name = hook.split("/")[-1] if "/" in hook else hook
                print(f"      {hook_name}: {stats['errors']} errors / {stats['count']} calls")
    else:
        print("   📊 No performance data available")

    # 2. Batching telemetry
    print("\n\n📦 BATCHING ENFORCEMENT:")
    batch_stats = analyze_batching_telemetry()

    if batch_stats:
        ratio = batch_stats["batching_ratio"] * 100
        print(f"   • Total turns: {batch_stats['total_turns']}")
        print(f"   • Batched turns: {batch_stats['batched_turns']}")
        print(f"   • Sequential turns: {batch_stats['sequential_turns']}")
        print(f"   • Batching ratio: {ratio:.1f}% (target: >80%)")
        print(f"   • Time saved: {batch_stats['total_time_saved_ms']:,}ms")

        if ratio < 80:
            print(f"\n   ⚠️  Batching ratio below target!")
    else:
        print("   📊 No batching telemetry available")

    # 3. Performance violations
    print("\n\n🚫 PERFORMANCE VIOLATIONS:")
    perf_stats = analyze_performance_telemetry()

    if perf_stats:
        print(f"   • Total checks: {perf_stats['total_checks']}")
        print(f"   • Total violations: {perf_stats['total_violations']}")

        if perf_stats['violations']:
            print(f"\n   Violations by type:")
            for vtype, count in sorted(perf_stats['violations'].items(), key=lambda x: x[1], reverse=True):
                print(f"      • {vtype}: {count}")
    else:
        print("   📊 No performance telemetry available")

    # 4. Scratch-first adoption
    print("\n\n📝 SCRATCH-FIRST ENFORCEMENT:")
    scratch_stats = analyze_scratch_telemetry()

    if scratch_stats:
        adoption = scratch_stats["adoption_rate"] * 100
        print(f"   • Total turns: {scratch_stats['total_turns']}")
        print(f"   • Detections: {scratch_stats['detections']}")
        print(f"   • Scripts written: {scratch_stats['scripts_written']}")
        print(f"   • Adoption rate: {adoption:.1f}%")

        if adoption < 50:
            print(f"\n   ⚠️  Low script adoption rate!")
    else:
        print("   📊 No scratch telemetry available")

    # 5. Circuit breaker status
    print("\n\n🔌 CIRCUIT BREAKER STATUS:")
    cb_state = check_circuit_breaker()

    if cb_state:
        for key, status in cb_state.items():
            state = status.get("state", "unknown")
            failures = status.get("failure_count", 0)
            emoji = "🔴" if state == "OPEN" else "🟡" if state == "HALF_OPEN" else "🟢"
            print(f"   {emoji} {key}: {state} (failures: {failures})")
    else:
        print("   📊 No circuit breaker data")

    # Summary
    print("\n" + "=" * 60)
    print("📋 PERFORMANCE SUMMARY:")

    warnings = []
    if hook_stats and slow:
        warnings.append(f"{len(slow)} slow hooks")
    if batch_stats and batch_stats["batching_ratio"] < 0.8:
        warnings.append("low batching ratio")
    if scratch_stats and scratch_stats["adoption_rate"] < 0.5:
        warnings.append("low script adoption")
    if perf_stats and perf_stats["total_violations"] > 10:
        warnings.append(f"{perf_stats['total_violations']} performance violations")

    if warnings:
        print(f"   ⚠️  Warnings: {', '.join(warnings)}")
    else:
        print(f"   ✅ Performance healthy!")

if __name__ == "__main__":
    main()
