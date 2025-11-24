#!/usr/bin/env python3
"""
Organizational Drift Detection Library
Prevents catastrophic file structure anti-patterns with auto-tuning
"""

import os
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict
import hashlib

# Configure logging (libraries should use logging, not print)
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# State file location (environment-configurable)
STATE_FILE = Path(os.getenv("DRIFT_STATE_PATH", str(Path.home() / ".claude" / "memory" / "org_drift_state.json")))

# Default thresholds (will auto-tune)
DEFAULT_THRESHOLDS = {
    "max_hooks": 30,
    "max_scratch_files": 500,
    "max_memory_sessions": 100,
    "max_depth": 6,
    "max_root_files": 0,  # Hard block
}

# Exclusion patterns
EXCLUDE_PATTERNS = [
    r"node_modules/",
    r"venv/",
    r"__pycache__/",
    r"\.git/",
    r"scratch/archive/",
    r"projects/",
    r"\.template/",
    r"\.pytest_cache/",
    r"\.mypy_cache/",
]

# Root allowlist (files allowed in repository root)
ROOT_ALLOWLIST = {
    "README.md",
    "CLAUDE.md",
    "LICENSE",
    ".gitignore",
    ".env",
    "requirements.txt",
    "package.json",
    "package-lock.json",
    "pyproject.toml",
    "Cargo.toml",
    "Makefile",
}

# Production zones (no test/scratch/debug files allowed)
PRODUCTION_ZONES = ["scripts/ops/", "scripts/lib/", ".claude/hooks/"]

# Test file patterns (banned from production zones)
TEST_PATTERNS = [
    r"test_.*\.py$",
    r".*_test\.py$",
    r"debug_.*\.py$",
    r".*\.tmp$",
    r"scratch_.*\.py$",
    r"temp_.*\.py$",
]


def load_state() -> Dict:
    """Load auto-tuning state with robust error handling"""
    if not STATE_FILE.exists():
        return {
            "thresholds": DEFAULT_THRESHOLDS.copy(),
            "false_positives": defaultdict(int),
            "total_checks": defaultdict(int),
            "last_tuning": None,
            "turn_count": 0,
            "sudo_overrides": [],  # Track what users override (for exception rules)
        }

    try:
        with open(STATE_FILE, 'r') as f:
            data = json.load(f)
            # Ensure defaultdicts
            data["false_positives"] = defaultdict(int, data.get("false_positives", {}))
            data["total_checks"] = defaultdict(int, data.get("total_checks", {}))
            return data
    except json.JSONDecodeError as e:
        logger.error(f"State file corrupted ({e}), using defaults")
        return {
            "thresholds": DEFAULT_THRESHOLDS.copy(),
            "false_positives": defaultdict(int),
            "total_checks": defaultdict(int),
            "last_tuning": None,
            "turn_count": 0,
            "sudo_overrides": [],
        }
    except (PermissionError, OSError) as e:
        logger.error(f"Cannot read state file ({e}), using defaults")
        return {
            "thresholds": DEFAULT_THRESHOLDS.copy(),
            "false_positives": defaultdict(int),
            "total_checks": defaultdict(int),
            "last_tuning": None,
            "turn_count": 0,
            "sudo_overrides": [],
        }


def save_state(state: Dict) -> bool:
    """
    Save auto-tuning state with error handling

    Returns:
        True if save succeeded, False otherwise
    """
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


def is_excluded(path: str) -> bool:
    """Check if path matches exclusion patterns"""
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, path):
            return True
    return False


def detect_recursion(path: str) -> Optional[str]:
    """
    Detect if path contains recursive directory structure
    Example: scripts/scripts/ops/ or .claude/hooks/.claude/hooks/
    """
    parts = path.split('/')
    for i, part in enumerate(parts):
        # Check if any later part matches current part
        if part and part in parts[i+1:]:
            return f"Recursive structure detected: '{part}' appears multiple times in path"
    return None


def detect_root_pollution(file_path: str, repo_root: str) -> Optional[str]:
    """Detect if file is being created in repository root (outside allowlist)"""
    path = Path(file_path)
    root = Path(repo_root)

    # Check if file is direct child of root
    if path.parent.resolve() != root.resolve():
        return None  # Not in root

    if path.name in ROOT_ALLOWLIST:
        return None  # Allowed

    return f"Root pollution: New file '{path.name}' in repository root (not in allowlist)"


