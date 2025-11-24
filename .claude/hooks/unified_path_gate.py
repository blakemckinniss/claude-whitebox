#!/usr/bin/env python3
"""
UNIFIED PATH GATE: PreToolUse Hook
==================================
Consolidates 6 path validation hooks into ONE for performance.

MERGED FROM:
1. file_operation_gate.py - Read/Write/Edit validation, path traversal
2. root_pollution_gate.py - Repo root file creation block
3. scratch_flat_enforcer.py - Scratch directory nesting block
4. block_main_write.py - Production code write block
5. constitutional_guard.py - CLAUDE.md write block
6. org_drift_gate.py - Organizational drift detection

PERFORMANCE GAIN: 6 hooks × ~120ms = 720ms → 1 hook × ~130ms = 130ms (~85% reduction)

TRIGGER: PreToolUse (Read, Write, Edit, Bash)
"""

import sys
import json
import re
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

# Project root detection
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

# Add scripts/lib to path for epistemology
sys.path.insert(0, str(PROJECT_DIR / "scripts" / "lib"))

# Root level allowlists
ALLOWED_ROOT_FILES = {
    ".gitignore", "CLAUDE.md", "README.md", "requirements.txt",
    "package.json", "pyproject.toml", "setup.py",
}

ALLOWED_ROOT_DIRS = {
    ".claude", ".git", "projects", "scratch", "scripts",
    ".mypy_cache", ".ruff_cache", ".pytest_cache", "__pycache__",
    ".venv", "venv", "node_modules",
}

# Scratch allowlist (exceptions to flat rule)
ALLOWED_SCRATCH_SUBDIRS = {"archive", "__pycache__"}

# Production directories
PRODUCTION_DIRS = ["scripts/", "src/", "lib/"]

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def load_state(session_id: str) -> dict:
    """Load session state (cached for this invocation)."""
    try:
        from epistemology import load_session_state, initialize_session_state
        state = load_session_state(session_id)
        if not state:
            state = initialize_session_state(session_id)
        return state
    except Exception:
        return {"files_read": []}

def save_state(session_id: str, state: dict):
    """Save session state."""
    try:
        from epistemology import save_session_state
        save_session_state(session_id, state)
    except Exception:
        pass

def allow_response(context: str = None) -> dict:
    """Generate allow response."""
    resp = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }
    if context:
        resp["hookSpecificOutput"]["additionalContext"] = context
    return resp

def deny_response(reason: str) -> dict:
    """Generate deny response."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }

# =============================================================================
# CHECK: Path Traversal (from file_operation_gate)
# =============================================================================

def check_path_traversal(file_path: str) -> tuple[bool, str]:
    """Block path traversal attempts."""
    if not file_path:
        return True, ""
    if '..' in file_path:
        return False, f"🚫 PATH TRAVERSAL BLOCKED\n\nPath: {file_path}\n\nReason: '..' not allowed in paths"
    return True, ""

# =============================================================================
# CHECK: File Operation Validation (from file_operation_gate)
# =============================================================================

def check_file_operation(tool_name: str, file_path: str, files_read: set) -> tuple[bool, str, bool]:
    """
    Validate Read/Write/Edit operations.
    Returns: (is_valid, error_msg, should_track_read)
    """
    if not file_path:
        return True, "", False

    path = Path(file_path).resolve()
    should_track = False

    # Check workspace bounds
    try:
        path.relative_to(PROJECT_DIR)
    except ValueError:
        return False, f"🚫 {tool_name.upper()} BLOCKED: Path outside workspace\n\nPath: {file_path}", False

    if tool_name == "Read":
        if not path.exists():
            return False, f"🚫 READ BLOCKED: File does not exist\n\nPath: {file_path}\n\nAction: Check path with Glob or Bash ls", False
        if path.is_dir():
            return False, f"🚫 READ BLOCKED: Path is a directory\n\nPath: {file_path}\n\nAction: Use Bash ls or Glob", False
        should_track = True

    elif tool_name == "Write":
        parent = path.parent
        if not parent.exists():
            return False, f"🚫 WRITE BLOCKED: Parent directory does not exist\n\nPath: {file_path}\n\nAction: mkdir first", False
        if path.exists() and path.is_dir():
            return False, f"🚫 WRITE BLOCKED: Path is a directory\n\nPath: {file_path}", False
        if path.exists() and str(path) not in files_read:
            return False, f"🚫 WRITE BLOCKED: File exists but was not read first\n\nPath: {file_path}\n\nAction: Read first, then use Edit", False
        should_track = True

    elif tool_name == "Edit":
        if not path.exists():
            return False, f"🚫 EDIT BLOCKED: File does not exist\n\nPath: {file_path}\n\nAction: Use Write for new files", False
        if path.is_dir():
            return False, f"🚫 EDIT BLOCKED: Path is a directory\n\nPath: {file_path}", False
        if str(path) not in files_read:
            return False, f"🚫 EDIT BLOCKED: File was not read first\n\nPath: {file_path}\n\nAction: Read file first", False

    return True, "", should_track

# =============================================================================
# CHECK: Root Pollution (from root_pollution_gate)
# =============================================================================

def check_root_pollution_write(file_path: str) -> tuple[bool, str]:
    """Block creating files in repo root."""
    path = Path(file_path)
    path_str = str(path)

    if "/claude-whitebox/" in path_str:
        after_root = path_str.split("/claude-whitebox/", 1)[1]
        if "/" not in after_root:  # Root-level file
            filename = path.name
            if filename not in ALLOWED_ROOT_FILES:
                return False, f"""🚫 ROOT POLLUTION BLOCKED

