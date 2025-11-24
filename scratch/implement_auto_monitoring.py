#!/usr/bin/env python3
"""
Implement Automatic Performance Monitoring
Creates self-healing monitoring system that alerts Claude Code when issues detected
"""

from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).parent.parent


def create_telemetry_collector():
    """Create PostToolUse hook to collect performance telemetry"""

    return '''#!/usr/bin/env python3
"""
Performance Telemetry Collector (PostToolUse)
Silently logs hook execution times to structured JSONL file
"""
import sys
import json
import time
from pathlib import Path

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    sys.exit(0)

# Extract data
tool_name = input_data.get("tool_name", "unknown")
session_id = input_data.get("session_id", "unknown")

# Log file
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

LOG_FILE = PROJECT_DIR / ".claude" / "memory" / "performance_telemetry.jsonl"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Simple metric: tool execution (could be enhanced)
entry = {
    "timestamp": time.time(),
    "session_id": session_id,
    "tool": tool_name,
    "event": "tool_use"
}

try:
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry) + "\\n")
except:
    pass

sys.exit(0)
'''


def create_performance_analyzer():
    """Create SessionStart hook to analyze logs and inject warnings"""

    return '''#!/usr/bin/env python3
"""
Performance Analyzer (SessionStart)
Reviews telemetry, detects degradation, injects alerts into context
"""
import sys
import json
import time
from pathlib import Path
from collections import defaultdict, Counter

# Find project root
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

LOG_FILE = PROJECT_DIR / ".claude" / "memory" / "performance_telemetry.jsonl"
ALERT_THRESHOLD_DAYS = 1  # Analyze last 24 hours

def load_recent_telemetry(hours=24):
    """Load telemetry from last N hours"""
    if not LOG_FILE.exists():
        return []

    cutoff = time.time() - (hours * 3600)
    data = []

    try:
        with open(LOG_FILE) as f:
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

def analyze_patterns(data):
    """Detect problematic patterns"""
    alerts = []

    if not data:
        return alerts

    # Pattern 1: Excessive tool usage (potential loop)
    tool_counts = Counter(entry["tool"] for entry in data)
    for tool, count in tool_counts.items():
        if count > 50:  # >50 uses in 24h
            alerts.append({
                "severity": "warning",
                "type": "excessive_tool_use",
                "message": f"Tool '{tool}' used {count} times in 24h (possible loop)"
            })

    # Pattern 2: Session fragmentation (many short sessions)
    session_counts = Counter(entry["session_id"] for entry in data)
    if len(session_counts) > 20:  # >20 sessions in 24h
        alerts.append({
            "severity": "info",
            "type": "session_fragmentation",
            "message": f"{len(session_counts)} sessions in 24h (consider longer sessions)"
        })

    # Pattern 3: Tool diversity (using too many different tools)
    unique_tools = len(tool_counts)
    if unique_tools > 30:
        alerts.append({
            "severity": "info",
            "type": "tool_sprawl",
            "message": f"{unique_tools} different tools used (complexity indicator)"
        })

    return alerts

def generate_context_injection(alerts):
    """Generate context to inject into session"""
    if not alerts:
        return ""

    lines = ["\\n⚠️  PERFORMANCE ALERTS (Last 24h):"]

    for alert in alerts:
        severity_icon = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "ℹ️"
        }.get(alert["severity"], "•")

        lines.append(f"{severity_icon} {alert['message']}")

    lines.append("")
    return "\\n".join(lines)

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    sys.exit(0)

# Analyze telemetry
data = load_recent_telemetry(hours=24)
alerts = analyze_patterns(data)

# Inject context if alerts exist
if alerts:
    context = generate_context_injection(alerts)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context
        }
    }

    print(json.dumps(output))

sys.exit(0)
'''


def create_hook_timing_wrapper():
    """Create wrapper that times individual hooks"""

    return '''#!/usr/bin/env python3
"""
Hook Timing Wrapper
Wraps hooks to measure execution time and log slow hooks
"""
import sys
import json
import time
import subprocess
from pathlib import Path

# Find project root
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

TIMING_LOG = PROJECT_DIR / ".claude" / "memory" / "hook_timing.jsonl"
TIMING_LOG.parent.mkdir(parents=True, exist_ok=True)

# Load hook input
try:
    input_data = json.load(sys.stdin)
except:
    sys.exit(0)

hook_name = sys.argv[1] if len(sys.argv) > 1 else "unknown"

# Execute hook with timing
start = time.time()

try:
    # Run actual hook
    result = subprocess.run(
        ["python3", hook_name],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=60
    )

    elapsed_ms = (time.time() - start) * 1000

    # Log timing
    timing_entry = {
        "timestamp": time.time(),
        "hook": Path(hook_name).name,
        "elapsed_ms": elapsed_ms,
        "success": result.returncode == 0
    }

    try:
        with open(TIMING_LOG, 'a') as f:
            f.write(json.dumps(timing_entry) + "\\n")
    except:
        pass

    # Pass through output
    print(result.stdout, end="")
    sys.exit(result.returncode)

except subprocess.TimeoutExpired:
    elapsed_ms = (time.time() - start) * 1000

    timing_entry = {
        "timestamp": time.time(),
        "hook": Path(hook_name).name,
        "elapsed_ms": elapsed_ms,
        "success": False,
        "error": "timeout"
    }

    try:
        with open(TIMING_LOG, 'a') as f:
            f.write(json.dumps(timing_entry) + "\\n")
    except:
        pass

    sys.exit(1)
'''


