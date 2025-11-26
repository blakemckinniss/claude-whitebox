#!/usr/bin/env python3
"""
The Janitor: Scans the project, updates indexes, verifies requirements, and cleans .claude/tmp/
"""
import sys
import os
import subprocess
import re
import ast
from datetime import datetime, timedelta

# Add .claude/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
# Find project root by looking for '.claude' directory
_current = _script_dir
while _current != "/":
    if os.path.exists(os.path.join(_current, ".claude", "lib", "core.py")):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with .claude/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, ".claude", "lib"))
from core import setup_script, finalize, logger, handle_debug  # noqa: E402


def extract_imports_from_file(filepath):
    """Extract all imported module names from a Python file."""
    imports = set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Get top-level module (e.g., 'os' from 'os.path')
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
    except Exception as e:
        logger.debug(f"Could not parse {filepath}: {e}")

    return imports


def update_registry(dry_run):
    """Run the indexer to update tool registry."""
    print("\n" + "=" * 70)
    print("🔧 [JANITOR] Updating Tool Registry...")
    print("=" * 70)

    if dry_run:
        print("  [DRY RUN] Would run: python3 .claude/ops/index.py")
        return True

    try:
        result = subprocess.run(
            [sys.executable, os.path.join(_project_root, ".claude", "index.py",
            timeout=10)],
            capture_output=True,
            text=True,
            cwd=_project_root,
        )

        if result.returncode == 0:
            print("  ✅ Registry updated successfully")
            return True
        else:
            print(f"  ❌ Registry update failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Failed to run indexer: {e}")
        return False


