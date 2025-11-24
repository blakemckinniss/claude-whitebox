#!/usr/bin/env python3
"""
Fix memory leaks in hooks - add rotation/cleanup to unbounded state files
"""
from pathlib import Path
import json

# 1. Fix performance_telemetry_collector.py - add log rotation
telemetry_hook = Path(".claude/hooks/performance_telemetry_collector.py")

new_telemetry_code = '''#!/usr/bin/env python3
"""
Performance Telemetry Collector (PostToolUse)
Silently logs hook execution times to structured JSONL file
WITH ROTATION: Keeps last 10,000 lines max
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
    # Append entry
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry) + "\\n")

    # Rotate if >10k lines (every 100th write to avoid overhead)
    import random
    if random.randint(1, 100) == 1:  # 1% sampling
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()

        if len(lines) > 10000:
            # Keep last 5000 lines
            with open(LOG_FILE, 'w') as f:
                f.writelines(lines[-5000:])
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
'''

print("🔧 Fixing memory leaks in hooks...")
print()

# Write fixed version
with open(telemetry_hook, 'w') as f:
    f.write(new_telemetry_code)

print(f"✅ Fixed: {telemetry_hook}")
print("   - Added rotation: keeps last 5,000 lines (triggers at 10,000)")
print()

# 2. Immediately rotate the existing files
print("🗑️  Rotating existing log files...")

# Rotate performance_telemetry.jsonl
telemetry_file = Path(".claude/memory/performance_telemetry.jsonl")
if telemetry_file.exists():
    with open(telemetry_file, 'r') as f:
        lines = f.readlines()

    original_size = len(lines)
    with open(telemetry_file, 'w') as f:
        f.writelines(lines[-5000:])  # Keep last 5000

    print(f"   {telemetry_file}: {original_size:,} → 5,000 lines")

# Rotate upkeep_log.md
upkeep_file = Path(".claude/memory/upkeep_log.md")
if upkeep_file.exists():
    with open(upkeep_file, 'r') as f:
        lines = f.readlines()

    original_size = len(lines)
    with open(upkeep_file, 'w') as f:
        f.writelines(lines[-1000:])  # Keep last 1000 lines

    print(f"   {upkeep_file}: {original_size:,} → 1,000 lines")

print()
print("✅ Memory leaks fixed!")
print()
print("Summary:")
print("  - performance_telemetry.jsonl now rotates at 10k lines")
print("  - Existing logs truncated to safe size")
