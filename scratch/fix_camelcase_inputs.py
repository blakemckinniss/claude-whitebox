#!/usr/bin/env python3
"""
Batch fix: Convert camelCase input field names to snake_case per official spec.

Official spec uses snake_case:
- tool_name (not toolName)
- tool_input (not toolInput, toolParams)
- session_id (not sessionId)
- tool_response (not toolResponse)
- tool_use_id (not toolUseId)
"""
import re
from pathlib import Path

HOOKS_DIR = Path("/home/jinx/workspace/claude-whitebox/.claude/hooks")

# Replacements: (pattern, replacement)
REPLACEMENTS = [
    # .get() calls
    (r'\.get\(["\']toolName["\']', '.get("tool_name"'),
    (r'\.get\(["\']toolInput["\']', '.get("tool_input"'),
    (r'\.get\(["\']toolParams["\']', '.get("tool_input"'),
    (r'\.get\(["\']sessionId["\']', '.get("session_id"'),
    (r'\.get\(["\']toolResponse["\']', '.get("tool_response"'),
    (r'\.get\(["\']toolUseId["\']', '.get("tool_use_id"'),
    (r'\.get\(["\']transcriptPath["\']', '.get("transcript_path"'),
    (r'\.get\(["\']permissionMode["\']', '.get("permission_mode"'),
    (r'\.get\(["\']userPrompt["\']', '.get("prompt"'),

    # Direct dict access with brackets
    (r'\[(["\'])toolName\1\]', '["tool_name"]'),
    (r'\[(["\'])toolInput\1\]', '["tool_input"]'),
    (r'\[(["\'])toolParams\1\]', '["tool_input"]'),
    (r'\[(["\'])sessionId\1\]', '["session_id"]'),
    (r'\[(["\'])toolResponse\1\]', '["tool_response"]'),
    (r'\[(["\'])toolUseId\1\]', '["tool_use_id"]'),
    (r'\[(["\'])transcriptPath\1\]', '["transcript_path"]'),
    (r'\[(["\'])permissionMode\1\]', '["permission_mode"]'),
]

def fix_file(filepath: Path) -> tuple[bool, list[str]]:
    """Fix camelCase to snake_case in a hook file. Returns (modified, changes)."""
    content = filepath.read_text()
    original = content
    changes = []

    for pattern, replacement in REPLACEMENTS:
        matches = re.findall(pattern, content)
        if matches:
            content = re.sub(pattern, replacement, content)
            changes.append(f"  {pattern} → {replacement}")

    if content != original:
        filepath.write_text(content)
        return True, changes
    return False, []

def main():
    fixed_count = 0

    for hook_file in sorted(HOOKS_DIR.glob("*.py")):
        if hook_file.name.startswith("_"):
            continue

        modified, changes = fix_file(hook_file)
        if modified:
            print(f"✅ Fixed {hook_file.name}:")
            for change in changes:
                print(change)
            fixed_count += 1

    print(f"\n📊 Fixed {fixed_count} files")

if __name__ == "__main__":
    main()
