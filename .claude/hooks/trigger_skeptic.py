#!/usr/bin/env python3
"""
Trigger Skeptic Hook: Warns when risky/destructive operations are about to be performed
"""
import sys
import json

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
    # If can't parse input, allow the operation
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

tool_name = input_data.get("toolName", "")
tool_params = input_data.get("toolParams", {})

# Define risky tools and keywords
risky_tools = ["Bash", "Write", "Edit"]
risky_keywords = [
    # Destructive operations
    "rm -rf",
    "delete",
    "drop table",
    "truncate",
    "purge",
    # Data migrations
    "migration",
    "migrate",
    "alter table",
    "schema change",
    # Large refactors
    "rewrite",
    "refactor",
    "restructure",
    "rearchitect",
    # System changes
    "chmod",
    "chown",
    "sudo",
    "systemctl",
    # Database operations
    "delete from",
    "drop database",
    "drop schema",
]

# Extract command/content based on tool
command = ""
if tool_name == "Bash":
    command = tool_params.get("command", "")
elif tool_name == "Write":
    command = tool_params.get("content", "")
    file_path = tool_params.get("file_path", "")
    # Check if writing to critical files
    critical_files = [".env", "requirements.txt", "package.json", "CLAUDE.md"]
    if any(critical in file_path for critical in critical_files):
        command += " CRITICAL_FILE"
elif tool_name == "Edit":
    command = tool_params.get("new_string", "")
    old_string = tool_params.get("old_string", "")
    # Large edits are risky
    if len(old_string) > 500 or len(command) > 500:
        command += " LARGE_EDIT"

# Check for risky patterns
is_risky = any(keyword in command.lower() for keyword in risky_keywords)

if tool_name in risky_tools and is_risky:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": (
                        "\n⚠️  RISK DETECTED: You are about to perform a potentially destructive or complex operation.\n\n"
                        "🧠 CARTESIAN PROTOCOL - META-COGNITION CHECK:\n"
                        '   1. Have you run `python3 scripts/ops/think.py "<problem>"` to decompose this task?\n'
                        '   2. Have you run `python3 scripts/ops/skeptic.py "<plan>"` to check for logical fallacies?\n\n'
                        "Common pitfalls:\n"
                        "   - XY Problem: Solving a symptom instead of the root cause\n"
                        "   - Sunk Cost Fallacy: Patching bad code instead of rewriting\n"
                        "   - Premature Optimization: Building complexity without measuring\n"
                        "   - Data Loss: Not considering failure modes mid-operation\n\n"
                        "If you haven't run The Skeptic, PAUSE and do it now.\n"
                        "Better to catch logical errors BEFORE execution than debug failures AFTER.\n"
                    ),
                }
            }
        )
    )
    sys.exit(0)

# No warning needed
print(
    json.dumps(
        {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": ""}}
    )
)
sys.exit(0)
