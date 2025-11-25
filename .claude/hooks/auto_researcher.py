#!/usr/bin/env python3
"""
Auto-Researcher Hook (PostToolUse)
Automatically spawns researcher agent when script outputs are large.

PURPOSE: Context firewall - prevents large documentation/API outputs from polluting main conversation

TRIGGERS:
- Bash command calls research.py/probe.py/xray.py
- Output size >1000 characters

ACTION: Suggest spawning researcher agent for compression (500 lines → 50 words)
"""

import sys
import json

def main():
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)  # Silent fail if input malformed

    tool_name = hook_input.get("tool_name", "")
    tool_params = hook_input.get("tool_input", {})
    result = hook_input.get("result", {})

    # Only process Bash tool
    if tool_name != "Bash":
        sys.exit(0)

    command = tool_params.get("command", "")
    output = result.get("output", "")
    output_size = len(output)

    # Check if command is a research/probe/xray operation
    research_commands = ["research.py", "probe.py", "xray.py", "spark.py"]
    is_research_cmd = any(cmd in command for cmd in research_commands)

    if not is_research_cmd:
        sys.exit(0)

    # Threshold for auto-invocation
    LARGE_OUTPUT_THRESHOLD = 1000

    if output_size > LARGE_OUTPUT_THRESHOLD:
        message = f"""📚 LARGE OUTPUT DETECTED ({output_size} chars)

The researcher agent provides context firewall (compresses large outputs).

RECOMMENDATION: Consider spawning researcher agent to:
  - Compress {output_size} chars → ~50 word summary
  - Extract only actionable findings
  - Prevent main context pollution

Example invocation:
  "Use researcher agent to analyze the probe.py output and extract key API signatures"

Why: Large outputs pollute main context, reducing available tokens for actual work.
See CLAUDE.md § Agent Delegation (Context Firewall)
"""

        print(json.dumps({
            "message": message,
            "severity": "info"
        }))

    sys.exit(0)

if __name__ == "__main__":
    main()
