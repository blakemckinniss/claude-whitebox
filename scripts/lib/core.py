#!/usr/bin/env python3
"""
Whitebox SDK Core Library
Shared utilities for all scripts in the arsenal.
"""
import argparse
import logging
import sys
from pathlib import Path

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
    # Load .env if present (override existing env vars to ensure .env takes precedence)
    try:
        from dotenv import load_dotenv

        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=True)
            logger.debug(f"Loaded environment from {env_path} (with override)")
    except ImportError:
        logger.debug("python-dotenv not installed, skipping .env load")

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
