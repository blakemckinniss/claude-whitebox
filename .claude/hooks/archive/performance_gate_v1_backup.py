#!/usr/bin/env python3
"""
Performance Gate Hook: META-COGNITION for parallel execution
Triggers on: PreToolUse
"""
import sys, json

input_data = json.load(sys.stdin)
tool = input_data.get("tool_name", '')
params = input_data.get("tool_input", {})

# Quick pattern detection for demo
block = False
message = ""

# Pattern 1: Bash loops
if tool == "Bash":
    cmd = params.get('command', '')
    if any(p in cmd for p in ['for ', 'while ', 'seq ']):
        if any(ext in cmd for ext in ['.txt', '.py', '.js', '.json', '.md']):
            block = True
            message = """🚫 PERFORMANCE GATE: Bash loop on files detected

REQUIRED: Use parallel.py instead

from scripts.lib.parallel import run_parallel
files = list(Path(".").glob("pattern"))
results = run_parallel(func, files, max_workers=50)

PENALTY: -20% confidence"""

# For now, just warn (not block) to test
if block:
    print(json.dumps({
        'hookSpecificOutput': {
            'hookEventName': 'PreToolUse',
            'permissionDecision': 'allow',  # Change to 'deny' when ready
            'additionalContext': message
        }
    }))
else:
    print(json.dumps({
        'hookSpecificOutput': {
            'hookEventName': 'PreToolUse',
            'permissionDecision': 'allow'
        }
    }))
