#!/usr/bin/env python3
"""
Performance Reward Hook: Detects and rewards parallel execution patterns
Triggers on: PostToolUse
"""
import sys
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import load_session_state, apply_reward

def validate_file_path(file_path: str) -> bool:
    """
    Validate file path to prevent path traversal attacks.
    Per official docs: "Block path traversal - Check for .. in file paths"
    """
    if not file_path:
        return True

    # Normalize path to resolve any . or .. components
    normalized = str(Path(file_path).resolve())

    # Check for path traversal attempts
    if '..' in file_path:
        return False

    return True


try:



    input_data = json.load(sys.stdin)



except json.JSONDecodeError as e:



    # Per official docs: "Validate and sanitize inputs"



    print(f"Error: Invalid JSON input: {e}", file=sys.stderr)



    sys.exit(1)
session_id = input_data.get("sessionId", "unknown")
tool_name = input_data.get("toolName", "")
tool_params = input_data.get("toolParams", {})
conversation_history = input_data.get("conversationHistory", [])

# Detect performance optimizations
reward_type = None
reward_message = ""

# Pattern 1: Script using parallel.py
if tool_name == "Write":
    file_path = tool_params.get("file_path", "")
    content = tool_params.get("content", "")
    
    if "from lib.parallel import" in content or "from scripts.lib.parallel import" in content:
        reward_type = "use_parallel_py"
        reward_message = "🚀 PERFORMANCE OPTIMIZATION: Used parallel.py (+25%)"

    elif file_path.startswith("/home/") and "/scratch/" in file_path and len(content.split('\n')) > 20:
        # Wrote substantial script instead of manual work
        reward_type = "write_batch_script"
        reward_message = "🚀 AUTOMATION: Wrote script instead of manual work (+20%)"

# Pattern 2: Parallel tool calls (check last message)
if conversation_history:
    last_msg = conversation_history[-1]
    if last_msg.get("role") == "assistant":
        tool_uses = last_msg.get("tool_uses", [])
        if len(tool_uses) >= 3:
            # Same tool type called multiple times in one message = parallel
            tool_types = [use.get("toolName") for use in tool_uses]
            if len(set(tool_types)) == 1 and tool_types[0] in ["Read", "Grep", "Glob"]:
                reward_type = "parallel_tool_calls"
                reward_message = f"🚀 PARALLEL EXECUTION: {len(tool_uses)}x {tool_types[0]} in parallel (+15%)"

# Pattern 3: Parallel agent delegation
if tool_name == "Task":
    if conversation_history:
        last_msg = conversation_history[-1]
        if last_msg.get("role") == "assistant":
            task_count = sum(1 for use in last_msg.get("tool_uses", []) if use.get("toolName") == "Task")
            if task_count >= 2:
                reward_type = "parallel_agent_delegation"
                reward_message = f"🚀 PARALLEL AGENTS: {task_count} agents delegated in parallel (+15%)\n💡 Agent context is FREE - each runs in separate context window!"
            elif task_count == 1:
                # Even single agent delegation for large research is good (free context)
                tool_params_check = tool_params.get("description", "")
                if any(keyword in tool_params_check.lower() for keyword in ["analyze", "research", "investigate", "review"]):
                    reward_type = "parallel_agent_delegation"
                    reward_message = f"🚀 AGENT CONTEXT USAGE: Offloaded work to agent (free context isolation) (+10%)"

# Apply reward if detected
if reward_type:
    state = load_session_state(session_id)
    turn = state.get("turn_count", 0) if state else 0
    
    new_confidence = apply_reward(
        session_id=session_id,
        reward_type=reward_type,
        turn=turn,
        reason=reward_message
    )
    
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": reward_message
        }
    }))
else:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ""
        }
    }))
