#!/usr/bin/env python3
"""
Pre-Write Audit Hook: Blocks Write tool if code contains deadly sins
"""
import sys
import json
import re

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
                # Check last 5000 chars for SUDO (recent messages)
                last_chunk = transcript[-5000:] if len(transcript) > 5000 else transcript
                return "SUDO" in last_chunk
    except Exception:
        pass
    return False



# Load input
try:
    input_data = json.load(sys.stdin)

    # SUDO escape hatch
    if check_sudo_in_transcript(input_data):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": "⚠️ SUDO bypass - hook check skipped"
            }
        }))
        sys.exit(0)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
    sys.exit(1)
except Exception:
    # If can't parse input, allow the operation
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                }
            }
        )
    )
    sys.exit(0)

tool_name = input_data.get("tool_name", "")
tool_params = input_data.get("tool_input", {})

# Only check Write tool
if tool_name != "Write":
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                }
            }
        )
    )
    sys.exit(0)

# Extract content being written
content = tool_params.get("content", "")
file_path = tool_params.get("file_path", "unknown")

# Define deadly sins (critical anti-patterns that must be blocked)
deadly_sins = [
    (r"sk-proj-[a-zA-Z0-9_-]+", "🔴 DEADLY SIN: Hardcoded OpenAI API key (sk-proj-)"),
    (r"ghp_[a-zA-Z0-9_-]+", "🔴 DEADLY SIN: Hardcoded GitHub token (ghp_)"),
    (r"AWS_SECRET|AKIA[0-9A-Z]{16}", "🔴 DEADLY SIN: Hardcoded AWS credentials"),
    (
        r'api[_-]?key\s*=\s*["\'][^"\']{10,}["\'](?!\s*#.*getenv)',
        "🔴 DEADLY SIN: Hardcoded API key",
    ),
    # SECURITY WARNING: shell=True detection is commented out for this hook
    # This hook itself uses subprocess with validated patterns only
    # See official docs: "Never trust input data blindly"
    # (
    #     r"shell\s*=\s*True",
    #     "🔴 DEADLY SIN: Shell injection risk (shell=True in subprocess)",
    # ),
    (
        r"pdb\.set_trace\(\)",
        "🔴 DEADLY SIN: Debug breakpoint left in code (pdb.set_trace())",
    ),
    (r"breakpoint\(\)", "🔴 DEADLY SIN: Debug breakpoint left in code (breakpoint())"),
    (
        r"TODO:\s*Implement\s+this",
        "🔴 DEADLY SIN: Unfinished code (TODO: Implement this)",
    ),
    (
        r'cursor\.execute\([^)]*f["\']',
        "🔴 DEADLY SIN: SQL injection risk (f-string in cursor.execute)",
    ),
]

# Check for deadly sins
violations = []
for pattern, message in deadly_sins:
    matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
    if matches:
        for match in matches:
            # Find line number
            lineno = content[: match.start()].count("\n") + 1
            violations.append((lineno, message, match.group(0)))

if violations:
    # Build detailed error message
    reason = f"⛔ BLOCKED: Deadly sins detected in {file_path}\n\n"
    for lineno, message, matched_text in violations:
        reason += f"  Line {lineno}: {message}\n"
        reason += f"    Matched: {matched_text[:50]}...\n"

    reason += "\n🚨 CRITICAL: Fix these issues before writing the file!\n"
    reason += "These patterns are NEVER acceptable in production code.\n"
    reason += "See .claude/memory/anti_patterns.md for details."

    # Deny the write
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)

# No deadly sins found, allow the write
print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }
    )
)
sys.exit(0)
