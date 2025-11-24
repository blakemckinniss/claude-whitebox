#!/usr/bin/env python3
"""
Auto-Commit Prompt Check Hook (UserPromptSubmit)
Shows current uncommitted stats to keep user aware of commit density
"""
import sys
import json
from pathlib import Path

# Add scripts/lib to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "lib"))

try:
    # Import enforcement library from scratch
    scratch_dir = Path(__file__).resolve().parent.parent.parent / "scratch"
    sys.path.insert(0, str(scratch_dir))
    import auto_commit_enforcement
except ImportError:
    # Library not available yet
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ""
        }
    }))
    sys.exit(0)

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ""
        }
    }))
    sys.exit(0)

# Get current stats
try:
    stats = auto_commit_enforcement.get_stats()

    # Only show message if we're approaching thresholds
    file_count = stats["current_file_count"]
    loc_changed = stats["current_loc_changed"]
    will_commit = stats["will_commit_next"]

    # Build status message
    if will_commit:
        # AT THRESHOLD - next Write/Edit/Bash will trigger commit
        message = f"""🔔 AUTO-COMMIT PENDING

Current uncommitted: {file_count} files, {loc_changed} LOC
Thresholds: {stats['thresholds']['file_count_min']} files, {stats['thresholds']['loc_threshold']} LOC

Reason: {stats['commit_reason']}

Next file operation will trigger automatic commit.
Total auto-commits this session: {stats['total_auto_commits']}"""

        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": message
            }
        }))

    elif file_count >= (stats['thresholds']['file_count_min'] * 0.7) or loc_changed >= (stats['thresholds']['loc_threshold'] * 0.7):
        # APPROACHING THRESHOLD (70%)
        file_percent = int((file_count / stats['thresholds']['file_count_min']) * 100)
        loc_percent = int((loc_changed / stats['thresholds']['loc_threshold']) * 100)

        message = f"""📊 COMMIT DENSITY TRACKER

Uncommitted: {file_count} files ({file_percent}%), {loc_changed} LOC ({loc_percent}%)
Thresholds: {stats['thresholds']['file_count_min']} files, {stats['thresholds']['loc_threshold']} LOC
Mode: {"COMBINED (both must trigger)" if stats['thresholds']['combined_mode'] else "INDIVIDUAL (either can trigger)"}

System is monitoring for automatic commit.
Total auto-commits: {stats['total_auto_commits']}"""

        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": message
            }
        }))

    else:
        # Below thresholds - silent
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": ""
            }
        }))

except Exception as e:
    # Error in stats check - don't block prompt
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": f"⚠️ Auto-commit stats failed: {e}"
        }
    }))

sys.exit(0)
