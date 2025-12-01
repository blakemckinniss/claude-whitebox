#!/usr/bin/env python3
"""
File Locking Utility: Thread-safe and process-safe file operations.

Prevents race conditions when multiple Claude instances access shared files.

Usage:
    from file_lock import atomic_json_update, atomic_write

    # Atomic read-modify-write for JSON files
    with atomic_json_update(filepath) as data:
        data["key"] = "value"  # Modifications are auto-saved

    # Atomic write (uses temp file + rename)
    atomic_write(filepath, content)
"""

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class FileLockError(Exception):
    """Raised when file locking fails."""
    pass


@contextmanager
def file_lock(filepath: Path | str, timeout: float = 5.0):
    """
    Context manager for exclusive file lock using fcntl.

    Args:
        filepath: Path to file (creates .lock file alongside)
        timeout: Seconds to wait for lock (not implemented - blocks indefinitely)

    Usage:
        with file_lock("/path/to/file.json"):
            # exclusive access to file
            data = json.load(open(filepath))
            data["key"] = "value"
            json.dump(data, open(filepath, 'w'))
    """
    filepath = Path(filepath)
    lock_path = filepath.with_suffix(filepath.suffix + ".lock")

    # Ensure parent directory exists
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    lock_fd = None
    try:
        # Open lock file (create if needed)
        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)

        # Acquire exclusive lock (blocks until available)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        yield

    finally:
        if lock_fd is not None:
            # Release lock
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)


@contextmanager
def atomic_json_update(filepath: Path | str, default: Any = None):
    """
    Context manager for atomic JSON read-modify-write.

    Acquires exclusive lock, loads JSON, yields mutable data,
    then atomically writes back on exit.

    Args:
        filepath: Path to JSON file
        default: Default value if file doesn't exist (default: {})

    Usage:
        with atomic_json_update("data.json") as data:
            data["count"] = data.get("count", 0) + 1
        # File is atomically updated on exit

    Raises:
        FileLockError: If locking or file operation fails
    """
    filepath = Path(filepath)
    if default is None:
        default = {}

    with file_lock(filepath):
        # Load existing data or use default
        data = default
        if filepath.exists():
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError):
                data = default

        # Yield mutable data for modification
        yield data

        # Atomic write: temp file + rename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=filepath.parent,
            suffix='.tmp',
            prefix=filepath.stem + '_'
        )
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp_path, filepath)  # Atomic on POSIX
        except Exception:
            # Clean up temp file on failure
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise


def atomic_write(filepath: Path | str, content: str | bytes, mode: str = 'w'):
    """
    Atomically write content to file using temp file + rename.

    Args:
        filepath: Destination file path
        content: Content to write (str or bytes)
        mode: 'w' for text, 'wb' for binary

    Usage:
        atomic_write("/path/to/file.txt", "content")
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with file_lock(filepath):
        fd, tmp_path = tempfile.mkstemp(
            dir=filepath.parent,
            suffix='.tmp',
            prefix=filepath.stem + '_'
        )
        try:
            with os.fdopen(fd, mode) as f:
                f.write(content)
            os.replace(tmp_path, filepath)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise


def atomic_json_write(filepath: Path | str, data: Any):
    """
    Atomically write JSON data to file.

    Args:
        filepath: Destination file path
        data: JSON-serializable data
    """
    filepath = Path(filepath)
    content = json.dumps(data, indent=2, default=str)
    atomic_write(filepath, content)


def locked_read_json(filepath: Path | str, default: Any = None) -> Any:
    """
    Read JSON file with exclusive lock.

    Args:
        filepath: Path to JSON file
        default: Default value if file doesn't exist

    Returns:
        Parsed JSON data or default
    """
    filepath = Path(filepath)
    if default is None:
        default = {}

    if not filepath.exists():
        return default

    with file_lock(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default
