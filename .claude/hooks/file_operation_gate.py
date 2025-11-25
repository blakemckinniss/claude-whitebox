#!/usr/bin/env python3
"""
File Operation Gate: PreToolUse Hook
Validates Read/Write/Edit operations BEFORE execution to prevent common errors.

BLOCKS:
1. Read to non-existent file
2. Read to directory instead of file
3. Write to existing file without reading first
4. Write to path that is a directory
5. Edit to non-existent file
6. Edit without reading first
7. Path traversal outside workspace

STATE TRACKING:
Persists files_read across session to enforce "Read before Write/Edit" rule.
"""

import sys
import json
from pathlib import Path

# Add scripts/lib to path
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

sys.path.insert(0, str(PROJECT_DIR / "scripts" / "lib"))

from epistemology import load_session_state, save_session_state, initialize_session_state

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



def validate_read(file_path: str, workspace_root: Path) -> tuple[bool, str]:
    """Validate Read operation"""
    path = Path(file_path).resolve()

    # Check if path is within workspace
    try:
        path.relative_to(workspace_root)
    except ValueError:
        return False, f"🚫 READ BLOCKED: Path outside workspace\n\nPath: {file_path}\n\nReason: Security violation - cannot read files outside repository."

    # Check if file exists
    if not path.exists():
        return False, f"🚫 READ BLOCKED: File does not exist\n\nPath: {file_path}\n\nReason: Cannot read non-existent file.\n\nAction: Check path with Glob or Bash ls before reading."

    # Check if it's actually a file (not directory)
    if path.is_dir():
        return False, f"🚫 READ BLOCKED: Path is a directory\n\nPath: {file_path}\n\nReason: Read tool expects a file, not a directory.\n\nAction: Use Bash ls or Glob to list directory contents."

    return True, ""


def validate_write(file_path: str, workspace_root: Path, files_read: set) -> tuple[bool, str]:
    """Validate Write operation"""
    path = Path(file_path).resolve()

    # Check if path is within workspace
    try:
        path.relative_to(workspace_root)
    except ValueError:
        return False, f"🚫 WRITE BLOCKED: Path outside workspace\n\nPath: {file_path}\n\nReason: Security violation - cannot write files outside repository."

    # Check if parent directory exists
    parent = path.parent
    if not parent.exists():
        return False, f"🚫 WRITE BLOCKED: Parent directory does not exist\n\nPath: {file_path}\nParent: {parent}\n\nReason: Cannot create file in non-existent directory.\n\nAction: Create parent directory first with Bash mkdir."

    if not parent.is_dir():
        return False, f"🚫 WRITE BLOCKED: Parent path is not a directory\n\nPath: {file_path}\nParent: {parent}\n\nReason: Parent path exists but is a file, not a directory."

    # Check if path is a directory (trying to write to directory)
    if path.exists() and path.is_dir():
        return False, f"🚫 WRITE BLOCKED: Path is a directory\n\nPath: {file_path}\n\nReason: Cannot write file to a directory path.\n\nAction: Specify a file path, not a directory."

    # Check if file already exists and was not read first
    if path.exists() and str(path) not in files_read:
        return False, f"🚫 WRITE BLOCKED: File exists but was not read first\n\nPath: {file_path}\n\nReason: Write tool overwrites files. You must Read first to understand existing content.\n\nAction: Read file first, then use Edit tool instead of Write."

    return True, ""


def validate_edit(file_path: str, workspace_root: Path, files_read: set) -> tuple[bool, str]:
    """Validate Edit operation"""
    path = Path(file_path).resolve()

    # Check if path is within workspace
    try:
        path.relative_to(workspace_root)
    except ValueError:
        return False, f"🚫 EDIT BLOCKED: Path outside workspace\n\nPath: {file_path}\n\nReason: Security violation - cannot edit files outside repository."

    # Check if file exists
    if not path.exists():
        return False, f"🚫 EDIT BLOCKED: File does not exist\n\nPath: {file_path}\n\nReason: Edit requires an existing file.\n\nAction: Use Write tool to create new files."

    # Check if it's actually a file (not directory)
    if path.is_dir():
        return False, f"🚫 EDIT BLOCKED: Path is a directory\n\nPath: {file_path}\n\nReason: Cannot edit a directory."

    # Check if file was read first
    if str(path) not in files_read:
        return False, f"🚫 EDIT BLOCKED: File was not read first\n\nPath: {file_path}\n\nReason: You must Read file before editing to understand context.\n\nAction: Read file first using Read tool."

    return True, ""


def main():
    """Main gate logic"""
    try:
        data = json.load(sys.stdin)
    except Exception:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    session_id = data.get("sessionId", "unknown")
    tool_name = data.get("toolName", "")
    tool_params = data.get("toolParams", {})
    prompt = data.get("prompt", "")

    # Only validate file operations
    if tool_name not in ["Read", "Write", "Edit"]:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Load session state
    state = load_session_state(session_id)
    if not state:
        state = initialize_session_state(session_id)

    # Get files_read tracking
    files_read = set(state.get("files_read", []))

    # Workspace root
    workspace_root = PROJECT_DIR

    # Validate based on tool
    is_valid = True
    error_msg = ""

    if tool_name == "Read":
        file_path = tool_params.get("file_path")
        if file_path:
            is_valid, error_msg = validate_read(file_path, workspace_root)
            if is_valid:
                # Track successful read
                files_read.add(str(Path(file_path).resolve()))

    elif tool_name == "Write":
        file_path = tool_params.get("file_path")
        if file_path:
            is_valid, error_msg = validate_write(file_path, workspace_root, files_read)
            if is_valid:
                # Track as read for future edits
                files_read.add(str(Path(file_path).resolve()))

    elif tool_name == "Edit":
        file_path = tool_params.get("file_path")
        if file_path:
            is_valid, error_msg = validate_edit(file_path, workspace_root, files_read)

    # Save updated state
    state["files_read"] = list(files_read)
    save_session_state(session_id, state)

    # Return result
    if not is_valid:
        # Check for SUDO bypass
        if "SUDO" in prompt:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": f"⚠️ File operation validation bypassed with SUDO\n\n{error_msg}",
                }
            }
        else:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": error_msg + "\n\n(Use SUDO keyword to bypass)",
                }
            }
    else:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
