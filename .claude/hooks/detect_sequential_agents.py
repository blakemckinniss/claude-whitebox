#!/usr/bin/env python3
"""
Sequential Agent Detection Hook

Detects and BLOCKS sequential agent delegation patterns.
Enforces parallel agent invocation (single message, multiple Task calls).

Triggers on: PreToolUse:Task
Action: HARD BLOCK if sequential pattern detected
"""
import sys
import os
import json
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
    except:
        return {}


def save_state(state):
    """Save session state"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"⚠️  Could not save state: {e}", file=sys.stderr)


def main():
    """Detect sequential agent pattern"""
    # Load state
    state = load_state()

    # Track agent calls
    if "agent_calls" not in state:
        state["agent_calls"] = []

    # Record this agent call
    state["agent_calls"].append({
        "turn": TURN_NUMBER,
        "timestamp": __import__('time').time()
    })

    # Keep only recent calls (last 5 turns)
    state["agent_calls"] = [
        call for call in state["agent_calls"]
        if TURN_NUMBER - call["turn"] <= 5
    ]

    # Count agent calls in current turn
    current_turn_calls = [
        call for call in state["agent_calls"]
        if call["turn"] == TURN_NUMBER
    ]

    # Save state
    save_state(state)

    # Check for sequential pattern
    if len(current_turn_calls) > 1:
        # Multiple agents in same turn = GOOD (parallel)
        # This is allowed, exit success
        sys.exit(0)

    # Check if there were agent calls in previous turn
    previous_turn = TURN_NUMBER - 1
    previous_calls = [
        call for call in state["agent_calls"]
        if call["turn"] == previous_turn
    ]

    if previous_calls and len(current_turn_calls) == 1:
        # Sequential pattern detected: agent in turn N-1, another in turn N
        print()
        print("🚫 SEQUENTIAL AGENT PATTERN DETECTED")
        print()
        print("VIOLATION: You are calling agents one-by-one across multiple turns.")
        print()
        print("RULE: When delegating to 2+ agents, use PARALLEL invocation.")
        print()
        print("❌ FORBIDDEN (Sequential):")
        print("   Turn N:   <invoke Task>agent1</invoke>")
        print("   Turn N+1: <invoke Task>agent2</invoke>")
        print()
        print("✅ REQUIRED (Parallel):")
        print("   Turn N:   <invoke Task>agent1</invoke>")
        print("             <invoke Task>agent2</invoke>")
        print("             <invoke Task>agent3</invoke>")
        print()
        print("WHY: Each agent = FREE separate context. Sequential = WASTE.")
        print()
        print("ACTION: Revise your response to invoke all agents in ONE message.")
        print()

        # HARD BLOCK
        sys.exit(1)

    # No violation detected
    sys.exit(0)


if __name__ == "__main__":
    main()
