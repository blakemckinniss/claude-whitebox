#!/usr/bin/env python3
"""
The Gatekeeper: Verifies project state before git commits
"""
import sys
import os
import subprocess
import hashlib

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


def get_file_hash(filepath):
    """Calculate MD5 hash of a file."""
    if not os.path.exists(filepath):
        return None

    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def main():
    parser = setup_script("The Gatekeeper: Verifies project state before git commits")

    args = parser.parse_args()
    handle_debug(args)

    print("\n" + "=" * 70)
    print("🚪 THE GATEKEEPER: Pre-Commit Validation")
    print("=" * 70)

    if args.dry_run:
        logger.warning("⚠️  DRY RUN MODE: Would verify but not update")

    try:
        tool_index_path = os.path.join(
            _project_root, ".claude", "skills", "tool_index.md"
        )

        # Get hash before running indexer
        hash_before = get_file_hash(tool_index_path)

        print("\n🔍 Checking if tool index is up to date...")

        if args.dry_run:
            print("  [DRY RUN] Would run: python3 scripts/index.py")
            print("  [DRY RUN] Would check for changes")
            print("\n✅ Dry-run complete\n")
            finalize(success=True)

        # Run indexer
        result = subprocess.run(
            [sys.executable, os.path.join(_project_root, "scripts", "index.py")],
            capture_output=True,
            text=True,
            cwd=_project_root,
        )

        if result.returncode != 0:
            print(f"❌ Indexer failed: {result.stderr}")
            finalize(success=False)

        # Get hash after running indexer
        hash_after = get_file_hash(tool_index_path)

        if hash_before != hash_after:
            print("\n" + "=" * 70)
            print("❌ COMMIT BLOCKED: Tool Index Was Stale")
            print("=" * 70)
            print("\nThe tool index was out of date. I've updated it for you.")
            print("Please stage the updated file and commit again:")
            print(f"\n  git add {tool_index_path}")
            print("  git commit")
            print("\n" + "=" * 70 + "\n")
            logger.error("Tool index was stale - commit blocked")
            finalize(success=False)
        else:
            print("✅ Tool index is up to date")
            print("\n" + "=" * 70)
            print("✅ Pre-commit checks passed! Ready to commit.")
            print("=" * 70 + "\n")
            logger.info("Pre-commit validation passed")
            finalize(success=True)

    except Exception as e:
        logger.error(f"Pre-commit check failed: {e}")
        import traceback

        traceback.print_exc()
        finalize(success=False)


if __name__ == "__main__":
    main()