def detect_production_pollution(file_path: str) -> Optional[str]:
    """Detect test/scratch/debug files in production zones"""
    for zone in PRODUCTION_ZONES:
        if zone in file_path:
            # Check if filename matches test patterns
            for pattern in TEST_PATTERNS:
                if re.search(pattern, Path(file_path).name):
                    return f"Production zone pollution: Test/debug file in {zone}"
    return None


def count_files_in_dir(dir_path: Path, pattern: str = "*") -> int:
    """Count files in directory (non-recursive, excluding excluded paths)"""
    if not dir_path.exists():
        return 0

    count = 0
    try:
        for item in dir_path.glob(pattern):
            if item.is_file() and not is_excluded(str(item)):
                count += 1
    except (PermissionError, OSError):
        # Cannot access directory, return 0
        return 0
    return count


def calculate_depth(path: str) -> int:
    """Calculate directory depth (relative to repo root)"""
    # Remove leading/trailing slashes
    path = path.strip('/')
    if not path:
        return 0
    return len(path.split('/'))


def detect_filename_collision(file_path: str, repo_root: str) -> Optional[str]:
    """
    Detect if filename exists in multiple production zones
    (e.g., audit.py in both scripts/ops/ and scripts/lib/)
    """
    path = Path(file_path)
    filename = path.name

    # Skip if not in a production zone
    in_production = any(zone in str(path) for zone in PRODUCTION_ZONES)
    if not in_production:
        return None

    # Search for same filename in other production zones
    root = Path(repo_root)
    collisions = []

    for zone in PRODUCTION_ZONES:
        zone_path = root / zone
        if zone_path.exists():
            try:
                for existing in zone_path.glob(f"**/{filename}"):
                    if existing.resolve() != path.resolve():
                        try:
                            collisions.append(str(existing.relative_to(root)))
                        except ValueError:
                            # Handle symlinks or cross-mount paths
                            collisions.append(str(existing))
            except (PermissionError, OSError):
                # Skip zones we can't access
                continue

    if collisions:
        return f"Filename collision: '{filename}' already exists in {', '.join(collisions)}"

    return None


