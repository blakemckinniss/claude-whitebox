#!/usr/bin/env python3
"""
Auto-Commit Enforcement Library (23rd Protocol)
AGGRESSIVE MODE: Maximize commit density for semantic context

Philosophy:
- More commits = better semantic timeline
- Git commits are free context markers for future analysis
- Only protect against runaway loops and broken states
- No "message quality" concerns - context > cleanliness

Triggers (AGGRESSIVE):
- 10-20 uncommitted file changes
- >500 LOC diff
- Both file count + LOC triggers

Safeguards (MINIMAL):
- Runaway loop detection (>5 commits in 2 minutes)
- Git command failures (don't retry broken commits)

Auto-Tuning: None - aggressive thresholds are fixed
"""
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# Memory dir
MEMORY_DIR = Path(__file__).resolve().parent.parent / ".claude" / "memory"
STATE_FILE = MEMORY_DIR / "auto_commit_state.json"

# AGGRESSIVE THRESHOLDS (FIXED - NO AUTO-TUNING)
FILE_COUNT_MIN = 10      # Start committing at 10 files
FILE_COUNT_MAX = 20      # Force commit at 20 files
LOC_THRESHOLD = 500      # Force commit at 500 LOC diff
COMBINED_THRESHOLD = True  # Both file count AND LOC must be met

# RUNAWAY PROTECTION (ONLY SAFETY)
MAX_COMMITS_PER_WINDOW = 5   # Max 5 commits in time window
COMMIT_WINDOW_SECONDS = 120  # 2 minute window
RETRY_BACKOFF_SECONDS = 300  # 5 minute backoff after git failure


def load_state() -> Dict:
    """Load auto-commit state"""
    if not STATE_FILE.exists():
        return {
            "enabled": True,
            "commit_history": [],  # List of timestamps
            "last_failure": None,   # Last git failure timestamp
            "total_auto_commits": 0,
            "initialized_at": datetime.now().isoformat(),
        }

    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        # Corrupted state or I/O error - reset to default
        return {
            "enabled": True,
            "commit_history": [],
            "last_failure": None,
            "total_auto_commits": 0,
            "initialized_at": datetime.now().isoformat(),
        }


def save_state(state: Dict) -> None:
    """Save auto-commit state"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except (IOError, OSError) as e:
        # Disk full, permissions, readonly filesystem
        import sys
        print(f"⚠️ Failed to save auto-commit state: {e}", file=sys.stderr)
        # Continue without saving - don't crash


def get_uncommitted_stats() -> Tuple[int, int, List[str]]:
    """
    Get uncommitted change statistics

    Returns:
        Tuple[int, int, List[str]]: (file_count, loc_changed, file_list)
    """
    try:
        # Get file count
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5
        )

        files = []
        for line in status_result.stdout.strip().split('\n'):
            if line:
                # Format: " M file.py" or "?? file.py"
                filepath = line[3:].strip()
                files.append(filepath)

        file_count = len(files)

        # Get LOC diff
        diff_result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Parse diff stat: "31 files changed, 1139 insertions(+), 26 deletions(-)"
        loc_changed = 0
        last_line = diff_result.stdout.strip().split('\n')[-1] if diff_result.stdout.strip() else ""

        if "insertion" in last_line or "deletion" in last_line:
            # Extract insertions
            if "insertion" in last_line:
                import re
                match = re.search(r'(\d+) insertion', last_line)
                if match:
                    loc_changed += int(match.group(1))

            # Extract deletions
            if "deletion" in last_line:
                import re
                match = re.search(r'(\d+) deletion', last_line)
                if match:
                    loc_changed += int(match.group(1))

        return file_count, loc_changed, files

    except subprocess.TimeoutExpired:
        # Git timeout - likely large repo
        import sys
        print("⚠️ Git timeout - repo too large for quick stats", file=sys.stderr)
        return 0, 0, []
    except FileNotFoundError:
        # Git not installed or not in PATH
        import sys
        print("⚠️ Git not found - auto-commit monitoring disabled", file=sys.stderr)
        return 0, 0, []
    except Exception as e:
        # Other errors - log but don't crash
        import sys
        print(f"⚠️ Git stats error: {e}", file=sys.stderr)
        return 0, 0, []


def check_runaway_loop(state: Dict) -> Tuple[bool, Optional[str]]:
    """
    Check if we're in a runaway commit loop

    Returns:
        Tuple[bool, str]: (is_runaway, error_message)
    """
    commit_history = state.get("commit_history", [])

    # Filter to commits in the time window
    now = datetime.now()
    window_start = now - timedelta(seconds=COMMIT_WINDOW_SECONDS)

    recent_commits = [
        datetime.fromisoformat(ts)
        for ts in commit_history
        if datetime.fromisoformat(ts) > window_start
    ]

    if len(recent_commits) >= MAX_COMMITS_PER_WINDOW:
        message = f"""🚨 RUNAWAY COMMIT LOOP DETECTED

