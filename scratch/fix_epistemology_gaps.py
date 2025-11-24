#!/usr/bin/env python3
"""
Fix epistemology.py root causes:
1. Add session cleanup/retention policy
2. Fix silent data loss bug (load failure → reinit)
3. Add file locking for concurrent writes
4. Add logging throughout
5. Add history pruning
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import fcntl
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

MEMORY_DIR = Path(__file__).resolve().parent.parent / ".claude" / "memory"
MAX_SESSION_AGE_DAYS = 7  # Delete sessions older than 7 days
MAX_HISTORY_LENGTH = 100  # Prune history/ledger to last 100 entries
MAX_RETRY_ATTEMPTS = 3  # For file locking
LOCK_TIMEOUT = 2  # seconds


class FileLock:
    """Context manager for file locking to prevent concurrent write corruption"""

    def __init__(self, file_path: Path, timeout: float = LOCK_TIMEOUT):
        self.file_path = file_path
        self.timeout = timeout
        self.lock_file = file_path.with_suffix(file_path.suffix + '.lock')
        self.fd = None

    def __enter__(self):
        """Acquire lock with timeout"""
        start_time = time.time()
        while True:
            try:
                self.lock_file.parent.mkdir(parents=True, exist_ok=True)
                self.fd = open(self.lock_file, 'w')
                fcntl.flock(self.fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                logging.debug(f"Acquired lock: {self.lock_file}")
                return self
            except (IOError, OSError) as e:
                if time.time() - start_time > self.timeout:
                    logging.error(f"Lock timeout for {self.lock_file}")
                    raise TimeoutError(f"Could not acquire lock for {self.file_path}")
                time.sleep(0.1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release lock"""
        if self.fd:
            try:
                fcntl.flock(self.fd.fileno(), fcntl.LOCK_UN)
                self.fd.close()
                self.lock_file.unlink(missing_ok=True)
                logging.debug(f"Released lock: {self.lock_file}")
            except Exception as e:
                logging.warning(f"Error releasing lock {self.lock_file}: {e}")


def safe_load_json(file_path: Path, default: Optional[Dict] = None) -> Optional[Dict]:
    """
    Safely load JSON with proper error handling and logging.
    Returns default (or None) on failure WITHOUT reinitializing.
    """
    if not file_path.exists():
        logging.debug(f"File not found: {file_path}")
        return default

    try:
        with open(file_path) as f:
            data = json.load(f)
            logging.debug(f"Loaded {file_path}")
            return data
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error in {file_path}: {e}")
        # DO NOT reinitialize - return default to preserve existing file
        return default
    except PermissionError as e:
        logging.error(f"Permission denied reading {file_path}: {e}")
        return default
    except Exception as e:
        logging.error(f"Unexpected error reading {file_path}: {e}")
        return default


