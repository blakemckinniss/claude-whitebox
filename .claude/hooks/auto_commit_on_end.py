#!/usr/bin/env python3
"""
Auto-Commit on Session End Hook
Triggers: SessionEnd
Purpose: Commit any uncommitted changes when session ends
"""
import sys
import json
import subprocess
from pathlib import Path

def has_uncommitted_changes():
    """Check if there are uncommitted changes"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return bool(result.stdout.strip())
    except:
        return False

def get_uncommitted_file_count():
    """Get count of uncommitted files"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return len([line for line in result.stdout.strip().split('\n') if line])
    except:
        return 0

def auto_commit_on_end():
    """Auto-commit uncommitted changes on session end"""
    if not has_uncommitted_changes():
        return "No uncommitted changes"

    file_count = get_uncommitted_file_count()

    try:
        # Run upkeep first
        subprocess.run(
            ["python3", "scripts/ops/upkeep.py"],
            capture_output=True,
            timeout=30
        )

        # Stage all changes
        subprocess.run(
            ["git", "add", "."],
            check=True,
            timeout=10
        )

        # Generate message
        message = f"""chore: Auto-commit on session end ({file_count} files)

Session ended with uncommitted changes. Auto-committing to preserve work.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

        # Commit
        subprocess.run(
            ["git", "commit", "-m", message],
            check=True,
            capture_output=True,
            timeout=10
        )

        return f"✅ Auto-committed {file_count} files on session end"

    except Exception as e:
        return f"⚠️ Auto-commit on end failed: {e}"

# Load input (SessionEnd doesn't get stdin, but we try anyway)
try:
    input_data = json.load(sys.stdin)
except:
    pass

# Auto-commit
result = auto_commit_on_end()

# Print result (SessionEnd hooks don't return context, but we print for logging)
print(result)

sys.exit(0)