def create_dashboard_generator():
    """Create script to generate performance dashboard"""

    return '''#!/usr/bin/env python3
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
        dashboard += "| Tool | Uses | Frequency |\\n"
        dashboard += "|------|------|-----------|\\n"

        for tool, count in tool_counts.most_common(10):
            dashboard += f"| {tool} | {count} | {count/24:.1f}/hr |\\n"
    else:
        dashboard += "No data available.\\n"

    dashboard += "\\n---\\n\\n## Hook Performance\\n\\n"

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

        dashboard += "| Hook | Executions | Mean | Median | Max |\\n"
        dashboard += "|------|------------|------|--------|-----|\\n"

        for stats in hook_stats[:15]:  # Top 15
            dashboard += f"| {stats['hook']} | {stats['count']} | {stats['mean']:.1f}ms | {stats['median']:.1f}ms | {stats['max']:.1f}ms |\\n"

        # Alerts
        dashboard += "\\n---\\n\\n## Alerts\\n\\n"

        slow_hooks = [s for s in hook_stats if s["mean"] > 100]
        if slow_hooks:
            dashboard += "### Slow Hooks (>100ms mean)\\n\\n"
            for stats in slow_hooks:
                dashboard += f"- **{stats['hook']}**: {stats['mean']:.1f}ms average\\n"
        else:
            dashboard += "✅ All hooks performing well (<100ms mean)\\n"
    else:
        dashboard += "No data available.\\n"

    # Write dashboard
    try:
        with open(DASHBOARD_FILE, 'w') as f:
            f.write(dashboard)
        print(f"✓ Dashboard generated: {DASHBOARD_FILE}")
    except Exception as e:
        print(f"Error generating dashboard: {e}")

if __name__ == "__main__":
    generate_dashboard()
'''


def main():
    print("="*80)
    print("IMPLEMENTING AUTOMATIC PERFORMANCE MONITORING")
    print("="*80)

    # 1. Create telemetry collector
    collector_path = PROJECT_ROOT / ".claude" / "hooks" / "performance_telemetry_collector.py"
    collector_path.write_text(create_telemetry_collector())
    print(f"\\n✓ Created: {collector_path.name}")

    # 2. Create performance analyzer
    analyzer_path = PROJECT_ROOT / ".claude" / "hooks" / "performance_analyzer.py"
    analyzer_path.write_text(create_performance_analyzer())
    print(f"✓ Created: {analyzer_path.name}")

    # 3. Create hook timing wrapper
    wrapper_path = PROJECT_ROOT / ".claude" / "hooks" / "hook_timing_wrapper.py"
    wrapper_path.write_text(create_hook_timing_wrapper())
    print(f"✓ Created: {wrapper_path.name}")

    # 4. Create dashboard generator
    dashboard_path = PROJECT_ROOT / "scratch" / "generate_performance_dashboard.py"
    dashboard_path.write_text(create_dashboard_generator())
    dashboard_path.chmod(0o755)
    print(f"✓ Created: {dashboard_path.name}")

    # 5. Instructions
    print("\\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("""
1. Add to settings.json:

PostToolUse hooks:
  - performance_telemetry_collector.py (logs tool usage)

SessionStart hooks:
  - performance_analyzer.py (injects alerts)

2. Generate dashboard:
   python3 scratch/generate_performance_dashboard.py

3. View results:
   cat .claude/memory/performance_dashboard.md

Features:
  ✓ Silent telemetry collection (PostToolUse)
  ✓ Automatic alert injection (SessionStart)
  ✓ Human-readable dashboard (manual)
  ✓ Pattern detection (loops, fragmentation, sprawl)
  ✓ Hook timing logs

Alerts trigger on:
  - Excessive tool use (>50 uses/24h)
  - Session fragmentation (>20 sessions/24h)
  - Tool sprawl (>30 different tools)
  - Slow hooks (>100ms mean)
    """)


if __name__ == "__main__":
    main()
