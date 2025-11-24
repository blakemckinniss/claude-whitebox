#!/usr/bin/env python3
"""
New functions to add to epistemology.py to fix root cause gaps.
These can be appended to the end of the file.
"""

import logging
import fcntl
import time
from datetime import datetime, timedelta

# Add these constants at the top of epistemology.py
"""
MAX_SESSION_AGE_DAYS = 7  # Delete sessions older than 7 days
MAX_HISTORY_LENGTH = 100  # Prune history/ledger to last 100 entries
LOCK_TIMEOUT = 2  # seconds for file locking
"""

# ===================================================================
# NEW FUNCTIONS TO ADD
# ===================================================================

# Setup logging (add at top after imports)
logging.basicConfig(
    level=logging.WARNING,  # Don't pollute stdout, but log errors
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class FileLock:
    """
    Context manager for file locking to prevent concurrent write corruption.

    Usage:
        with FileLock(file_path):
            # Safe to write to file_path
            with open(file_path, 'w') as f:
                json.dump(data, f)
    """

    def __init__(self, file_path: Path, timeout: float = 2.0):
        self.file_path = file_path
        self.timeout = timeout
        self.lock_file = file_path.with_suffix(file_path.suffix + '.lock')
        self.fd = None

    def __enter__(self):
        """Acquire exclusive lock with timeout"""
        start_time = time.time()
        while True:
            try:
                self.lock_file.parent.mkdir(parents=True, exist_ok=True)
                self.fd = open(self.lock_file, 'w')
                fcntl.flock(self.fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (IOError, OSError):
                if time.time() - start_time > self.timeout:
                    logging.error(f"Lock timeout for {self.lock_file}")
                    raise TimeoutError(f"Could not acquire lock for {self.file_path}")
                time.sleep(0.05)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release lock"""
        if self.fd:
            try:
                fcntl.flock(self.fd.fileno(), fcntl.LOCK_UN)
                self.fd.close()
                self.lock_file.unlink(missing_ok=True)
            except Exception as e:
                logging.warning(f"Error releasing lock: {e}")


def safe_load_session_state(session_id: str) -> Optional[Dict]:
    """
    REPLACEMENT for load_session_state() - fixes silent data loss bug.

    Old behavior: load fails → return None → caller reinitializes → data loss
    New behavior: load fails → log error → return None → caller must handle

    Callers should check if None and decide whether to:
    - Try backup/recovery
    - Alert user
    - Reinitialize (only if confirmed file is corrupted beyond repair)
    """
    state_file = get_session_state_file(session_id)
    if not state_file.exists():
        logging.debug(f"Session file not found: {session_id}")
        return None

    try:
        with open(state_file) as f:
            data = json.load(f)
            logging.debug(f"Loaded session: {session_id}")
            return data
    except json.JSONDecodeError as e:
        logging.error(f"JSON CORRUPTION in session {session_id}: {e}")
        logging.error(f"File: {state_file}")
        logging.error("DO NOT REINITIALIZE - data may be recoverable")
        # Could implement backup/recovery here
        return None
    except PermissionError as e:
        logging.error(f"PERMISSION DENIED reading session {session_id}: {e}")
        # Temporary failure - DO NOT reinitialize
        return None
    except Exception as e:
        logging.error(f"UNEXPECTED ERROR loading session {session_id}: {e}")
        return None


def safe_save_session_state(session_id: str, state: Dict) -> bool:
    """
    REPLACEMENT for save_session_state() - adds error handling and file locking.

    Returns:
        bool: True on success, False on failure
    """
    state_file = get_session_state_file(session_id)

    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)

        # Use file locking for concurrent safety
        with FileLock(state_file):
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)

        logging.debug(f"Saved session: {session_id}")
        return True

    except PermissionError as e:
        logging.error(f"PERMISSION DENIED writing session {session_id}: {e}")
        return False
    except OSError as e:
        logging.error(f"OS ERROR writing session {session_id}: {e}")
        return False
    except Exception as e:
        logging.error(f"UNEXPECTED ERROR saving session {session_id}: {e}")
        return False


def prune_session_history(state: Dict, max_length: int = 100) -> Dict:
    """
    Prune evidence_ledger, confidence_history, risk_events to prevent unbounded growth.

    Args:
        state: Session state dict
        max_length: Maximum entries to keep (default 100)

    Returns:
        Modified state dict with pruned history
    """
    # Prune evidence_ledger
    if "evidence_ledger" in state and len(state["evidence_ledger"]) > max_length:
        old_len = len(state["evidence_ledger"])
        state["evidence_ledger"] = state["evidence_ledger"][-max_length:]
        logging.info(f"Pruned evidence_ledger: {old_len} → {max_length}")

    # Prune confidence_history
    if "confidence_history" in state and len(state["confidence_history"]) > max_length:
        old_len = len(state["confidence_history"])
        state["confidence_history"] = state["confidence_history"][-max_length:]
        logging.info(f"Pruned confidence_history: {old_len} → {max_length}")

    # Prune risk_events
    if "risk_events" in state and len(state["risk_events"]) > max_length:
        old_len = len(state["risk_events"])
        state["risk_events"] = state["risk_events"][-max_length:]
        logging.info(f"Pruned risk_events: {old_len} → {max_length}")

    return state


def cleanup_old_sessions(max_age_days: int = 7, dry_run: bool = False) -> Dict[str, list]:
    """
    Delete session state files older than max_age_days.

    Args:
        max_age_days: Maximum age in days (default 7)
        dry_run: If True, only report what would be deleted

    Returns:
        Dict with 'deleted', 'kept', 'errors' lists
    """
    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    deleted = []
    kept = []
    errors = []

    for session_file in MEMORY_DIR.glob("session_*_state.json"):
        try:
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
            age_days = (datetime.now() - mtime).days

            if mtime < cutoff_date:
                if dry_run:
                    logging.info(f"[DRY-RUN] Would delete: {session_file.name} ({age_days} days old)")
                else:
                    session_file.unlink()
                    logging.info(f"Deleted old session: {session_file.name} ({age_days} days old)")
                deleted.append(session_file.name)
            else:
                kept.append(session_file.name)

        except Exception as e:
            logging.error(f"Error processing {session_file.name}: {e}")
            errors.append(f"{session_file.name}: {str(e)}")

    return {"deleted": deleted, "kept": kept, "errors": errors}


def delete_session_state(session_id: str) -> bool:
    """
    Delete session state file for given session_id.
    Fills the CRUD gap: create/read/update existed, but delete was missing.

    Args:
        session_id: Session identifier

    Returns:
        bool: True if deleted, False if not found or error
    """
    state_file = get_session_state_file(session_id)

    if not state_file.exists():
        logging.warning(f"Session file not found: {session_id}")
        return False

    try:
        state_file.unlink()
        logging.info(f"Deleted session: {session_id}")
        return True
    except Exception as e:
        logging.error(f"Error deleting session {session_id}: {e}")
        return False


def safe_update_global_state(data: Dict) -> bool:
    """
    Thread-safe update to global STATE_FILE with file locking.

    Args:
        data: State data to write

    Returns:
        bool: True on success, False on failure
    """
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

        with FileLock(STATE_FILE):
            with open(STATE_FILE, 'w') as f:
                json.dump(data, f, indent=2)

        return True

    except Exception as e:
        logging.error(f"Failed to update global state: {e}")
        return False


# ===================================================================
# USAGE NOTES FOR MIGRATING EXISTING CODE
# ===================================================================

"""
MIGRATION GUIDE:

1. Replace load_session_state() calls:
   OLD:
       state = load_session_state(session_id)
       if not state:
           state = initialize_session_state(session_id)  # DESTROYS DATA

   NEW:
       state = safe_load_session_state(session_id)
       if not state:
           logging.error(f"Cannot load session {session_id}")
           # Decide: try recovery, alert user, or initialize fresh
           state = initialize_session_state(session_id)  # Only if confirmed OK

2. Replace save_session_state() calls:
   OLD:
       save_session_state(session_id, state)  # Silent failure

   NEW:
       success = safe_save_session_state(session_id, state)
       if not success:
           logging.error("Failed to save session state!")

3. Add pruning to high-frequency update functions:
   In update_confidence(), apply_penalty(), apply_reward():

       # After modifying state, before saving:
       state = prune_session_history(state)  # Prevent unbounded growth
       safe_save_session_state(session_id, state)

4. Replace global state updates:
   OLD:
       try:
           with open(STATE_FILE, 'w') as f:
               json.dump(data, f)
       except:
           pass  # Silent failure + race conditions

   NEW:
       safe_update_global_state(data)  # Thread-safe, logged

5. Add cleanup to SessionEnd hook:
   cleanup_old_sessions(max_age_days=7, dry_run=False)
"""
