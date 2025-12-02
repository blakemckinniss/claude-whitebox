#!/usr/bin/env python3
"""
Project Detector v1.0: Auto-detect project context for multi-project isolation.

This module enables the hook system to work as a "swiss army knife" across
multiple projects without context pollution.

Detection Strategy (in order of precedence):
1. Git remote URL (most stable identifier)
2. Git repo root directory name
3. package.json/pyproject.toml project name
4. Working directory path hash

Project Types:
- "project": Has git repo, code files, structured work
- "ephemeral": No project markers, casual conversation, disposable context

Design Principles:
- Zero human declaration required
- Fast detection (<10ms)
- Stable IDs across sessions
- Graceful fallback chain
"""

import os
import re
import json
import hashlib
import subprocess
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class ProjectContext:
    """Detected project context."""
    project_id: str           # Stable identifier (hash or name)
    project_name: str         # Human-readable name
    project_type: str         # "project" | "ephemeral"
    root_path: str            # Absolute path to project root
    detection_method: str     # How we identified this project
    git_remote: str = ""      # Git remote URL if available
    language: str = ""        # Primary language (python, javascript, etc.)
    framework: str = ""       # Detected framework (react, fastapi, etc.)


# =============================================================================
# GIT DETECTION
# =============================================================================

def get_git_root() -> Optional[str]:
    """Get git repository root path."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=os.getcwd(),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def get_git_remote() -> Optional[str]:
    """Get git remote origin URL."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=os.getcwd(),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def extract_repo_name(remote_url: str) -> str:
    """Extract repository name from git remote URL.

    Examples:
    - git@github.com:user/repo.git -> repo
    - https://github.com/user/repo.git -> repo
    - https://github.com/user/repo -> repo
    """
    if not remote_url:
        return ""

    # Remove .git suffix
    url = remote_url.rstrip("/").removesuffix(".git")

    # Extract last path component
    if "/" in url:
        return url.split("/")[-1]
    if ":" in url:
        return url.split(":")[-1].split("/")[-1]

    return url


# =============================================================================
# PROJECT FILE DETECTION
# =============================================================================

def find_project_file(root: str) -> Optional[tuple[str, dict]]:
    """Find and parse project configuration file.

    Returns: (file_type, parsed_data) or None
    """
    root_path = Path(root)

    # package.json (Node.js)
    pkg_json = root_path / "package.json"
    if pkg_json.exists():
        try:
            with open(pkg_json) as f:
                data = json.load(f)
            return ("package.json", data)
        except (json.JSONDecodeError, IOError):
            pass

    # pyproject.toml (Python)
    pyproject = root_path / "pyproject.toml"
    if pyproject.exists():
        try:
            # Simple TOML parsing for name field
            content = pyproject.read_text()
            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if name_match:
                return ("pyproject.toml", {"name": name_match.group(1)})
        except IOError:
            pass

    # Cargo.toml (Rust)
    cargo = root_path / "Cargo.toml"
    if cargo.exists():
        try:
            content = cargo.read_text()
            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if name_match:
                return ("Cargo.toml", {"name": name_match.group(1)})
        except IOError:
            pass

    # go.mod (Go)
    gomod = root_path / "go.mod"
    if gomod.exists():
        try:
            content = gomod.read_text()
            module_match = re.search(r'^module\s+(\S+)', content, re.MULTILINE)
            if module_match:
                module = module_match.group(1)
                name = module.split("/")[-1]
                return ("go.mod", {"name": name})
        except IOError:
            pass

    return None


def detect_language(root: str) -> str:
    """Detect primary language from file extensions."""
    root_path = Path(root)

    # Count files by extension (limit search depth)
    counts = {}
    lang_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".rb": "ruby",
        ".php": "php",
    }

    try:
        for ext, lang in lang_map.items():
            # Quick glob, limited depth
            files = list(root_path.glob(f"**/*{ext}"))[:100]
            if files:
                counts[lang] = len(files)
    except OSError:
        pass

    if counts:
        return max(counts, key=counts.get)
    return ""


def detect_framework(root: str, language: str) -> str:
    """Detect framework from dependencies or file patterns."""
    root_path = Path(root)

    # Check package.json dependencies
    pkg_json = root_path / "package.json"
    if pkg_json.exists():
        try:
            with open(pkg_json) as f:
                data = json.load(f)
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

            if "next" in deps:
                return "nextjs"
            if "react" in deps:
                return "react"
            if "vue" in deps:
                return "vue"
            if "svelte" in deps:
                return "svelte"
            if "express" in deps:
                return "express"
        except (json.JSONDecodeError, IOError):
            pass

    # Check Python frameworks
    if language == "python":
        requirements = root_path / "requirements.txt"
        if requirements.exists():
            try:
                content = requirements.read_text().lower()
                if "fastapi" in content:
                    return "fastapi"
                if "django" in content:
                    return "django"
                if "flask" in content:
                    return "flask"
            except IOError:
                pass

    return ""


# =============================================================================
# PROJECT ID GENERATION
# =============================================================================

