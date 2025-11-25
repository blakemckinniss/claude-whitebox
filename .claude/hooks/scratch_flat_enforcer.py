#!/usr/bin/env python3
"""
Scratch Flat Structure Enforcer: PreToolUse Hook
Blocks directory creation within scratch/ to maintain single-layer substrate design

BLOCKS:
1. Bash mkdir/mkdirs commands targeting scratch/
2. Write operations to paths with subdirectories in scratch/
3. Any attempt to create nested structure in scratch/

ALLOWLIST EXCEPTIONS:
- scratch/archive/ (explicitly permitted for cleanup)
- scratch/__pycache__/ (Python runtime artifact)
- scratch/.* (hidden directories like .claude)

Philosophy: scratch/ is a flat workbench for temporary operations.
Nested structures defeat the "single layer substrate" design.
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


# Allowed scratch subdirectories (exceptions to flat rule)
ALLOWED_SCRATCH_SUBDIRS = {
    "archive",      # Cleanup/archival storage
    "__pycache__",  # Python runtime
}

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

tool_name = input_data.get("toolName", "")
tool_params = input_data.get("toolParams", {})
prompt = input_data.get("prompt", "")

# Check for SUDO bypass keyword
if "SUDO" in prompt:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": "⚠️ Scratch flat structure enforcement bypassed with SUDO",
                }
            }
        )
    )
    sys.exit(0)

# ============================================================================
# RULE 1: Block Bash mkdir commands targeting scratch/
# ============================================================================
if tool_name == "Bash":
    command = tool_params.get("command", "")

    # Detect mkdir operations in scratch/
    # Patterns: mkdir scratch/foo, mkdir -p scratch/foo/bar, mkdir scratch/{a,b}
    mkdir_patterns = [
        r"mkdir\s+(?:-[p]\s+)?scratch/([^\s]+)",  # mkdir scratch/foo or mkdir -p scratch/foo
        r"mkdir\s+(?:-[p]\s+)?.*scratch/([^\s;|&]+)",  # mkdir in compound commands
    ]

    for pattern in mkdir_patterns:
        match = re.search(pattern, command)
        if match:
            target_path = match.group(1)

            # Extract first component (before any /)
            first_component = target_path.split("/")[0].split()[0]

            # Remove shell glob chars for checking
            clean_component = first_component.strip("{},'\"")

            # Skip if it's an allowed subdir
            if clean_component in ALLOWED_SCRATCH_SUBDIRS:
                continue

            # Skip if it starts with . (hidden dirs)
            if clean_component.startswith("."):
                continue

            block_message = f"""🚫 SCRATCH FLAT STRUCTURE VIOLATION

You attempted: {command}
Target: scratch/{target_path}

RULE: scratch/ MUST remain a flat, single-layer substrate

Philosophy:
  • scratch/ is a temporary workbench for quick operations
  • Nested directories defeat the single-layer design
  • Files in scratch/ should be discoverable with `ls scratch/`
  • Complex nested structures belong in projects/

Allowed exceptions:
  • scratch/archive/  (cleanup storage)
  • scratch/__pycache__/  (Python runtime)
  • scratch/.*  (hidden directories)

Required action:
  • Write all scratch files to scratch/ root (scratch/my_script.py)
  • Use descriptive prefixes instead of folders (scratch/auth_test.py, scratch/auth_mock.py)
  • For complex projects with structure, use projects/<name>/

Bypass: Include "SUDO" keyword in prompt to override (logged for review)

See CLAUDE.md § Scratch-First Enforcement Protocol"""

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
# RULE 2: Block Write operations to nested paths in scratch/
# ============================================================================
if tool_name == "Write":
    file_path = tool_params.get("file_path", "")

    if file_path:
        path = Path(file_path)

        # Check if path is in scratch/
        try:
            path_str = str(path.resolve())

            # Detect scratch/ in path
            if "/scratch/" in path_str:
                # Extract the part after scratch/
                after_scratch = path_str.split("/scratch/", 1)[1]

                # If there's a slash in the remainder, it's nested
                if "/" in after_scratch:
                    # Get the subdirectory name
                    subdir = after_scratch.split("/", 1)[0]

                    # Check if it's allowed
                    if subdir not in ALLOWED_SCRATCH_SUBDIRS and not subdir.startswith("."):
                        block_message = f"""🚫 SCRATCH FLAT STRUCTURE VIOLATION

You attempted to write: {path.name}
Location: scratch/{after_scratch}

RULE: scratch/ MUST remain a flat, single-layer substrate

Philosophy:
  • scratch/ is a temporary workbench for quick operations
  • All files should be at scratch/ root level
  • Nested directories defeat the single-layer design
  • Files should be discoverable with `ls scratch/`

Current violation:
  • You're creating: scratch/{subdir}/...
  • This creates unwanted nesting

Allowed exceptions:
  • scratch/archive/  (cleanup storage)
  • scratch/__pycache__/  (Python runtime)
  • scratch/.*  (hidden directories)

Required action:
  • Write directly to scratch/ root: scratch/{path.name}
  • Use descriptive prefixes: scratch/{subdir}_{path.name}
  • For complex structures, use projects/<name>/

Example:
  ❌ scratch/auth/test.py
  ✅ scratch/auth_test.py
  ✅ projects/auth_service/tests/test.py

Bypass: Include "SUDO" keyword in prompt to override (logged for review)

See CLAUDE.md § Scratch-First Enforcement Protocol"""

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
