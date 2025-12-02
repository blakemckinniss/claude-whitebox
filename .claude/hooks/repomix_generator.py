#!/usr/bin/env python3
"""
Repomix Generator Hook: Auto-generate codebase summaries for AI context.

SUDO SECURITY

Runs on SessionStart to:
1. Detect if we're in a project (not ephemeral)
2. Check if repomix output exists and is fresh (matches current git HEAD)
3. Generate repomix output if missing or stale
4. Store in project memory for context injection

Zero config - just works when entering any project directory.
"""

import _lib_path  # noqa: F401
import sys
import json
import os
import subprocess
import hashlib
from pathlib import Path

try:
    from project_detector import get_current_project, get_project_memory_dir
    PROJECT_AWARE = True
except ImportError:
    PROJECT_AWARE = False


# =============================================================================
# CONFIGURATION
# =============================================================================

# Output filename in project memory
REPOMIX_OUTPUT = "repomix_context.md"
REPOMIX_META = "repomix_meta.json"

# Max age before regeneration (even if git hash unchanged)
MAX_AGE_HOURS = 24

# Repomix CLI options for optimal AI consumption
REPOMIX_OPTS = [
    "--style", "markdown",
    "--compress",  # Reduce tokens by ~70%
    "--remove-comments",
    "--remove-empty-lines",
]


# =============================================================================
# GIT HELPERS
# =============================================================================

def get_git_head_hash(root: str) -> str:
    """Get current git HEAD commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=root,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return ""


def get_tree_hash(root: str) -> str:
    """Get hash of current working tree state (detects uncommitted changes)."""
    try:
        # Get status of tracked files
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=root,
        )
        if result.returncode == 0:
            # Combine HEAD + status for change detection
            head = get_git_head_hash(root)
            status_hash = hashlib.sha256(result.stdout.encode()).hexdigest()[:8]
            return f"{head}_{status_hash}"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return ""


# =============================================================================
# REPOMIX DETECTION & EXECUTION
# =============================================================================

def check_repomix_available() -> bool:
    """Check if repomix is available via npx."""
    try:
        result = subprocess.run(
            ["npx", "--yes", "repomix", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def run_repomix(root: str, output_path: Path) -> tuple[bool, str]:
    """Run repomix and save output.

    Returns: (success, error_message)
    """
    try:
        cmd = [
            "npx", "--yes", "repomix",
            "--output", str(output_path),
            *REPOMIX_OPTS,
            root,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minutes max
            cwd=root,
        )

        if result.returncode == 0:
            return True, ""
        else:
            return False, result.stderr[:200]

    except subprocess.TimeoutExpired:
        return False, "timeout"
    except FileNotFoundError:
        return False, "npx not found"
    except OSError as e:
        return False, str(e)[:100]


# =============================================================================
# STATE MANAGEMENT
# =============================================================================

def load_repomix_meta(memory_dir: Path) -> dict:
    """Load repomix metadata (last generation info)."""
    meta_path = memory_dir / REPOMIX_META
    if meta_path.exists():
        try:
            with open(meta_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_repomix_meta(memory_dir: Path, meta: dict):
    """Save repomix metadata."""
    memory_dir.mkdir(parents=True, exist_ok=True)
    meta_path = memory_dir / REPOMIX_META
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)


def needs_regeneration(memory_dir: Path, current_hash: str) -> tuple[bool, str]:
    """Check if repomix output needs regeneration.

    Returns: (needs_regen, reason)
    """
    import time

    output_path = memory_dir / REPOMIX_OUTPUT

    # Check if output exists
    if not output_path.exists():
        return True, "missing"

    # Check metadata
    meta = load_repomix_meta(memory_dir)

    # Check git hash
    if meta.get("tree_hash") != current_hash:
        return True, "changed"

    # Check age
    generated_at = meta.get("generated_at", 0)
    age_hours = (time.time() - generated_at) / 3600
    if age_hours > MAX_AGE_HOURS:
        return True, f"stale ({int(age_hours)}h)"

    return False, "fresh"


# =============================================================================
# MAIN HOOK
# =============================================================================

def main():
    """SessionStart hook entry point."""
    # Consume stdin
    try:
        json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        pass

    output = {}

    # Skip if project detection not available
    if not PROJECT_AWARE:
        print(json.dumps(output))
        sys.exit(0)

    try:
        # Get project context
        project = get_current_project()

        # Skip ephemeral sessions
        if project.project_type == "ephemeral":
            print(json.dumps(output))
            sys.exit(0)

        # Get project memory directory
        memory_dir = get_project_memory_dir(project.project_id)

        # Get current tree state
        tree_hash = get_tree_hash(project.root_path)
        if not tree_hash:
            # Not a git repo or git failed - skip
            print(json.dumps(output))
            sys.exit(0)

        # Check if regeneration needed
        needs_regen, reason = needs_regeneration(memory_dir, tree_hash)

        if not needs_regen:
            # Fresh - nothing to do
            print(json.dumps(output))
            sys.exit(0)

        # Check repomix availability
        if not check_repomix_available():
            # npx/repomix not available - skip silently
            print(json.dumps(output))
            sys.exit(0)

        # Run repomix (this may take a few seconds)
        output_path = memory_dir / REPOMIX_OUTPUT
        memory_dir.mkdir(parents=True, exist_ok=True)

        success, error = run_repomix(project.root_path, output_path)

        if success:
            # Save metadata
            import time
            save_repomix_meta(memory_dir, {
                "tree_hash": tree_hash,
                "generated_at": time.time(),
                "project_name": project.project_name,
                "root_path": project.root_path,
            })

            # Get file size for feedback
            size_kb = output_path.stat().st_size / 1024
            output["message"] = f"📦 Repomix: Updated ({size_kb:.0f}KB, {reason})"
        else:
            # Log error but don't fail the hook
            if error:
                import sys as _sys
                print(f"repomix error: {error}", file=_sys.stderr)

    except Exception as e:
        # Don't fail session start - repomix is optional
        import sys as _sys
        print(f"repomix hook error: {e}", file=_sys.stderr)

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
