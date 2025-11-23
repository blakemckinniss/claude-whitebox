#!/usr/bin/env python3
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

    lines = ["\n⚠️  PERFORMANCE ALERTS (Last 24h):"]

    for alert in alerts:
        severity_icon = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "ℹ️"
        }.get(alert["severity"], "•")

        lines.append(f"{severity_icon} {alert['message']}")

    lines.append("")
    return "\n".join(lines)

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
