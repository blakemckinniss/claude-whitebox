#!/usr/bin/env python3
"""
The Janitor: Pre-commit health checks and project maintenance.
Run before commits to catch issues early.
"""
import sys
import os
import subprocess
import re
import ast
import stat
from datetime import datetime, timedelta

# Add .claude/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
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


# Standard library modules for dependency checking
STDLIB_MODULES = {
    "abc", "argparse", "ast", "asyncio", "base64", "collections", "concurrent",
    "copy", "csv", "datetime", "decimal", "email", "enum", "functools", "glob",
    "hashlib", "hmac", "html", "http", "importlib", "inspect", "io", "itertools",
    "json", "logging", "math", "multiprocessing", "operator", "os", "pathlib",
    "pickle", "platform", "pprint", "re", "secrets", "shutil", "socket", "sqlite3",
    "stat", "statistics", "string", "subprocess", "sys", "tempfile", "textwrap",
    "threading", "time", "traceback", "typing", "unittest", "urllib", "uuid",
    "warnings", "xml", "contextlib", "dataclasses", "difflib", "fnmatch",
    "getpass", "grp", "pwd", "queue", "random", "select", "signal", "struct",
    "tarfile", "zipfile", "zlib", "types", "weakref", "array", "binascii",
    "fcntl", "termios", "tty", "pty", "resource", "syslog",  # Unix-specific
}

# Import name -> Package name mapping
IMPORT_TO_PACKAGE = {
    "dotenv": "python-dotenv",
    "cv2": "opencv-python",
    "PIL": "pillow",
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
}


def section(title, icon="📋"):
    """Print a section header."""
    print(f"\n{icon} {title}")
    print("-" * 60)


def extract_imports_from_file(filepath):
    """Extract all imported module names from a Python file."""
    imports = set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
    except Exception as e:
        logger.debug(f"Could not parse {filepath}: {e}")
    return imports


def check_git_status(dry_run):
    """Check git status for uncommitted changes."""
    section("Git Status", "📊")

    try:
        # Get current branch
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=_project_root
        )
        current_branch = branch.stdout.strip() or "detached HEAD"

        # Get status
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=_project_root
        )

        if result.returncode != 0:
            print("  ⚠️  Not a git repository or git error")
            return True

        lines = [l for l in result.stdout.strip().split("\n") if l]

        if not lines:
            print(f"  ✅ Clean working tree on '{current_branch}'")
            return True

        staged = [l for l in lines if l[0] != " " and l[0] != "?"]
        unstaged = [l for l in lines if l[0] == " " or l[1] != " "]
        untracked = [l for l in lines if l.startswith("??")]

        print(f"  Branch: {current_branch}")
        print(f"  Staged: {len(staged)} | Modified: {len(unstaged) - len(untracked)} | Untracked: {len(untracked)}")

        if staged:
            print("  📦 Ready to commit:")
            for line in staged[:5]:
                print(f"     {line}")
            if len(staged) > 5:
                print(f"     ... and {len(staged) - 5} more")

        return True
    except FileNotFoundError:
        print("  ⚠️  git not found")
        return True


def check_hooks_health(dry_run, fix=False):
    """Verify hooks are executable and have valid syntax."""
    section("Hooks Health", "🪝")

    hooks_dir = os.path.join(_project_root, ".claude", "hooks")
    if not os.path.exists(hooks_dir):
        print("  ℹ️  No hooks directory")
        return True

    issues = []
    fixed = 0

    for item in os.listdir(hooks_dir):
        if item.startswith((".", "_")) or item == "__pycache__":
            continue

        filepath = os.path.join(hooks_dir, item)
        if not os.path.isfile(filepath):
            continue

        # Check executable for .py and .sh files
        if item.endswith((".py", ".sh", ".js")):
            mode = os.stat(filepath).st_mode
            is_exec = mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            if not is_exec:
                if fix and not dry_run:
                    os.chmod(filepath, mode | stat.S_IXUSR)
                    print(f"  🔧 Fixed: {item} (made executable)")
                    fixed += 1
                else:
                    issues.append(f"{item} not executable")

        # Check Python syntax
        if item.endswith(".py"):
            try:
                with open(filepath, "r") as f:
                    ast.parse(f.read(), filename=item)
            except SyntaxError as e:
                issues.append(f"{item} syntax error: {e.msg} (line {e.lineno})")

    if issues:
        print(f"  ⚠️  {len(issues)} issue(s):")
        for issue in issues:
            print(f"     - {issue}")
        if not fix:
            print("  💡 Run with --fix to auto-repair")
        return False

    hook_count = len([f for f in os.listdir(hooks_dir)
                      if os.path.isfile(os.path.join(hooks_dir, f))
                      and not f.startswith((".", "_"))])
    print(f"  ✅ {hook_count} hooks healthy" + (f" ({fixed} fixed)" if fixed else ""))
    return True


