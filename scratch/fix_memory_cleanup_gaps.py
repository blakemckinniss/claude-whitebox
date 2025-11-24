#!/usr/bin/env python3
"""
Script to apply critical gap fixes to memory_cleanup.py

Fixes identified by void:
1. Add file locking for concurrent access
2. Add session archive cleanup (prevent unbounded growth)
3. Better error handling with specific exceptions
4. Add environment variable for MEMORY_DIR override
"""

import sys
from pathlib import Path

# Read the original file
memory_file = Path("scratch/memory_cleanup.py")
content = memory_file.read_text()

# Fix 1: Add imports
if "import fcntl" not in content:
    content = content.replace(
        "import json",
        "import json\nimport os\nimport fcntl\nimport logging"
    )

# Fix 2: Add logging config
if "logging.basicConfig" not in content:
    content = content.replace(
        "# Paths\nMEMORY_DIR",
        """# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='[%(name)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('memory_cleanup')

# Paths (environment variable override supported)
MEMORY_DIR"""
    )

# Fix 3: Add environment variable override for MEMORY_DIR
content = content.replace(
    "# Paths\nMEMORY_DIR = Path(__file__).resolve().parent.parent / \".claude\" / \"memory\"",
    """# Paths (environment variable override supported)
MEMORY_DIR = Path(os.environ.get('CLAUDE_MEMORY_PATH',
                                   str(Path(__file__).resolve().parent.parent / ".claude" / "memory")))"""
)

# Fix 4: Add session_unknown_state.json to limits (not excluded)
content = content.replace(
    "    return [\n        f\n        for f in MEMORY_DIR.glob(\"session_*_state.json\")\n        if f.name != \"session_unknown_state.json\"  # Skip default session\n    ]",
    """    # Include ALL session files (no exclusions - all must be managed)
    return list(MEMORY_DIR.glob("session_*_state.json"))"""
)

# Fix 5: Add archive cleanup function
archive_cleanup = '''

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
'''

if "cleanup_old_archives" not in content:
    content = content.replace(
        "def cleanup_all() -> Dict[str, List[str]]:",
        archive_cleanup + "\n\ndef cleanup_all() -> Dict[str, List[str]]:"
    )

# Fix 6: Update cleanup_all to include archive cleanup
content = content.replace(
    "    results = {\n        \"telemetry_rotations\": rotate_all_telemetry(),\n        \"session_pruning\": prune_old_sessions(),\n        \"session_truncations\": truncate_all_sessions(),\n    }",
    """    results = {
        "telemetry_rotations": rotate_all_telemetry(),
        "session_pruning": prune_old_sessions(),
        "session_truncations": truncate_all_sessions(),
        "archive_cleanup": cleanup_old_archives(load_memory_limits()),
    }"""
)

# Fix 7: Add file locking to truncate functions
truncate_with_lock = '''def truncate_evidence_ledger(session_file: Path, limits: Dict) -> bool:
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
        return False'''

# Replace truncate_evidence_ledger
old_truncate_evidence = '''def truncate_evidence_ledger(session_file: Path, limits: Dict) -> bool:
    """
    Truncate evidence ledger in session state

    Returns:
        True if truncated, False otherwise
    """
    try:
        with open(session_file) as f:
            state = json.load(f)

        evidence = state.get("evidence_ledger", [])
        max_entries = limits["evidence_ledger_max"]

        if len(evidence) > max_entries:
            # Keep last N entries
            state["evidence_ledger"] = evidence[-max_entries:]

            with open(session_file, "w") as f:
                json.dump(state, f, indent=2)

            return True

    except:
        pass

    return False'''

content = content.replace(old_truncate_evidence, truncate_with_lock)

# Fix 8: Improve error handling in load_memory_limits
content = content.replace(
    "    if config_file.exists():\n        try:\n            with open(config_file) as f:\n                config = json.load(f)\n                return config.get(\"memory_limits\", DEFAULT_LIMITS)\n        except:\n            pass",
    """    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
                return config.get("memory_limits", DEFAULT_LIMITS)
        except json.JSONDecodeError as e:
            logger.error(f"Config file corrupted: {e}. Using defaults.")
        except Exception as e:
            logger.warning(f"Failed to load config: {e}. Using defaults.")"""
)

# Fix 9: Add archive_keep_count to DEFAULT_LIMITS
content = content.replace(
    "    \"tool_history_max\": 50,\n}",
    """    "tool_history_max": 50,
    "archive_keep_count": 20,  # Max session archives to keep
}"""
)

# Write fixed file
memory_file.write_text(content)

print("✅ Applied gap fixes to memory_cleanup.py")
print("\nFixes applied:")
print("1. Added file locking for truncate operations")
print("2. Added archive cleanup (prevents unbounded archive growth)")
print("3. Added environment variable CLAUDE_MEMORY_PATH override")
print("4. Removed session_unknown_state.json exclusion")
print("5. Improved error handling with specific exceptions")
print("6. Added logging to stderr for error visibility")

sys.exit(0)
