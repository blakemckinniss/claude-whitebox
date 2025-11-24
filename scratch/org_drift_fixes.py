#!/usr/bin/env python3
"""
Fixes for org_drift.py based on void analysis
Critical: Error handling, CRUD operations, config flexibility
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional
from collections import defaultdict

# Environment-configurable state path
STATE_FILE = Path(os.getenv("DRIFT_STATE_PATH", str(Path.home() / ".claude" / "memory" / "org_drift_state.json")))

# Configure logging (library should use logging, not print)
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)


def load_state() -> Dict:
    """Load auto-tuning state with robust error handling"""
    if not STATE_FILE.exists():
        return _get_default_state()

    try:
        with open(STATE_FILE, 'r') as f:
            data = json.load(f)
            # Ensure defaultdicts
            data["false_positives"] = defaultdict(int, data.get("false_positives", {}))
            data["total_checks"] = defaultdict(int, data.get("total_checks", {}))
            return data
    except json.JSONDecodeError as e:
        logger.error(f"State file corrupted ({e}), using defaults")
        return _get_default_state()
    except (PermissionError, OSError) as e:
        logger.error(f"Cannot read state file ({e}), using defaults")
        return _get_default_state()


def save_state(state: Dict) -> bool:
    """Save auto-tuning state with error handling"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        logger.error(f"Cannot create state directory ({e})")
        return False

    # Convert defaultdicts to regular dicts for JSON
    state_copy = state.copy()
    state_copy["false_positives"] = dict(state["false_positives"])
    state_copy["total_checks"] = dict(state["total_checks"])

    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state_copy, f, indent=2)
        return True
    except (PermissionError, OSError) as e:
        logger.error(f"Cannot write state file ({e})")
        return False


def _get_default_state() -> Dict:
    """Get default state structure"""
    from org_drift import DEFAULT_THRESHOLDS  # Import from original
    return {
        "thresholds": DEFAULT_THRESHOLDS.copy(),
        "false_positives": defaultdict(int),
        "total_checks": defaultdict(int),
        "last_tuning": None,
        "turn_count": 0,
        "sudo_overrides": [],
    }


def reset_state(full: bool = True, threshold: Optional[str] = None, violation_type: Optional[str] = None) -> bool:
    """
    Granular state reset

    Args:
        full: Reset everything
        threshold: Reset specific threshold to default
        violation_type: Clear FP/checks for specific violation type

    Returns:
        True if reset succeeded
    """
    if full:
        try:
            if STATE_FILE.exists():
                STATE_FILE.unlink()
                logger.info("Full state reset complete")
            return True
        except (PermissionError, OSError) as e:
            logger.error(f"Cannot delete state file ({e})")
            return False

    # Granular reset
    state = load_state()

    if threshold:
        from org_drift import DEFAULT_THRESHOLDS
        if threshold in DEFAULT_THRESHOLDS:
            state["thresholds"][threshold] = DEFAULT_THRESHOLDS[threshold]
            logger.info(f"Reset {threshold} to {DEFAULT_THRESHOLDS[threshold]}")
        else:
            logger.error(f"Unknown threshold: {threshold}")
            return False

    if violation_type:
        if violation_type in state["false_positives"]:
            del state["false_positives"][violation_type]
        if violation_type in state["total_checks"]:
            del state["total_checks"][violation_type]
        logger.info(f"Cleared statistics for {violation_type}")

    return save_state(state)


def record_false_positive(violation_type: str) -> Dict[str, int]:
    """
    Record a false positive for auto-tuning

    Returns:
        Dict with updated statistics
    """
    state = load_state()
    state["false_positives"][violation_type] += 1

    success = save_state(state)

    total = state["total_checks"].get(violation_type, 0)
    fp_count = state["false_positives"][violation_type]
    fp_rate = (fp_count / total * 100) if total > 0 else 0

    return {
        "success": success,
        "fp_count": fp_count,
        "total_checks": total,
        "fp_rate": fp_rate
    }


def revoke_false_positive(violation_type: str) -> Dict[str, int]:
    """
    Remove a false positive (undo accidental marking)

    Returns:
        Dict with updated statistics
    """
    state = load_state()

    if violation_type in state["false_positives"] and state["false_positives"][violation_type] > 0:
        state["false_positives"][violation_type] -= 1
        success = save_state(state)

        total = state["total_checks"].get(violation_type, 0)
        fp_count = state["false_positives"][violation_type]
        fp_rate = (fp_count / total * 100) if total > 0 else 0

        return {
            "success": success,
            "fp_count": fp_count,
            "total_checks": total,
            "fp_rate": fp_rate
        }
    else:
        return {
            "success": False,
            "error": "No false positives to revoke"
        }


def auto_tune_thresholds(state: Dict) -> List[str]:
    """
    Auto-adjust thresholds based on false positive rate

    Returns:
        List of adjustment messages (for logging)
    """
    adjustments = []

    for check_type in ["hook_explosion", "scratch_bloat", "memory_fragmentation", "deep_nesting"]:
        total = state["total_checks"].get(check_type, 0)
        if total < 10:
            continue  # Need more data

        fp_count = state["false_positives"].get(check_type, 0)
        fp_rate = (fp_count / total) * 100

        # Map check type to threshold key
        threshold_map = {
            "hook_explosion": "max_hooks",
            "scratch_bloat": "max_scratch_files",
            "memory_fragmentation": "max_memory_sessions",
            "deep_nesting": "max_depth",
        }

        threshold_key = threshold_map[check_type]
        current = state["thresholds"][threshold_key]

        # Adjust based on FP rate
        if fp_rate > 15:  # Too many false positives - loosen
            adjustment = int(current * 0.2)  # Increase by 20%
            state["thresholds"][threshold_key] = current + adjustment
            adjustments.append(f"{check_type}: {current} → {current + adjustment} (FP rate {fp_rate:.1f}%)")

        elif fp_rate < 5 and total > 50:  # Very few FPs + enough data - tighten
            adjustment = int(current * 0.1)  # Decrease by 10%
            new_val = max(current - adjustment, 1)  # Never go below 1
            state["thresholds"][threshold_key] = new_val
            adjustments.append(f"{check_type}: {current} → {new_val} (FP rate {fp_rate:.1f}%)")

    if adjustments:
        state["last_tuning"] = datetime.now().isoformat()
        # Use logger instead of print
        logger.info(f"🔧 Auto-tuned thresholds (Turn {state['turn_count']}):")
        for adj in adjustments:
            logger.info(f"   • {adj}")

    return adjustments


# Validation helpers
def validate_threshold_value(threshold_name: str, value: int) -> Tuple[bool, Optional[str]]:
    """
    Validate threshold value is logically sound

    Returns:
        (is_valid, error_message)
    """
    if value < 0:
        return False, f"Threshold value must be non-negative (got {value})"

    # Specific validations
    if threshold_name == "max_root_files" and value != 0:
        return False, "max_root_files must be 0 (hard block on root pollution)"

    if threshold_name in ["max_hooks", "max_scratch_files", "max_memory_sessions"] and value < 5:
        return False, f"{threshold_name} too low (minimum 5)"

    if threshold_name == "max_depth" and value < 3:
        return False, "max_depth too low (minimum 3)"

    return True, None


if __name__ == "__main__":
    print("Organizational Drift Library Fixes")
    print("- Robust error handling")
    print("- Granular CRUD operations")
    print("- Configuration validation")
    print("- Logging instead of print")
