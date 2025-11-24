#!/usr/bin/env python3
"""
Native Tool Batching Enforcer (PreToolUse Hook)

Detects when Claude is about to execute sequential Read/Grep/Glob operations
and blocks the action if batching is possible.

GOAL: Enforce parallel tool invocation for common operations.

STRATEGY:
1. Track tool usage patterns in session state
2. Detect when same tool is being called multiple times sequentially
3. Block and suggest parallel invocation pattern
4. Allow bypass for legitimate sequential needs (dependency chains)

ENFORCEMENT RULES:
- Read: If >1 Read in single response and files are independent → BLOCK
- Grep: If >1 Grep with different patterns/paths → SUGGEST parallel
- Glob: If >1 Glob with different patterns → SUGGEST parallel
- WebFetch/WebSearch: If >1 web operation → BLOCK (batch into single call)
"""

import sys
import json
import os
from pathlib import Path

# Environment
PROJECT_DIR = os.getenv("CLAUDE_PROJECT_DIR", os.getcwd())
SESSION_ID = os.getenv("CLAUDE_SESSION_ID", "unknown")
TURN_NUMBER = int(os.getenv("CLAUDE_TURN_NUMBER", "0"))
TOOL_NAME = os.getenv("CLAUDE_TOOL_NAME", "")

# State file
STATE_FILE = Path(PROJECT_DIR) / ".claude" / "memory" / f"session_{SESSION_ID}_state.json"

# Tools to track
BATCHABLE_TOOLS = ["Read", "Grep", "Glob", "WebFetch", "WebSearch"]


def load_state():
    """Load session state"""
    if not STATE_FILE.exists():
        return {}

    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {}


def save_state(state):
    """Save session state"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except:
        pass


def get_tool_calls_in_turn(state, turn):
    """Get all tool calls in a specific turn"""
    if "tool_calls" not in state:
        state["tool_calls"] = []

    return [
        call for call in state["tool_calls"]
        if call["turn"] == turn
    ]


def record_tool_call(state, tool_name, turn):
    """Record a tool call"""
    if "tool_calls" not in state:
        state["tool_calls"] = []

    state["tool_calls"].append({
        "tool": tool_name,
        "turn": turn,
        "timestamp": __import__('time').time()
    })

    # Keep only last 10 turns
    min_turn = turn - 10
    state["tool_calls"] = [
        call for call in state["tool_calls"]
        if call["turn"] >= min_turn
    ]


def analyze_batching_opportunity(state, current_tool, current_turn):
    """
    Analyze if current tool call should be batched.

    Returns: (should_block: bool, suggestion: str)
    """
    current_turn_calls = get_tool_calls_in_turn(state, current_turn)

    # Count how many times this tool has been called in current turn
    same_tool_count = sum(1 for call in current_turn_calls if call["tool"] == current_tool)

    # RULE 1: Multiple Read calls in same turn
    if current_tool == "Read" and same_tool_count >= 1:
        return (
            True,
            f"""
🚫 SEQUENTIAL READ DETECTED

You are calling Read tool {same_tool_count + 1} times in this turn.

RULE: Multiple independent Read operations MUST be parallelized.

❌ FORBIDDEN (Sequential):
   Read(file1)
   [wait for response]
   Read(file2)

✅ REQUIRED (Parallel):
   Single message with:
   <invoke name="Read"><parameter name="file_path">file1</parameter></invoke>
   <invoke name="Read"><parameter name="file_path">file2</parameter></invoke>
   <invoke name="Read"><parameter name="file_path">file3</parameter></invoke>

WHY:
- Parallel reads = 10x faster
- No context pollution from waiting
- Better token efficiency

EXCEPTION: If file2 path depends on file1 contents, sequential is OK.

ACTION: Revise your response to batch all Read calls in ONE message.
"""
        )

    # RULE 2: Multiple Grep calls
    if current_tool == "Grep" and same_tool_count >= 2:
        return (
            False,  # Warning only, not hard block
            f"""
⚠️  SEQUENTIAL GREP DETECTED

You are calling Grep {same_tool_count + 1} times in this turn.

RECOMMENDATION: Batch Grep operations in parallel for better performance.

Pattern:
   <invoke name="Grep">pattern1</invoke>
   <invoke name="Grep">pattern2</invoke>
   <invoke name="Grep">pattern3</invoke>

Benefit: 3x faster execution, cleaner response.
"""
        )

    # RULE 3: Multiple web operations
    if current_tool in ["WebFetch", "WebSearch"] and same_tool_count >= 1:
        return (
            True,
            f"""
🚫 SEQUENTIAL WEB OPERATION DETECTED

You are calling {current_tool} {same_tool_count + 1} times in this turn.

RULE: Multiple web operations MUST be parallelized.

❌ FORBIDDEN (Sequential):
   WebFetch(url1)
   [wait]
   WebFetch(url2)

✅ REQUIRED (Parallel):
   Single message with multiple invocations.

WHY:
- Web I/O is SLOW (100-500ms each)
- Parallel = massive speedup
- Network latency hides in parallelism

ACTION: Batch all web operations in ONE message.
"""
        )

    # No blocking needed
    return (False, "")


def main():
    """Main enforcement logic"""

    # Only track batchable tools
    if TOOL_NAME not in BATCHABLE_TOOLS:
        sys.exit(0)

    # Load state
    state = load_state()

    # Analyze batching opportunity
    should_block, message = analyze_batching_opportunity(state, TOOL_NAME, TURN_NUMBER)

    # Record this tool call
    record_tool_call(state, TOOL_NAME, TURN_NUMBER)
    save_state(state)

    # Block if necessary
    if should_block:
        print(message, file=sys.stderr)
        sys.exit(1)

    # Show suggestion if any
    if message:
        print(message, file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
