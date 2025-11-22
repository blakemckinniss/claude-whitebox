#!/usr/bin/env python3
"""
Auto Remember Hook: Automatically executes memory triggers from Stop messages

Extracts "Memory Trigger: remember.py add ..." commands from the last assistant
response and executes them automatically to persist lessons/decisions/context.
"""
import sys
import json
import subprocess
import re


def parse_transcript(transcript_path: str) -> list[dict]:
    """Parse JSONL transcript file."""
    messages = []
    try:
        with open(transcript_path, "r") as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []
    return messages


def get_last_assistant_message(messages: list[dict]) -> str:
    """Get the last assistant message content from transcript."""
    for entry in reversed(messages):
        # Transcript format: {"type": "assistant", "message": {"content": [...]}}
        if entry.get("type") == "assistant":
            message = entry.get("message", {})
            content = message.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        return block.get("text", "")
            elif isinstance(content, str):
                return content
    return ""


def extract_memory_triggers(text: str) -> list[str]:
    """
    Extract remember.py commands from Memory Trigger suggestions.

    Matches patterns like:
    - **Memory Trigger:** `remember.py add lessons "..."`
    - *Memory Trigger:* remember.py add decisions "..."
    - 🐘 Memory Trigger: `remember.py add context "..."`
    """
    # Pattern that handles markdown formatting (**, *, emojis) between "Memory Trigger" and the command
    # Matches: Memory Trigger [anything] `remember.py add TYPE "text"`
    pattern = r'Memory Trigger.*?`(remember\.py add \w+ ".*?")`'

    commands = []
    matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    for match in matches:
        command = match.group(1)
        if command not in commands:  # Dedup
            commands.append(command)

    return commands


def execute_remember_command(command: str, project_dir: str) -> bool:
    """Execute a remember.py command. Returns True if successful."""
    try:
        # Parse the command to extract arguments
        # Format: remember.py add TYPE "text"
        parts = command.split(
            None, 2
        )  # Split into ['remember.py', 'add', 'TYPE "text"']
        if len(parts) < 3 or parts[1] != "add":
            return False

        # Extract type and text
        remainder = parts[2]
        type_match = re.match(r'(\w+)\s+"(.+)"', remainder, re.DOTALL)
        if not type_match:
            return False

        memory_type = type_match.group(1)
        text = type_match.group(2)

        # Execute remember.py
        result = subprocess.run(
            [
                "python3",
                f"{project_dir}/scripts/ops/remember.py",
                "add",
                memory_type,
                text,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_dir,
        )

        return result.returncode == 0

    except Exception as e:
        print(f"Error executing remember command: {e}", file=sys.stderr)
        return False


def main():
    """Main hook execution."""
    # Load input
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Invalid input, exit silently
        sys.exit(0)

    # Get transcript path and project directory
    transcript_path = input_data.get("transcript_path", "")
    project_dir = input_data.get("cwd", "")

    if not transcript_path or not project_dir:
        # Missing required fields, exit silently
        sys.exit(0)

    # Check if stop hook is already active to prevent loops
    if input_data.get("stop_hook_active", False):
        # Already running due to a stop hook, don't run again
        sys.exit(0)

    # Parse transcript and get last assistant message
    messages = parse_transcript(transcript_path)
    last_message = get_last_assistant_message(messages)

    if not last_message:
        # No assistant message found
        sys.exit(0)

    # Extract memory triggers
    commands = extract_memory_triggers(last_message)

    if not commands:
        # No memory triggers found
        sys.exit(0)

    # Execute each command
    executed = []
    failed = []

    for command in commands:
        if execute_remember_command(command, project_dir):
            executed.append(command)
        else:
            failed.append(command)

    # Report results to user (stdout shown in verbose mode)
    if executed:
        print("📝 Auto-executed memory triggers:")
        for cmd in executed:
            print(f"  ✅ {cmd}")

    if failed:
        print("⚠️  Failed to execute:", file=sys.stderr)
        for cmd in failed:
            print(f"  ❌ {cmd}", file=sys.stderr)

    # Exit with success - don't block Stop
    sys.exit(0)


if __name__ == "__main__":
    main()
