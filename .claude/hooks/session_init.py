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
)

# Import spark_core for pre-warming (lazy load synapse map)
try:
    from spark_core import _load_synapses, fire_synapses
    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False

# Scope's punch list file
PUNCH_LIST_FILE = MEMORY_DIR / "punch_list.json"

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

def initialize_session() -> dict:
    """Initialize or refresh session state."""
    result = {
        "action": "none",
        "message": "",
        "session_id": "",
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

    # Load state BEFORE initialize (to capture previous session's context)
    previous_state = load_state()

    # Initialize session
    result = initialize_session()

    # SUDO SECURITY: Audit passed - clear stop hook flags for this session
    session_id = os.environ.get("CLAUDE_SESSION_ID", "default")[:16]
    dismissal_flag = MEMORY_DIR / f"dismissal_shown_{session_id}.flag"
    if dismissal_flag.exists():
        try:
            dismissal_flag.unlink()
        except (IOError, OSError):
            pass

    # Output result (brief, informational)
    output = {}

    if result["action"] == "reset":
        # Fresh session - just note it
        output["message"] = f"🔄 {result['message']}"
    elif result["action"] == "refresh":
        # Resuming - surface actionable context from previous state
        context = build_resume_context(previous_state, result)
        if context:
            output["message"] = f"🔁 Resuming: {context}"

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
