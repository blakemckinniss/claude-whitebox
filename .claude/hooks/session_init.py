#!/usr/bin/env python3
"""
Session Init Hook v3: SessionStart hook for initialization.

This hook fires when Claude Code starts a new session and:
- Detects stale state from previous sessions
- Initializes fresh state with proper session_id
- Refreshes ops script discovery
- Clears accumulated errors/gaps from dead sessions
- Sets up session metadata
- Surfaces actionable context on resume (files, tasks, errors)

Silent by default - outputs brief status only if resuming work or issues detected.
"""

import _lib_path  # noqa: F401
import sys
import json
import os
import time
from pathlib import Path

# Import the state machine
from session_state import (
    load_state, save_state, reset_state,
    MEMORY_DIR,
    _discover_ops_scripts,
    get_next_work_item, start_feature,
)

# Import project-aware state management
try:
    from project_detector import get_current_project, ProjectContext
    from project_state import (
        get_active_project_state, save_active_state, run_maintenance,
        get_contextual_lessons, is_same_project,
    )
    PROJECT_AWARE = True
except ImportError:
    PROJECT_AWARE = False

# Import spark_core for pre-warming (lazy load synapse map)
try:
    from spark_core import _load_synapses, fire_synapses
    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False

# Scope's punch list file
PUNCH_LIST_FILE = MEMORY_DIR / "punch_list.json"

# Autonomous agent files (legacy - now project-scoped)
HANDOFF_FILE = MEMORY_DIR / "handoff.json"
PROGRESS_FILE = MEMORY_DIR / "progress.json"


def _get_project_handoff_file(project_context=None) -> Path:
    """Get handoff file path (project-scoped if available)."""
    if PROJECT_AWARE and project_context:
        try:
            from project_state import get_project_memory_dir
            return get_project_memory_dir(project_context.project_id) / "handoff.json"
        except Exception:
            pass
    return HANDOFF_FILE


def _get_project_progress_file(project_context=None) -> Path:
    """Get progress file path (project-scoped if available)."""
    if PROJECT_AWARE and project_context:
        try:
            from project_state import get_project_memory_dir
            return get_project_memory_dir(project_context.project_id) / "progress.json"
        except Exception:
            pass
    return PROGRESS_FILE

# =============================================================================
# CONFIGURATION
# =============================================================================

# Sessions older than this are considered stale (in seconds)
STALE_SESSION_THRESHOLD = 3600  # 1 hour

# Maximum age for errors to carry over (in seconds)
ERROR_CARRY_OVER_MAX = 600  # 10 minutes

# =============================================================================
# MEMORY PRE-WARMING
# =============================================================================

def prewarm_memory_cache():
    """Pre-load synapse map and warm cache with common patterns.

    This runs at session start to eliminate cold-start latency on first prompt.
    Target: <50ms total.
    """
    if not SPARK_AVAILABLE:
        return

    try:
        # 1. Load synapse map into memory (cached for session)
        _load_synapses()

        # 2. Pre-warm spark cache with common terms (optional, disabled by default)
        # Uncomment to pre-fire for common patterns:
        # common_prompts = ["error", "test", "fix", "implement"]
        # for prompt in common_prompts:
        #     fire_synapses(prompt, include_constraints=False)

    except Exception:
        pass  # Non-critical, don't fail session init


# =============================================================================
# STALE DETECTION
# =============================================================================

def is_session_stale(state) -> tuple[bool, str]:
    """Check if the existing session state is stale."""
    if not state.started_at:
        return True, "no_timestamp"

    age = time.time() - state.started_at

    if age > STALE_SESSION_THRESHOLD:
        return True, f"age_{int(age)}s"

    # Check if session_id changed (new Claude session)
    current_session_id = os.environ.get("CLAUDE_SESSION_ID", "")[:16]
    if current_session_id and state.session_id and current_session_id != state.session_id:
        return True, "session_id_changed"

    return False, "fresh"


