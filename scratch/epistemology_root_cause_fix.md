# Epistemology Root Cause Fix

## Problem Summary

`void.py` analysis revealed three production files with critical gaps:

### 1. **epistemology.py** (scripts/lib/)
- **Silent data loss bug**: load failure → reinitialize → overwrite existing file
- **Concurrency race conditions**: Multiple sessions writing global state without locking
- **No retention policy**: Session files and history lists grow infinitely
- **Missing CRUD delete**: No function to delete session state
- **No logging**: Errors occur in vacuum

### 2. **session_init.py** (.claude/hooks/)
- **State/display disconnect**: Initializes state but shows hardcoded "0%" instead of actual value
- **Silent failures**: Malformed input defaults to empty dict without warning

### 3. **session_digest.py** (.claude/hooks/)
- **Write-only memory**: Creates digests but never reads them back
- **No retention policy**: Digests grow infinitely
- **Silent failures**: All errors completely hidden

## Root Cause

The memory directory cleanup we did (adding to .gitignore) addresses the **symptom** (unbounded file growth) but not the **root cause** (missing deletion/pruning in the epistemology library).

## Solution Implemented

### A. New Retention Policy Script

**File**: `scratch/fix_epistemology_gaps.py` (370 lines)

**Features**:
- Session cleanup (delete files >7 days old)
- History pruning (trim ledger/history to last 100 entries)
- Statistics reporting
- Dry-run mode for safety
- File locking to prevent corruption
- Comprehensive logging

**Usage**:
```bash
# Show statistics
python3 scratch/fix_epistemology_gaps.py stats

# Cleanup old sessions (dry-run)
python3 scratch/fix_epistemology_gaps.py cleanup --dry-run

# Actually cleanup
python3 scratch/fix_epistemology_gaps.py cleanup --days 7

# Prune history in all sessions
python3 scratch/fix_epistemology_gaps.py prune
```

### B. Epistemology Library Patches

**File**: `scratch/epistemology_patches.py` (350 lines)

**New functions to add to epistemology.py**:

1. **FileLock** class - File locking context manager
   - Prevents concurrent write corruption
   - Timeout-based lock acquisition
   - Automatic cleanup

2. **safe_load_session_state()** - Replacement for load_session_state()
   - Logs errors instead of silent failure
   - Does NOT reinitialize on corruption (prevents data loss)
   - Returns None with error context

3. **safe_save_session_state()** - Replacement for save_session_state()
   - Uses file locking
   - Returns bool success status
   - Comprehensive error handling

4. **prune_session_history()** - Auto-pruning function
   - Trims evidence_ledger to last 100 entries
   - Trims confidence_history to last 100 entries
   - Trims risk_events to last 100 entries

5. **cleanup_old_sessions()** - Retention policy enforcement
   - Deletes sessions older than N days
   - Dry-run mode for safety
   - Returns detailed results

6. **delete_session_state()** - Missing CRUD delete operation
   - Explicitly delete a session
   - Fills the CRUD gap

7. **safe_update_global_state()** - Thread-safe global state updates
   - Uses file locking
   - Prevents race conditions

### C. session_init.py Fix

**File**: `.claude/hooks/session_init.py`

**Change**: Fixed state/display disconnect
- Now extracts actual confidence/risk from initialized state
- Calculates correct tier based on actual confidence
- Displays real values instead of hardcoded "0%"

**Before**:
```python
state = initialize_session_state(session_id)
# ... hardcoded message with "0%"
```

**After**:
```python
state = initialize_session_state(session_id)
confidence = state.get("confidence", 0)
risk = state.get("risk", 0)
tier = calculate_tier(confidence)
# ... display actual values
```

## Migration Guide

### Step 1: Add new functions to epistemology.py

Append contents of `scratch/epistemology_patches.py` to `scripts/lib/epistemology.py`:

```bash
cat scratch/epistemology_patches.py >> scripts/lib/epistemology.py
```

### Step 2: Replace function calls throughout codebase

