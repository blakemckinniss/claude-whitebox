#!/usr/bin/env python3
"""Test auto_remember.py with actual transcript."""
import json
import subprocess

# Prepare test input with actual transcript path
test_input = {
    "session_id": "test123",
    "transcript_path": "/home/jinx/.claude/projects/-home-jinx-workspace-claude-whitebox/ee8bd3f4-aaba-4255-bf2a-da3ccae0defd.jsonl",
    "cwd": "/home/jinx/workspace/claude-whitebox",
    "permission_mode": "default",
    "hook_event_name": "Stop",
    "stop_hook_active": False
}

# Run the hook
result = subprocess.run(
    ["python3", ".claude/hooks/auto_remember.py"],
    input=json.dumps(test_input),
    capture_output=True,
    text=True,
    cwd="/home/jinx/workspace/claude-whitebox"
)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nExit code: {result.returncode}")
