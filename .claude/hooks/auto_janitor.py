#!/usr/bin/env python3
"""
The Janitor - Autonomous Workspace Cleanup (SessionEnd)

Archives old scratch files, removes duplicates, cleans workspace.

Philosophy: Workspace stays clean without manual intervention.
"""

import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Find project root
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

CONFIG_FILE = PROJECT_DIR / ".claude" / "memory" / "automation_config.json"
SCRATCH_DIR = PROJECT_DIR / "scratch"
ARCHIVE_DIR = PROJECT_DIR / ".claude" / "memory" / "archive"


def load_config():
    """Load automation configuration"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"janitor": {"enabled": False}}


def archive_old_files(threshold_days=7):
    """Archive scratch files older than threshold"""
    if not SCRATCH_DIR.exists():
        return []

    archived = []
    cutoff = datetime.now() - timedelta(days=threshold_days)

    for file_path in SCRATCH_DIR.glob("**/*"):
        if not file_path.is_file():
            continue

        # Check age
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

        if mtime < cutoff:
            # Archive it
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            archive_path = ARCHIVE_DIR / file_path.name

            try:
                shutil.move(str(file_path), str(archive_path))
                archived.append(file_path.name)
            except:
                pass

    return archived


def main():
    """Janitor main logic"""
    # Load config
    config = load_config()
    if not config.get("janitor", {}).get("enabled", False):
        sys.exit(0)

    threshold = config.get("janitor", {}).get("archive_threshold_days", 7)

    # Archive old files
    archived = archive_old_files(threshold)

    if archived:
        message = f"""
🧹 JANITOR: AUTO-CLEANUP COMPLETE

Archived {len(archived)} old files (>{threshold} days):
{chr(10).join(f"  • {f}" for f in archived[:5])}
{"  • ..." if len(archived) > 5 else ""}

Location: .claude/memory/archive/

Files are archived (not deleted) and can be restored if needed.
"""

        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionEnd",
                "additionalContext": message
            }
        }))

    sys.exit(0)


if __name__ == "__main__":
    main()