**load_session_state → safe_load_session_state**:
```python
# OLD (silent data loss)
state = load_session_state(session_id)
if not state:
    state = initialize_session_state(session_id)  # DESTROYS DATA

# NEW (explicit error handling)
state = safe_load_session_state(session_id)
if not state:
    logging.error(f"Cannot load session {session_id}")
    # Decide: try recovery, alert user, or initialize
    state = initialize_session_state(session_id)  # Only if confirmed OK
```

**save_session_state → safe_save_session_state**:
```python
# OLD (silent failure)
save_session_state(session_id, state)

# NEW (error handling)
success = safe_save_session_state(session_id, state)
if not success:
    logging.error("Failed to save session state!")
```

**Add pruning to update functions**:
```python
# In update_confidence(), apply_penalty(), apply_reward():
# After modifying state, before saving:
state = prune_session_history(state)  # Prevent unbounded growth
safe_save_session_state(session_id, state)
```

**Replace global state updates**:
```python
# OLD (race conditions)
try:
    with open(STATE_FILE, 'w') as f:
        json.dump(data, f)
except:
    pass

# NEW (thread-safe)
safe_update_global_state(data)
```

### Step 3: Add cleanup to SessionEnd hook

Create `.claude/hooks/session_cleanup.py`:

```python
#!/usr/bin/env python3
"""Session cleanup on session end"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from lib.epistemology import cleanup_old_sessions, prune_session_history

# Cleanup old sessions (>7 days)
cleanup_old_sessions(max_age_days=7, dry_run=False)

sys.exit(0)
```

Register in `.claude/settings.json`:
```json
{
  "hooks": {
    "SessionEnd": [
      ".claude/hooks/session_cleanup.py"
    ]
  }
}
```

## Testing

### Test 1: Retention policy stats
```bash
python3 scratch/fix_epistemology_gaps.py stats
```
Expected: Shows current session file statistics

### Test 2: Cleanup dry-run
```bash
python3 scratch/fix_epistemology_gaps.py cleanup --dry-run
```
Expected: Reports what would be deleted (0 files if all recent)

### Test 3: Prune dry-run
```bash
python3 scratch/fix_epistemology_gaps.py prune --dry-run
```
Expected: Reports what would be pruned

### Test 4: session_init.py displays real values
- Start new session
- Check that confidence shows actual value (not hardcoded 0%)
- Check that tier matches confidence level

## Impact

**Before**:
- Session files grow unbounded → need manual cleanup or gitignore
- Silent data loss on load failures → corrupted sessions destroyed
- Race conditions → occasional JSON corruption
- No visibility into errors → black box failures

**After**:
- Automatic cleanup of old sessions (>7 days)
- Automatic pruning of history (>100 entries)
- Protected against data loss (no automatic overwrite on errors)
- Thread-safe concurrent access (file locking)
- Comprehensive logging (errors visible)
- Complete CRUD operations (delete added)

## Files Changed

1. ✅ `.claude/hooks/session_init.py` - Fixed state/display disconnect
2. 📝 `scripts/lib/epistemology.py` - Need to add patches (manual step)
3. ✅ `scratch/fix_epistemology_gaps.py` - Standalone retention tool (working)
4. ✅ `scratch/epistemology_patches.py` - Migration guide (documented)
5. 📝 `.claude/hooks/session_cleanup.py` - Need to create (optional)

## Next Steps

1. Review patches in `scratch/epistemology_patches.py`
2. Decide on migration strategy:
   - Option A: Append patches to epistemology.py (immediate)
   - Option B: Refactor epistemology.py completely (safer but more work)
3. Create SessionEnd cleanup hook (optional, can run manually)
4. Test in production session
5. Monitor logs for errors

## Rationale

**Why fix the root cause?**
- Gitignoring symptoms doesn't prevent the problem
- Files will still grow unbounded locally
- Silent failures will still corrupt data
- Race conditions will still corrupt JSON
- Users will hit disk space issues eventually

**Why not just delete everything?**
- Sessions contain valuable state (confidence, evidence)
- Aggressive deletion loses context mid-session
- Retention policy balances history vs disk space
- 7 days is sufficient for debugging while preventing bloat