def generate_project_id(name: str, remote: str = "", root: str = "") -> str:
    """Generate stable project ID.

    Priority:
    1. Hash of git remote URL (most stable across machines)
    2. Hash of project name + root path (stable per machine)
    3. Hash of root path only (fallback)
    """
    if remote:
        # Normalize remote URL for consistent hashing
        normalized = remote.lower().rstrip("/").removesuffix(".git")
        return f"git_{hashlib.sha256(normalized.encode()).hexdigest()[:12]}"

    if name:
        # Use name + root for local uniqueness
        combo = f"{name}:{root}"
        return f"prj_{hashlib.sha256(combo.encode()).hexdigest()[:12]}"

    # Fallback to root path hash
    return f"dir_{hashlib.sha256(root.encode()).hexdigest()[:12]}"


# =============================================================================
# MAIN DETECTION
# =============================================================================

def detect_project() -> ProjectContext:
    """Detect current project context.

    Returns ProjectContext with detected information.
    Detection takes <10ms in typical cases.
    """
    cwd = os.getcwd()

    # Try git detection first (most reliable)
    git_root = get_git_root()
    git_remote = get_git_remote() if git_root else ""

    if git_root:
        # We have a git repo
        root = git_root
        detection_method = "git_remote" if git_remote else "git_root"

        # Try to get name from remote
        name = extract_repo_name(git_remote) if git_remote else ""

        # Fallback to project file
        if not name:
            project_file = find_project_file(root)
            if project_file:
                _, data = project_file
                name = data.get("name", "")
                detection_method = f"git+{project_file[0]}"

        # Fallback to directory name
        if not name:
            name = Path(root).name
            detection_method = "git_dirname"

        project_id = generate_project_id(name, git_remote, root)
        language = detect_language(root)
        framework = detect_framework(root, language)

        return ProjectContext(
            project_id=project_id,
            project_name=name,
            project_type="project",
            root_path=root,
            detection_method=detection_method,
            git_remote=git_remote,
            language=language,
            framework=framework,
        )

    # No git - check for project files
    project_file = find_project_file(cwd)
    if project_file:
        file_type, data = project_file
        name = data.get("name", Path(cwd).name)
        project_id = generate_project_id(name, "", cwd)
        language = detect_language(cwd)
        framework = detect_framework(cwd, language)

        return ProjectContext(
            project_id=project_id,
            project_name=name,
            project_type="project",
            root_path=cwd,
            detection_method=file_type,
            language=language,
            framework=framework,
        )

    # No project markers - ephemeral context
    # Use a stable ID for the working directory
    dir_name = Path(cwd).name

    # Check if this looks like a code directory at all
    has_code = any(
        Path(cwd).glob(f"*.{ext}")
        for ext in ["py", "js", "ts", "rs", "go", "java"]
    )

    if has_code:
        # Looks like code but no project structure
        project_id = generate_project_id(dir_name, "", cwd)
        return ProjectContext(
            project_id=project_id,
            project_name=dir_name,
            project_type="project",
            root_path=cwd,
            detection_method="code_files",
            language=detect_language(cwd),
        )

    # Truly ephemeral - no project context
    return ProjectContext(
        project_id="ephemeral",
        project_name="ephemeral",
        project_type="ephemeral",
        root_path=cwd,
        detection_method="none",
    )


def get_project_memory_dir(project_id: str) -> Path:
    """Get the memory directory for a specific project."""
    # Find .claude directory relative to this file
    lib_dir = Path(__file__).resolve().parent
    claude_dir = lib_dir.parent
    memory_dir = claude_dir / "memory"

    if project_id == "ephemeral":
        return memory_dir / "ephemeral"

    return memory_dir / "projects" / project_id


def get_global_memory_dir() -> Path:
    """Get the global (cross-project) memory directory."""
    lib_dir = Path(__file__).resolve().parent
    claude_dir = lib_dir.parent
    return claude_dir / "memory" / "global"


# =============================================================================
# PROJECT REGISTRY
# =============================================================================

def get_project_index_path() -> Path:
    """Get path to project index file."""
    lib_dir = Path(__file__).resolve().parent
    claude_dir = lib_dir.parent
    return claude_dir / "memory" / "projects" / "_index.json"


def load_project_index() -> dict:
    """Load project index with last-active timestamps."""
    index_path = get_project_index_path()
    if index_path.exists():
        try:
            with open(index_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"projects": {}}


def save_project_index(index: dict):
    """Save project index."""
    index_path = get_project_index_path()
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2)


def register_project_activity(context: ProjectContext):
    """Register activity for a project (updates last-active timestamp)."""
    import time

    if context.project_type == "ephemeral":
        return

    index = load_project_index()
    index["projects"][context.project_id] = {
        "name": context.project_name,
        "root_path": context.root_path,
        "language": context.language,
        "framework": context.framework,
        "last_active": time.time(),
        "detection_method": context.detection_method,
    }
    save_project_index(index)


def get_stale_projects(max_age_days: int = 7) -> list[str]:
    """Get list of project IDs that haven't been active recently."""
    import time

    index = load_project_index()
    cutoff = time.time() - (max_age_days * 86400)

    stale = []
    for project_id, info in index.get("projects", {}).items():
        if info.get("last_active", 0) < cutoff:
            stale.append(project_id)

    return stale


# =============================================================================
# CONVENIENCE
# =============================================================================

def get_current_project() -> ProjectContext:
    """Get current project context and register activity.

    This is the main entry point for hooks to get project context.
    """
    context = detect_project()
    register_project_activity(context)
    return context


if __name__ == "__main__":
    # Test detection
    ctx = detect_project()
    print(json.dumps(asdict(ctx), indent=2))
