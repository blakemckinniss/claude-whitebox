#!/usr/bin/env python3
"""
Project State Manager v1.0: Multi-project state isolation with auto-cleanup.

This module provides project-aware state management that:
- Isolates state per project (no cross-contamination)
- Auto-cleans ephemeral/stale contexts
- Supports fast project switching (<10ms)
- Maintains global lessons across projects

Design for Fast Movement:
- Projects can be created/abandoned rapidly
- Ephemeral contexts auto-expire (1 hour)
- Stale projects auto-archive (7 days)
- Global wisdom persists and transfers

Memory Layout:
  .claude/memory/
  ├── global/              # Cross-project (persists forever)
  │   ├── lessons.json    # Universal patterns
  │   └── skills.json     # Tool/language proficiency
  ├── projects/           # Per-project (auto-managed)
  │   ├── _index.json     # Registry with timestamps
  │   └── {project_id}/   # Project-specific state
  │       ├── state.json
  │       ├── progress.json
  │       └── handoff.json
  └── ephemeral/          # Disposable (aggressive cleanup)
      └── state.json
"""

import json
import time
import shutil
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

from project_detector import (
    ProjectContext,
    get_current_project,
    get_project_memory_dir,
    get_global_memory_dir,
    get_stale_projects,
    load_project_index,
    save_project_index,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Ephemeral contexts expire after this many seconds
EPHEMERAL_EXPIRY = 3600  # 1 hour

# Projects without activity for this many days get archived
STALE_PROJECT_DAYS = 7

# Maximum projects to keep in active state
MAX_ACTIVE_PROJECTS = 20

# =============================================================================
# GLOBAL MEMORY (Cross-Project Wisdom)
# =============================================================================

@dataclass
class GlobalMemory:
    """Cross-project accumulated wisdom."""
    # Universal lessons that apply everywhere
    lessons: list = field(default_factory=list)

    # Language/tool proficiency (tracks what agent is good at)
    skills: dict = field(default_factory=dict)

    # Patterns that worked well (extracted from successful projects)
    winning_patterns: list = field(default_factory=list)

    # Anti-patterns to avoid (extracted from failures)
    anti_patterns: list = field(default_factory=list)


def load_global_memory() -> GlobalMemory:
    """Load cross-project global memory."""
    global_dir = get_global_memory_dir()
    lessons_path = global_dir / "lessons.json"

    if lessons_path.exists():
        try:
            with open(lessons_path) as f:
                data = json.load(f)
            return GlobalMemory(**data)
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    return GlobalMemory()


def save_global_memory(memory: GlobalMemory):
    """Save cross-project global memory."""
    global_dir = get_global_memory_dir()
    global_dir.mkdir(parents=True, exist_ok=True)

    lessons_path = global_dir / "lessons.json"
    with open(lessons_path, 'w') as f:
        json.dump(asdict(memory), f, indent=2, default=str)


def add_global_lesson(lesson: str, category: str = "general"):
    """Add a lesson to global memory (survives project switches)."""
    import hashlib
    memory = load_global_memory()

    # Check for duplicates using content hash (more robust than prefix match)
    lesson_hash = hashlib.sha256(lesson.encode()).hexdigest()[:16]
    existing_hashes = {
        hashlib.sha256(entry.get("content", "").encode()).hexdigest()[:16]
        for entry in memory.lessons
    }
    if lesson_hash in existing_hashes:
        return

    memory.lessons.append({
        "content": lesson[:200],
        "category": category,
        "added_at": time.time(),
    })

    # Keep last 100 lessons
    memory.lessons = memory.lessons[-100:]
    save_global_memory(memory)


def get_relevant_global_lessons(keywords: list[str], limit: int = 5) -> list[dict]:
    """Get global lessons relevant to given keywords."""
    memory = load_global_memory()

    scored = []
    for lesson in memory.lessons:
        content = lesson.get("content", "").lower()
        category = lesson.get("category", "").lower()

        # Score by keyword matches
        score = sum(1 for kw in keywords if kw.lower() in content or kw.lower() in category)
        if score > 0:
            scored.append((score, lesson))

    # Sort by score, return top N
    scored.sort(key=lambda x: x[0], reverse=True)
    return [lesson_entry for _, lesson_entry in scored[:limit]]


# =============================================================================
# PROJECT STATE
# =============================================================================

@dataclass
class ProjectState:
    """Per-project session state (isolated from other projects)."""
    # Project identity
    project_id: str = ""
    project_name: str = ""

    # Timestamps
    created_at: float = 0.0
    last_active: float = 0.0

    # Session state (same as SessionState but project-scoped)
    session_id: str = ""
    turn_count: int = 0
    domain: str = ""

    # File tracking (project-specific)
    files_read: list = field(default_factory=list)
    files_edited: list = field(default_factory=list)
    files_created: list = field(default_factory=list)

    # Work tracking (project-specific)
    current_feature: str = ""
    current_feature_started: float = 0.0
    work_queue: list = field(default_factory=list)
    progress_log: list = field(default_factory=list)

    # Goal tracking (project-specific - key for isolation!)
    original_goal: str = ""
    goal_keywords: list = field(default_factory=list)

    # Errors/patterns (project-specific)
    errors_recent: list = field(default_factory=list)
    consecutive_failures: int = 0

    # Project-specific lessons (not global)
    local_lessons: list = field(default_factory=list)


def get_project_state_path(project_id: str) -> Path:
    """Get path to project state file."""
    return get_project_memory_dir(project_id) / "state.json"


def load_project_state(context: ProjectContext) -> ProjectState:
    """Load state for a specific project."""
    state_path = get_project_state_path(context.project_id)

    if state_path.exists():
        try:
            with open(state_path) as f:
                data = json.load(f)
            state = ProjectState(**data)
            state.last_active = time.time()
            return state
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    # New project state
    return ProjectState(
        project_id=context.project_id,
        project_name=context.project_name,
        created_at=time.time(),
        last_active=time.time(),
    )


def save_project_state(state: ProjectState):
    """Save state for a specific project."""
    state_path = get_project_state_path(state.project_id)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    state.last_active = time.time()

    # Trim lists to prevent bloat
    state.files_read = state.files_read[-50:]
    state.files_edited = state.files_edited[-50:]
    state.work_queue = state.work_queue[-30:]
    state.progress_log = state.progress_log[-20:]
    state.errors_recent = state.errors_recent[-10:]
    state.local_lessons = state.local_lessons[-20:]

    with open(state_path, 'w') as f:
        json.dump(asdict(state), f, indent=2, default=str)


def clear_project_state(project_id: str):
    """Clear state for a project (fresh start)."""
    state_path = get_project_state_path(project_id)
    if state_path.exists():
        state_path.unlink()


# =============================================================================
# EPHEMERAL STATE (Disposable)
# =============================================================================

def is_ephemeral_state_stale() -> bool:
    """Check if ephemeral state has expired."""
    state_path = get_project_state_path("ephemeral")
    if not state_path.exists():
        return True

    try:
        mtime = state_path.stat().st_mtime
        return (time.time() - mtime) > EPHEMERAL_EXPIRY
    except OSError:
        return True


def clear_ephemeral_state():
    """Clear ephemeral state (aggressive cleanup)."""
    ephemeral_dir = get_project_memory_dir("ephemeral")
    if ephemeral_dir.exists():
        try:
            shutil.rmtree(ephemeral_dir)
        except OSError:
            pass


# =============================================================================
# AUTO-CLEANUP
# =============================================================================

def cleanup_stale_projects():
    """Archive/remove stale project states.

    Called periodically to prevent memory bloat.
    """
    stale_ids = get_stale_projects(STALE_PROJECT_DAYS)

    for project_id in stale_ids:
        project_dir = get_project_memory_dir(project_id)

        # Archive by moving to archive subdirectory
        if project_dir.exists():
            archive_dir = project_dir.parent / "_archive" / project_id
            archive_dir.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(project_dir), str(archive_dir))
            except OSError:
                # If move fails, just delete
                try:
                    shutil.rmtree(project_dir)
                except OSError:
                    pass

        # Remove from index
        index = load_project_index()
        if project_id in index.get("projects", {}):
            del index["projects"][project_id]
            save_project_index(index)


