#!/usr/bin/env python3
"""
File Operation Validator Library
Validates file operations BEFORE execution to prevent common errors:

1. Read to non-existent file
2. Write to file without reading first
3. Write to path that is actually a directory
4. Edit to non-existent file
5. Path traversal outside workspace
"""

import os
from pathlib import Path
from typing import Dict, Tuple, Optional


class FileOperationValidator:
    """Validates file operations against filesystem reality"""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()
        # Track files read in this session
        self.files_read = set()

    def validate_read(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Read operation.

        Returns: (is_valid, error_message)
        """
        path = Path(file_path).resolve()

        # Check if path is within workspace
        try:
            path.relative_to(self.workspace_root)
        except ValueError:
            return False, f"Path outside workspace: {file_path}"

        # Check if file exists
        if not path.exists():
            return False, f"File does not exist: {file_path}"

        # Check if it's actually a file (not directory)
        if path.is_dir():
            return False, f"Path is a directory, not a file: {file_path}"

        # Check if file is readable
        if not os.access(path, os.R_OK):
            return False, f"File is not readable: {file_path}"

        # Track successful read
        self.files_read.add(str(path))

        return True, None

    def validate_write(self, file_path: str, is_new_file: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Validate Write operation.

        Args:
            file_path: Path to write to
            is_new_file: If True, expects file NOT to exist

        Returns: (is_valid, error_message)
        """
        path = Path(file_path).resolve()

        # Check if path is within workspace
        try:
            path.relative_to(self.workspace_root)
        except ValueError:
            return False, f"Path outside workspace: {file_path}"

        # Check if parent directory exists
        parent = path.parent
        if not parent.exists():
            return False, f"Parent directory does not exist: {parent}"

        if not parent.is_dir():
            return False, f"Parent path is not a directory: {parent}"

        # Check if path is a directory (trying to write to directory)
        if path.exists() and path.is_dir():
            return False, f"Path is a directory, cannot write file: {file_path}"

        # Check if file already exists (for new file creation)
        if is_new_file and path.exists():
            return False, f"File already exists (use Edit instead): {file_path}"

        # Check if file exists and was not read first (for existing file)
        if path.exists() and str(path) not in self.files_read:
            return False, f"File exists but was not read first (Read before Write): {file_path}"

        # Check if parent is writable
        if not os.access(parent, os.W_OK):
            return False, f"Parent directory is not writable: {parent}"

        return True, None

    def validate_edit(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Edit operation.

        Returns: (is_valid, error_message)
        """
        path = Path(file_path).resolve()

        # Check if path is within workspace
        try:
            path.relative_to(self.workspace_root)
        except ValueError:
            return False, f"Path outside workspace: {file_path}"

        # Check if file exists
        if not path.exists():
            return False, f"File does not exist (use Write to create): {file_path}"

        # Check if it's actually a file (not directory)
        if path.is_dir():
            return False, f"Path is a directory, not a file: {file_path}"

        # Check if file was read first
        if str(path) not in self.files_read:
            return False, f"File was not read first (Read before Edit): {file_path}"

        # Check if file is writable
        if not os.access(path, os.W_OK):
            return False, f"File is not writable: {file_path}"

        return True, None

    def mark_as_read(self, file_path: str):
        """Manually mark a file as read (for tracking)"""
        path = Path(file_path).resolve()
        self.files_read.add(str(path))

    def reset_session(self):
        """Reset session-specific tracking"""
        self.files_read.clear()


def validate_tool_operation(
    tool_name: str,
    tool_params: Dict,
    validator: FileOperationValidator
) -> Tuple[bool, Optional[str]]:
    """
    Validate a tool operation.

    Returns: (is_valid, error_message)
    """
    if tool_name == "Read":
        file_path = tool_params.get("file_path")
        if not file_path:
            return False, "Read operation missing file_path parameter"
        return validator.validate_read(file_path)

    elif tool_name == "Write":
        file_path = tool_params.get("file_path")
        if not file_path:
            return False, "Write operation missing file_path parameter"

        # Determine if this is a new file creation
        path = Path(file_path)
        is_new = not path.exists()

        return validator.validate_write(file_path, is_new_file=is_new)

    elif tool_name == "Edit":
        file_path = tool_params.get("file_path")
        if not file_path:
            return False, "Edit operation missing file_path parameter"
        return validator.validate_edit(file_path)

    # Other tools are not validated
    return True, None


# Example usage
if __name__ == "__main__":
    import sys

    validator = FileOperationValidator(Path.cwd())

    # Test cases
    test_cases = [
        ("Read", {"file_path": "/nonexistent/file.txt"}),
        ("Read", {"file_path": ".claude/hooks"}),  # Directory
        ("Write", {"file_path": "scratch/test.txt"}),  # No read first
        ("Edit", {"file_path": "nonexistent.py"}),  # File doesn't exist
    ]

    print("🧪 File Operation Validator Tests\n")

    for tool_name, params in test_cases:
        is_valid, error = validate_tool_operation(tool_name, params, validator)
        status = "✅ PASS" if not is_valid else "❌ FAIL (should have caught)"
        print(f"{status}: {tool_name}({params})")
        if error:
            print(f"   Error: {error}\n")
