#!/usr/bin/env python3
"""
Session Cleanup Hook v3: SessionEnd hook for cleanup and persistence.

This hook fires when Claude Code session ends and:
- Persists learned patterns to long-term memory
- Updates lessons.md with session insights
- Cleans up .claude/tmp/ temporary files
- Generates session summary for telemetry
- Saves final state snapshot

Silent by default - performs cleanup in background.
"""

import _lib_path  # noqa: F401
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Import the state machine
from session_state import (
    load_state, save_state, get_session_summary,
    MEMORY_DIR,
    prepare_handoff, complete_feature, extract_work_from_errors,
)

# Import project-aware state management
try:
    from project_detector import get_current_project, ProjectContext
    from project_state import (
        get_active_project_state, save_active_state, get_project_memory_dir,
        add_global_lesson, promote_lesson_to_global,
    )
    PROJECT_AWARE = True
except ImportError:
    PROJECT_AWARE = False

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRATCH_DIR = Path(__file__).resolve().parent.parent / "tmp"  # .claude/hooks -> .claude -> .claude/tmp
LESSONS_FILE = MEMORY_DIR / "__lessons.md"
SESSION_LOG_FILE = MEMORY_DIR / "session_log.jsonl"

# Legacy paths (used as fallback when not project-aware)
PROGRESS_FILE = MEMORY_DIR / "progress.json"  # Autonomous agent progress tracking
HANDOFF_FILE = MEMORY_DIR / "handoff.json"  # Session handoff data


def _get_project_progress_file() -> Path:
    """Get progress file path (project-scoped if available)."""
    if PROJECT_AWARE:
        try:
            context = get_current_project()
            return get_project_memory_dir(context.project_id) / "progress.json"
        except Exception:
            pass
    return PROGRESS_FILE


def _get_project_handoff_file() -> Path:
    """Get handoff file path (project-scoped if available)."""
    if PROJECT_AWARE:
        try:
            context = get_current_project()
            return get_project_memory_dir(context.project_id) / "handoff.json"
        except Exception:
            pass
    return HANDOFF_FILE

# Files in .claude/tmp/ older than this get cleaned (in seconds)
SCRATCH_CLEANUP_AGE = 86400  # 24 hours

# Minimum edits to a file before generating a lesson
LESSON_EDIT_THRESHOLD = 3

# =============================================================================
# PATTERN EXTRACTION
# =============================================================================

def check_abandoned_creations(state) -> list[dict]:
    """Check for files created this session that may have stubs/TODOs."""
    warnings = []

    if not state.files_created:
        return warnings

    # Patterns indicating incomplete work
    STUB_PATTERNS = [
        b'TODO',
        b'FIXME',
        b'NotImplementedError',
        b'pass  #',
        b'raise NotImplementedError',
        b'...',  # Python ellipsis stub
        b'stub',
        b'STUB',
    ]

    for filepath in state.files_created:
        path = Path(filepath)
        if not path.exists():
            continue

        # Skip non-code files
        if path.suffix not in {'.py', '.js', '.ts', '.rs', '.go', '.java'}:
            continue

        try:
            content = path.read_bytes()
            found_stubs = []
            for pattern in STUB_PATTERNS:
                if pattern in content:
                    found_stubs.append(pattern.decode())

            if found_stubs:
                warnings.append({
                    "file": filepath,
                    "name": path.name,
                    "stubs": found_stubs[:3],  # Limit to 3
                })
        except (OSError, PermissionError):
            pass

    return warnings