def enforce_max_projects():
    """Enforce maximum number of active projects.

    Archives least-recently-used projects when limit exceeded.
    """
    index = load_project_index()
    projects = index.get("projects", {})

    if len(projects) <= MAX_ACTIVE_PROJECTS:
        return

    # Sort by last_active, archive oldest
    sorted_projects = sorted(
        projects.items(),
        key=lambda x: x[1].get("last_active", 0)
    )

    to_archive = len(projects) - MAX_ACTIVE_PROJECTS
    for project_id, _ in sorted_projects[:to_archive]:
        project_dir = get_project_memory_dir(project_id)
        if project_dir.exists():
            archive_dir = project_dir.parent / "_archive" / project_id
            archive_dir.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(project_dir), str(archive_dir))
            except OSError:
                pass

        del projects[project_id]

    index["projects"] = projects
    save_project_index(index)


def run_maintenance():
    """Run all maintenance tasks.

    Call this at session start/end to keep memory clean.
    """
    # Clean up ephemeral if stale
    if is_ephemeral_state_stale():
        clear_ephemeral_state()

    # Archive stale projects
    cleanup_stale_projects()

    # Enforce project limit
    enforce_max_projects()


# =============================================================================
# HIGH-LEVEL API
# =============================================================================

_current_context: Optional[ProjectContext] = None
_current_state: Optional[ProjectState] = None