Auto-commit suspended: {len(recent_commits)} commits in {COMMIT_WINDOW_SECONDS}s

This indicates a broken loop or conflict. Auto-commit disabled until manual intervention.

Recent commits:
{chr(10).join(f"  • {ts.isoformat()}" for ts in recent_commits[-5:])}

To reset:
  rm {STATE_FILE}

Or manually fix the issue and the system will auto-resume after {COMMIT_WINDOW_SECONDS}s."""

        return True, message

    return False, None


def check_git_failure_backoff(state: Dict) -> Tuple[bool, Optional[str]]:
    """
    Check if we're in backoff period after git failure

    Returns:
        Tuple[bool, str]: (in_backoff, error_message)
    """
    last_failure = state.get("last_failure")
    if not last_failure:
        return False, None

    failure_time = datetime.fromisoformat(last_failure)
    now = datetime.now()
    elapsed = (now - failure_time).total_seconds()

    if elapsed < RETRY_BACKOFF_SECONDS:
        remaining = int(RETRY_BACKOFF_SECONDS - elapsed)
        message = f"""⏸️ AUTO-COMMIT BACKOFF ACTIVE

Last git commit failed at {failure_time.strftime('%H:%M:%S')}
Backing off for {remaining}s to avoid retry loops.

If you've fixed the issue, delete the state file:
  rm {STATE_FILE}"""

        return True, message

    return False, None


def should_force_commit(file_count: int, loc_changed: int) -> Tuple[bool, str]:
    """
    Check if we should force a commit

    Returns:
        Tuple[bool, str]: (should_commit, reason)
    """
    reasons = []

    # File count threshold
    file_trigger = file_count >= FILE_COUNT_MIN
    if file_trigger:
        reasons.append(f"{file_count} files changed (threshold: {FILE_COUNT_MIN})")

    # LOC threshold
    loc_trigger = loc_changed >= LOC_THRESHOLD
    if loc_trigger:
        reasons.append(f"{loc_changed} LOC changed (threshold: {LOC_THRESHOLD})")

    # COMBINED or INDIVIDUAL triggers
    if COMBINED_THRESHOLD:
        # Both must be true
        should_commit = file_trigger and loc_trigger
    else:
        # Either can be true
        should_commit = file_trigger or loc_trigger

    if should_commit:
        return True, " AND ".join(reasons)

    return False, ""


def generate_commit_message(file_count: int, loc_changed: int, files: List[str]) -> str:
    """Generate aggressive commit message (semantic context optimized)"""

    # Categorize files by directory for semantic context
    categories = {
        "hooks": [],
        "libs": [],
        "scripts": [],
        "docs": [],
        "memory": [],
        "config": [],
        "tests": [],
        "other": []
    }

    for f in files:
        if '.claude/hooks' in f:
            categories["hooks"].append(f)
        elif 'scripts/lib' in f:
            categories["libs"].append(f)
        elif 'scripts/ops' in f:
            categories["scripts"].append(f)
        elif f.endswith('.md'):
            categories["docs"].append(f)
        elif '.claude/memory' in f:
            categories["memory"].append(f)
        elif '.claude/settings' in f or f.endswith('.json'):
            categories["config"].append(f)
        elif 'test' in f.lower():
            categories["tests"].append(f)
        else:
            categories["other"].append(f)

    # Build semantic summary
    parts = []
    for cat, items in categories.items():
        if items:
            parts.append(f"{cat}({len(items)})")

    summary = " + ".join(parts) if parts else f"{file_count} files"

    # Prefix based on dominant category
    dominant_cat = max(categories.items(), key=lambda x: len(x[1]))[0] if any(categories.values()) else "other"

    prefix_map = {
        "hooks": "feat(hooks)",
        "libs": "feat(lib)",
        "scripts": "feat(scripts)",
        "docs": "docs",
        "memory": "chore(memory)",
        "config": "chore(config)",
        "tests": "test",
        "other": "chore"
    }

    prefix = prefix_map.get(dominant_cat, "chore")

    # Build detailed message
    details = []
    for cat, items in categories.items():
        if items:
            # Show first 3 files per category for semantic context
            file_list = ", ".join(Path(f).name for f in items[:3])
            if len(items) > 3:
                file_list += f" +{len(items) - 3} more"
            details.append(f"  • {cat}: {file_list}")

    message = f"""{prefix}: Auto-commit {summary} ({loc_changed} LOC)

Semantic checkpoint - {file_count} files, {loc_changed} LOC changed
Triggered by aggressive commit enforcement for context density

Changes by category:
{chr(10).join(details)}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

    return message


