#!/usr/bin/env python3
"""
Root Pollution Gate Hook: Prevents creating files/folders in repository root
Triggers on: PreToolUse (Write, Bash mkdir/touch)
Purpose: Hard-block root pollution - enforce clean architecture zones
"""
import sys
import json
import re
from pathlib import Path

def validate_file_path(file_path: str) -> bool:
    """
    Validate file path to prevent path traversal attacks.
    Per official docs: "Block path traversal - Check for .. in file paths"
    """
    if not file_path:
        return True

    # Normalize path to resolve any . or .. components
    normalized = str(Path(file_path).resolve())

    # Check for path traversal attempts
    if '..' in file_path:
        return False

    return True


# Load input
try:
    input_data = json.load(sys.stdin)
except Exception:
    # Fail open on parse error
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                }
            }
        )
    )
    sys.exit(0)

tool_name = input_data.get("tool_name", "")
tool_params = input_data.get("tool_input", {})

# ============================================================================
# Allowed root-level files (whitelist)
# ============================================================================
ALLOWED_ROOT_FILES = {
    ".gitignore",
    "CLAUDE.md",
    "README.md",
    "requirements.txt",
    "package.json",
    "pyproject.toml",
    "setup.py",
}

# Allowed root directories
ALLOWED_ROOT_DIRS = {
    ".claude",
    ".git",
    "projects",
    "scratch",
    "scripts",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}

# ============================================================================
# RULE: Write tool cannot create root-level files (except whitelist)
# ============================================================================
if tool_name == "Write":
    file_path = tool_params.get("file_path", "")

    if file_path:
        path = Path(file_path)

        # Check if writing to root (no parent dirs except root)
        try:
            # Get path relative to repo root
            parts = path.parts

            # If path has only 2 parts (e.g., /home/jinx/workspace/claude-whitebox/foo.py)
            # Then it's root-level (after removing leading /)
            if len(parts) > 0:
                # Check if it's a root-level file
                filename = path.name

                # Heuristic: if path contains /claude-whitebox/ followed by just a filename
                path_str = str(path)
                if "/claude-whitebox/" in path_str:
                    after_root = path_str.split("/claude-whitebox/", 1)[1]

                    # If no slashes after root, it's a root file
                    if "/" not in after_root:
                        # Check whitelist
                        if filename not in ALLOWED_ROOT_FILES:
                            block_message = f"""🚫 ROOT POLLUTION BLOCKED

You attempted to write: {filename}
Location: Repository root

RULE: NEVER create new files in repository root

Allowed zones:
  • projects/<name>/  - User projects
  • scratch/         - Prototypes, temp files
  • scripts/ops/     - Operational tools (production)

Whitelist (already exists):
  • {', '.join(sorted(ALLOWED_ROOT_FILES))}

Why:
  - Root pollution creates clutter
  - Template must stay clean
  - Architecture zones enforce separation

Required action:
  • Move to projects/<name>/ for user projects
  • Move to scratch/ for temporary work
  • Move to scripts/ for operational tools

See CLAUDE.md § Hard Block #1 (Root Pollution Ban)"""

                            print(
                                json.dumps(
                                    {
                                        "hookSpecificOutput": {
                                            "hookEventName": "PreToolUse",
                                            "permissionDecision": "deny",
                                            "permissionDecisionReason": block_message,
                                        }
                                    }
                                )
                            )
                            sys.exit(0)
        except Exception:
            # If path parsing fails, allow (fail open)
            pass

# ============================================================================
# RULE: Bash mkdir/touch cannot create root-level dirs/files (except whitelist)
# ============================================================================
if tool_name == "Bash":
    command = tool_params.get("command", "")

    # Detect mkdir/touch/echo > at root level
    patterns = [
        r"mkdir\s+([^\s/]+)$",  # mkdir dirname (no path)
        r"touch\s+([^\s/]+)$",  # touch filename (no path)
        r"echo.*>\s*([^\s/]+)$",  # echo > filename (no path)
        r"cat.*>\s*([^\s/]+)$",  # cat > filename (no path)
    ]

    for pattern in patterns:
        match = re.search(pattern, command)
        if match:
            target = match.group(1)

            # Check if it's a root-level target (no slashes)
            if "/" not in target and target not in ALLOWED_ROOT_FILES and target not in ALLOWED_ROOT_DIRS:
                block_message = f"""🚫 ROOT POLLUTION BLOCKED

You attempted to create: {target}
Command: {command}
Location: Repository root

RULE: NEVER create new files/directories in repository root

Allowed zones:
  • projects/<name>/  - User projects
  • scratch/         - Prototypes, temp files
  • scripts/ops/     - Operational tools

Whitelisted root items:
  • Files: {', '.join(sorted(ALLOWED_ROOT_FILES))}
  • Dirs: {', '.join(sorted(d for d in ALLOWED_ROOT_DIRS if not d.startswith('.')))}

Why:
  - Root pollution creates clutter
  - Template must stay clean for future projects
  - Architecture zones enforce separation of concerns

Required action:
  • Use projects/<name>/{target} for user projects
  • Use scratch/{target} for temporary work
  • Use scripts/ops/{target} for operational tools

See CLAUDE.md § Hard Block #1 (Root Pollution Ban)"""

                print(
                    json.dumps(
                        {
                            "hookSpecificOutput": {
                                "hookEventName": "PreToolUse",
                                "permissionDecision": "deny",
                                "permissionDecisionReason": block_message,
                            }
                        }
                    )
                )
                sys.exit(0)

# ============================================================================
# All checks passed - allow action
# ============================================================================
print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }
    )
)
sys.exit(0)
