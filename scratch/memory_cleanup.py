#!/usr/bin/env python3
"""
Memory Cleanup Library: Prevent Memory Leaks

Handles log rotation, session pruning, and bounded data structures.
"""

import sys
import json
import os
import fcntl
import logging
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='[%(name)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('memory_cleanup')

# Paths (environment variable override supported)
MEMORY_DIR = Path(__file__).resolve().parent.parent / ".claude" / "memory"
ARCHIVE_DIR = MEMORY_DIR / "archives"

# Default configuration (loaded from circuit_breaker_config.json)
DEFAULT_LIMITS = {
    "telemetry_max_lines": 1000,
    "telemetry_max_kb": 50,
    "telemetry_max_age_days": 7,
    "telemetry_keep_rotations": 5,
    "session_max_active": 10,
    "session_max_age_days": 7,
    "evidence_ledger_max": 100,
    "tool_history_max": 50,
    "archive_keep_count": 20,  # Max session archives to keep
}


def load_memory_limits() -> Dict:
    """Load memory limits from config"""
    config_file = MEMORY_DIR / "circuit_breaker_config.json"

    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
                return config.get("memory_limits", DEFAULT_LIMITS)
        except json.JSONDecodeError as e:
            logger.error(f"Config file corrupted: {e}. Using defaults.")
        except Exception as e:
            logger.warning(f"Failed to load config: {e}. Using defaults.")

    return DEFAULT_LIMITS


def get_telemetry_files() -> List[Path]:
    """Get list of telemetry JSONL files"""
    if not MEMORY_DIR.exists():
        return []

    return list(MEMORY_DIR.glob("*_telemetry.jsonl"))


def get_session_files() -> List[Path]:
    """Get list of session state JSON files"""
    if not MEMORY_DIR.exists():
        return []

    # Include ALL session files (no exclusions - all must be managed)
    return list(MEMORY_DIR.glob("session_*_state.json"))


def count_lines(file_path: Path) -> int:
    """Count lines in file"""
    try:
        with open(file_path) as f:
            return sum(1 for _ in f)
    except:
        return 0


def get_file_size_kb(file_path: Path) -> float:
    """Get file size in KB"""
    try:
        return file_path.stat().st_size / 1024
    except:
        return 0.0


def get_file_age_days(file_path: Path) -> float:
    """Get file age in days"""
    try:
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        age = datetime.now() - mtime
        return age.total_seconds() / 86400
    except:
        return 0.0


def should_rotate_telemetry(file_path: Path, limits: Dict) -> Tuple[bool, str]:
    """
    Check if telemetry file should be rotated

    Returns:
        Tuple[bool, str]: (should_rotate, reason)
    """
    lines = count_lines(file_path)
    size_kb = get_file_size_kb(file_path)
    age_days = get_file_age_days(file_path)

    if lines >= limits["telemetry_max_lines"]:
        return (True, f"exceeded {limits['telemetry_max_lines']} lines ({lines} lines)")

    if size_kb >= limits["telemetry_max_kb"]:
        return (True, f"exceeded {limits['telemetry_max_kb']}KB ({size_kb:.1f}KB)")

    if age_days >= limits["telemetry_max_age_days"]:
        return (True, f"exceeded {limits['telemetry_max_age_days']} days ({age_days:.1f} days)")

    return (False, "")


