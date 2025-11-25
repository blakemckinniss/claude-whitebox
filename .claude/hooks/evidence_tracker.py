#!/usr/bin/env python3
"""
Evidence Tracker Hook: Tracks tool usage and updates confidence
Triggers on: PostToolUse

Enhanced 2025-11-25: Also tracks verified_knowledge for anti-hallucination
- When research.py is run, record libraries from query as verified
- When probe.py is run, record probed module as verified
- When Read tool reads .py files, record imported libraries as verified
"""
import sys
import json
from pathlib import Path

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import (
    load_session_state,
    initialize_session_state,
    update_confidence,
    get_confidence_tier,
    record_verified_library,
    extract_libraries_from_bash_output,
    extract_libraries_from_code_read,
)

# Load input
try:
    input_data = json.load(sys.stdin)
except Exception:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

session_id = input_data.get("session_id", "unknown")
tool_name = input_data.get("tool_name", "")
tool_params = input_data.get("tool_input", {})
tool_result = input_data.get("tool_response", {})

if not tool_name:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

# Load session state
state = load_session_state(session_id)
if not state:
    state = initialize_session_state(session_id)

# Get current turn
turn = state.get("turn_count", 0)

# Update confidence based on tool usage
old_confidence = state.get("confidence", 0)
new_confidence, boost = update_confidence(
    session_id=session_id,
    tool_name=tool_name,
    tool_input=tool_params,
    turn=turn,
    reason=f"{tool_name} usage",
)

# ==============================================================================
# VERIFIED KNOWLEDGE TRACKING (Anti-Hallucination)
# ==============================================================================

verified_libs = []

# Track libraries from Bash commands (research.py, probe.py)
if tool_name == "Bash":
    command = tool_params.get("command", "")
    output = ""

    # Extract output from tool_result
    if isinstance(tool_result, dict):
        content = tool_result.get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    output += item.get("text", "")

    libs = extract_libraries_from_bash_output(command, output)
    for lib in libs:
        verification_method = "research" if "research.py" in command else "probe"
        record_verified_library(
            session_id=session_id,
            library_name=lib,
            verification_method=verification_method,
            turn=turn,
            source=command[:100],
        )
        verified_libs.append(lib)

# Track libraries from Read tool (existing code patterns)
elif tool_name == "Read":
    file_path = tool_params.get("file_path", "")
    if file_path.endswith(".py"):
        # Extract content from tool_result
        content = ""
        if isinstance(tool_result, dict):
            result_content = tool_result.get("content", [])
            if isinstance(result_content, list):
                for item in result_content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        content += item.get("text", "")

        if content:
            libs = extract_libraries_from_code_read(file_path, content)
            for lib in libs:
                record_verified_library(
                    session_id=session_id,
                    library_name=lib,
                    verification_method="read",
                    turn=turn,
                    source=file_path,
                )
                verified_libs.append(lib)

# ==============================================================================
# OUTPUT
# ==============================================================================

# Only show feedback if confidence actually changed
if boost != 0:
    tier_name, _ = get_confidence_tier(new_confidence)

    # Determine what was accessed
    target = ""
    if "file_path" in tool_params:
        target = f" ({Path(tool_params['file_path']).name})"
    elif "query" in tool_params:
        target = f" ('{tool_params['query'][:30]}...')"
    elif "command" in tool_params:
        cmd = tool_params["command"]
        if len(cmd) > 40:
            cmd = cmd[:37] + "..."
        target = f" ({cmd})"

    sign = "+" if boost > 0 else ""
    context = f"""
📈 EVIDENCE GATHERED: {tool_name}{target}
   • Confidence: {old_confidence}% → {new_confidence}% ({sign}{boost}%)
   • Current Tier: {tier_name}
"""

    # Add verified libraries info if any
    if verified_libs:
        context += f"   • Verified Libraries: {', '.join(verified_libs)}\n"

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": context,
                }
            }
        )
    )
else:
    # No confidence change, but might have verified libs
    if verified_libs:
        context = f"\n📚 LIBRARIES VERIFIED: {', '.join(verified_libs)}\n"
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": context,
                    }
                }
            )
        )
    else:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": "",
                    }
                }
            )
        )

sys.exit(0)
