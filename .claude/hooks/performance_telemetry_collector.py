#!/usr/bin/env python3
"""
Performance Telemetry Collector (PostToolUse)
Silently logs hook execution times to structured JSONL file
"""
import sys
import json
import time
from pathlib import Path

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    sys.exit(0)

# Extract data
tool_name = input_data.get("tool_name", "unknown")
session_id = input_data.get("session_id", "unknown")

# Log file
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

LOG_FILE = PROJECT_DIR / ".claude" / "memory" / "performance_telemetry.jsonl"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Simple metric: tool execution (could be enhanced)
entry = {
    "timestamp": time.time(),
    "session_id": session_id,
    "tool": tool_name,
    "event": "tool_use"
}

try:
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry) + "\n")
except:
    pass

# Output required hook structure
output = {
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": ""
    }
}
print(json.dumps(output))
sys.exit(0)
