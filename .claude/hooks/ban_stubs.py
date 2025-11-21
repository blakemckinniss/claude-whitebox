#!/usr/bin/env python3
"""
Ban Stubs Hook: Prevents Write operations containing stub code
Blocks: TODO, FIXME, pass, ..., NotImplementedError
"""
import sys
import json
import re

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    # If parsing fails, allow the operation
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "action": "allow"
        }
    }))
    sys.exit(0)

tool_name = input_data.get("toolName", "")
tool_params = input_data.get("toolParams", {})

# Only intercept Write operations
if tool_name != "Write":
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "action": "allow"
        }
    }))
    sys.exit(0)

# Get the content being written
content = tool_params.get("content", "")

if not content:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "action": "allow"
        }
    }))
    sys.exit(0)

# Stub patterns (same as void.py)
STUB_PATTERNS = [
    (r'#\s*TODO:', 'TODO comment'),
    (r'#\s*FIXME:', 'FIXME comment'),
    (r'def\s+\w+\([^)]*\):\s*pass\s*$', 'Function stub (pass)'),
    (r'def\s+\w+\([^)]*\):\s*\.\.\.\s*$', 'Function stub (...)'),
    (r'raise\s+NotImplementedError', 'NotImplementedError'),
]

# Scan content for stubs
stubs_found = []
for line_num, line in enumerate(content.split('\n'), 1):
    for pattern, description in STUB_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            stubs_found.append({
                'line': line_num,
                'type': description,
                'content': line.strip()
            })

# If stubs detected, block the operation
if stubs_found:
    stub_details = "\n".join([
        f"    Line {s['line']}: {s['type']}\n      → {s['content']}"
        for s in stubs_found[:5]  # Show first 5
    ])

    if len(stubs_found) > 5:
        stub_details += f"\n    ... and {len(stubs_found) - 5} more"

    additional_context = f"""
🚨 STUB CODE DETECTED - WRITE BLOCKED

The Void Hunter has detected {len(stubs_found)} stub(s) in the code you're trying to write:

{stub_details}

⚠️ COMPLETENESS PROTOCOL VIOLATION:

You are attempting to write INCOMPLETE CODE to the filesystem.

FORBIDDEN PATTERNS:
  • # TODO: - Unfinished work markers
  • # FIXME: - Known broken code
  • def function(): pass - Empty function stubs
  • def function(): ... - Ellipsis stubs
  • raise NotImplementedError - Placeholder implementations

REQUIRED ACTIONS:
  1. FINISH THE IMPLEMENTATION before writing to disk
  2. Replace stubs with actual logic
  3. If the function is intentionally empty, document WHY in a docstring

The filesystem is not a notebook. Only write COMPLETE, FUNCTIONAL code.

To override this check (NOT recommended), remove the stub patterns from your code.
"""

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "action": "deny",
            "denyReason": additional_context
        }
    }))
    sys.exit(0)

# No stubs detected, allow the operation
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "action": "allow"
    }
}))
sys.exit(0)