def rotate_telemetry_file(file_path: Path, limits: Dict) -> str:
    """
    Rotate telemetry file (compress and archive)

    Returns:
        Status message
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"{file_path.stem}_{timestamp}.jsonl.gz"
    archive_path = ARCHIVE_DIR / "telemetry" / archive_name

    # Create archive directory
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    # Compress and move
    try:
        with open(file_path, "rb") as f_in:
            with gzip.open(archive_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Create fresh file
        file_path.unlink()
        file_path.touch()

        # Clean old rotations
        rotations = sorted(
            archive_path.parent.glob(f"{file_path.stem}_*.jsonl.gz"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        deleted_count = 0
        for old_rotation in rotations[limits["telemetry_keep_rotations"] :]:
            old_rotation.unlink()
            deleted_count += 1

        return f"✅ Rotated {file_path.name} → {archive_name} (deleted {deleted_count} old rotations)"

    except Exception as e:
        return f"❌ Failed to rotate {file_path.name}: {e}"


def rotate_all_telemetry() -> List[str]:
    """
    Rotate all telemetry files that exceed limits

    Returns:
        List of status messages
    """
    limits = load_memory_limits()
    telemetry_files = get_telemetry_files()
    messages = []

    for file_path in telemetry_files:
        should_rotate, reason = should_rotate_telemetry(file_path, limits)

        if should_rotate:
            message = rotate_telemetry_file(file_path, limits)
            messages.append(f"{message} (reason: {reason})")

    return messages


def should_prune_session(file_path: Path, limits: Dict) -> Tuple[bool, str]:
    """
    Check if session file should be pruned

    Returns:
        Tuple[bool, str]: (should_prune, reason)
    """
    age_days = get_file_age_days(file_path)

    if age_days >= limits["session_max_age_days"]:
        return (True, f"exceeded {limits['session_max_age_days']} days ({age_days:.1f} days)")

    return (False, "")


def prune_session_file(file_path: Path) -> str:
    """
    Prune session file (archive and delete)

    Returns:
        Status message
    """
    timestamp = datetime.now().strftime("%Y%m%d")
    archive_name = file_path.name.replace(".json", f"_{timestamp}.json.gz")
    archive_path = ARCHIVE_DIR / "sessions" / archive_name

    # Create archive directory
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    # Compress and move
    try:
        with open(file_path, "rb") as f_in:
            with gzip.open(archive_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Delete original
        file_path.unlink()

        return f"✅ Pruned {file_path.name} → {archive_name}"

    except Exception as e:
        return f"❌ Failed to prune {file_path.name}: {e}"


def prune_old_sessions() -> List[str]:
    """
    Prune old session files

    Returns:
        List of status messages
    """
    limits = load_memory_limits()
    session_files = get_session_files()
    messages = []

    # Sort by modification time (oldest first)
    session_files.sort(key=lambda p: p.stat().st_mtime)

    # Prune old sessions (by age)
    for file_path in session_files:
        should_prune, reason = should_prune_session(file_path, limits)

        if should_prune:
            message = prune_session_file(file_path)
            messages.append(f"{message} (reason: {reason})")

    # Prune excess sessions (by count)
    remaining_sessions = get_session_files()
    if len(remaining_sessions) > limits["session_max_active"]:
        excess = len(remaining_sessions) - limits["session_max_active"]
        # Sort again (may have changed after pruning)
        remaining_sessions.sort(key=lambda p: p.stat().st_mtime)

        for file_path in remaining_sessions[:excess]:
            message = prune_session_file(file_path)
            messages.append(f"{message} (reason: exceeded {limits['session_max_active']} active sessions)")

    return messages


def truncate_evidence_ledger(session_file: Path, limits: Dict) -> bool:
    """
    Truncate evidence ledger in session state (with file locking)

    Returns:
        True if truncated, False otherwise
    """
    try:
        with open(session_file, 'r+') as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                state = json.load(f)

                evidence = state.get("evidence_ledger", [])
                max_entries = limits["evidence_ledger_max"]

                if len(evidence) > max_entries:
                    # Keep last N entries
                    state["evidence_ledger"] = evidence[-max_entries:]

                    # Rewrite file
                    f.seek(0)
                    f.truncate()
                    json.dump(state, f, indent=2)

                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    return True

                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return False

            except json.JSONDecodeError as e:
                logger.error(f"Corrupted JSON in {session_file}: {e}")
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return False
            except Exception as e:
                logger.error(f"Failed to truncate evidence in {session_file}: {e}")
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return False

    except PermissionError as e:
        logger.error(f"Permission denied for {session_file}: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to open {session_file}: {e}")
        return False


def truncate_tool_history(session_file: Path, limits: Dict) -> bool:
    """
    Truncate tool_history in session state

    Returns:
        True if truncated, False otherwise
    """
    try:
        with open(session_file) as f:
            state = json.load(f)

        history = state.get("tool_history", [])
        max_entries = limits["tool_history_max"]

        if len(history) > max_entries:
            # Keep last N entries
            state["tool_history"] = history[-max_entries:]

            with open(session_file, "w") as f:
                json.dump(state, f, indent=2)

            return True

    except:
        pass

    return False


def truncate_all_sessions() -> List[str]:
    """
    Truncate evidence ledgers and tool histories in all sessions

    Returns:
        List of status messages
    """
    limits = load_memory_limits()
    session_files = get_session_files()
    messages = []

    for file_path in session_files:
        truncated_evidence = truncate_evidence_ledger(file_path, limits)
        truncated_history = truncate_tool_history(file_path, limits)

        if truncated_evidence or truncated_history:
            parts = []
            if truncated_evidence:
                parts.append(f"evidence→{limits['evidence_ledger_max']}")
            if truncated_history:
                parts.append(f"history→{limits['tool_history_max']}")

            messages.append(f"✅ Truncated {file_path.name}: {', '.join(parts)}")

    return messages




def cleanup_old_archives(limits: Dict) -> List[str]:
    """
    Clean up old session archives to prevent unbounded growth

    Keeps last N archives (configurable), deletes older ones.

    Returns:
        List of status messages
    """
    messages = []
    archive_keep_count = limits.get("archive_keep_count", 20)  # Keep last 20 archives

    if not ARCHIVE_DIR.exists():
        return messages

    # Get all session archives sorted by modification time
    session_archives = sorted(
        (ARCHIVE_DIR / "sessions").glob("*.json.gz") if (ARCHIVE_DIR / "sessions").exists() else [],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    # Delete oldest archives beyond keep limit
    if len(session_archives) > archive_keep_count:
        for old_archive in session_archives[archive_keep_count:]:
            try:
                size_kb = get_file_size_kb(old_archive)
                old_archive.unlink()
                messages.append(f"✅ Deleted old archive: {old_archive.name} ({size_kb:.1f}KB)")
            except Exception as e:
                logger.error(f"Failed to delete archive {old_archive}: {e}")
                messages.append(f"❌ Failed to delete {old_archive.name}: {e}")

    return messages


def cleanup_all() -> Dict[str, List[str]]:
    """
    Run all cleanup tasks

    Returns:
        Dict with results from each task
    """
    results = {
        "telemetry_rotations": rotate_all_telemetry(),
        "session_pruning": prune_old_sessions(),
        "session_truncations": truncate_all_sessions(),
        "archive_cleanup": cleanup_old_archives(load_memory_limits()),
    }

    return results


def get_memory_stats() -> Dict:
    """
    Get memory usage statistics

    Returns:
        Dict with memory stats
    """
    limits = load_memory_limits()
    telemetry_files = get_telemetry_files()
    session_files = get_session_files()

    # Calculate total memory usage
    total_size_kb = 0.0
    telemetry_size_kb = 0.0
    session_size_kb = 0.0

    for f in telemetry_files:
        size = get_file_size_kb(f)
        total_size_kb += size
        telemetry_size_kb += size

    for f in session_files:
        size = get_file_size_kb(f)
        total_size_kb += size
        session_size_kb += size

    # Count lines in telemetry
    total_telemetry_lines = sum(count_lines(f) for f in telemetry_files)

    # Archive stats
    archive_files = []
    if ARCHIVE_DIR.exists():
        archive_files = list(ARCHIVE_DIR.rglob("*.gz"))
    archive_size_kb = sum(get_file_size_kb(f) for f in archive_files)

    return {
        "total_size_kb": total_size_kb,
        "telemetry_size_kb": telemetry_size_kb,
        "session_size_kb": session_size_kb,
        "archive_size_kb": archive_size_kb,
        "telemetry_files": len(telemetry_files),
        "telemetry_lines": total_telemetry_lines,
        "session_files": len(session_files),
        "archive_files": len(archive_files),
        "limits": limits,
    }


def format_memory_report() -> str:
    """
    Generate formatted memory usage report

    Returns:
        Report string
    """
    stats = get_memory_stats()
    limits = stats["limits"]

    # Calculate percentages
    telemetry_pct = (
        stats["telemetry_lines"] / limits["telemetry_max_lines"] * 100
        if limits["telemetry_max_lines"] > 0
        else 0
    )
    session_pct = (
        stats["session_files"] / limits["session_max_active"] * 100
        if limits["session_max_active"] > 0
        else 0
    )

    output = [
        "💾 MEMORY USAGE REPORT",
        "",
        "Active Memory:",
        f"  • Total: {stats['total_size_kb']:.1f}KB",
        f"  • Telemetry: {stats['telemetry_size_kb']:.1f}KB ({stats['telemetry_files']} files, {stats['telemetry_lines']} lines)",
        f"  • Sessions: {stats['session_size_kb']:.1f}KB ({stats['session_files']} files)",
        "",
        "Archived:",
        f"  • Archives: {stats['archive_size_kb']:.1f}KB ({stats['archive_files']} files)",
        "",
        "Limits:",
        f"  • Telemetry Lines: {stats['telemetry_lines']} / {limits['telemetry_max_lines']} ({telemetry_pct:.1f}%)",
        f"  • Active Sessions: {stats['session_files']} / {limits['session_max_active']} ({session_pct:.1f}%)",
        "",
    ]

    # Warnings
    warnings = []
    if telemetry_pct > 80:
        warnings.append(
            f"⚠️ Telemetry near limit ({telemetry_pct:.0f}%) - rotation recommended"
        )
    if session_pct > 80:
        warnings.append(
            f"⚠️ Active sessions near limit ({session_pct:.0f}%) - pruning recommended"
        )

    if warnings:
        output.append("Warnings:")
        output.extend([f"  {w}" for w in warnings])
        output.append("")

    return "\n".join(output)


def auto_cleanup_on_startup() -> str:
    """
    Run automatic cleanup on session start

    Returns:
        Summary message
    """
    results = cleanup_all()

    total_actions = (
        len(results["telemetry_rotations"])
        + len(results["session_pruning"])
        + len(results["session_truncations"])
    )

    if total_actions == 0:
        return "✅ Memory cleanup: No action needed (all within limits)"

    # Build summary
    output = [f"🧹 AUTOMATIC MEMORY CLEANUP ({total_actions} actions)", ""]

    if results["telemetry_rotations"]:
        output.append(f"Telemetry Rotations ({len(results['telemetry_rotations'])}):")
        output.extend([f"  {msg}" for msg in results["telemetry_rotations"]])
        output.append("")

    if results["session_pruning"]:
        output.append(f"Session Pruning ({len(results['session_pruning'])}):")
        output.extend([f"  {msg}" for msg in results["session_pruning"]])
        output.append("")

    if results["session_truncations"]:
        output.append(f"Session Truncations ({len(results['session_truncations'])}):")
        output.extend([f"  {msg}" for msg in results["session_truncations"]])
        output.append("")

    # Stats after cleanup
    stats = get_memory_stats()
    output.append(f"Memory after cleanup: {stats['total_size_kb']:.1f}KB")

    return "\n".join(output)
