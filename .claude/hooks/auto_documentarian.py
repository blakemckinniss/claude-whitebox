#!/usr/bin/env python3
"""
The Documentarian - Autonomous Documentation Sync (PostToolUse:Write/Edit)

Detects changes to scripts/ops/ → updates CLAUDE.md automatically.

Philosophy: Documentation never drifts from code.
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


# Find project root
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

CLAUDE_MD = PROJECT_DIR / "CLAUDE.md"
CONFIG_FILE = PROJECT_DIR / ".claude" / "memory" / "automation_config.json"


def load_config():
    """Load automation configuration"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"documentarian": {"enabled": False}}


def should_sync_docs(file_path):
    """Check if file change requires doc sync"""
    watch_paths = ["scripts/ops/", ".claude/hooks/"]
    return any(watch in file_path for watch in watch_paths)


def extract_tool_info(file_path):
    """Extract tool name and description from script"""
    try:
        with open(file_path) as f:
            content = f.read()

        # Extract from docstring
        docstring_match = re.search(r'"""\n(.*?)\n"""', content, re.DOTALL)
        if docstring_match:
            doc = docstring_match.group(1).strip()
            return {"description": doc.split("\n")[0]}

        return {"description": ""}

    except Exception:
        return {"description": ""}


def update_claude_md(tool_name, tool_path, tool_info):
    """Update CLAUDE.md with new tool (if not already there)"""
    if not CLAUDE_MD.exists():
        return False, "CLAUDE.md not found"

    content = CLAUDE_MD.read_text()

    # Check if tool already documented
    if tool_name in content:
        return True, f"{tool_name} already documented"

    # Find CLI Shortcuts section
    cli_section_match = re.search(
        r"(## ⌨️ CLI Shortcuts.*?commands:.*?)(\n\n##|$)",
        content,
        re.DOTALL
    )

    if not cli_section_match:
        return False, "CLI Shortcuts section not found"

    # Add tool to shortcuts
    shortcuts_section = cli_section_match.group(1)
    new_line = f'  {tool_name}: "python3 {tool_path}"\n'

    # Insert before next section
    updated_content = content.replace(
        shortcuts_section,
        shortcuts_section + new_line
    )

    # Write back (dry-run for now)
    # CLAUDE_MD.write_text(updated_content)

    return True, f"Would add {tool_name} to CLI Shortcuts"


def main():
    """Documentarian main logic"""
    # Load input
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    # Check if enabled
    config = load_config()
    if not config.get("documentarian", {}).get("enabled", False):
        sys.exit(0)

    # Get tool info
    tool_name = input_data.get("toolName", "")
    tool_input = input_data.get("toolInput", {})

    if tool_name not in ["Write", "Edit"]:
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    
    # Validate file path (per official docs security best practices)
    if file_path and not validate_file_path(file_path):
        print(f"Security: Path traversal detected in {file_path}", file=sys.stderr)
        sys.exit(2)

    # Check if needs doc sync
    if not should_sync_docs(file_path):
        sys.exit(0)

    # Extract tool info
    tool_info = extract_tool_info(file_path)

    # Determine tool name from path
    script_name = Path(file_path).stem

    # Update docs (dry-run)
    success, message = update_claude_md(script_name, file_path, tool_info)

    if success:
        output_message = f"""
📚 DOCUMENTARIAN: AUTO-SYNC

File: {file_path}
Action: {message}

The Documentarian is tracking this change for doc sync.
Dry-run mode: Changes not applied yet.
"""

        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": output_message
            }
        }))

    sys.exit(0)


if __name__ == "__main__":
    main()
