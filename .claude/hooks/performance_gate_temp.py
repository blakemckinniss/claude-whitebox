#!/usr/bin/env python3
"""
Performance Gate Hook: Blocks sequential when parallel possible
Triggers on: PreToolUse
"""
import sys
import json

# Load input
input_data = json.load(sys.stdin)
tool_name = input_data.get('toolName', '')
tool_params = input_data.get('toolParams', {})

# For now, just allow (implementation coming)
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'allow'
    }
}))
