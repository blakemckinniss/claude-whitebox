#!/usr/bin/env python3
"""
UNIFIED TELEMETRY: PostToolUse Hook
===================================
Consolidates 5 telemetry hooks into ONE for performance.

MERGED FROM:
1. command_tracker.py - Tracks workflow command execution
2. evidence_tracker.py - Updates confidence on tool use
3. batching_telemetry.py - Tracks batching efficiency
4. background_telemetry.py - Tracks background execution ratio
5. performance_telemetry_collector.py - Logs tool execution times

PERFORMANCE GAIN: 5 hooks × ~120ms = 600ms → 1 hook × ~130ms = 130ms (~78% reduction)

TRIGGER: PostToolUse (all tools)
"""

import sys
import json
import re
import time
import os
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

sys.path.insert(0, str(PROJECT_DIR / "scripts" / "lib"))

MEMORY_DIR = PROJECT_DIR / ".claude" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# Environment
SESSION_ID = os.getenv("CLAUDE_SESSION_ID", "unknown")
TURN_NUMBER = int(os.getenv("CLAUDE_TURN_NUMBER", "0"))

# Telemetry files
PERF_LOG = MEMORY_DIR / "performance_telemetry.jsonl"
BATCHING_LOG = MEMORY_DIR / "batching_telemetry.jsonl"
BACKGROUND_LOG = MEMORY_DIR / "background_telemetry.jsonl"

# Constants
BATCHABLE_TOOLS = ["Read", "Grep", "Glob", "WebFetch", "WebSearch"]

COMMAND_PATTERNS = {
    "verify": r"(scripts/ops/verify\.py|/verify\s)",
    "upkeep": r"(scripts/ops/upkeep\.py|/upkeep)",
    "xray": r"(scripts/ops/xray\.py|/xray\s)",
    "think": r"(scripts/ops/think\.py|/think\s)",
    "audit": r"(scripts/ops/audit\.py|/audit\s)",
    "void": r"(scripts/ops/void\.py|/void\s)",
    "research": r"(scripts/ops/research\.py|/research\s)",
}

COMMAND_TIMES = {
    "pytest": 30, "test": 20, "build": 45,
    "install": 60, "docker": 90, "migrate": 30,
}

# =============================================================================
# TELEMETRY FUNCTIONS
# =============================================================================

def log_performance(tool_name: str, session_id: str):
    """Log tool execution (from performance_telemetry_collector)."""
    entry = {
        "timestamp": time.time(),
        "session_id": session_id,
        "tool": tool_name,
        "event": "tool_use"
    }
    try:
        with open(PERF_LOG, 'a') as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def track_command(session_id: str, tool_name: str, command: str, turn: int):
    """Track workflow commands (from command_tracker)."""
    if tool_name != "Bash" or not command:
        return

    try:
        from epistemology import record_command_run
        for cmd_name, pattern in COMMAND_PATTERNS.items():
            if re.search(pattern, command):
                record_command_run(session_id, cmd_name, turn, command)
                break
    except Exception:
        pass


def update_evidence(session_id: str, tool_name: str, tool_params: dict, turn: int) -> str:
    """Update confidence based on tool usage (from evidence_tracker)."""
    if not tool_name:
        return ""

    try:
        from epistemology import (
            load_session_state, initialize_session_state,
            update_confidence, get_confidence_tier
        )

        state = load_session_state(session_id)
        if not state:
            state = initialize_session_state(session_id)

        old_confidence = state.get("confidence", 0)
        new_confidence, boost = update_confidence(
            session_id=session_id,
            tool_name=tool_name,
            tool_input=tool_params,
            turn=turn,
            reason=f"{tool_name} usage",
        )

        if boost != 0:
            tier_name, _ = get_confidence_tier(new_confidence)
            target = ""
            if "file_path" in tool_params:
                target = f" ({Path(tool_params['file_path']).name})"
            elif "query" in tool_params:
                target = f" ('{tool_params['query'][:30]}...')"

            sign = "+" if boost > 0 else ""
            return f"📈 {tool_name}{target}: {old_confidence}%→{new_confidence}% ({sign}{boost}%) [{tier_name}]"
    except Exception:
        pass
    return ""


def log_batching(tool_name: str, state: dict, turn: int):
    """Log batching efficiency (from batching_telemetry)."""
    if tool_name not in BATCHABLE_TOOLS:
        return

    try:
        tool_calls = state.get("tool_calls", [])
        turn_calls = [c for c in tool_calls if c.get("turn") == turn]
        if not turn_calls:
            return

        tools_in_turn = len(turn_calls)
        batchable = [c for c in turn_calls if c.get("tool") in BATCHABLE_TOOLS]
        is_batched = tools_in_turn > 1

        entry = {
            "timestamp": time.time(),
            "session_id": SESSION_ID,
            "turn": turn,
            "tools_in_turn": tools_in_turn,
            "batchable_tools": len(batchable),
            "is_batched": is_batched,
        }

        with open(BATCHING_LOG, 'a') as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def log_background(tool_name: str, command: str, is_background: bool):
    """Log background execution (from background_telemetry)."""
    if tool_name != "Bash" or not command:
        return

    try:
        command_lower = command.lower()
        category = "other"
        if any(x in command_lower for x in ["pytest", "test", "jest"]):
            category = "test"
        elif any(x in command_lower for x in ["build", "webpack", "compile"]):
            category = "build"
        elif any(x in command_lower for x in ["install", "npm i", "pip install"]):
            category = "install"

        est_time = 10
        for pattern, t in COMMAND_TIMES.items():
            if pattern in command_lower:
                est_time = t
                break

        entry = {
            "timestamp": time.time(),
            "session_id": SESSION_ID,
            "turn": TURN_NUMBER,
            "command": command[:100],
            "background": is_background,
            "category": category,
            "estimated_time_sec": est_time
        }

        with open(BACKGROUND_LOG, 'a') as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# =============================================================================
# MAIN
# =============================================================================

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ""}}))
        sys.exit(0)

    session_id = data.get("sessionId", SESSION_ID)
    tool_name = data.get("toolName", "")
    tool_params = data.get("toolParams", {})
    turn = data.get("turn", TURN_NUMBER)

    # Load state once
    state = {}
    try:
        from epistemology import load_session_state
        state = load_session_state(session_id) or {}
    except Exception:
        pass

    turn = state.get("turn_count", turn)

    # Run all telemetry (silent, no blocking)
    log_performance(tool_name, session_id)

    command = tool_params.get("command", "")
    track_command(session_id, tool_name, command, turn)

    log_batching(tool_name, state, turn)

    is_background = tool_params.get("run_in_background", False)
    log_background(tool_name, command, is_background)

    # Evidence tracking (may produce output)
    context = update_evidence(session_id, tool_name, tool_params, turn)

    # Output
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": context
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
