#!/usr/bin/env python3
"""
Hook Performance Monitor

Tracks hook execution times and generates performance reports.
Runs on: PostToolUse (silent tracking)

Generates weekly report identifying slow hooks for optimization.
"""
import sys
import os
import json
import time
from pathlib import Path
from collections import defaultdict
from statistics import mean, median

# Environment
PROJECT_DIR = os.getenv("CLAUDE_PROJECT_DIR", os.getcwd())
PROJECT_ROOT = Path(PROJECT_DIR)

# Performance log
PERF_LOG = PROJECT_ROOT / ".claude" / "memory" / "hook_performance.jsonl"
REPORT_FILE = PROJECT_ROOT / ".claude" / "memory" / "hook_performance_report.md"


def load_performance_data(days=7):
    """Load performance data from last N days"""
    if not PERF_LOG.exists():
        return []

    cutoff = time.time() - (days * 86400)  # N days ago
    data = []

    try:
        with open(PERF_LOG) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("timestamp", 0) > cutoff:
                        data.append(entry)
                except:
                    continue
    except:
        return []

    return data


def analyze_performance(data):
    """Analyze performance data"""
    if not data:
        return None

    # Group by phase
    by_phase = defaultdict(list)

    for entry in data:
        phase = entry.get("phase", "unknown")
        elapsed = entry.get("elapsed_ms", 0)
        by_phase[phase].append(elapsed)

    # Calculate stats
    stats = {}

    for phase, times in by_phase.items():
        stats[phase] = {
            "count": len(times),
            "mean_ms": mean(times),
            "median_ms": median(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "p95_ms": sorted(times)[int(len(times) * 0.95)] if len(times) > 20 else max(times)
        }

    return stats


def generate_report(stats):
    """Generate performance report"""
    if not stats:
        return

    report = f"""# Hook Performance Report

**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}
**Period:** Last 7 days

---

## Summary

"""

    # Sort by mean latency
    sorted_phases = sorted(stats.items(), key=lambda x: x[1]["mean_ms"], reverse=True)

    for phase, data in sorted_phases:
        report += f"""
### {phase}

- **Executions:** {data['count']}
- **Mean:** {data['mean_ms']:.1f}ms
- **Median:** {data['median_ms']:.1f}ms
- **P95:** {data['p95_ms']:.1f}ms
- **Range:** {data['min_ms']:.1f}ms - {data['max_ms']:.1f}ms

"""

    # Recommendations
    report += """---

## Recommendations

"""

    # Find slow phases
    slow_phases = [
        (phase, data)
        for phase, data in stats.items()
        if data["mean_ms"] > 200  # Slow threshold: 200ms
    ]

    if slow_phases:
        report += "### Optimization Targets (>200ms mean)\n\n"
        for phase, data in sorted(slow_phases, key=lambda x: x[1]["mean_ms"], reverse=True):
            report += f"- **{phase}**: {data['mean_ms']:.1f}ms (investigate for parallelization)\n"
    else:
        report += "✅ All phases performing well (< 200ms mean)\n"

    # Write report
    try:
        with open(REPORT_FILE, 'w') as f:
            f.write(report)

        print(f"📊 Hook performance report generated: {REPORT_FILE}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  Could not generate report: {e}", file=sys.stderr)


def main():
    """Monitor hook performance"""
    # Check if it's time to generate report (once per day)
    last_report_time = 0

    if REPORT_FILE.exists():
        try:
            last_report_time = REPORT_FILE.stat().st_mtime
        except:
            pass

    # Generate report if last one is >24h old
    if time.time() - last_report_time > 86400:  # 24 hours
        data = load_performance_data(days=7)

        if data:
            stats = analyze_performance(data)
            generate_report(stats)

    sys.exit(0)


if __name__ == "__main__":
    main()