def check_organizational_drift(
    file_path: str,
    repo_root: str,
    is_sudo: bool = False
) -> Tuple[bool, List[str], List[str]]:
    """
    Main drift detection function

    Returns:
        (allowed, errors, warnings)
        - allowed: bool (whether operation should proceed)
        - errors: List[str] (catastrophic violations - hard blocks)
        - warnings: List[str] (soft violations - logged but allowed)
    """
    state = load_state()
    state["turn_count"] += 1

    errors = []
    warnings = []

    # Skip if path is excluded
    if is_excluded(file_path):
        save_state(state)
        return True, [], []

    # === PHASE 1: CATASTROPHIC CHECKS (Hard Blocks) ===

    # Check 1: Recursion (CRITICAL)
    recursion = detect_recursion(file_path)
    if recursion:
        errors.append(recursion)
        state["total_checks"]["recursion"] += 1
        if is_sudo:
            state["sudo_overrides"].append({
                "type": "recursion",
                "path": file_path,
                "timestamp": datetime.now().isoformat()
            })

    # Check 2: Root Pollution (CRITICAL)
    root_pollution = detect_root_pollution(file_path, repo_root)
    if root_pollution:
        errors.append(root_pollution)
        state["total_checks"]["root_pollution"] += 1
        if is_sudo:
            state["sudo_overrides"].append({
                "type": "root_pollution",
                "path": file_path,
                "timestamp": datetime.now().isoformat()
            })

    # Check 3: Production Zone Pollution (HIGH)
    prod_pollution = detect_production_pollution(file_path)
    if prod_pollution:
        errors.append(prod_pollution)
        state["total_checks"]["prod_pollution"] += 1
        if is_sudo:
            state["sudo_overrides"].append({
                "type": "prod_pollution",
                "path": file_path,
                "timestamp": datetime.now().isoformat()
            })

    # Check 4: Filename Collision (HIGH)
    collision = detect_filename_collision(file_path, repo_root)
    if collision:
        errors.append(collision)
        state["total_checks"]["filename_collision"] += 1
        if is_sudo:
            state["sudo_overrides"].append({
                "type": "filename_collision",
                "path": file_path,
                "timestamp": datetime.now().isoformat()
            })

    # === PHASE 2: THRESHOLD CHECKS (Soft Warnings with Auto-Tuning) ===

    repo_path = Path(repo_root)

    # Check 5: Hook Explosion
    hooks_dir = repo_path / ".claude" / "hooks"
    hook_count = count_files_in_dir(hooks_dir, "*.py")
    if hook_count > state["thresholds"]["max_hooks"]:
        warnings.append(
            f"Hook explosion: {hook_count} hooks (threshold: {state['thresholds']['max_hooks']}). "
            "Consider consolidating hooks."
        )
        state["total_checks"]["hook_explosion"] += 1

    # Check 6: Scratch Bloat (excluding archive)
    scratch_dir = repo_path / "scratch"
    scratch_count = 0
    if scratch_dir.exists():
        try:
            for item in scratch_dir.rglob("*"):
                if item.is_file() and not is_excluded(str(item)) and "archive" not in str(item):
                    scratch_count += 1
        except (PermissionError, OSError):
            # Cannot access scratch directory, skip check
            pass

    if scratch_count > state["thresholds"]["max_scratch_files"]:
        warnings.append(
            f"Scratch bloat: {scratch_count} files (threshold: {state['thresholds']['max_scratch_files']}). "
            "Consider archiving or cleaning."
        )
        state["total_checks"]["scratch_bloat"] += 1

    # Check 7: Memory Session Fragmentation
    memory_dir = repo_path / ".claude" / "memory"
    session_count = len(list(memory_dir.glob("session_*_state.json"))) if memory_dir.exists() else 0
    if session_count > state["thresholds"]["max_memory_sessions"]:
        warnings.append(
            f"Memory fragmentation: {session_count} session files (threshold: {state['thresholds']['max_memory_sessions']}). "
            "Consider pruning old sessions."
        )
        state["total_checks"]["memory_fragmentation"] += 1

    # Check 8: Deep Nesting
    depth = calculate_depth(file_path)
    if depth > state["thresholds"]["max_depth"]:
        warnings.append(
            f"Deep nesting: Depth {depth} (threshold: {state['thresholds']['max_depth']}). "
            "Consider flattening structure."
        )
        state["total_checks"]["deep_nesting"] += 1

    # Auto-tune every 100 turns
    if state["turn_count"] % 100 == 0:
        auto_tune_thresholds(state)

    save_state(state)

    # Determine if operation is allowed
    allowed = len(errors) == 0 or is_sudo

    return allowed, errors, warnings


def record_false_positive(violation_type: str) -> Dict[str, any]:
    """
    Record a false positive for auto-tuning

    Returns:
        Dict with success status and updated statistics
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


def revoke_false_positive(violation_type: str) -> Dict[str, any]:
    """
    Remove a false positive (undo accidental marking)

    Returns:
        Dict with success status and updated statistics
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


def auto_tune_thresholds(state: Dict) -> List[str]:
    """
    Auto-adjust thresholds based on false positive rate
    Goal: Keep FP rate between 5-15%

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
        logger.info(f"🔧 Auto-tuned thresholds (Turn {state['turn_count']}):")
        for adj in adjustments:
            logger.info(f"   • {adj}")

    return adjustments


def get_drift_report() -> str:
    """Generate human-readable drift report"""
    state = load_state()

    report = ["📊 Organizational Drift Report\n"]
    report.append(f"Turn: {state['turn_count']}")
    report.append(f"Last Tuning: {state.get('last_tuning', 'Never')}\n")

    report.append("Current Thresholds:")
    for key, value in state["thresholds"].items():
        report.append(f"  • {key}: {value}")

    report.append("\nCheck Statistics:")
    for check_type, count in state["total_checks"].items():
        fp_count = state["false_positives"].get(check_type, 0)
        fp_rate = (fp_count / count * 100) if count > 0 else 0
        report.append(f"  • {check_type}: {count} checks, {fp_count} FP ({fp_rate:.1f}%)")

    if state["sudo_overrides"]:
        report.append(f"\nRecent SUDO Overrides ({len(state['sudo_overrides'])} total):")
        for override in state["sudo_overrides"][-5:]:  # Show last 5
            report.append(f"  • {override['type']}: {override['path']}")

    return "\n".join(report)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "report":
        print(get_drift_report())
    else:
        print("Organizational Drift Detection Library")
        print("Usage: python org_drift.py report")
