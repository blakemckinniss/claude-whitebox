#!/usr/bin/env python3
"""
Auto Remember Hook (Debug Version): Logs all execution to debug.log
"""
import sys
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime


LOG_FILE = Path(__file__).parent.parent / "debug_auto_remember.log"


def log(message: str):
    """Log to debug file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")


def parse_transcript(transcript_path: str) -> list[dict]:
    """Parse JSONL transcript file."""
    messages = []
    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
    except FileNotFoundError:
        log(f"ERROR: Transcript not found: {transcript_path}")
        return []
    except json.JSONDecodeError as e:
        log(f"ERROR: JSON decode error: {e}")
        return []
    return messages


def get_last_assistant_message(messages: list[dict]) -> str:
    """Get the last assistant message content from transcript."""
    for entry in reversed(messages):
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
    """Extract remember.py commands from Memory Trigger suggestions."""
    pattern = r'Memory Trigger.*?`(remember\.py add \w+ ".*?")`'

    commands = []
    matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    for match in matches:
        command = match.group(1)
        if command not in commands:
            commands.append(command)

    return commands


def execute_remember_command(command: str, project_dir: str) -> bool:
    """Execute a remember.py command. Returns True if successful."""
    try:
        parts = command.split(None, 2)
        if len(parts) < 3 or parts[1] != 'add':
            log(f"ERROR: Invalid command format: {command}")
            return False

        remainder = parts[2]
        type_match = re.match(r'(\w+)\s+"(.+)"', remainder, re.DOTALL)
        if not type_match:
            log(f"ERROR: Could not parse type and text from: {remainder}")
            return False

        memory_type = type_match.group(1)
        text = type_match.group(2)

        log(f"Executing: remember.py add {memory_type} '{text[:50]}...'")

        result = subprocess.run(
            ["python3", f"{project_dir}/scripts/ops/remember.py", "add", memory_type, text],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_dir
        )

        if result.returncode == 0:
            log(f"SUCCESS: Command executed")
            return True
        else:
            log(f"ERROR: Command failed with code {result.returncode}: {result.stderr}")
            return False

    except Exception as e:
        log(f"ERROR: Exception executing command: {e}")
        return False


def main():
    """Main hook execution."""
    log("=" * 60)
    log("Hook triggered")

    # Load input
    try:
        input_data = json.load(sys.stdin)
        log(f"Input received: {json.dumps(input_data, indent=2)}")
    except json.JSONDecodeError as e:
        log(f"ERROR: Invalid JSON input: {e}")
        sys.exit(0)

    # Get required fields
    transcript_path = input_data.get("transcript_path", "")
    project_dir = input_data.get("cwd", "")

    log(f"Transcript path: {transcript_path}")
    log(f"Project dir: {project_dir}")

    if not transcript_path or not project_dir:
        log("ERROR: Missing transcript_path or cwd")
        sys.exit(0)

    # Check stop_hook_active to prevent loops
    if input_data.get("stop_hook_active", False):
        log("INFO: stop_hook_active is True, exiting to prevent loop")
        sys.exit(0)

    # Parse transcript
    log("Parsing transcript...")
    messages = parse_transcript(transcript_path)
    log(f"Found {len(messages)} messages")

    if not messages:
        log("ERROR: No messages in transcript")
        sys.exit(0)

    # Get last assistant message
    log("Extracting last assistant message...")
    last_message = get_last_assistant_message(messages)

    if not last_message:
        log("ERROR: No assistant message found")
        sys.exit(0)

    log(f"Last message length: {len(last_message)} chars")
    log(f"Last message preview: {last_message[:200]}...")

    # Extract memory triggers
    log("Extracting memory triggers...")
    commands = extract_memory_triggers(last_message)
    log(f"Found {len(commands)} memory triggers")

    for cmd in commands:
        log(f"  - {cmd}")

    if not commands:
        log("INFO: No memory triggers found")
        sys.exit(0)

    # Execute commands
    executed = []
    failed = []

    for command in commands:
        if execute_remember_command(command, project_dir):
            executed.append(command)
        else:
            failed.append(command)

    # Report results
    if executed:
        print("📝 Auto-executed memory triggers:")
        for cmd in executed:
            print(f"  ✅ {cmd}")
        log(f"Successfully executed {len(executed)} commands")

    if failed:
        print("⚠️  Failed to execute:", file=sys.stderr)
        for cmd in failed:
            print(f"  ❌ {cmd}", file=sys.stderr)
        log(f"Failed to execute {len(failed)} commands")

    log("Hook completed")
    sys.exit(0)


if __name__ == "__main__":
    main()
