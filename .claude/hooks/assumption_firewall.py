#!/usr/bin/env python3
"""
ASSUMPTION FIREWALL - PreToolUse Hook

PREVENTS: Implementing solutions that contradict user-provided examples

DETECTION:
- User provides working code/commands (curl, code snippets)
- Claude researches alternatives
- Claude attempts to implement different approach
- BLOCK: "Test user's example first"

PHILOSOPHY: User input = ground truth. Research = context. Never override user examples.
"""
import sys
import json
import re

def extract_user_examples(history):
    """Extract code examples from user messages"""
    examples = []

    for msg in history:
        if msg.get("role") != "user":
            continue

        content = msg.get("content", "")

        # Extract curl commands
        curl_matches = re.findall(r'curl\s+[^\n]+', content, re.IGNORECASE)
        examples.extend([("curl", cmd.strip()) for cmd in curl_matches])

        # Extract code blocks (```...```)
        code_blocks = re.findall(r'```[\w]*\n(.*?)```', content, re.DOTALL)
        examples.extend([("code", block.strip()) for block in code_blocks])

        # Extract inline commands (backticks with http/command indicators)
        inline_cmds = re.findall(r'`([^`]+(?:http|\.py|\.sh|npm|pip|cargo)[^`]*)`', content)
        examples.extend([("inline", cmd.strip()) for cmd in inline_cmds])

    return examples

def check_implementation_divergence(user_examples, tool_name, params):
    """Check if implementation diverges from user examples"""

    # Only check Write/Edit operations (actual implementations)
    if tool_name not in ["Write", "Edit"]:
        return None

    file_path = params.get("file_path", "")
    content = params.get("content", params.get("new_string", ""))

    # Skip non-production code
    if "scratch/" in file_path or "test_" in file_path:
        return None

    if not user_examples:
        return None

    # Check for divergence signals
    divergences = []

    for ex_type, example in user_examples:
        # If user provided curl with specific URL pattern
        if ex_type == "curl" and "context7.com/api/v1" in example:
            # Check if implementation uses different URL
            if "context7.com/api/v1" not in content and "mcp" in content.lower():
                divergences.append({
                    "type": "url_mismatch",
                    "user_example": example,
                    "reason": "User provided REST API curl, implementation uses MCP protocol"
                })

        # If user provided specific endpoint
        if "api/v1/" in example:
            # Extract endpoint from user example
            endpoint_match = re.search(r'(https?://[^\s"]+)', example)
            if endpoint_match:
                user_endpoint = endpoint_match.group(1)
                # Check if implementation has different base URL
                impl_endpoints = re.findall(r'(https?://[^\s"\']+)', content)
                if impl_endpoints and not any(user_endpoint.split('/')[2] in impl for impl in impl_endpoints):
                    divergences.append({
                        "type": "endpoint_mismatch",
                        "user_example": user_endpoint,
                        "impl_endpoints": impl_endpoints,
                        "reason": "Implementation uses different base URL than user example"
                    })

    return divergences if divergences else None

def check_sudo_in_transcript(data: dict) -> bool:
    """Check if SUDO keyword is in recent transcript messages."""
    transcript_path = data.get("transcript_path", "")
    if not transcript_path:
        return False
    try:
        import os
        if os.path.exists(transcript_path):
            with open(transcript_path, 'r') as tf:
                transcript = tf.read()
                last_chunk = transcript[-5000:] if len(transcript) > 5000 else transcript
                return "SUDO" in last_chunk
    except Exception:
        pass
    return False


def main():
    # Read hook input from stdin
    hook_input = json.load(sys.stdin)

    # SUDO escape hatch
    if check_sudo_in_transcript(hook_input):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": "⚠️ SUDO bypass - assumption firewall check skipped"
            }
        }))
        return 0

    tool_name = hook_input.get("tool_name")
    tool_params = hook_input.get("tool_input", {})
    history = hook_input.get("conversationHistory", [])

    # Extract user examples from conversation
    user_examples = extract_user_examples(history)

    # Check for divergence
    divergences = check_implementation_divergence(user_examples, tool_name, tool_params)

    if divergences:
        # Build warning message
        warnings = []
        for div in divergences:
            warnings.append(f"  • {div['reason']}")
            warnings.append(f"    User provided: {div.get('user_example', 'N/A')[:100]}")

        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "⚠️ ASSUMPTION FIREWALL VIOLATION\n\n"
                    "You are implementing a solution that CONTRADICTS user-provided examples.\n\n"
                    "RULE: User examples = ground truth. Test them FIRST.\n\n"
                    "Violations detected:\n" + "\n".join(warnings) + "\n\n"
                    "REQUIRED ACTION:\n"
                    "1. Test user's example with verify.py command_success\n"
                    "2. If it works → use that approach\n"
                    "3. If it fails → THEN research alternatives\n"
                    "4. If conflict → ASK USER which is correct\n\n"
                    "See scratch/assumption_failure_analysis.md for details."
                )
            }
        }
    else:
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "No assumption violations detected"
            }
        }

    print(json.dumps(result))
    return 0

if __name__ == "__main__":
    sys.exit(main())
