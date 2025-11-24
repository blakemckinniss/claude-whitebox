#!/usr/bin/env python3
"""
Batching Telemetry Hook (PostToolUse)

Tracks batching compliance and calculates efficiency metrics.

RECORDS:
- Sequential vs Parallel tool usage patterns
- Tools per message ratio
- Estimated time savings
- Violation patterns

OUTPUT:
- Appends to .claude/memory/batching_telemetry.jsonl
- Generates periodic reports
"""

import sys
import json
import os
import time
from pathlib import Path
from collections import defaultdict

# Environment
PROJECT_DIR = os.getenv("CLAUDE_PROJECT_DIR", os.getcwd())
SESSION_ID = os.getenv("CLAUDE_SESSION_ID", "unknown")
TURN_NUMBER = int(os.getenv("CLAUDE_TURN_NUMBER", "0"))

# Files
TELEMETRY_FILE = Path(PROJECT_DIR) / ".claude" / "memory" / "batching_telemetry.jsonl"
STATE_FILE = Path(PROJECT_DIR) / ".claude" / "memory" / f"session_{SESSION_ID}_state.json"

# Tool timings (estimated average latency in ms)
TOOL_LATENCY = {
    "Read": 100,
    "Write": 150,
    "Edit": 150,
    "Grep": 200,
    "Glob": 100,
    "WebFetch": 500,
    "WebSearch": 800,
    "Bash": 300,
}

BATCHABLE_TOOLS = ["Read", "Grep", "Glob", "WebFetch", "WebSearch"]


def load_state():
    """Load session state"""
    if not STATE_FILE.exists():
        return {}

    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {}


def analyze_turn_batching(state, turn):
    """
    Analyze batching efficiency for a specific turn.

    Returns: {
        "tools_in_turn": int,
        "unique_tools": int,
        "batchable_tools": int,
        "is_batched": bool,
        "efficiency_score": float,
        "estimated_time_saved_ms": int
    }
    """
    if "tool_calls" not in state:
        return None

    turn_calls = [call for call in state["tool_calls"] if call["turn"] == turn]

    if not turn_calls:
        return None

    tools_in_turn = len(turn_calls)
    unique_tools = len(set(call["tool"] for call in turn_calls))

    # Count batchable tools
    batchable = [call for call in turn_calls if call["tool"] in BATCHABLE_TOOLS]
    batchable_count = len(batchable)

    # Is batched? (>1 tool call in single turn)
    is_batched = tools_in_turn > 1

    # Calculate efficiency score
    # Perfect score = all tools batched in one turn
    # Poor score = many turns with 1 tool each
    if is_batched and batchable_count > 1:
        efficiency_score = 1.0  # Perfect batching
    elif batchable_count > 0:
        efficiency_score = 0.5  # Some batchable tools, but not batched
    else:
        efficiency_score = 1.0  # No batchable tools, nothing to optimize

    # Estimate time saved
    # If 3 Read calls in one turn → saved 2 turn latencies (~4s)
    # If 1 Read per turn × 3 turns → wasted 2 turn latencies
    time_saved_ms = 0
    if is_batched and batchable_count > 1:
        # Saved (N-1) turn roundtrips
        turn_latency_ms = 2000  # Assume 2s per turn
        time_saved_ms = (batchable_count - 1) * turn_latency_ms

    return {
        "tools_in_turn": tools_in_turn,
        "unique_tools": unique_tools,
        "batchable_tools": batchable_count,
        "is_batched": is_batched,
        "efficiency_score": efficiency_score,
        "estimated_time_saved_ms": time_saved_ms,
    }


def record_telemetry(analysis):
    """Append telemetry entry to JSONL file"""
    if not analysis:
        return

    TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": time.time(),
        "session_id": SESSION_ID,
        "turn": TURN_NUMBER,
        **analysis
    }

    try:
        with open(TELEMETRY_FILE, 'a') as f:
            f.write(json.dumps(entry) + "\n")
    except:
        pass


def generate_summary_report(lookback_hours=24):
    """
    Generate summary report from recent telemetry.

    Returns: dict with summary stats
    """
    if not TELEMETRY_FILE.exists():
        return None

    cutoff = time.time() - (lookback_hours * 3600)
    entries = []

    try:
        with open(TELEMETRY_FILE) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("timestamp", 0) > cutoff:
                        entries.append(entry)
                except:
                    continue
    except:
        return None

    if not entries:
        return None

    # Calculate summary stats
    total_turns = len(entries)
    total_batched = sum(1 for e in entries if e.get("is_batched", False))
    total_time_saved_ms = sum(e.get("estimated_time_saved_ms", 0) for e in entries)
    avg_tools_per_turn = sum(e.get("tools_in_turn", 0) for e in entries) / total_turns
    avg_efficiency = sum(e.get("efficiency_score", 0) for e in entries) / total_turns

    return {
        "lookback_hours": lookback_hours,
        "total_turns": total_turns,
        "batched_turns": total_batched,
        "batching_ratio": total_batched / total_turns if total_turns > 0 else 0,
        "total_time_saved_ms": total_time_saved_ms,
        "total_time_saved_sec": total_time_saved_ms / 1000,
        "avg_tools_per_turn": avg_tools_per_turn,
        "avg_efficiency_score": avg_efficiency,
    }


def main():
    """Main telemetry logic"""
    try:
        data = json.load(sys.stdin)
    except:
        sys.exit(0)

    tool_name = data.get("tool_name", "")

    # Only track batchable tools
    if tool_name not in BATCHABLE_TOOLS:
        sys.exit(0)

    # Load state
    state = load_state()

    # Analyze current turn
    analysis = analyze_turn_batching(state, TURN_NUMBER)

    # Record telemetry
    if analysis:
        record_telemetry(analysis)

    # Every 10 turns, generate summary report (silent)
    if TURN_NUMBER % 10 == 0:
        summary = generate_summary_report(lookback_hours=24)

        if summary and summary["batching_ratio"] < 0.5:
            # Low batching ratio - inject warning
            message = f"""
⚠️  BATCHING EFFICIENCY REPORT (Last 24h):
   • Batching Ratio: {summary['batching_ratio']:.1%} (Target: >80%)
   • Time Saved: {summary['total_time_saved_sec']:.1f}s
   • Avg Tools/Turn: {summary['avg_tools_per_turn']:.1f}

RECOMMENDATION: Use more parallel tool invocations.
"""

            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": message
                }
            }

            print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
