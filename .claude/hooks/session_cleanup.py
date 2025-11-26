#!/usr/bin/env python3
"""
Session Cleanup Hook v3: SessionEnd hook for cleanup and persistence.

This hook fires when Claude Code session ends and:
- Persists learned patterns to long-term memory
- Updates lessons.md with session insights
- Cleans up scratch/ temporary files
- Generates session summary for telemetry
- Saves final state snapshot

Silent by default - performs cleanup in background.
"""

import sys
import json
import os
import time
from pathlib import Path
from datetime import datetime

# Import the state machine
from session_state import (
    load_state, save_state, get_session_summary,
    MEMORY_DIR,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRATCH_DIR = Path(__file__).resolve().parent.parent.parent / "scratch"
LESSONS_FILE = MEMORY_DIR / "lessons.md"
SESSION_LOG_FILE = MEMORY_DIR / "session_log.jsonl"

# Files in scratch/ older than this get cleaned (in seconds)
SCRATCH_CLEANUP_AGE = 86400  # 24 hours

# Minimum edits to a file before generating a lesson
LESSON_EDIT_THRESHOLD = 3

# =============================================================================
# PATTERN EXTRACTION
# =============================================================================

def extract_lessons(state) -> list[dict]:
    """Extract lessons from session patterns."""
    lessons = []

    # Lesson: Files edited multiple times (might indicate API complexity)
    for filepath, count in state.edit_counts.items():
        if count >= LESSON_EDIT_THRESHOLD:
            filename = Path(filepath).name
            lessons.append({
                "type": "file_complexity",
                "file": filename,
                "edits": count,
                "insight": f"Edited {filename} {count}x - review for API quirks or complexity",
            })

    # Lesson: Libraries used without research (potential knowledge gap)
    unresearched = set(state.libraries_used) - set(state.libraries_researched)
    if unresearched:
        lessons.append({
            "type": "unresearched_libs",
            "libraries": list(unresearched),
            "insight": f"Used without research: {', '.join(unresearched)}",
        })

    # Lesson: Recurring errors
    error_types = {}
    for error in state.errors_recent:
        etype = error.get("type", "unknown")
        error_types[etype] = error_types.get(etype, 0) + 1

    for etype, count in error_types.items():
        if count >= 2:
            lessons.append({
                "type": "recurring_error",
                "error_type": etype,
                "count": count,
                "insight": f"Recurring error: {etype} ({count}x)",
            })

    # Lesson: Domain detected
    if state.domain != "unknown" and state.domain_confidence > 0.5:
        lessons.append({
            "type": "domain_focus",
            "domain": state.domain,
            "confidence": state.domain_confidence,
            "insight": f"Session focused on {state.domain} ({state.domain_confidence:.0%} confidence)",
        })

    return lessons


def persist_lessons(lessons: list[dict]):
    """Append lessons to lessons.md file."""
    if not lessons:
        return

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Read existing content
    existing = ""
    if LESSONS_FILE.exists():
        existing = LESSONS_FILE.read_text()

    # Check if we already have a lessons section
    if "## Session Lessons" not in existing:
        existing += "\n\n## Session Lessons\n"

    # Add new lessons
    new_content = f"\n### {timestamp}\n"
    for lesson in lessons:
        new_content += f"- [{lesson['type']}] {lesson['insight']}\n"

    # Append to file
    with open(LESSONS_FILE, 'a') as f:
        if "## Session Lessons" not in existing:
            f.write("\n\n## Session Lessons\n")
        f.write(new_content)


# =============================================================================
# SCRATCH CLEANUP
# =============================================================================

def cleanup_scratch():
    """Clean up old files in scratch/ directory."""
    if not SCRATCH_DIR.exists():
        return []

    cleaned = []
    cutoff = time.time() - SCRATCH_CLEANUP_AGE

    for filepath in SCRATCH_DIR.iterdir():
        # Skip .gitkeep and directories
        if filepath.name == ".gitkeep" or filepath.is_dir():
            continue

        try:
            mtime = filepath.stat().st_mtime
            if mtime < cutoff:
                filepath.unlink()
                cleaned.append(filepath.name)
        except (OSError, PermissionError):
            pass

    return cleaned


# =============================================================================
# SESSION LOG
# =============================================================================

def log_session(state, lessons: list[dict]):
    """Append session summary to log file."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    summary = get_session_summary(state)
    summary["ended_at"] = time.time()
    summary["lessons_count"] = len(lessons)
    summary["timestamp"] = datetime.now().isoformat()

    with open(SESSION_LOG_FILE, 'a') as f:
        f.write(json.dumps(summary) + "\n")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """SessionEnd hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        input_data = {}

    # Load current state
    state = load_state()

    # Extract lessons from session patterns
    lessons = extract_lessons(state)

    # Persist lessons to long-term memory
    persist_lessons(lessons)

    # Clean up old scratch files
    cleaned_files = cleanup_scratch()

    # Log session summary
    log_session(state, lessons)

    # Save final state
    save_state(state)

    # Output result (silent unless debugging)
    output = {}

    # Optionally surface cleanup info
    if cleaned_files:
        output["message"] = f"🧹 Cleaned {len(cleaned_files)} old scratch files"

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
