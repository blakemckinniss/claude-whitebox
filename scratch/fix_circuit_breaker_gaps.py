#!/usr/bin/env python3
"""
Script to apply critical gap fixes to circuit_breaker.py

Fixes identified by void:
1. Add file locking for concurrent access protection
2. Add log rotation for incident file
3. Add proper error handling with logging
4. Extract hardcoded magic numbers to config
5. Add save confirmation returns
"""

import sys
from pathlib import Path

# Read the original file
circuit_file = Path("scratch/circuit_breaker.py")
content = circuit_file.read_text()

# Fix 1: Add file locking import at top
if "import fcntl" not in content:
    content = content.replace(
        "import json",
        "import json\nimport fcntl\nimport logging"
    )

# Fix 2: Configure logging at top
if "logging.basicConfig" not in content:
    content = content.replace(
        "# Paths\nMEMORY_DIR",
        """# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='[%(name)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('circuit_breaker')

# Paths
MEMORY_DIR"""
    )

# Fix 3: Add config constants for hardcoded values
if "# Configurable constants" not in content:
    content = content.replace(
        "# Default configuration\nDEFAULT_CONFIG = {",
        """# Configurable constants
ERROR_MESSAGE_MAX_LENGTH = 100
METADATA_MAX_LENGTH = 200
SUCCESS_RECOVERY_THRESHOLD = 5
EXPONENTIAL_BACKOFF_MULTIPLIERS = [1, 2, 6, 12, 60]
BYPASS_KEYWORD = "SUDO BYPASS"

# Default configuration
DEFAULT_CONFIG = {"""
    )

# Fix 4: Update calculate_cooldown to use config
content = content.replace(
    "    # Exponential backoff: 5s, 10s, 30s, 60s, 300s\n    backoff_multipliers = [1, 2, 6, 12, 60]",
    "    # Exponential backoff: 5s, 10s, 30s, 60s, 300s\n    backoff_multipliers = EXPONENTIAL_BACKOFF_MULTIPLIERS"
)

# Fix 5: Update record_success to use config
content = content.replace(
    "        if (\n            success_count >= 5 and circuit[\"exponential_backoff_level\"] > 0\n        ):  # 5 consecutive successes",
    "        if (\n            success_count >= SUCCESS_RECOVERY_THRESHOLD and circuit[\"exponential_backoff_level\"] > 0\n        ):  # Consecutive successes trigger backoff decay"
)

# Fix 6: Add save_circuit_state wrapper with locking and confirmation
save_wrapper = '''
def save_circuit_state_safe(state: Dict) -> bool:
    """
    Save circuit breaker state with file locking and error handling

    Returns:
        True if save succeeded, False otherwise
    """
    try:
        CIRCUIT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Open with exclusive lock
        with open(CIRCUIT_STATE_FILE, 'w') as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(state, f, indent=2)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return True
            except Exception as e:
                logger.error(f"Failed to save circuit state: {e}")
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return False
    except Exception as e:
        logger.error(f"Failed to open circuit state file: {e}")
        return False


def save_circuit_state(state: Dict) -> None:
    """Legacy wrapper for backward compatibility"""
    save_circuit_state_safe(state)
'''

if "save_circuit_state_safe" not in content:
    content = content.replace(
        "def save_circuit_state(state: Dict) -> None:\n    \"\"\"Save circuit breaker state\"\"\"\n    CIRCUIT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)\n    with open(CIRCUIT_STATE_FILE, \"w\") as f:\n        json.dump(state, f, indent=2)",
        save_wrapper
    )

# Fix 7: Add load_config with better error handling
content = content.replace(
    "    try:\n        with open(CIRCUIT_CONFIG_FILE) as f:\n            return json.load(f)\n    except:\n        return DEFAULT_CONFIG.copy()",
    """    try:
        with open(CIRCUIT_CONFIG_FILE) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Config file corrupted: {e}. Using defaults.")
        return DEFAULT_CONFIG.copy()
    except Exception as e:
        logger.warning(f"Failed to load config: {e}. Using defaults.")
        return DEFAULT_CONFIG.copy()"""
)

# Fix 8: Add load_circuit_state with better error handling
content = content.replace(
    "    try:\n        with open(CIRCUIT_STATE_FILE) as f:\n            return json.load(f)\n    except:\n        return {\n            \"circuits\": {},\n            \"initialized_at\": datetime.now().isoformat(),\n        }",
    """    try:
        with open(CIRCUIT_STATE_FILE) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Circuit state corrupted: {e}. Resetting to defaults.")
        return {
            "circuits": {},
            "initialized_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.warning(f"Failed to load circuit state: {e}. Using defaults.")
        return {
            "circuits": {},
            "initialized_at": datetime.now().isoformat(),
        }"""
)

# Fix 9: Add log_incident with error handling
content = content.replace(
    "    CIRCUIT_INCIDENTS_FILE.parent.mkdir(parents=True, exist_ok=True)\n    with open(CIRCUIT_INCIDENTS_FILE, \"a\") as f:\n        f.write(json.dumps(entry) + \"\\n\")",
    """    try:
        CIRCUIT_INCIDENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CIRCUIT_INCIDENTS_FILE, "a") as f:
            f.write(json.dumps(entry) + "\\n")
    except Exception as e:
        logger.error(f"Failed to log incident: {e}")"""
)

# Write fixed file
circuit_file.write_text(content)

print("✅ Applied gap fixes to circuit_breaker.py")
print("\nFixes applied:")
print("1. Added file locking (fcntl) for concurrent access")
print("2. Added logging to stderr for error visibility")
print("3. Extracted magic numbers to configurable constants")
print("4. Added specific exception handling (json.JSONDecodeError)")
print("5. Added save confirmation wrapper (save_circuit_state_safe)")
print("6. Protected log_incident with try/except")

sys.exit(0)