def get_active_project_state() -> tuple[ProjectContext, ProjectState]:
    """Get current project context and state.

    This is the main entry point for hooks.
    Detects project, loads appropriate state, handles cleanup.
    """
    global _current_context, _current_state

    # Detect project (cached for session)
    context = get_current_project()

    # Check if we need to switch projects
    if _current_context and _current_context.project_id != context.project_id:
        # Project changed! Save old state first
        if _current_state:
            save_project_state(_current_state)
        _current_state = None

    _current_context = context

    # Load state for current project
    if _current_state is None:
        _current_state = load_project_state(context)

    return context, _current_state


def save_active_state():
    """Save current project state."""
    global _current_state
    if _current_state:
        save_project_state(_current_state)


def reset_active_state():
    """Reset current project state (fresh start)."""
    global _current_context, _current_state

    if _current_context:
        clear_project_state(_current_context.project_id)

    _current_state = None


def is_same_project(previous_context: Optional[ProjectContext]) -> bool:
    """Check if we're still in the same project."""
    current = get_current_project()
    if previous_context is None:
        return False
    return current.project_id == previous_context.project_id


# =============================================================================
# LESSON PROMOTION
# =============================================================================

def promote_lesson_to_global(lesson: str, category: str = "general"):
    """Promote a project-specific lesson to global memory.

    Call this when a pattern proves useful across multiple projects.
    """
    add_global_lesson(lesson, category)


def get_contextual_lessons(keywords: list[str]) -> list[dict]:
    """Get lessons relevant to current context.

    Combines:
    1. Global lessons matching keywords
    2. Current project's local lessons
    """
    global _current_state

    lessons = []

    # Global lessons
    lessons.extend(get_relevant_global_lessons(keywords, limit=3))

    # Local lessons
    if _current_state and _current_state.local_lessons:
        for lesson in _current_state.local_lessons[-5:]:
            if any(kw.lower() in lesson.get("content", "").lower() for kw in keywords):
                lessons.append(lesson)

    return lessons[:5]
