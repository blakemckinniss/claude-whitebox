#!/usr/bin/env python3
"""
Auto-Commit on Stop/SessionEnd with Threshold Gating
Triggers: Stop, SessionEnd
Purpose: Only commit when there are significant changes (large diff or many files)

Philosophy:
- Commits only on session boundaries (Stop/SessionEnd)
- Requires EITHER significant file count OR significant LOC changes
- No constant commit spam during work - batch at boundaries
- Protects against committing trivial 1-2 file changes
"""
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# =============================================================================
# THRESHOLDS - Adjust these to control commit sensitivity
# =============================================================================
MIN_FILES_THRESHOLD = 3        # Minimum files changed to trigger commit
MIN_LOC_THRESHOLD = 100        # Minimum lines of code changed to trigger commit
# Note: Either threshold being met will trigger a commit (OR logic)

# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def get_uncommitted_stats():
    """
    Get uncommitted change statistics.

    Returns:
        tuple: (file_count, loc_changed, file_list)
    """
    try:
        # Get file count from git status
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5
        )

        files = []
        for line in status_result.stdout.strip().split('\n'):
            if line.strip():
                filepath = line[3:].strip()
                files.append(filepath)

        file_count = len(files)

        # Get LOC diff (staged + unstaged)
        diff_result = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )

        loc_changed = 0
        last_line = diff_result.stdout.strip().split('\n')[-1] if diff_result.stdout.strip() else ""

        # Parse: "X files changed, Y insertions(+), Z deletions(-)"
        import re
        ins_match = re.search(r'(\d+) insertion', last_line)
        del_match = re.search(r'(\d+) deletion', last_line)

        if ins_match:
            loc_changed += int(ins_match.group(1))
        if del_match:
            loc_changed += int(del_match.group(1))

        return file_count, loc_changed, files

    except Exception as e:
        print(f"⚠️ Git stats error: {e}", file=sys.stderr)
        return 0, 0, []


def should_commit(file_count: int, loc_changed: int) -> tuple:
    """
    Check if thresholds are met for auto-commit.

    Returns:
        tuple: (should_commit: bool, reason: str)
    """
    reasons = []

    # Check file threshold
    files_met = file_count >= MIN_FILES_THRESHOLD
    if files_met:
        reasons.append(f"{file_count} files (threshold: {MIN_FILES_THRESHOLD})")

    # Check LOC threshold
    loc_met = loc_changed >= MIN_LOC_THRESHOLD
    if loc_met:
        reasons.append(f"{loc_changed} LOC (threshold: {MIN_LOC_THRESHOLD})")

    # Either threshold triggers commit
    if files_met or loc_met:
        return True, " OR ".join(reasons)

    return False, f"Below thresholds: {file_count} files < {MIN_FILES_THRESHOLD}, {loc_changed} LOC < {MIN_LOC_THRESHOLD}"


def generate_commit_message(file_count: int, loc_changed: int, files: list) -> str:
    """Generate semantic commit message based on changed files."""

    # Categorize files
    categories = {
        "hooks": [f for f in files if '.claude/hooks' in f],
        "libs": [f for f in files if 'scripts/lib' in f],
        "scripts": [f for f in files if 'scripts/ops' in f],
        "memory": [f for f in files if '.claude/memory' in f],
        "docs": [f for f in files if f.endswith('.md')],
        "config": [f for f in files if f.endswith('.json')],
        "scratch": [f for f in files if 'scratch/' in f],
    }

    # Build summary
    parts = [f"{cat}({len(items)})" for cat, items in categories.items() if items]
    summary = " + ".join(parts) if parts else f"{file_count} files"

    # Determine prefix from dominant category
    dominant = max(categories.items(), key=lambda x: len(x[1]))[0] if any(categories.values()) else "other"
    prefix_map = {
        "hooks": "feat(hooks)",
        "libs": "feat(lib)",
        "scripts": "feat(scripts)",
        "memory": "chore(memory)",
        "docs": "docs",
        "config": "chore(config)",
        "scratch": "chore(scratch)",
    }
    prefix = prefix_map.get(dominant, "chore")

    message = f"""{prefix}: Auto-commit on session end ({summary})

Session ended with {file_count} files changed, {loc_changed} LOC modified.
Threshold-gated commit (min: {MIN_FILES_THRESHOLD} files OR {MIN_LOC_THRESHOLD} LOC).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

    return message


def execute_commit():
    """Execute the auto-commit with upkeep."""
    file_count, loc_changed, files = get_uncommitted_stats()

    if file_count == 0:
        return "No uncommitted changes"

    # Check thresholds
    commit_needed, reason = should_commit(file_count, loc_changed)

    if not commit_needed:
        return f"⏭️ Skipping auto-commit: {reason}"

    try:
        # Run upkeep first (optional, don't fail if missing)
        try:
            subprocess.run(
                ["python3", "scripts/ops/upkeep.py"],
                capture_output=True,
                timeout=30
            )
        except:
            pass  # Upkeep is optional

        # Stage all changes
        subprocess.run(
            ["git", "add", "."],
            check=True,
            timeout=10
        )

        # Generate and execute commit
        message = generate_commit_message(file_count, loc_changed, files)

        subprocess.run(
            ["git", "commit", "-m", message],
            check=True,
            capture_output=True,
            timeout=10
        )

        return f"✅ Auto-committed {file_count} files ({loc_changed} LOC) - {reason}"

    except subprocess.CalledProcessError as e:
        return f"⚠️ Auto-commit failed: {e}"
    except Exception as e:
        return f"⚠️ Auto-commit error: {e}"


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # This hook runs on Stop/SessionEnd - no stdin expected
    try:
        input_data = json.load(sys.stdin)
    except:
        pass  # Stop/SessionEnd don't always provide stdin

    result = execute_commit()
    print(result)
    sys.exit(0)
