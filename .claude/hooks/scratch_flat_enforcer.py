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


def check_sudo_in_transcript(data: dict) -> bool:
    """Check if SUDO keyword is in recent transcript messages."""
    transcript_path = data.get("transcript_path", "")
    if not transcript_path:
        return False
    try:
        import os
        if os.path.exists(transcript_path):
            with open(transcript_path, 'r') as tf:
                transcript = tf.read()
                # Check last 5000 chars for SUDO (recent messages)
                last_chunk = transcript[-5000:] if len(transcript) > 5000 else transcript
                return "SUDO" in last_chunk
    except Exception:
        pass
    return False


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

tool_name = input_data.get("tool_name", "")
tool_params = input_data.get("tool_input", {})
# PreToolUse hooks don't receive 'prompt' - check transcript for SUDO
sudo_bypass = check_sudo_in_transcript(input_data)

# Check for SUDO bypass keyword
if sudo_bypass:
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
                        # Auto-flatten: scratch/auth/test.py → scratch/auth_test.py
                        flat_name = after_scratch.replace("/", "_")
                        flat_path = path_str.split("/scratch/")[0] + "/scratch/" + flat_name

                        auto_fix_message = f"""🔧 AUTO-FLATTENED: scratch path normalized

Original: scratch/{after_scratch}
Fixed:    scratch/{flat_name}

RULE: scratch/ MUST remain a flat, single-layer substrate

Philosophy:
  • scratch/ is a temporary workbench for quick operations
  • All files should be at scratch/ root level
  • Nested directories defeat the single-layer design

The path was automatically flattened using underscore separators.
For complex structures with real nesting, use projects/<name>/

See CLAUDE.md § Scratch Flat Structure Protocol"""

                        print(
                            json.dumps(
                                {
                                    "hookSpecificOutput": {
                                        "hookEventName": "PreToolUse",
                                        "permissionDecision": "allow",
                                        "permissionDecisionReason": auto_fix_message,
                                        "updatedInput": {
                                            "file_path": flat_path,
                                            "content": tool_params.get("content", "")
                                        }
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
