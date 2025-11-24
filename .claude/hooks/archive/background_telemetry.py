#!/usr/bin/env python3
"""
Background Execution Telemetry (PostToolUse:Bash)

Tracks background vs foreground Bash execution ratio.
Reports underutilization warnings.

METRICS:
- Background usage ratio
- Estimated time savings
- Unchecked background processes
- Command categories (tests, builds, etc)
"""

import sys
import json
import os
import time
from pathlib import Path

# Environment
PROJECT_DIR = os.getenv("CLAUDE_PROJECT_DIR", os.getcwd())
SESSION_ID = os.getenv("CLAUDE_SESSION_ID", "unknown")
TURN_NUMBER = int(os.getenv("CLAUDE_TURN_NUMBER", "0"))

# Files
TELEMETRY_FILE = Path(PROJECT_DIR) / ".claude" / "memory" / "background_telemetry.jsonl"

# Estimated time savings (rough heuristics)
COMMAND_TIMES = {
    "pytest": 30,
    "test": 20,
    "build": 45,
    "install": 60,
    "docker": 90,
    "migrate": 30,
}


def estimate_command_time(command):
    """Estimate command execution time in seconds"""
    command_lower = command.lower()

    for pattern, time_sec in COMMAND_TIMES.items():
        if pattern in command_lower:
            return time_sec

    # Default estimate
    return 10


def categorize_command(command):
    """Categorize command by type"""
    command_lower = command.lower()

    if any(x in command_lower for x in ["pytest", "test", "jest"]):
        return "test"
    elif any(x in command_lower for x in ["build", "webpack", "compile"]):
        return "build"
    elif any(x in command_lower for x in ["install", "npm i", "pip install"]):
        return "install"
    elif any(x in command_lower for x in ["docker", "compose"]):
        return "docker"
    elif "migrate" in command_lower:
        return "migration"
    else:
        return "other"


def record_telemetry(command, is_background):
    """Append telemetry entry"""
    TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": time.time(),
        "session_id": SESSION_ID,
        "turn": TURN_NUMBER,
        "command": command[:100],  # Truncate long commands
        "background": is_background,
        "category": categorize_command(command),
        "estimated_time_sec": estimate_command_time(command)
    }

    try:
        with open(TELEMETRY_FILE, 'a') as f:
            f.write(json.dumps(entry) + "\n")
    except:
        pass


def analyze_recent_usage(lookback_turns=20):
    """Analyze recent background usage"""
    if not TELEMETRY_FILE.exists():
        return None

    min_turn = TURN_NUMBER - lookback_turns
    entries = []

    try:
        with open(TELEMETRY_FILE) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("session_id") == SESSION_ID and entry.get("turn", 0) >= min_turn:
                        entries.append(entry)
                except:
                    continue
    except:
        return None

    if not entries:
        return None

    total = len(entries)
    background_count = sum(1 for e in entries if e["background"])
    background_ratio = background_count / total if total > 0 else 0

    # Calculate potential time savings if all were background
    total_time = sum(e["estimated_time_sec"] for e in entries)
    time_saved = sum(e["estimated_time_sec"] for e in entries if e["background"])
    potential_savings = total_time - time_saved

    # Category breakdown
    categories = {}
    for entry in entries:
        cat = entry["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "background": 0}
        categories[cat]["total"] += 1
        if entry["background"]:
            categories[cat]["background"] += 1

    return {
        "total_commands": total,
        "background_count": background_count,
        "background_ratio": background_ratio,
        "total_time_sec": total_time,
        "time_saved_sec": time_saved,
        "potential_savings_sec": potential_savings,
        "categories": categories
    }


def generate_report(analysis):
    """Generate underutilization report"""
    if not analysis:
        return ""

    ratio = analysis["background_ratio"]
    target = 0.3  # 30% target for background usage

    if ratio >= target:
        # Good usage, no warning
        return ""

    message = f"""
⚠️  BACKGROUND EXECUTION UNDERUTILIZED (Last {analysis['total_commands']} commands)

Current Stats:
  • Background Usage: {ratio:.0%} (Target: >{target:.0%})
  • Total Commands: {analysis['total_commands']}
  • Background: {analysis['background_count']}
  • Time Saved: {analysis['time_saved_sec']:.0f}s
  • Potential Savings: {analysis['potential_savings_sec']:.0f}s

Category Breakdown:
"""

    for category, stats in analysis["categories"].items():
        cat_ratio = stats["background"] / stats["total"] if stats["total"] > 0 else 0
        message += f"  • {category.capitalize()}: {cat_ratio:.0%} background ({stats['background']}/{stats['total']})\n"

    message += """
RECOMMENDATION:
  Use run_in_background=true for:
  • Tests: pytest, npm test, cargo test
  • Builds: npm run build, cargo build
  • Installs: pip install, npm install
  • Long operations: >5 seconds estimated

Impact:
  • Zero blocking time
  • Parallel execution
  • Faster perceived responsiveness

See: CLAUDE.md § Background Execution Protocol
"""

    return message


def main():
    """Main telemetry logic"""
    try:
        data = json.load(sys.stdin)
    except:
        sys.exit(0)

    # Get command and background status
    tool_params = data.get("parameters", {})
    command = tool_params.get("command", "")
    is_background = tool_params.get("run_in_background", False)

    if not command:
        sys.exit(0)

    # Record telemetry
    record_telemetry(command, is_background)

    # Every 20 turns, analyze and report
    if TURN_NUMBER % 20 == 0 and TURN_NUMBER > 0:
        analysis = analyze_recent_usage(lookback_turns=20)

        if analysis:
            report = generate_report(analysis)

            if report:
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": report
                    }
                }

                print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
