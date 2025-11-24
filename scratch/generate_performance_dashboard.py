#!/usr/bin/env python3
"""
Performance Dashboard Generator
Analyzes telemetry and generates human-readable dashboard
"""
import json
import time
from pathlib import Path
from collections import defaultdict, Counter
from statistics import mean, median

PROJECT_ROOT = Path(__file__).parent.parent

TELEMETRY_FILE = PROJECT_ROOT / ".claude" / "memory" / "performance_telemetry.jsonl"
TIMING_FILE = PROJECT_ROOT / ".claude" / "memory" / "hook_timing.jsonl"
DASHBOARD_FILE = PROJECT_ROOT / ".claude" / "memory" / "performance_dashboard.md"

def load_jsonl(filepath, hours=24):
    """Load JSONL file with time filter"""
    if not filepath.exists():
        return []

    cutoff = time.time() - (hours * 3600)
    data = []

    try:
        with open(filepath) as f:
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

def generate_dashboard():
    """Generate performance dashboard"""

    telemetry = load_jsonl(TELEMETRY_FILE, hours=24)
    timing = load_jsonl(TIMING_FILE, hours=24)

    dashboard = f"""# Performance Dashboard

**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}
**Period:** Last 24 hours

---

## Tool Usage

"""

    if telemetry:
        tool_counts = Counter(entry["tool"] for entry in telemetry)
        dashboard += "| Tool | Uses | Frequency |\n"
        dashboard += "|------|------|-----------|\n"

        for tool, count in tool_counts.most_common(10):
            dashboard += f"| {tool} | {count} | {count/24:.1f}/hr |\n"
    else:
        dashboard += "No data available.\n"

    dashboard += "\n---\n\n## Hook Performance\n\n"

    if timing:
        # Group by hook
        by_hook = defaultdict(list)
        for entry in timing:
            by_hook[entry["hook"]].append(entry["elapsed_ms"])

        # Calculate stats
        hook_stats = []
        for hook, times in by_hook.items():
            hook_stats.append({
                "hook": hook,
                "count": len(times),
                "mean": mean(times),
                "median": median(times),
                "max": max(times)
            })

        # Sort by mean
        hook_stats.sort(key=lambda x: x["mean"], reverse=True)

        dashboard += "| Hook | Executions | Mean | Median | Max |\n"
        dashboard += "|------|------------|------|--------|-----|\n"

        for stats in hook_stats[:15]:  # Top 15
            dashboard += f"| {stats['hook']} | {stats['count']} | {stats['mean']:.1f}ms | {stats['median']:.1f}ms | {stats['max']:.1f}ms |\n"

        # Alerts
        dashboard += "\n---\n\n## Alerts\n\n"

        slow_hooks = [s for s in hook_stats if s["mean"] > 100]
        if slow_hooks:
            dashboard += "### Slow Hooks (>100ms mean)\n\n"
            for stats in slow_hooks:
                dashboard += f"- **{stats['hook']}**: {stats['mean']:.1f}ms average\n"
        else:
            dashboard += "✅ All hooks performing well (<100ms mean)\n"
    else:
        dashboard += "No data available.\n"

    # Write dashboard
    try:
        with open(DASHBOARD_FILE, 'w') as f:
            f.write(dashboard)
        print(f"✓ Dashboard generated: {DASHBOARD_FILE}")
    except Exception as e:
        print(f"Error generating dashboard: {e}")

if __name__ == "__main__":
    generate_dashboard()
