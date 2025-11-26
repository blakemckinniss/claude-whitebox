#!/usr/bin/env python3
"""
Hook Error Logging Utility

Provides centralized error logging for hooks instead of silent swallowing.
Logs to .claude/tmp/hook_debug.jsonl for debugging.

Usage in hooks:
    from hook_logging import log_hook_error, log_hook_event

    try:
        # hook logic
    except Exception as e:
        log_hook_error("my_hook", e, {"context": "value"})
"""

import json
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

# =============================================================================
# PATHS
# =============================================================================

LIB_DIR = Path(__file__).resolve().parent
CLAUDE_DIR = LIB_DIR.parent
TMP_DIR = CLAUDE_DIR / "tmp"
LOG_FILE = TMP_DIR / "hook_debug.jsonl"

# Max log file size (1MB) - rotate when exceeded
MAX_LOG_SIZE = 1_000_000

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================


def _ensure_tmp_dir():
    """Ensure tmp directory exists."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)


def _rotate_if_needed():
    """Rotate log file if too large."""
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > MAX_LOG_SIZE:
        # Keep last 500 lines
        try:
            lines = LOG_FILE.read_text().strip().split('\n')
            LOG_FILE.write_text('\n'.join(lines[-500:]) + '\n')
        except (IOError, OSError):
            pass


def log_hook_error(
    hook_name: str,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a hook error to the debug log.

    Args:
        hook_name: Name of the hook (e.g., "gap_detector")
        error: The exception that occurred
        context: Optional dict with additional context
    """
    try:
        _ensure_tmp_dir()
        _rotate_if_needed()

        entry = {
            "timestamp": time.time(),
            "level": "error",
            "hook": hook_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
        }

        if context:
            entry["context"] = context

        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    except Exception:
        pass  # Don't fail the hook if logging fails


def log_hook_event(
    hook_name: str,
    event: str,
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a hook event for debugging.

    Args:
        hook_name: Name of the hook
        event: Event type (e.g., "blocked", "skipped", "triggered")
        data: Optional dict with event data
    """
    try:
        _ensure_tmp_dir()
        _rotate_if_needed()

        entry = {
            "timestamp": time.time(),
            "level": "info",
            "hook": hook_name,
            "event": event,
        }

        if data:
            entry["data"] = data

        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    except Exception:
        pass


def get_recent_errors(hook_name: Optional[str] = None, limit: int = 10) -> list:
    """
    Get recent errors from the log.

    Args:
        hook_name: Optional filter by hook name
        limit: Max number of errors to return

    Returns:
        List of error entries (newest first)
    """
    if not LOG_FILE.exists():
        return []

    try:
        lines = LOG_FILE.read_text().strip().split('\n')
        errors = []

        for line in reversed(lines):
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("level") != "error":
                    continue
                if hook_name and entry.get("hook") != hook_name:
                    continue
                errors.append(entry)
                if len(errors) >= limit:
                    break
            except json.JSONDecodeError:
                continue

        return errors

    except (IOError, OSError):
        return []


def clear_log() -> bool:
    """Clear the debug log. Returns True if successful."""
    try:
        if LOG_FILE.exists():
            LOG_FILE.unlink()
        return True
    except (IOError, OSError):
        return False
