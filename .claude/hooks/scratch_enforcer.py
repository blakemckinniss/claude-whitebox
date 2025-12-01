#!/usr/bin/env python3
"""
Scratch Enforcer Hook v3: Detect repetitive manual work, suggest scripts.

Hook Type: PostToolUse
Latency Target: <10ms (counter-based, no API calls)

Problem: Claude does repetitive manual operations instead of writing scripts
Solution: Track tool call patterns, suggest .claude/tmp/ script after N repetitions
"""

import sys
import json
import time
from pathlib import Path

# =============================================================================
# CONFIG
# =============================================================================

MEMORY_FILE = Path(__file__).resolve().parent.parent / "memory" / "scratch_enforcer_state.json"
REPETITION_THRESHOLD = 4  # Suggest script after this many similar operations
WINDOW_SECONDS = 300  # 5 minute window for pattern detection

# Patterns that indicate repetitive work
REPETITIVE_PATTERNS = {
    "multi_file_edit": {
        "tools": ["Edit", "Write"],
        "threshold": 4,
        "suggestion": "Consider writing a .claude/tmp/ script to batch these edits"
    },
    "multi_file_read": {
        "tools": ["Read"],
        "threshold": 5,
        "suggestion": "Use Glob/Grep or write a .claude/tmp/ analysis script"
    },
    "multi_bash": {
        "tools": ["Bash"],
        "threshold": 4,
        "suggestion": "Chain commands with && or write a .claude/tmp/ script"
    },
    "multi_grep": {
        "tools": ["Grep"],
        "threshold": 4,
        "suggestion": "Write a .claude/tmp/ script for complex multi-pattern search"
    }
}

# =============================================================================
# STATE MANAGEMENT
# =============================================================================

def load_state() -> dict:
    """Load state from memory file."""
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"tool_counts": {}, "last_reset": time.time(), "suggestions_given": []}


def save_state(state: dict):
    """Save state to memory file (atomic write for concurrency safety)."""
    import fcntl
    import tempfile
    import os

    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Use file locking for atomic write
        lock_path = MEMORY_FILE.with_suffix('.lock')
        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)

            # Atomic write: temp file + rename
            fd, tmp_path = tempfile.mkstemp(dir=MEMORY_FILE.parent, suffix='.json')
            with os.fdopen(fd, 'w') as f:
                json.dump(state, f)
            os.replace(tmp_path, MEMORY_FILE)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
    except IOError:
        pass


def cleanup_old_counts(state: dict) -> dict:
    """Reset counts if window expired."""
    now = time.time()
    if now - state.get("last_reset", 0) > WINDOW_SECONDS:
        state["tool_counts"] = {}
        state["last_reset"] = now
        state["suggestions_given"] = []
    return state

# =============================================================================
# DETECTION LOGIC
# =============================================================================

def check_patterns(state: dict) -> str | None:
    """Check if any repetitive pattern threshold is exceeded."""
    counts = state.get("tool_counts", {})
    given = state.get("suggestions_given", [])

    for pattern_name, config in REPETITIVE_PATTERNS.items():
        if pattern_name in given:
            continue  # Already suggested this pattern

        total = sum(counts.get(tool, 0) for tool in config["tools"])
        if total >= config["threshold"]:
            state["suggestions_given"].append(pattern_name)
            return config["suggestion"]

    return None


def main():
    """PostToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if not tool_name:
        print(json.dumps({}))
        sys.exit(0)

    # Load and update state
    state = load_state()
    state = cleanup_old_counts(state)

    # Increment tool counter
    counts = state.setdefault("tool_counts", {})
    counts[tool_name] = counts.get(tool_name, 0) + 1

    # Check for patterns
    suggestion = check_patterns(state)
    save_state(state)

    if suggestion:
        output = {
            "additionalContext": f"🔄 REPETITIVE PATTERN DETECTED:\n   {suggestion}\n   (.claude/tmp/ scripts are faster than manual iteration)"
        }
    else:
        output = {}

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