def prune_old_errors(state):
    """Remove errors older than carry-over threshold."""
    cutoff = time.time() - ERROR_CARRY_OVER_MAX

    state.errors_recent = [
        e for e in state.errors_recent
        if e.get("timestamp", 0) > cutoff
    ]
    state.errors_unresolved = [
        e for e in state.errors_unresolved
        if e.get("timestamp", 0) > cutoff
    ]


def prune_old_gaps(state):
    """Clear gaps from previous sessions."""
    # Gaps don't have timestamps, so clear all on new session
    state.gaps_detected = []
    state.gaps_surfaced = []


# =============================================================================
# AUTONOMOUS AGENT: HANDOFF & ONBOARDING
# =============================================================================

def load_handoff_data(project_context=None) -> dict | None:
    """Load handoff data from previous session.

    This implements the Anthropic pattern of bridging context across sessions:
    https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

    NOTE: Now project-scoped to load context for the specific project.
    """
    handoff_file = _get_project_handoff_file(project_context)
    if not handoff_file.exists():
        return None
    try:
        with open(handoff_file) as f:
            data = json.load(f)
        # Check if handoff is stale (>24h old)
        from datetime import datetime, timezone
        prepared = data.get("prepared_at", "")
        if prepared:
            try:
                # Parse ISO format, normalize to UTC for consistent comparison
                prepared_dt = datetime.fromisoformat(prepared.replace("Z", "+00:00"))
                if prepared_dt.tzinfo is not None:
                    # Convert to UTC then to naive for comparison
                    prepared_dt = prepared_dt.astimezone(timezone.utc).replace(tzinfo=None)
                    now = datetime.now(timezone.utc).replace(tzinfo=None)
                else:
                    now = datetime.now()
                age_hours = (now - prepared_dt).total_seconds() / 3600
                if age_hours > 24:
                    return None  # Stale handoff
            except (ValueError, TypeError):
                pass
        return data
    except (json.JSONDecodeError, KeyError):
        return None


def load_work_queue(project_context=None) -> list:
    """Load pending work items from progress file.

    NOTE: Now project-scoped.
    """
    progress_file = _get_project_progress_file(project_context)
    if not progress_file.exists():
        return []
    try:
        with open(progress_file) as f:
            data = json.load(f)
        return data.get("work_queue", [])
    except (json.JSONDecodeError, KeyError):
        return []