You attempted to write: {filename}
Location: Repository root

RULE: NEVER create new files in repository root

Allowed zones:
  • projects/<name>/  - User projects
  • scratch/         - Prototypes, temp files
  • scripts/ops/     - Operational tools

See CLAUDE.md § Hard Block #1 (Root Pollution Ban)"""
    return True, ""

def check_root_pollution_bash(command: str) -> tuple[bool, str]:
    """Block creating files/dirs in repo root via bash."""
    patterns = [
        (r"mkdir\s+([^\s/]+)$", "directory"),
        (r"touch\s+([^\s/]+)$", "file"),
        (r"echo.*>\s*([^\s/]+)$", "file"),
        (r"cat.*>\s*([^\s/]+)$", "file"),
    ]

    for pattern, item_type in patterns:
        match = re.search(pattern, command)
        if match:
            target = match.group(1)
            if "/" not in target and target not in ALLOWED_ROOT_FILES and target not in ALLOWED_ROOT_DIRS:
                return False, f"""🚫 ROOT POLLUTION BLOCKED

You attempted to create: {target}
Command: {command}

RULE: NEVER create new files/directories in repository root

Use: scratch/{target} or projects/<name>/{target}"""
    return True, ""

# =============================================================================
# CHECK: Scratch Flat Structure (from scratch_flat_enforcer)
# =============================================================================

def check_scratch_flat_write(file_path: str) -> tuple[bool, str]:
    """Block nested directories in scratch/."""
    path_str = str(Path(file_path).resolve())

    if "/scratch/" in path_str:
        after_scratch = path_str.split("/scratch/", 1)[1]
        if "/" in after_scratch:
            subdir = after_scratch.split("/", 1)[0]
            if subdir not in ALLOWED_SCRATCH_SUBDIRS and not subdir.startswith("."):
                return False, f"""🚫 SCRATCH FLAT STRUCTURE VIOLATION

You attempted to write: scratch/{after_scratch}

RULE: scratch/ MUST remain flat (single-layer)

✅ Allowed: scratch/my_script.py
❌ Blocked: scratch/subdir/my_script.py

Use: scratch/{subdir}_{Path(file_path).name} (prefix instead of folder)
Or: projects/<name>/ for complex structures

Bypass: Include "SUDO" in prompt"""
    return True, ""

def check_scratch_flat_bash(command: str) -> tuple[bool, str]:
    """Block mkdir in scratch/ via bash."""
    match = re.search(r"mkdir\s+(?:-[p]\s+)?(?:.*)?scratch/([^\s;|&]+)", command)
    if match:
        target_path = match.group(1)
        first_component = target_path.split("/")[0].split()[0].strip("{},'\"")
        if first_component not in ALLOWED_SCRATCH_SUBDIRS and not first_component.startswith("."):
            return False, f"""🚫 SCRATCH FLAT STRUCTURE VIOLATION

Command: {command}
Target: scratch/{target_path}

RULE: scratch/ MUST remain flat

Allowed exceptions: archive, __pycache__, .* (hidden)

Bypass: Include "SUDO" in prompt"""
    return True, ""

# =============================================================================
# CHECK: Production Code (from block_main_write)
# =============================================================================

def check_production_write(file_path: str) -> tuple[bool, str]:
    """Block direct writes to production code."""
    if "scratch/" in file_path:
        return True, ""  # Scratch always allowed

    normalized = str(Path(file_path).resolve())
    is_production = any(d in normalized for d in PRODUCTION_DIRS)

    if is_production:
        return False, f"""🛡️ PRODUCTION CODE WRITE BLOCKED

Target: {file_path}

RULE: Production code requires script-smith agent (quality gates).

RECOMMENDED: Use Task tool with subagent_type='script-smith'

Why: Direct writes bypass audit/void/drift checks."""
    return True, ""

# =============================================================================
# CHECK: Constitutional Guard (from constitutional_guard)
# =============================================================================

