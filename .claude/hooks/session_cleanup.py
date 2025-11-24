#!/usr/bin/env python3
"""
Session Cleanup Hook: Cleanup old sessions on session end
Triggers on: SessionEnd

Runs retention policy to delete sessions older than 7 days.
This prevents unbounded growth of session state files.
"""
import sys
from pathlib import Path

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import cleanup_old_sessions

try:
    # Cleanup old sessions (>7 days)
    result = cleanup_old_sessions(max_age_days=7, dry_run=False)

    # Silent success - only log if there were deletions
    if result["deleted"]:
        print(f"🧹 Cleaned up {len(result['deleted'])} old session(s)")

    # Log errors if any
    if result["errors"]:
        print(f"⚠️  {len(result['errors'])} error(s) during cleanup")
        for error in result["errors"][:3]:  # Show first 3
            print(f"   - {error}")

except Exception as e:
    # Don't fail the hook on cleanup errors
    print(f"⚠️  Session cleanup error: {e}")

sys.exit(0)