def safe_save_json(file_path: Path, data: Dict, use_lock: bool = True) -> bool:
    """
    Safely save JSON with file locking and error handling.
    Returns True on success, False on failure.
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if use_lock:
            with FileLock(file_path):
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
        else:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)

        logging.debug(f"Saved {file_path}")
        return True

    except PermissionError as e:
        logging.error(f"Permission denied writing {file_path}: {e}")
        return False
    except OSError as e:
        logging.error(f"OS error writing {file_path}: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error writing {file_path}: {e}")
        return False


def prune_session_history(state: Dict) -> Dict:
    """
    Prune evidence_ledger and confidence_history to prevent unbounded growth.
    Keeps last MAX_HISTORY_LENGTH entries.
    """
    modified = False

    # Prune evidence_ledger
    if "evidence_ledger" in state and len(state["evidence_ledger"]) > MAX_HISTORY_LENGTH:
        old_len = len(state["evidence_ledger"])
        state["evidence_ledger"] = state["evidence_ledger"][-MAX_HISTORY_LENGTH:]
        logging.info(f"Pruned evidence_ledger: {old_len} → {len(state['evidence_ledger'])}")
        modified = True

    # Prune confidence_history
    if "confidence_history" in state and len(state["confidence_history"]) > MAX_HISTORY_LENGTH:
        old_len = len(state["confidence_history"])
        state["confidence_history"] = state["confidence_history"][-MAX_HISTORY_LENGTH:]
        logging.info(f"Pruned confidence_history: {old_len} → {len(state['confidence_history'])}")
        modified = True

    # Prune risk_events
    if "risk_events" in state and len(state["risk_events"]) > MAX_HISTORY_LENGTH:
        old_len = len(state["risk_events"])
        state["risk_events"] = state["risk_events"][-MAX_HISTORY_LENGTH:]
        logging.info(f"Pruned risk_events: {old_len} → {len(state['risk_events'])}")
        modified = True

    return state


def cleanup_old_sessions(dry_run: bool = False) -> Dict[str, List[str]]:
    """
    Delete session state files older than MAX_SESSION_AGE_DAYS.
    Returns dict with 'deleted' and 'kept' lists.
    """
    if not MEMORY_DIR.exists():
        logging.warning(f"Memory directory not found: {MEMORY_DIR}")
        return {"deleted": [], "kept": [], "errors": []}

    cutoff_date = datetime.now() - timedelta(days=MAX_SESSION_AGE_DAYS)
    deleted = []
    kept = []
    errors = []

    for session_file in MEMORY_DIR.glob("session_*_state.json"):
        try:
            # Get file modification time
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime)

            if mtime < cutoff_date:
                if dry_run:
                    logging.info(f"[DRY-RUN] Would delete: {session_file.name} (age: {(datetime.now() - mtime).days} days)")
                    deleted.append(session_file.name)
                else:
                    session_file.unlink()
                    logging.info(f"Deleted old session: {session_file.name} (age: {(datetime.now() - mtime).days} days)")
                    deleted.append(session_file.name)
            else:
                kept.append(session_file.name)
                logging.debug(f"Kept recent session: {session_file.name}")

        except Exception as e:
            logging.error(f"Error processing {session_file.name}: {e}")
            errors.append(f"{session_file.name}: {e}")

    return {"deleted": deleted, "kept": kept, "errors": errors}


def cleanup_session_digests(dry_run: bool = False) -> Dict[str, List[str]]:
    """
    Delete session digest files older than MAX_SESSION_AGE_DAYS.
    Returns dict with 'deleted' and 'kept' lists.
    """
    digest_dir = MEMORY_DIR / "session_digests"
    if not digest_dir.exists():
        logging.warning(f"Session digests directory not found: {digest_dir}")
        return {"deleted": [], "kept": [], "errors": []}

    cutoff_date = datetime.now() - timedelta(days=MAX_SESSION_AGE_DAYS)
    deleted = []
    kept = []
    errors = []

    for digest_file in digest_dir.glob("*.json"):
        try:
            mtime = datetime.fromtimestamp(digest_file.stat().st_mtime)

            if mtime < cutoff_date:
                if dry_run:
                    logging.info(f"[DRY-RUN] Would delete: {digest_file.name} (age: {(datetime.now() - mtime).days} days)")
                    deleted.append(digest_file.name)
                else:
                    digest_file.unlink()
                    logging.info(f"Deleted old digest: {digest_file.name} (age: {(datetime.now() - mtime).days} days)")
                    deleted.append(digest_file.name)
            else:
                kept.append(digest_file.name)

        except Exception as e:
            logging.error(f"Error processing {digest_file.name}: {e}")
            errors.append(f"{digest_file.name}: {e}")

    return {"deleted": deleted, "kept": kept, "errors": errors}


def prune_all_sessions(dry_run: bool = False) -> None:
    """
    Prune history in all existing session files to prevent unbounded growth.
    """
    if not MEMORY_DIR.exists():
        logging.warning(f"Memory directory not found: {MEMORY_DIR}")
        return

    pruned_count = 0
    error_count = 0

    for session_file in MEMORY_DIR.glob("session_*_state.json"):
        try:
            state = safe_load_json(session_file)
            if not state:
                logging.warning(f"Could not load {session_file.name}")
                error_count += 1
                continue

            # Check if pruning needed
            needs_pruning = (
                len(state.get("evidence_ledger", [])) > MAX_HISTORY_LENGTH or
                len(state.get("confidence_history", [])) > MAX_HISTORY_LENGTH or
                len(state.get("risk_events", [])) > MAX_HISTORY_LENGTH
            )

            if needs_pruning:
                if dry_run:
                    logging.info(f"[DRY-RUN] Would prune: {session_file.name}")
                    pruned_count += 1
                else:
                    state = prune_session_history(state)
                    if safe_save_json(session_file, state):
                        pruned_count += 1
                        logging.info(f"Pruned session: {session_file.name}")
                    else:
                        error_count += 1

        except Exception as e:
            logging.error(f"Error pruning {session_file.name}: {e}")
            error_count += 1

    logging.info(f"Pruning complete: {pruned_count} sessions pruned, {error_count} errors")


def show_retention_stats() -> None:
    """Show statistics about session file retention"""
    if not MEMORY_DIR.exists():
        logging.error(f"Memory directory not found: {MEMORY_DIR}")
        return

    session_files = list(MEMORY_DIR.glob("session_*_state.json"))
    digest_files = list((MEMORY_DIR / "session_digests").glob("*.json")) if (MEMORY_DIR / "session_digests").exists() else []

    if not session_files:
        print("No session files found.")
        return

    print(f"\n{'='*70}")
    print(f"SESSION RETENTION STATISTICS")
    print(f"{'='*70}\n")

    print(f"Total session state files: {len(session_files)}")
    print(f"Total session digest files: {len(digest_files)}")
    print(f"Retention policy: {MAX_SESSION_AGE_DAYS} days\n")

    # Age distribution
    now = datetime.now()
    cutoff = now - timedelta(days=MAX_SESSION_AGE_DAYS)

    old_sessions = []
    recent_sessions = []

    for session_file in session_files:
        mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
        age_days = (now - mtime).days

        if mtime < cutoff:
            old_sessions.append((session_file.name, age_days))
        else:
            recent_sessions.append((session_file.name, age_days))

    print(f"Sessions to delete (>{MAX_SESSION_AGE_DAYS} days): {len(old_sessions)}")
    if old_sessions:
        for name, age in sorted(old_sessions, key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {name} ({age} days old)")
        if len(old_sessions) > 5:
            print(f"  ... and {len(old_sessions) - 5} more")

    print(f"\nSessions to keep (≤{MAX_SESSION_AGE_DAYS} days): {len(recent_sessions)}")
    if recent_sessions:
        for name, age in sorted(recent_sessions, key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {name} ({age} days old)")
        if len(recent_sessions) > 5:
            print(f"  ... and {len(recent_sessions) - 5} more")

    # Size estimation
    total_size = sum(f.stat().st_size for f in session_files) / 1024  # KB
    print(f"\nTotal size of session files: {total_size:.1f} KB")

    if old_sessions:
        old_size = sum((MEMORY_DIR / name).stat().st_size for name, _ in old_sessions) / 1024
        print(f"Space to be freed: {old_size:.1f} KB\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Epistemology retention policy management")
    parser.add_argument("action", choices=["cleanup", "prune", "stats"],
                       help="Action to perform: cleanup (delete old), prune (trim history), stats (show info)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without actually doing it")
    parser.add_argument("--days", type=int, default=MAX_SESSION_AGE_DAYS,
                       help=f"Max age in days for session files (default: {MAX_SESSION_AGE_DAYS})")
    parser.add_argument("--max-history", type=int, default=MAX_HISTORY_LENGTH,
                       help=f"Max history entries to keep (default: {MAX_HISTORY_LENGTH})")

    args = parser.parse_args()

    # Update globals if specified
    MAX_SESSION_AGE_DAYS = args.days
    MAX_HISTORY_LENGTH = args.max_history

    if args.action == "stats":
        show_retention_stats()

    elif args.action == "cleanup":
        print(f"\n{'='*70}")
        print(f"SESSION CLEANUP {'(DRY RUN)' if args.dry_run else ''}")
        print(f"{'='*70}\n")

        # Cleanup session state files
        result = cleanup_old_sessions(dry_run=args.dry_run)
        print(f"\nSession state files:")
        print(f"  Deleted: {len(result['deleted'])}")
        print(f"  Kept: {len(result['kept'])}")
        if result['errors']:
            print(f"  Errors: {len(result['errors'])}")

        # Cleanup session digest files
        digest_result = cleanup_session_digests(dry_run=args.dry_run)
        print(f"\nSession digest files:")
        print(f"  Deleted: {len(digest_result['deleted'])}")
        print(f"  Kept: {len(digest_result['kept'])}")
        if digest_result['errors']:
            print(f"  Errors: {len(digest_result['errors'])}")

        if args.dry_run:
            print("\nThis was a dry run. Use without --dry-run to actually delete files.")

    elif args.action == "prune":
        print(f"\n{'='*70}")
        print(f"SESSION HISTORY PRUNING {'(DRY RUN)' if args.dry_run else ''}")
        print(f"{'='*70}\n")
        print(f"Pruning history to last {MAX_HISTORY_LENGTH} entries per session...\n")

        prune_all_sessions(dry_run=args.dry_run)

        if args.dry_run:
            print("\nThis was a dry run. Use without --dry-run to actually prune files.")
