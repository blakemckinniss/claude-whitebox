#!/usr/bin/env python3
"""
Performance Telemetry Collector (PostToolUse)
Silently logs hook execution times to structured JSONL file
WITH ROTATION: Keeps last 10,000 lines max
"""
import sys
import json
import time
import subprocess
from pathlib import Path

# Load input
try:
    input_data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

# Extract data (Claude hooks use camelCase keys)
tool_name = input_data.get("toolName", "unknown")
session_id = input_data.get("sessionId", "unknown")

# Log file
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

LOG_FILE = PROJECT_DIR / ".claude" / "memory" / "performance_telemetry.jsonl"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Simple metric: tool execution
entry = {
    "timestamp": time.time(),
    "session_id": session_id,
    "tool": tool_name,
    "event": "tool_use"
}

try:
    # Append entry
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry) + "\n")

    # Rotate if >10k lines (1% sampling to avoid overhead)
    import random
    import os
    if random.randint(1, 100) == 1:
        line_count = int(subprocess.check_output(['wc', '-l', str(LOG_FILE)]).split()[0], timeout=30)

        if line_count > 10000:
            # Use tail to keep last 5000 lines (memory efficient)
            subprocess.run(['tail', '-n', '5000', str(LOG_FILE)], stdout=open(str(LOG_FILE) + '.tmp', 'w'), timeout=30)
            os.replace(str(LOG_FILE) + '.tmp', str(LOG_FILE))
except Exception:
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
