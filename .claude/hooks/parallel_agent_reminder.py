#!/usr/bin/env python3
"""
Parallel Agent Reminder Hook

Fires on PreToolUse:Task to remind Claude about parallel agent invocation.
"""
import os
import sys
import json

# Read stdin (tool parameters)
stdin_data = sys.stdin.read()

try:
    tool_data = json.loads(stdin_data)
except json.JSONDecodeError:
    # Not JSON, pass through
    sys.exit(0)

# Check if this is a Task call
if os.getenv("CLAUDE_TOOL_NAME") == "Task":
    # Reminder to use parallel agents
    print("⚡ REMINDER: If delegating to multiple agents, use PARALLEL invocation")
    print("   (Single message, multiple <invoke> blocks)")
    print()

sys.exit(0)
