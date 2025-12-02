#!/usr/bin/env python3
"""
Whitebox SDK Core Library
Shared utilities for all scripts in the arsenal.
"""
import argparse
import logging
import os
import sys
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=1)
def get_project_root() -> Path:
    """Find project root by walking up to find .claude/lib/core.py.

    This function is cached so repeated calls are fast.
    Can be called from any script in the project.

    Returns:
        Path to project root directory

    Raises:
        RuntimeError if project root cannot be found
    """
    # Start from this file's location
    current = Path(__file__).resolve().parent

    # Walk up looking for .claude/lib/core.py marker
    while current != current.parent:
        marker = current / ".claude" / "lib" / "core.py"
        if marker.exists():
            return current  # This directory contains .claude/
        current = current.parent

    raise RuntimeError("Could not find project root with .claude/lib/core.py")


@lru_cache(maxsize=1)
def load_config() -> dict:
    """Load enforcement.json configuration.

    Returns cached config dict. Falls back to empty dict if file missing.
    """
    import json
    config_path = get_project_root() / ".claude" / "config" / "enforcement.json"
    try:
        with open(config_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_threshold(key: str, default: int = 50) -> int:
    """Get a threshold value from config.

    Args:
        key: Threshold key (e.g., 'production_write', 'strategic_advice')
        default: Default value if not found

    Returns:
        Threshold value as integer
    """
    config = load_config()
    thresholds = config.get("thresholds", {})
    if key in thresholds:
        return thresholds[key].get("min_confidence", default)
    return default


# Standardized Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("Whitebox")


def setup_script(description):
    """
    Standard setup for ALL scripts.
    Returns: parser (argparse.ArgumentParser)

    Usage:
        parser = setup_script("My script description")
        parser.add_argument('--target', required=True)
        args = parser.parse_args()
    """
    # API keys are now in ~/.bashrc (global), no .env loading needed

    # Standard Args
    parser = argparse.ArgumentParser(
        description=description, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate actions without making changes"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    return parser


def handle_debug(args):
    """Enable debug logging if --debug flag is set"""
    if hasattr(args, "debug") and args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")


def check_dry_run(args, action_description):
    """
    Helper to handle dry-run mode consistently.

    Usage:
        if check_dry_run(args, "delete file X"):
            return  # Skip actual operation
        os.remove(file)
    """
    if hasattr(args, "dry_run") and args.dry_run:
        logger.warning(f"⚠️  DRY RUN: Would {action_description}")
        return True
    return False


def finalize(success=True, message=None):
    """
    Standard exit for all scripts.

    Args:
        success: Whether operation succeeded
        message: Optional custom message
    """
    if success:
        msg = message or "Operation Complete"
        logger.info(f"✅ {msg}")
        sys.exit(0)
    else:
        msg = message or "Operation Failed"
        logger.error(f"❌ {msg}")
        sys.exit(1)


def safe_execute(func, *args, **kwargs):
    """
    Wrapper for safe execution with consistent error handling.

    Usage:
        def my_operation():
            # ... do work
            return result

        result = safe_execute(my_operation)
    """
    try:
        return func(*args, **kwargs)
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        finalize(success=False, message="Cancelled")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        finalize(success=False, message=str(e))
