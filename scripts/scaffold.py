#!/usr/bin/env python3
"""
Script Scaffolder - Generates new scripts with Whitebox SDK standards built-in.

Usage:
    python3 scripts/scaffold.py scripts/<category>/<name>.py "Description of task"
    python3 scripts/scaffold.py scratch/tmp_test.py "Quick test script"
"""
import sys
import os
from pathlib import Path

TEMPLATE = '''#!/usr/bin/env python3
"""
{description}
"""
import sys
import os

# Add scripts/lib to path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)  # Go up one level from script location
sys.path.insert(0, os.path.join(_project_root, 'scripts', 'lib'))
from core import setup_script, finalize, logger, handle_debug, check_dry_run


def main():
    parser = setup_script("{description}")

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
        logger.info(f"Result: {{result}}")

        # ============================================================

    except Exception as e:
        logger.error(f"Operation failed: {{e}}")
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
'''


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/scaffold.py <path> <description>")
        print()
        print("Examples:")
        print('  python3 scripts/scaffold.py scripts/db/query.py "Query database"')
        print('  python3 scripts/scaffold.py scratch/tmp_test.py "Test something"')
        sys.exit(1)

    path = sys.argv[1]
    description = " ".join(sys.argv[2:])

    # Ensure directory exists
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)

    # Generate content
    content = TEMPLATE.format(description=description)

    # Write file
    with open(path, "w") as f:
        f.write(content)

    # Make executable
    os.chmod(path, 0o755)

    print(f"✅ Scaffolded new script at: {path}")
    print(f"📝 Description: {description}")
    print()
    print("Next steps:")
    print(f"  1. Edit {path} and add your logic")
    print(f"  2. Run: python3 {path} --dry-run")
    print(f"  3. Run: python3 {path}")


if __name__ == "__main__":
    main()