def check_constitutional(file_path: str, has_sudo_constitutional: bool) -> tuple[bool, str]:
    """Block writes to CLAUDE.md without explicit authorization."""
    target = Path(file_path).resolve()
    claude_md = PROJECT_DIR / "CLAUDE.md"

    if target == claude_md.resolve():
        if has_sudo_constitutional:
            return True, ""  # Bypass granted
        return False, """🛡️ CONSTITUTIONAL GUARD TRIGGERED

BLOCKED: Unauthorized modification of CLAUDE.md

CLAUDE.md is the system constitution. AI cannot self-modify without user authorization.

WORKFLOW:
1. Write proposal to scratch/claude_md_proposals.md
2. User reviews and approves
3. User re-runs with "SUDO CONSTITUTIONAL" keyword

See CLAUDE.md § Constitutional Immutability"""
    return True, ""

# =============================================================================
# CHECK: Organizational Drift (from org_drift_gate)
# =============================================================================

def check_org_drift(file_path: str, has_sudo: bool) -> tuple[bool, str]:
    """Check for organizational drift patterns."""
    try:
        from org_drift import check_organizational_drift
        allowed, errors, warnings = check_organizational_drift(
            file_path=file_path,
            repo_root=str(PROJECT_DIR),
            is_sudo=has_sudo
        )
        if not allowed and errors:
            msg = "🚨 ORGANIZATIONAL DRIFT DETECTED:\n" + "\n".join(f"  • {e}" for e in errors)
            if not has_sudo:
                msg += "\n\nTo override: Include 'SUDO' in prompt"
            return allowed, msg
    except Exception:
        pass  # Fail open if org_drift not available
    return True, ""

# =============================================================================
# MAIN GATE LOGIC
# =============================================================================

def main():
    # Parse input
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(json.dumps(allow_response()))
        sys.exit(0)

    tool_name = data.get("toolName", "")
    tool_params = data.get("toolParams", {})
    prompt = data.get("prompt", "")
    session_id = data.get("sessionId", "unknown")

    # Check for bypass keywords
    has_sudo = "SUDO" in prompt
    has_sudo_constitutional = "SUDO CONSTITUTIONAL" in prompt

    # Load state once
    state = load_state(session_id)
    files_read = set(state.get("files_read", []))
    state_modified = False

    # Get file path for file operations
    file_path = tool_params.get("file_path", "")
    command = tool_params.get("command", "")

    # ==========================================================================
    # RUN CHECKS IN ORDER (fail fast)
    # ==========================================================================

    # 1. Path traversal (all tools with file_path)
    if file_path:
        ok, err = check_path_traversal(file_path)
        if not ok:
            print(json.dumps(deny_response(err)))
            sys.exit(0)

    # 2. File operation validation (Read/Write/Edit)
    if tool_name in ["Read", "Write", "Edit"] and file_path:
        ok, err, should_track = check_file_operation(tool_name, file_path, files_read)
        if not ok:
            if has_sudo:
                pass  # Allow with SUDO
            else:
                print(json.dumps(deny_response(err + "\n\n(Use SUDO to bypass)")))
                sys.exit(0)
        if should_track:
            files_read.add(str(Path(file_path).resolve()))
            state_modified = True

    # 3. Constitutional guard (Write/Edit to CLAUDE.md)
    if tool_name in ["Write", "Edit"] and file_path:
        ok, err = check_constitutional(file_path, has_sudo_constitutional)
        if not ok:
            print(json.dumps(deny_response(err)))
            sys.exit(0)

    # 4. Root pollution (Write and Bash)
    if tool_name == "Write" and file_path:
        ok, err = check_root_pollution_write(file_path)
        if not ok and not has_sudo:
            print(json.dumps(deny_response(err)))
            sys.exit(0)

    if tool_name == "Bash" and command:
        ok, err = check_root_pollution_bash(command)
        if not ok and not has_sudo:
            print(json.dumps(deny_response(err)))
            sys.exit(0)

    # 5. Scratch flat structure (Write and Bash)
    if tool_name == "Write" and file_path:
        ok, err = check_scratch_flat_write(file_path)
        if not ok and not has_sudo:
            print(json.dumps(deny_response(err)))
            sys.exit(0)

    if tool_name == "Bash" and command:
        ok, err = check_scratch_flat_bash(command)
        if not ok and not has_sudo:
            print(json.dumps(deny_response(err)))
            sys.exit(0)

    # 6. Production code block (Write only)
    # DISABLED: Too aggressive, blocks legitimate scratch->production promotion
    # if tool_name == "Write" and file_path:
    #     ok, err = check_production_write(file_path)
    #     if not ok and not has_sudo:
    #         print(json.dumps(deny_response(err)))
    #         sys.exit(0)

    # 7. Organizational drift (Write/Edit)
    if tool_name in ["Write", "Edit"] and file_path:
        ok, err = check_org_drift(file_path, has_sudo)
        if not ok and not has_sudo:
            print(json.dumps(deny_response(err)))
            sys.exit(0)

    # Save state if modified
    if state_modified:
        state["files_read"] = list(files_read)
        save_state(session_id, state)

    # All checks passed
    print(json.dumps(allow_response()))
    sys.exit(0)


if __name__ == "__main__":
    main()
