#!/usr/bin/env python3
"""
Reward Detection Hook: Applies positive reinforcement for good practices
Detects: Agent usage, protocol execution, verification
"""
import sys
import json
import subprocess
from pathlib import Path

CONFIDENCE_CMD = Path(__file__).resolve().parent.parent.parent / "scripts" / "ops" / "confidence.py"

def apply_reward(action_key, reason):
    """Apply confidence reward"""
    try:
        subprocess.run(
            ["python3", str(CONFIDENCE_CMD), "gain", action_key, reason],
            capture_output=True,
            timeout=5
        )
    except:
        pass  # Silent failure

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ""
        }
    }))
    sys.exit(0)

tool_name = input_data.get("toolName", "")
tool_params = input_data.get("toolParams", {})

# Detect Read operations
if tool_name == "Read":
    file_path = tool_params.get("file_path", "")
    if file_path:
        apply_reward("read_file", f"Read {Path(file_path).name}")

# Detect Bash commands (protocol execution)
if tool_name == "Bash":
    command = tool_params.get("command", "")

    # Detect protocol scripts
    if "scripts/ops/verify.py" in command:
        apply_reward("verify", "Ran verification")
    elif "scripts/ops/audit.py" in command:
        apply_reward("run_audit", "Ran audit.py")
    elif "scripts/ops/void.py" in command:
        apply_reward("run_void", "Ran void.py")
    elif "scripts/ops/drift_check.py" in command:
        apply_reward("run_drift", "Ran drift_check.py")
    elif "scripts/ops/research.py" in command:
        apply_reward("research_manual", "Used research.py")
    elif "scripts/ops/probe.py" in command:
        apply_reward("probe", "Used probe.py")
    elif "scripts/ops/council.py" in command:
        apply_reward("use_council", "Consulted council")
    elif "scripts/ops/critic.py" in command:
        apply_reward("use_critic", "Consulted critic")
    elif "pytest" in command or "python -m pytest" in command:
        apply_reward("run_tests", "Ran test suite")

# Detect Task tool (agent delegation)
if tool_name == "Task":
    subagent_type = tool_params.get("subagent_type", "")

    if subagent_type == "researcher":
        apply_reward("use_researcher", "Delegated to researcher agent")
    elif subagent_type == "script-smith":
        apply_reward("use_script_smith", "Delegated to script-smith agent")
    elif subagent_type == "sherlock":
        apply_reward("use_sherlock", "Delegated to sherlock agent")

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": ""
    }
}))
sys.exit(0)