def check_ops_syntax(dry_run):
    """Validate Python syntax in all ops/ scripts."""
    section("Ops Syntax Check", "🔍")

    ops_dir = os.path.join(_project_root, ".claude", "ops")
    if not os.path.exists(ops_dir):
        print("  ℹ️  No ops directory")
        return True

    errors = []
    checked = 0

    for item in os.listdir(ops_dir):
        if not item.endswith(".py"):
            continue
        filepath = os.path.join(ops_dir, item)
        checked += 1

        try:
            with open(filepath, "r") as f:
                ast.parse(f.read(), filename=item)
        except SyntaxError as e:
            errors.append(f"{item}:{e.lineno}: {e.msg}")

    if errors:
        print(f"  ❌ {len(errors)} syntax error(s):")
        for err in errors:
            print(f"     {err}")
        return False

    print(f"  ✅ {checked} scripts valid")
    return True


def check_dependencies(dry_run):
    """Scan scripts for imports and verify against requirements.txt."""
    section("Dependencies", "📦")

    # Auto-detect local modules from .claude subdirs
    local_modules = {"core", "parallel", "lib"}  # 'lib' is a package reference
    for subdir in ["lib", "agents", "ops", "hooks"]:
        mod_dir = os.path.join(_project_root, ".claude", subdir)
        if os.path.isdir(mod_dir):
            for f in os.listdir(mod_dir):
                if f.endswith(".py") and not f.startswith("_"):
                    local_modules.add(f[:-3])

    scripts_dir = os.path.join(_project_root, ".claude")
    all_imports = set()

    for root, dirs, files in os.walk(scripts_dir):
        dirs[:] = [d for d in dirs if d not in {".venv", "__pycache__", ".ruff_cache"}]
        for file in files:
            if file.endswith(".py"):
                imports = extract_imports_from_file(os.path.join(root, file))
                all_imports.update(imports)

    external_imports = {
        imp for imp in all_imports
        if imp not in STDLIB_MODULES
        and imp not in local_modules
        and not imp.startswith("_")
    }

    # Read requirements.txt
    requirements_file = os.path.join(_project_root, ".claude", "requirements.txt")
    required_packages = set()

    if os.path.exists(requirements_file):
        with open(requirements_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    pkg_name = re.split(r"[=<>!\[]", line)[0].strip()
                    required_packages.add(pkg_name.lower())

    missing = []
    for imp in external_imports:
        pkg_name = IMPORT_TO_PACKAGE.get(imp, imp)
        if pkg_name.lower() not in required_packages:
            missing.append(imp)

    if missing:
        print(f"  ⚠️  {len(missing)} potentially undocumented:")
        for pkg in sorted(missing):
            print(f"     - {pkg}")
        return False

    print(f"  ✅ {len(external_imports)} external deps documented")
    return True


def check_tmp_dir(dry_run, fix=False):
    """Check .claude/tmp/ for stale files."""
    section("Temp Directory", "🧹")

    tmp_dir = os.path.join(_project_root, ".claude", "tmp")

    if not os.path.exists(tmp_dir):
        print("  ℹ️  .claude/tmp/ does not exist")
        return True

    files = [f for f in os.listdir(tmp_dir)
             if os.path.isfile(os.path.join(tmp_dir, f))]

    if not files:
        print("  ✅ Clean (empty)")
        return True

    cutoff = datetime.now() - timedelta(hours=24)
    old_files = []

    for fname in files:
        fpath = os.path.join(tmp_dir, fname)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
        if mtime < cutoff:
            age_h = (datetime.now() - mtime).total_seconds() / 3600
            old_files.append((fname, age_h))

    print(f"  📊 {len(files)} file(s), {len(old_files)} stale (>24h)")

    if old_files:
        if fix and not dry_run:
            for fname, _ in old_files:
                os.remove(os.path.join(tmp_dir, fname))
            print(f"  🧹 Cleaned {len(old_files)} stale files")
            return True
        else:
            for fname, age in old_files[:3]:
                print(f"     - {fname} ({age:.0f}h old)")
            if len(old_files) > 3:
                print(f"     ... and {len(old_files) - 3} more")
            print("  💡 Run with --fix to clean, or promote to ops/")
            return False

    return True


def check_large_files(dry_run):
    """Check for large uncommitted files."""
    section("Large Files Check", "📏")

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=_project_root
        )
        if result.returncode != 0:
            return True

        lines = result.stdout.strip().split("\n")
        large_files = []
        size_limit = 1024 * 1024  # 1MB

        for line in lines:
            if not line or line.startswith("??"):
                continue
            filepath = line[3:].strip()
            if " -> " in filepath:  # rename
                filepath = filepath.split(" -> ")[1]

            full_path = os.path.join(_project_root, filepath)
            if os.path.isfile(full_path):
                size = os.path.getsize(full_path)
                if size > size_limit:
                    large_files.append((filepath, size / 1024 / 1024))

        if large_files:
            print(f"  ⚠️  {len(large_files)} large file(s) staged:")
            for fpath, size_mb in large_files:
                print(f"     - {fpath} ({size_mb:.1f}MB)")
            return False

        print("  ✅ No large files staged")
        return True
    except Exception:
        return True