def build_onboarding_context(state, handoff: dict | None, project_context=None) -> str:
    """Build the session onboarding protocol context.

    Implements the Anthropic pattern:
    1. Read progress files and git logs to understand recent work
    2. Select the highest-priority incomplete feature
    3. Verify baseline before implementing

    For autonomous agents, this is AUTOMATIC - no human input needed.

    NEW: Project-aware onboarding surfaces project context for fast switching.
    """
    parts = []

    # === STEP 0: Project Context (for multi-project swiss army knife) ===
    if project_context and PROJECT_AWARE:
        proj_name = project_context.project_name
        proj_type = project_context.project_type

        if proj_type == "ephemeral":
            parts.append(f"💬 **MODE**: Ephemeral (no project context)")
        else:
            lang = project_context.language or "unknown"
            framework = project_context.framework
            ctx_str = f"📁 **PROJECT**: {proj_name}"
            if framework:
                ctx_str += f" ({framework}/{lang})"
            elif lang:
                ctx_str += f" ({lang})"
            parts.append(ctx_str)

    # === STEP 1: Previous Session Summary ===
    if handoff:
        summary = handoff.get("summary", "")
        if summary:
            parts.append(f"📋 **PREVIOUS SESSION**: {summary}")

        # Blockers from previous session
        blockers = handoff.get("blockers", [])
        if blockers:
            blocker_list = ", ".join(b.get("type", "unknown")[:20] for b in blockers[:2])
            parts.append(f"🚧 **BLOCKERS**: {blocker_list}")

        # Recent files (context continuity)
        recent = handoff.get("recent_files", [])
        if recent:
            names = [Path(f).name for f in recent[:3]]
            parts.append(f"📝 **RECENT FILES**: {', '.join(names)}")

    # === STEP 2: Auto-Select Next Work Item ===
    next_item = get_next_work_item(state)
    if next_item:
        item_type = next_item.get("type", "task")
        desc = next_item.get("description", "")[:60]
        priority = next_item.get("priority", 50)
        parts.append(f"🎯 **NEXT PRIORITY** [{item_type}|P{priority}]: {desc}")

        # Auto-start this feature for tracking
        start_feature(state, desc)
    else:
        # Check handoff next_steps as fallback
        if handoff:
            next_steps = handoff.get("next_steps", [])
            if next_steps:
                step = next_steps[0]
                desc = step.get("description", "")[:60]
                parts.append(f"🎯 **SUGGESTED**: {desc}")

    # === STEP 3: Recovery Point ===
    if handoff:
        checkpoint = handoff.get("last_checkpoint")
        if checkpoint:
            cp_id = checkpoint.get("checkpoint_id", "")
            commit = checkpoint.get("commit_hash", "")[:7]
            if commit:
                parts.append(f"💾 **RECOVERY POINT**: {cp_id} (commit: {commit})")

    # === STEP 4: Relevant Global Lessons (cross-project wisdom) ===
    if PROJECT_AWARE and project_context and project_context.project_type != "ephemeral":
        # Get lessons relevant to this project's language/framework
        keywords = [project_context.language, project_context.framework, project_context.project_name]
        keywords = [k for k in keywords if k]
        if keywords:
            lessons = get_contextual_lessons(keywords)
            if lessons:
                lesson_preview = lessons[0].get("content", "")[:50]
                parts.append(f"💡 **WISDOM**: {lesson_preview}...")

    return "\n".join(parts) if parts else ""


# =============================================================================
# CONTEXT GENERATION (for resume)
# =============================================================================

def get_active_scope_task() -> dict | None:
    """Check if there's an active scope task from punch_list.json."""
    if not PUNCH_LIST_FILE.exists():
        return None
    try:
        with open(PUNCH_LIST_FILE) as f:
            data = json.load(f)
        # Only return if not 100% complete
        if data.get("percent", 100) < 100:
            return {
                "description": data.get("description", "")[:60],
                "percent": data.get("percent", 0),
                "items_done": sum(1 for i in data.get("items", []) if i.get("done")),
                "items_total": len(data.get("items", [])),
            }
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def build_resume_context(state, result: dict) -> str:
    """Build actionable context string for session resume."""
    parts = []

    # 1. Active scope task (highest priority)
    scope_task = get_active_scope_task()
    if scope_task:
        desc = scope_task["description"]
        pct = scope_task["percent"]
        done = scope_task["items_done"]
        total = scope_task["items_total"]
        parts.append(f"📋 Active task: \"{desc}\" ({done}/{total} items, {pct}%)")

    # 2. Recently edited files (from previous session state)
    if state.files_edited:
        recent = []
        for f in state.files_edited[-3:]:
            try:
                recent.append(Path(f).name)
            except (ValueError, OSError):
                recent.append(str(f).split('/')[-1] if '/' in str(f) else str(f))
        parts.append(f"📝 Last edited: {', '.join(recent)}")

    # 3. Unresolved errors (warn, don't block)
    if state.errors_unresolved:
        count = len(state.errors_unresolved)
        latest = state.errors_unresolved[-1].get("type", "error")[:40]
        parts.append(f"⚠️ {count} unresolved: {latest}")

    return " | ".join(parts) if parts else ""


# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize_session(project_context=None) -> dict:
    """Initialize or refresh session state.

    Args:
        project_context: Optional ProjectContext for project-scoped operations.
    """
    result = {
        "action": "none",
        "message": "",
        "session_id": "",
        "handoff": None,  # For onboarding context
    }

    # Try to load existing state
    existing_state = load_state()

    # Check staleness
    is_stale, reason = is_session_stale(existing_state)

    if is_stale:
        # Reset to fresh state
        state = reset_state()
        result["action"] = "reset"
        result["message"] = f"Fresh session (reason: {reason})"

        # === AUTONOMOUS AGENT: Restore work queue from progress file ===
        # Now project-scoped to load correct project's work queue
        work_queue = load_work_queue(project_context)
        if work_queue:
            state.work_queue = work_queue
    else:
        # Refresh existing state
        state = existing_state

        # Prune old data
        prune_old_errors(state)
        prune_old_gaps(state)

        # Clear stale integration greps (prevents cross-session blocking)
        state.pending_integration_greps = []

        # Refresh ops scripts (might have changed)
        state.ops_scripts = _discover_ops_scripts()

        result["action"] = "refresh"
        result["message"] = "Session resumed"

    # Ensure session_id is set
    if not state.session_id:
        state.session_id = os.environ.get("CLAUDE_SESSION_ID", "")[:16] or f"ses_{int(time.time())}"

    result["session_id"] = state.session_id

    # === AUTONOMOUS AGENT: Load handoff data ===
    # Now project-scoped to load correct project's handoff
    handoff = load_handoff_data(project_context)
    result["handoff"] = handoff

    # Save updated state
    save_state(state)

    # Pre-warm memory cache (synapse map, lessons index)
    prewarm_memory_cache()

    return result


# =============================================================================
# MAIN
# =============================================================================

def main():
    """SessionStart hook entry point."""
    try:
        json.load(sys.stdin)  # Consume stdin
    except (json.JSONDecodeError, ValueError):
        pass

    # === PROJECT-AWARE INITIALIZATION ===
    project_context = None
    if PROJECT_AWARE:
        try:
            project_context = get_current_project()
            # Run maintenance (cleanup stale projects, ephemeral state)
            run_maintenance()
        except (ImportError, FileNotFoundError, PermissionError):
            # Expected errors: module not available, git not found, permission issues
            pass  # Fall back to legacy behavior
        except Exception as e:
            # Unexpected errors: log for debugging but don't block
            import sys
            print(f"Warning: project detection failed: {type(e).__name__}: {e}", file=sys.stderr)

    # Load state BEFORE initialize (to capture previous session's context)
    previous_state = load_state()

    # Initialize session (pass project_context for project-scoped operations)
    result = initialize_session(project_context)

    # SUDO SECURITY: Audit passed - clear stop hook flags for this session
    session_id = os.environ.get("CLAUDE_SESSION_ID", "default")[:16]
    dismissal_flag = MEMORY_DIR / f"dismissal_shown_{session_id}.flag"
    if dismissal_flag.exists():
        try:
            dismissal_flag.unlink()
        except (IOError, OSError):
            pass

    # Output result
    output = {}

    # === AUTONOMOUS AGENT: Session Onboarding Protocol ===
    # This implements the Anthropic pattern for agent session starts:
    # https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
    #
    # ENHANCED: Project-aware onboarding for multi-project swiss army knife

    if result["action"] == "reset":
        # Fresh session - load state for onboarding context
        state = load_state()
        handoff = result.get("handoff")

        # Build onboarding context (auto-selects next work item)
        # Pass project_context for multi-project awareness
        onboarding = build_onboarding_context(state, handoff, project_context)

        if onboarding:
            output["message"] = f"🚀 **SESSION START**\n{onboarding}"
            # Save state (may have started a feature)
            save_state(state)
        else:
            # Even without handoff, show project context if available
            if project_context and project_context.project_type != "ephemeral":
                output["message"] = f"🚀 **SESSION START**\n📁 **PROJECT**: {project_context.project_name}"
            else:
                output["message"] = f"🔄 {result['message']}"

    elif result["action"] == "refresh":
        # Resuming within same session - surface context from previous state
        context = build_resume_context(previous_state, result)
        if context:
            output["message"] = f"🔁 Resuming: {context}"

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
