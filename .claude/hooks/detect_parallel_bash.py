#!/usr/bin/env python3
"""
Parallel Bash Detector (PreToolUse:Bash)

Detects when multiple Bash calls are being made in same response.
Suggests running all in background for parallelism.

LOGIC:
- Track Bash calls per turn
- If 2+ Bash calls detected → suggest all run in background
- Reset counter on new turn
"""

import sys
import json
import os
from pathlib import Path

# Environment
PROJECT_DIR = os.getenv("CLAUDE_PROJECT_DIR", os.getcwd())
SESSION_ID = os.getenv("CLAUDE_SESSION_ID", "unknown")
TURN_NUMBER = int(os.getenv("CLAUDE_TURN_NUMBER", "0"))

# State file
STATE_FILE = Path(PROJECT_DIR) / ".claude" / "memory" / f"session_{SESSION_ID}_state.json"


def load_state():
    """Load session state"""
    if not STATE_FILE.exists():
        return {}

    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    """Save session state"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def main():
    """Main detection logic"""
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    # Load state
    state = load_state()

    # Initialize bash call tracking
    if "bash_calls" not in state:
        state["bash_calls"] = []

    # Record this Bash call
    state["bash_calls"].append({
        "turn": TURN_NUMBER,
        "timestamp": __import__('time').time()
    })

    # Keep only current turn
    state["bash_calls"] = [
        call for call in state["bash_calls"]
        if call["turn"] == TURN_NUMBER
    ]

    # Count Bash calls in current turn
    bash_count = len(state["bash_calls"])

    # Save state
    save_state(state)

    # Suggest parallelism if 2+ Bash calls
    if bash_count >= 2:
        # Check if already using background
        tool_params = data.get("parameters", {})
        already_background = tool_params.get("run_in_background", False)

        if not already_background:
            message = f"""
⚡ MULTIPLE BASH OPERATIONS DETECTED ({bash_count} calls this turn)

You're executing {bash_count} Bash commands in this response.

RECOMMENDATION: Use run_in_background=true for ALL

Pattern (Single Response):
  <invoke name="Bash">
    <parameter name="command">pytest tests/</parameter>
    <parameter name="run_in_background">true</parameter>
  </invoke>
  <invoke name="Bash">
    <parameter name="command">npm run lint</parameter>
    <parameter name="run_in_background">true</parameter>
  </invoke>
  <invoke name="Bash">
    <parameter name="command">mypy src/</parameter>
    <parameter name="run_in_background">true</parameter>
  </invoke>

Later (collect results):
  BashOutput(bash_id="test_shell")
  BashOutput(bash_id="lint_shell")
  BashOutput(bash_id="mypy_shell")

Benefits:
  • {bash_count}x speedup (parallel execution)
  • Zero blocking time
  • Results available on demand

Note: Only use if operations are INDEPENDENT.
"""

            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": message
                }
            }

            print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