def check_claude_md(dry_run):
    """Verify CLAUDE.md exists and is readable."""
    section("CLAUDE.md", "📄")

    claude_md = os.path.join(_project_root, "CLAUDE.md")

    if not os.path.exists(claude_md):
        print("  ⚠️  CLAUDE.md not found in project root")
        return False

    try:
        with open(claude_md, "r") as f:
            content = f.read()

        lines = len(content.split("\n"))
        size_kb = len(content) / 1024

        # Basic sanity checks
        issues = []
        if size_kb > 50:
            issues.append(f"Large ({size_kb:.1f}KB) - consider trimming")
        if "## " not in content:
            issues.append("No section headers found")

        if issues:
            print(f"  ⚠️  CLAUDE.md ({lines} lines):")
            for issue in issues:
                print(f"     - {issue}")
            return False

        print(f"  ✅ CLAUDE.md valid ({lines} lines, {size_kb:.1f}KB)")
        return True
    except Exception as e:
        print(f"  ❌ Could not read CLAUDE.md: {e}")
        return False


def log_maintenance(dry_run):
    """Log maintenance timestamp."""
    log_file = os.path.join(_project_root, ".claude", "memory", "upkeep_log.md")

    if dry_run:
        return True

    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        if not os.path.exists(log_file):
            with open(log_file, "w") as f:
                f.write("# Upkeep Log\n\n")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(log_file, "a") as f:
            f.write(f"- {timestamp}\n")

        return True
    except Exception:
        return True


def main():
    parser = setup_script(
        "The Janitor: Pre-commit health checks and project maintenance."
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Skip slow checks (large files, full syntax scan)"
    )
    parser.add_argument(
        "--fix", action="store_true",
        help="Auto-fix issues where possible (chmod hooks, clean tmp)"
    )

    args = parser.parse_args()
    handle_debug(args)

    print("\n" + "=" * 60)
    print("🧹 UPKEEP: Project Health Check")
    print("=" * 60)

    if args.dry_run:
        print("⚠️  DRY RUN MODE")
    if args.fix:
        print("🔧 FIX MODE: Will auto-repair issues")

    issues = []

    # Always run these
    if not check_git_status(args.dry_run):
        issues.append("git status")

    if not check_hooks_health(args.dry_run, fix=args.fix):
        issues.append("hooks health")

    if not check_ops_syntax(args.dry_run):
        issues.append("ops syntax")

    if not check_dependencies(args.dry_run):
        issues.append("dependencies")

    if not check_tmp_dir(args.dry_run, fix=args.fix):
        issues.append("stale tmp files")

    if not check_claude_md(args.dry_run):
        issues.append("CLAUDE.md")

    # Slower checks (skip with --quick)
    if not args.quick:
        if not check_large_files(args.dry_run):
            issues.append("large files")

    # Log run
    log_maintenance(args.dry_run)

    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)

    if issues:
        print(f"  ⚠️  {len(issues)} area(s) need attention:")
        for issue in issues:
            print(f"     • {issue}")
        if not args.fix:
            print("\n  💡 Run with --fix to auto-repair fixable issues")
        finalize(success=False, message=f"Upkeep found {len(issues)} issue(s)")
    else:
        print("  ✅ All checks passed!")
        finalize(success=True, message="Upkeep complete - project healthy")


if __name__ == "__main__":
    main()