def execute_auto_commit(state: Dict) -> Tuple[bool, str]:
    """
    Execute auto-commit with quality gates

    Returns:
        Tuple[bool, str]: (success, message)
    """
    file_count, loc_changed, files = get_uncommitted_stats()

    if file_count == 0:
        return False, "No uncommitted changes"

    try:
        # Stage all changes
        subprocess.run(
            ["git", "add", "."],
            check=True,
            timeout=10,
            capture_output=True
        )

        # Generate message
        message = generate_commit_message(file_count, loc_changed, files)

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", message],
            check=True,
            capture_output=True,
            text=True,
            timeout=10
        )

        # Record success
        state["commit_history"].append(datetime.now().isoformat())
        # Prune old history (keep last 100 commits)
        if len(state["commit_history"]) > 100:
            state["commit_history"] = state["commit_history"][-100:]
        state["total_auto_commits"] = state.get("total_auto_commits", 0) + 1
        state["last_failure"] = None  # Clear any previous failure
        save_state(state)

        success_msg = f"""✅ AUTO-COMMITTED {file_count} FILES ({loc_changed} LOC)

Semantic checkpoint created for context injection.

Files: {file_count}
LOC: {loc_changed}
Total auto-commits: {state['total_auto_commits']}

Summary: {message.split(chr(10))[0]}

System will continue monitoring for next threshold."""

        return True, success_msg

    except subprocess.CalledProcessError as e:
        # Git command failed - record failure and enter backoff
        state["last_failure"] = datetime.now().isoformat()
        save_state(state)

        error_msg = f"""⚠️ AUTO-COMMIT FAILED (Git Error)

Git command failed: {e}
Stderr: {e.stderr if hasattr(e, 'stderr') else 'N/A'}

Entering {RETRY_BACKOFF_SECONDS}s backoff to avoid retry loops.

You may need to:
  1. Fix merge conflicts
  2. Check git status
  3. Manually commit if needed

Auto-commit will resume after backoff period."""

        return False, error_msg

    except Exception as e:
        # Unexpected error
        state["last_failure"] = datetime.now().isoformat()
        save_state(state)

        error_msg = f"""⚠️ AUTO-COMMIT FAILED (Unexpected Error)

Error: {e}

Entering {RETRY_BACKOFF_SECONDS}s backoff.

To reset: rm {STATE_FILE}"""

        return False, error_msg


def check_and_commit() -> Optional[str]:
    """
    Main enforcement function - check thresholds and commit if needed

    Returns:
        Optional[str]: Message to display (None if no action needed)
    """
    state = load_state()

    # Check if disabled
    if not state.get("enabled", True):
        return None

    # Check runaway loop
    is_runaway, runaway_msg = check_runaway_loop(state)
    if is_runaway:
        state["enabled"] = False  # Disable until manual reset
        save_state(state)
        return runaway_msg

    # Check git failure backoff
    in_backoff, backoff_msg = check_git_failure_backoff(state)
    if in_backoff:
        return None  # Silent during backoff

    # Get current stats
    file_count, loc_changed, files = get_uncommitted_stats()

    # Check if we should force commit
    should_commit, reason = should_force_commit(file_count, loc_changed)

    if not should_commit:
        return None  # Below thresholds

    # Execute commit
    success, message = execute_auto_commit(state)

    return message


def get_stats() -> Dict:
    """Get auto-commit statistics"""
    state = load_state()
    file_count, loc_changed, files = get_uncommitted_stats()

    # Check thresholds
    should_commit, reason = should_force_commit(file_count, loc_changed)

    return {
        "enabled": state.get("enabled", True),
        "total_auto_commits": state.get("total_auto_commits", 0),
        "current_file_count": file_count,
        "current_loc_changed": loc_changed,
        "thresholds": {
            "file_count_min": FILE_COUNT_MIN,
            "file_count_max": FILE_COUNT_MAX,
            "loc_threshold": LOC_THRESHOLD,
            "combined_mode": COMBINED_THRESHOLD
        },
        "will_commit_next": should_commit,
        "commit_reason": reason if should_commit else "Below thresholds",
        "commit_history_count": len(state.get("commit_history", [])),
        "last_failure": state.get("last_failure"),
        "initialized_at": state.get("initialized_at"),
    }


def reset_state() -> str:
    """Reset auto-commit state (for debugging)"""
    STATE_FILE.unlink(missing_ok=True)
    return "✅ Auto-commit state reset"


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "check":
            result = check_and_commit()
            if result:
                print(result)

        elif cmd == "stats":
            stats = get_stats()
            print(json.dumps(stats, indent=2))

        elif cmd == "reset":
            print(reset_state())

        else:
            print(f"Unknown command: {cmd}")
            print("Usage: auto_commit_enforcement.py [check|stats|reset]")

    else:
        # Default: check and commit
        result = check_and_commit()
        if result:
            print(result)
