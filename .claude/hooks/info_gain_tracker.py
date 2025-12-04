#!/usr/bin/env python3
"""
Information Gain Tracker Hook: Detects "spinning" - reads without progress.

Hook Type: PostToolUse (on Read/Grep/Glob)
Purpose: Detect when multiple reads yield no decisions/actions.

THE INSIGHT:
Claude can read 10 files and still be confused. This is worse than failures
because it looks like progress but isn't. After N reads without an Edit/Write/
decision, inject: "STALL DETECTED: What question are you trying to answer?"

Behavior:
1. Track Read/Grep/Glob calls
2. Track "progress" actions (Edit, Write, Bash with action commands)
3. If reads_since_progress >= threshold: Inject stall warning
4. Reset on progress action
"""

import sys
import json
import time
from pathlib import Path

# =============================================================================
# CONFIG
# =============================================================================

MEMORY_DIR = Path(__file__).parent.parent / "memory"
STATE_FILE = MEMORY_DIR / "info_gain_state.json"

# Thresholds
# NOTE: Set higher to avoid premature "stop reading" nudges during audits.
# The original 4/7 was too aggressive - caused incomplete infrastructure analysis.
READS_BEFORE_WARN = 8   # Warn after 8 reads without progress
READS_BEFORE_BLOCK = 15  # Consider blocking after 15

# Tools that indicate progress (information was used)
PROGRESS_TOOLS = {"Edit", "Write"}

# Tools that count as "reading" (gathering information)
READ_TOOLS = {"Read", "Grep", "Glob"}

# Bash patterns that indicate progress (not just exploration)
PROGRESS_BASH_PATTERNS = [
    "pytest", "npm test", "npm run", "cargo test", "cargo build",
    "python3 .claude/ops/verify", "python3 .claude/ops/audit",
    "git commit", "git add", "pip install", "npm install",
]

# =============================================================================
# STATE
# =============================================================================

def load_state() -> dict:
    """Load tracker state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "reads_since_progress": 0,
        "last_progress_turn": 0,
        "files_read_this_burst": [],
        "last_stall_warn": 0,
        "total_stall_warnings": 0,
    }


def save_state(state: dict):
    """Save tracker state."""
    try:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except IOError:
        pass


# =============================================================================
# DETECTION
# =============================================================================

def is_progress_bash(command: str) -> bool:
    """Check if Bash command indicates progress (not just exploration)."""
    command_lower = command.lower()
    return any(p in command_lower for p in PROGRESS_BASH_PATTERNS)


def format_stall_warning(state: dict) -> str:
    """Format the stall warning message."""
    reads = state["reads_since_progress"]
    files = state.get("files_read_this_burst", [])[-5:]

    file_names = [Path(f).name if f else "?" for f in files]
    file_list = ", ".join(file_names) if file_names else "multiple files"

    severity = "⚠️" if reads < READS_BEFORE_BLOCK else "🛑"

    lines = [
        f"\n{severity} INFORMATION GAIN CHECK:",
        f"  Reads since last action: {reads}",
        f"  Files: {file_list}",
        "",
        "  **Questions to answer:**",
        "  1. What specific question am I trying to answer?",
        "  2. Did the last read give me actionable info?",
        "  3. Should I act on what I know, or do I need more?",
        "",
    ]

    if reads >= READS_BEFORE_BLOCK:
        lines.append("  💡 Consider: Write what you know to .claude/tmp/ to crystallize.")

    return "\n".join(lines)


# =============================================================================
# HOOK INTERFACE
# =============================================================================

def main():
    """PostToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse"}}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    state = load_state()
    output_context = ""

    # Track read tools
    if tool_name in READ_TOOLS:
        # Safe access - initialize if missing
        if "reads_since_progress" not in state:
            state["reads_since_progress"] = 0
        state["reads_since_progress"] += 1

        # Track files read in this "burst"
        filepath = tool_input.get("file_path", "") or tool_input.get("pattern", "")
        if filepath:
            state["files_read_this_burst"].append(filepath)
            state["files_read_this_burst"] = state["files_read_this_burst"][-10:]

        # Check if we should warn
        reads = state["reads_since_progress"]
        time_since_warn = time.time() - state.get("last_stall_warn", 0)

        # Warn after threshold, but not more than once per 60 seconds
        if reads >= READS_BEFORE_WARN and time_since_warn > 60:
            output_context = format_stall_warning(state)
            state["last_stall_warn"] = time.time()
            # Safe access - initialize if missing
            if "total_stall_warnings" not in state:
                state["total_stall_warnings"] = 0
            state["total_stall_warnings"] += 1

    # Track progress tools (reset counter)
    elif tool_name in PROGRESS_TOOLS:
        state["reads_since_progress"] = 0
        state["files_read_this_burst"] = []
        state["last_progress_turn"] = int(time.time())

    # Check Bash for progress patterns
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        if is_progress_bash(command):
            state["reads_since_progress"] = 0
            state["files_read_this_burst"] = []
            state["last_progress_turn"] = int(time.time())

    save_state(state)

    result = {"hookSpecificOutput": {"hookEventName": "PostToolUse"}}
    if output_context:
        result["hookSpecificOutput"]["additionalContext"] = output_context

    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
