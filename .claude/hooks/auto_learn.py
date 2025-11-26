#!/usr/bin/env python3
"""
Auto Learn Hook v3: PostToolUse hook that captures lessons from errors.

Hook Type: PostToolUse
Latency Target: <50ms

Automatically captures lessons when:
- Tool execution fails with useful error messages
- Patterns emerge (same error twice = capture)
- Hook blocks with actionable feedback

Writes to lessons.md without manual intervention.
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime

# =============================================================================
# PATHS
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
MEMORY_DIR = PROJECT_ROOT / ".claude" / "memory"
LESSONS_FILE = MEMORY_DIR / "__lessons.md"
AUTO_LEARN_STATE = MEMORY_DIR / "auto_learn_state.json"

# =============================================================================
# ERROR PATTERN DETECTION
# =============================================================================

# Patterns that indicate useful learnable errors
LEARNABLE_PATTERNS = [
    # Python errors with actionable info
    (r"ModuleNotFoundError: No module named '([^']+)'", "Missing module: {0}"),
    (r"ImportError: cannot import name '([^']+)'", "Import error: {0}"),
    (r"AttributeError: '(\w+)' object has no attribute '(\w+)'", "{0} has no attribute {1}"),
    (r"TypeError: ([^(]+)\(\) got an unexpected keyword argument '(\w+)'", "{0} doesn't accept '{1}' argument"),
    (r"FileNotFoundError: \[Errno 2\].*'([^']+)'", "File not found: {0}"),

    # Hook blocks with reasons
    (r"🛑 GAP: (.+)", "Gap detected: {0}"),
    (r"BLOCKED: (.+)", "Blocked: {0}"),

    # Common CLI errors
    (r"command not found: (\w+)", "Command not found: {0}"),
    (r"Permission denied", "Permission denied"),

    # Git errors
    (r"fatal: (.+)", "Git error: {0}"),
    (r"error: (.+patch.+)", "Patch error: {0}"),
]

# Errors NOT worth capturing (noise)
IGNORE_PATTERNS = [
    r"^\s*$",  # Empty
    r"warning:",  # Warnings not errors
    r"^\d+ passed",  # Test output
    r"ModuleNotFoundError.*No module named 'test_'",  # Test discovery noise
]


def extract_lesson_from_error(output: str) -> str | None:
    """Extract a learnable lesson from error output."""
    # Check ignore patterns first
    for pattern in IGNORE_PATTERNS:
        if re.search(pattern, output, re.IGNORECASE):
            return None

    # Check learnable patterns
    for pattern, template in LEARNABLE_PATTERNS:
        match = re.search(pattern, output)
        if match:
            try:
                lesson = template.format(*match.groups())
                return lesson
            except (IndexError, KeyError):
                return match.group(0)[:100]

    return None


# =============================================================================
# STATE MANAGEMENT
# =============================================================================

def load_state() -> dict:
    """Load auto-learn state."""
    if AUTO_LEARN_STATE.exists():
        try:
            return json.loads(AUTO_LEARN_STATE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {"errors_seen": {}, "lessons_written": []}


def save_state(state: dict):
    """Save auto-learn state."""
    try:
        AUTO_LEARN_STATE.write_text(json.dumps(state, indent=2))
    except IOError:
        pass


def should_capture(state: dict, lesson: str) -> bool:
    """Decide if this lesson should be captured (avoid duplicates)."""
    # Normalize for comparison
    normalized = lesson.lower().strip()

    # Check if already written
    if normalized in [line.lower() for line in state.get("lessons_written", [])]:
        return False

    # Check recent captures (avoid spam)
    recent = state.get("lessons_written", [])[-10:]
    for r in recent:
        # Fuzzy match - if 80% similar, skip
        if len(set(normalized.split()) & set(r.lower().split())) > 3:
            return False

    return True


def write_lesson(lesson: str, context: str = ""):
    """Append lesson to lessons.md."""
    try:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d")
        entry = f"- [{timestamp}] [auto] {lesson}"
        if context:
            entry += f" (context: {context[:50]})"
        entry += "\n"

        # Append to file
        with open(LESSONS_FILE, "a") as f:
            f.write(entry)

        return True
    except IOError:
        return False


# =============================================================================
# MAIN
# =============================================================================

def main():
    """PostToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse"}}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_output = input_data.get("tool_output", "")

    # Only process Bash tool outputs (where errors are most learnable)
    if tool_name != "Bash":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse"}}))
        sys.exit(0)

    # Check if output contains errors
    if not tool_output or "error" not in tool_output.lower() and "failed" not in tool_output.lower():
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse"}}))
        sys.exit(0)

    # Try to extract lesson
    lesson = extract_lesson_from_error(tool_output)

    if not lesson:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse"}}))
        sys.exit(0)

    # Load state and check if we should capture
    state = load_state()

    if not should_capture(state, lesson):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse"}}))
        sys.exit(0)

    # Write the lesson
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")[:50] if isinstance(tool_input, dict) else ""

    if write_lesson(lesson, command):
        state["lessons_written"].append(lesson)
        state["lessons_written"] = state["lessons_written"][-50:]  # Keep last 50
        save_state(state)

        # Notify that a lesson was captured
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"🐘 Auto-learned: {lesson[:60]}...",
            }
        }
    else:
        output = {"hookSpecificOutput": {"hookEventName": "PostToolUse"}}

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
