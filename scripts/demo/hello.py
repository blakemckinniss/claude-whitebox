#!/usr/bin/env python3
"""
Demo script that prints a greeting
"""
import sys
import os

# Add scripts/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
# Find project root by looking for 'scripts' directory
_current = _script_dir
while _current != "/":
    if os.path.exists(os.path.join(_current, "scripts", "lib", "core.py")):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with scripts/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, "scripts", "lib"))
from core import setup_script, finalize, logger, handle_debug


def main():
    parser = setup_script("Demo script that prints a greeting")

    # Add custom arguments here
    # parser.add_argument('--target', required=True, help="Target resource")
    # parser.add_argument('--count', type=int, default=10, help="Number of items")

    args = parser.parse_args()
    handle_debug(args)

    logger.info("Starting operation...")

    if args.dry_run:
        logger.warning("⚠️  DRY RUN MODE: No changes will be made")

    try:
        # ============================================================
        # YOUR LOGIC HERE
        # ============================================================

        # Example: Check before making changes
        # if check_dry_run(args, "delete all files"):
        #     return
        #
        # os.remove(file)

        result = "placeholder"
        logger.info(f"Result: {result}")

        # ============================================================

    except Exception as e:
        logger.error(f"Operation failed: {e}")
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
