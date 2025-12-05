#!/usr/bin/env python3
"""
Auto Learn Hook v4: PostToolUse hook that captures lessons AND provides quality hints.

Hook Type: PostToolUse
Latency Target: <50ms

Automatically captures lessons when:
- Tool execution fails with useful error messages
- Patterns emerge (same error twice = capture)
- Hook blocks with actionable feedback

NEW in v4: Post-action quality hints
- Suggest ruff after Python edits
- Suggest rg over grep
- Tool-specific best practice reminders

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


# =============================================================================
# POST-ACTION QUALITY HINTS (v4)
# =============================================================================

# Hint cooldown state file
HINT_STATE = MEMORY_DIR / "quality_hint_state.json"


def load_hint_state() -> dict:
    """Load hint cooldown state."""
    if HINT_STATE.exists():
        try:
            return json.loads(HINT_STATE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {"last_hints": {}, "session_hints": []}


def save_hint_state(state: dict):
    """Save hint cooldown state."""
    try:
        HINT_STATE.write_text(json.dumps(state, indent=2))
    except IOError:
        pass


def should_show_hint(hint_state: dict, hint_id: str, cooldown: int = 5) -> bool:
    """Check if hint should be shown (avoid spam). Cooldown = tool calls."""
    last_hints = hint_state.get("last_hints", {})
    session_hints = hint_state.get("session_hints", [])

    # Max 3 hints per session for same type
    if session_hints.count(hint_id) >= 3:
        return False

    # Cooldown: don't repeat same hint within N tool calls
    # If never shown before (not in last_hints), allow it
    if hint_id not in last_hints:
        return True

    last_shown_at = last_hints[hint_id]
    current_count = len(session_hints)
    if current_count - last_shown_at < cooldown:
        return False

    return True


def record_hint_shown(hint_state: dict, hint_id: str):
    """Record that a hint was shown."""
    hint_state["session_hints"].append(hint_id)
    hint_state["last_hints"][hint_id] = len(hint_state["session_hints"])
    # Keep bounded
    hint_state["session_hints"] = hint_state["session_hints"][-50:]


def get_quality_hints(tool_name: str, tool_input: dict, tool_output: str) -> list[str]:
    """Generate post-action quality hints based on tool usage."""
    hints = []

    if tool_name in ("Write", "Edit"):
        file_path = tool_input.get("file_path", "")

        # Python file hints
        if file_path.endswith(".py"):
            hints.append(("py_ruff", "Run `ruff check --fix && ruff format` after editing Python"))

        # JavaScript/TypeScript hints
        elif file_path.endswith((".js", ".ts", ".tsx", ".jsx")):
            hints.append(("js_lint", "Run `npm run lint -- --fix` or `eslint --fix` after editing"))

    elif tool_name == "Bash":
        command = tool_input.get("command", "")

        # grep vs ripgrep
        if re.search(r'\bgrep\s+-r', command) and "rg " not in command:
            hints.append(("use_rg", "Use `rg` (ripgrep) instead of `grep -r` for 10-100x speed"))

        # find vs fd
        if re.search(r'\bfind\s+\.\s+-name', command) and "fd " not in command:
            hints.append(("use_fd", "Use `fd` instead of `find . -name` for faster/simpler syntax"))

        # cat large files
        if re.search(r'\bcat\s+\S+\s*\|\s*head', command):
            hints.append(("use_head", "Use `head -n <file>` directly instead of `cat | head`"))

        # pip without -q
        if re.search(r'\bpip\s+install\b', command) and "-q" not in command:
            hints.append(("pip_quiet", "Use `pip install -q` to reduce noise"))

    return hints


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
    tool_input = input_data.get("tool_input", {}) or {}

    messages = []

    # ==========================================================================
    # Part 1: Error Learning (Bash only)
    # ==========================================================================
    if tool_name == "Bash":
        # Check if output contains errors
        if tool_output and ("error" in tool_output.lower() or "failed" in tool_output.lower()):
            lesson = extract_lesson_from_error(tool_output)
            if lesson:
                state = load_state()
                if should_capture(state, lesson):
                    command = tool_input.get("command", "")[:50] if isinstance(tool_input, dict) else ""
                    if write_lesson(lesson, command):
                        state["lessons_written"].append(lesson)
                        state["lessons_written"] = state["lessons_written"][-50:]
                        save_state(state)
                        messages.append(f"🐘 Auto-learned: {lesson[:60]}...")

    # ==========================================================================
    # Part 2: Quality Hints (Write, Edit, Bash)
    # ==========================================================================
    if tool_name in ("Write", "Edit", "Bash"):
        hint_state = load_hint_state()
        raw_hints = get_quality_hints(tool_name, tool_input, tool_output)

        for hint_id, hint_text in raw_hints:
            if should_show_hint(hint_state, hint_id):
                record_hint_shown(hint_state, hint_id)
                messages.append(f"💡 {hint_text}")
                break  # Max 1 hint per tool call

        save_hint_state(hint_state)

    # ==========================================================================
    # Output
    # ==========================================================================
    if messages:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "\n".join(messages),
            }
        }
    else:
        output = {"hookSpecificOutput": {"hookEventName": "PostToolUse"}}

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