def extract_lessons(state) -> list[dict]:
    """Extract lessons from session patterns.

    NOTE: Only extract HIGH-VALUE lessons worth persisting to lessons.md.
    Telemetry/stats go to session_log.jsonl, not lessons.md.

    Removed (low value, polluted lessons.md):
    - file_complexity: "Edited X 5x" - noise, not actionable
    - unresearched_libs: Lists stdlib modules - garbage
    - domain_focus: "Session focused on X" - trivia
    - recurring_error: Rarely actionable without context

    Keep only:
    - abandoned_stubs: Actual incomplete work needing attention
    """
    lessons = []

    # LESSON: Files created with stubs (abandoned work warning)
    # This is actionable - user should know about incomplete work
    abandoned = check_abandoned_creations(state)
    if abandoned:
        files = [a["name"] for a in abandoned]
        lessons.append({
            "type": "abandoned_stubs",
            "files": files,
            "insight": f"⚠️ ABANDONED WORK: {', '.join(files)} contain stubs/TODOs",
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
    """Clean up old files in .claude/tmp/ directory."""
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
# AUTONOMOUS AGENT: PROGRESS & HANDOFF PERSISTENCE
# =============================================================================

def save_progress(state):
    """Save progress log to JSON file for cross-session persistence.

    This implements the Anthropic "progress tracking" pattern:
    https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

    Using JSON instead of Markdown because "the model is less likely to
    inappropriately change or overwrite JSON files compared to Markdown files."

    NOTE: Progress is now project-scoped to avoid cross-project pollution.
    """
    progress_file = _get_project_progress_file()
    progress_file.parent.mkdir(parents=True, exist_ok=True)

    # Load existing progress
    existing = []
    if progress_file.exists():
        try:
            with open(progress_file) as f:
                data = json.load(f)
                existing = data.get("entries", [])
        except (json.JSONDecodeError, KeyError):
            pass

    # Merge new progress (dedupe by feature_id)
    existing_ids = {e.get("feature_id") for e in existing}
    for entry in state.progress_log:
        if entry.get("feature_id") not in existing_ids:
            existing.append(entry)

    # Trim to last 50 entries
    existing = existing[-50:]

    # Save
    progress_data = {
        "last_updated": datetime.now().isoformat(),
        "session_id": state.session_id,
        "entries": existing,
        "work_queue": [w for w in state.work_queue if w.get("status") == "pending"][:20],
    }

    with open(progress_file, 'w') as f:
        json.dump(progress_data, f, indent=2, default=str)


def save_handoff(state):
    """Save session handoff data for next session.

    This is the key insight from Anthropic's agent harness:
    "agents need a way to bridge the gap between coding sessions"
    through structured artifacts.

    NOTE: Handoff is now project-scoped to avoid cross-project pollution.
    """
    handoff_file = _get_project_handoff_file()
    handoff_file.parent.mkdir(parents=True, exist_ok=True)

    # Prepare handoff data
    handoff = prepare_handoff(state)

    # Add session metadata
    handoff_data = {
        "prepared_at": datetime.now().isoformat(),
        "session_id": state.session_id,
        "summary": handoff["summary"],
        "next_steps": handoff["next_steps"],
        "blockers": handoff["blockers"],
        # Include recent file context for onboarding
        "recent_files": state.files_edited[-5:],
        "recent_commits": [],  # Could be populated from git log
        # Include checkpoint for recovery
        "last_checkpoint": state.checkpoints[-1] if state.checkpoints else None,
    }

    with open(handoff_file, 'w') as f:
        json.dump(handoff_data, f, indent=2, default=str)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """SessionEnd hook entry point."""
    try:
        json.load(sys.stdin)  # Consume stdin
    except (json.JSONDecodeError, ValueError):
        pass

    # Load current state
    state = load_state()

    # === AUTONOMOUS AGENT: Finalize current work ===

    # Complete any in-progress feature (mark as interrupted if session ending)
    if state.current_feature:
        complete_feature(state, "interrupted")

    # Auto-extract work items from unresolved errors
    extract_work_from_errors(state)

    # Extract lessons from session patterns
    lessons = extract_lessons(state)

    # Persist lessons to long-term memory
    persist_lessons(lessons)

    # === AUTONOMOUS AGENT: Save progress & handoff ===

    # Save progress log (JSON, survives sessions)
    save_progress(state)

    # Save handoff data for next session onboarding
    save_handoff(state)

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