def check_dependencies(dry_run):
    """Scan scripts for imports and verify against requirements.txt."""
    print("\n" + "=" * 70)
    print("📦 [JANITOR] Checking Dependencies...")
    print("=" * 70)

    # Standard library modules (incomplete list, but covers common ones)
    stdlib_modules = {
        "abc",
        "argparse",
        "ast",
        "asyncio",
        "base64",
        "collections",
        "concurrent",
        "copy",
        "csv",
        "datetime",
        "decimal",
        "email",
        "enum",
        "functools",
        "glob",
        "hashlib",
        "hmac",
        "html",
        "http",
        "importlib",
        "inspect",
        "io",
        "itertools",
        "json",
        "logging",
        "math",
        "multiprocessing",
        "operator",
        "os",
        "pathlib",
        "pickle",
        "platform",
        "pprint",
        "re",
        "secrets",
        "shutil",
        "socket",
        "sqlite3",
        "statistics",
        "string",
        "subprocess",
        "sys",
        "tempfile",
        "textwrap",
        "threading",
        "time",
        "traceback",
        "typing",
        "unittest",
        "urllib",
        "uuid",
        "warnings",
        "xml",
    }

    # Local project modules (our own code)
    local_modules = {"core", "parallel"}  # .claude/lib/* modules

    # Scan all Python files in .claude/ops/
    scripts_dir = os.path.join(_project_root, ".claude")
    all_imports = set()

    for root, dirs, files in os.walk(scripts_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                imports = extract_imports_from_file(filepath)
                all_imports.update(imports)

    # Filter out stdlib and local modules
    external_imports = {
        imp
        for imp in all_imports
        if imp not in stdlib_modules
        and imp not in local_modules
        and not imp.startswith("_")
    }

    # Read requirements.txt
    requirements_file = os.path.join(_project_root, "requirements.txt")
    required_packages = set()

    if os.path.exists(requirements_file):
        with open(requirements_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract package name (before ==, >=, etc.)
                    pkg_name = re.split(r"[=<>!]", line)[0].strip()
                    required_packages.add(pkg_name.lower())

    # Import name -> Package name mapping for packages with different names
    import_to_package = {
        "dotenv": "python-dotenv",
        "cv2": "opencv-python",
        "PIL": "pillow",
        "yaml": "pyyaml",
        "bs4": "beautifulsoup4",
    }

    # Check for missing dependencies
    missing = []
    for imp in external_imports:
        # Map import name to package name if needed
        pkg_name = import_to_package.get(imp, imp)

        if pkg_name.lower() not in required_packages:
            missing.append(imp)

    if missing:
        print(f"  ⚠️  Found {len(missing)} potentially missing dependencies:")
        for pkg in sorted(missing):
            print(f"     - {pkg}")
        print("\n  💡 If these are needed, add them to requirements.txt:")
        print(f"     echo '{' '.join(sorted(missing))}' >> requirements.txt")
        return False
    else:
        print(
            f"  ✅ All {len(external_imports)} external dependencies appear to be documented"
        )
        if external_imports:
            print(f"     Verified: {', '.join(sorted(external_imports))}")
        return True


def check_scratch(dry_run):
    """Check .claude/tmp/ for old files and warn about cleanup."""
    print("\n" + "=" * 70)
    print("🧹 [JANITOR] Checking Scratch Directory...")
    print("=" * 70)

    scratch_dir = os.path.join(_project_root, "scratch")

    if not os.path.exists(scratch_dir):
        print("  ℹ️  .claude/tmp/ directory does not exist")
        return True

    # Find all files in .claude/tmp/
    scratch_files = []
    for item in os.listdir(scratch_dir):
        item_path = os.path.join(scratch_dir, item)
        if os.path.isfile(item_path):
            scratch_files.append(item_path)

    if not scratch_files:
        print("  ✅ .claude/tmp/ is clean (no files)")
        return True

    # Check for old files (>24 hours)
    cutoff_time = datetime.now() - timedelta(hours=24)
    old_files = []

    for filepath in scratch_files:
        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        if mtime < cutoff_time:
            old_files.append((filepath, mtime))

    print(f"  📊 Found {len(scratch_files)} file(s) in .claude/tmp/")

    if old_files:
        print(f"  ⚠️  {len(old_files)} file(s) are older than 24 hours:")
        for filepath, mtime in old_files:
            age_hours = (datetime.now() - mtime).total_seconds() / 3600
            print(f"     - {os.path.basename(filepath)} ({age_hours:.1f}h old)")
        print("\n  💡 Consider:")
        print("     - Promote useful scripts to .claude/ops/")
        print("     - Delete obsolete files")
        return False
    else:
        print("  ✅ All files are recent (<24h old)")
        return True


def consolidate_lessons(dry_run):
    """Consolidate auto-learned lessons (Reflexion Memory)"""
    print("\n" + "=" * 70)
    print("🧠 [JANITOR] Consolidating Auto-Learned Lessons...")
    print("=" * 70)

    if dry_run:
        print("  [DRY RUN] Would consolidate duplicate auto-learned lessons")
        return True

    try:
        result = subprocess.run(
            [sys.executable, os.path.join(_project_root, ".claude", "ops", "consolidate_lessons.py",
            timeout=10)],
            capture_output=True,
            text=True,
            cwd=_project_root,
        )

        if result.returncode == 0:
            print(f"  {result.stdout.strip()}")
            return True
        else:
            print(f"  ⚠️  Consolidation failed (non-critical): {result.stderr[:100]}")
            return True  # Non-blocking
    except Exception as e:
        print(f"  ⚠️  Failed to consolidate lessons: {e}")
        return True  # Non-blocking


def rebuild_scratch_index(dry_run):
    """Rebuild .claude/tmp/ semantic index for associative memory"""
    print("\n" + "=" * 70)
    print("🗂️  [JANITOR] Rebuilding Scratch Index...")
    print("=" * 70)

    if dry_run:
        print("  [DRY RUN] Would rebuild scratch index")
        return True

    try:
        # Run indexer
        result = subprocess.run(
            [sys.executable, os.path.join(_project_root, "scratch", "prototype_scratch_indexer.py",
            timeout=10)],
            capture_output=True,
            text=True,
            cwd=_project_root,
        )

        if result.returncode == 0:
            # Extract file count from output
            import re
            match = re.search(r'Indexed (\d+) files', result.stdout)
            if match:
                count = match.group(1)
                print(f"  ✅ Rebuilt index with {count} files")
            else:
                print("  ✅ Index rebuilt successfully")
            return True
        else:
            print(f"  ⚠️  Index rebuild failed (non-critical): {result.stderr[:100]}")
            return True  # Non-critical failure
    except Exception as e:
        print(f"  ⚠️  Index rebuild failed (non-critical): {e}")
        return True  # Non-critical failure


def log_maintenance(dry_run):
    """Log that maintenance was performed."""
    print("\n" + "=" * 70)
    print("📝 [JANITOR] Logging Maintenance...")
    print("=" * 70)

    log_file = os.path.join(_project_root, ".claude", "memory", "upkeep_log.md")

    if dry_run:
        print(f"  [DRY RUN] Would append timestamp to {log_file}")
        return True

    try:
        # Create log file if it doesn't exist
        if not os.path.exists(log_file):
            with open(log_file, "w") as f:
                f.write("# Upkeep Log\n\n")
                f.write("Records of automated maintenance runs.\n\n")

        # Append timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a") as f:
            f.write(f"- {timestamp}: Upkeep completed\n")

        print(f"  ✅ Logged to {os.path.basename(log_file)}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to log maintenance: {e}")
        return False


def main():
    parser = setup_script(
        "The Janitor: Scans the project, updates indexes, verifies requirements, and cleans .claude/tmp/"
    )

    args = parser.parse_args()
    handle_debug(args)

    print("\n" + "=" * 70)
    print("🧹 THE JANITOR: Project Upkeep")
    print("=" * 70)

    if args.dry_run:
        logger.warning("⚠️  DRY RUN MODE: No changes will be made")

    try:
        issues_found = []

        # 1. Update Registry
        if not update_registry(args.dry_run):
            issues_found.append("Registry update failed")

        # 2. Check Dependencies
        if not check_dependencies(args.dry_run):
            issues_found.append("Missing dependencies detected")

        # 3. Check Scratch
        if not check_scratch(args.dry_run):
            issues_found.append("Old scratch files need attention")

        # 4. Rebuild Scratch Index
        rebuild_scratch_index(args.dry_run)

        # 5. Consolidate Auto-Learned Lessons
        consolidate_lessons(args.dry_run)

        # 6. Log Maintenance
        if not log_maintenance(args.dry_run):
            issues_found.append("Maintenance logging failed")

        # Summary
        print("\n" + "=" * 70)
        print("📊 UPKEEP SUMMARY")
        print("=" * 70)

        if issues_found:
            print(f"  ⚠️  {len(issues_found)} issue(s) require attention:")
            for issue in issues_found:
                print(f"     - {issue}")
            print("\n  💡 Review the warnings above and take action.")
            logger.warning(f"Upkeep completed with {len(issues_found)} warnings")
        else:
            print("  ✅ All checks passed! Project is clean.")
            logger.info("Upkeep completed successfully - no issues found")

        print("=" * 70 + "\n")

    except Exception as e:
        logger.error(f"Upkeep failed: {e}")
        import traceback

        traceback.print_exc()
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
