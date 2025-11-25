#!/usr/bin/env python3
"""
Reflexion Memory: Auto-Learn from Failures (PostToolUse hook)
Detects verification failures, bash errors, edit rejections and auto-saves to lessons.md
"""
import sys
import json
import subprocess  # nosec B404 - internal tool execution only
from pathlib import Path

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


MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
LESSONS_FILE = MEMORY_DIR / "lessons.md"
REMEMBER_CMD = (
    Path(__file__).resolve().parent.parent.parent / "scripts" / "ops" / "remember.py"
)


def auto_learn_failure(tool_name, error_context, lesson_text):
    """Automatically add lesson to lessons.md"""
    try:
        # Use remember.py to add lesson with AUTO tag
        lesson_with_tag = f"[AUTO-LEARNED-FAILURE] {lesson_text}"
        subprocess.run(  # nosec B603 B607 - controlled internal script
            ["python3", str(REMEMBER_CMD), "add", "lessons", lesson_with_tag],
            capture_output=True,
            timeout=5,
        )
        return True
    except Exception:  # Hook resilience requires catching all errors
        return False


def extract_bash_error(result):
    """Extract meaningful error from bash command"""
    stderr = result.get("stderr", "")
    stdout = result.get("stdout", "")
    exit_code = result.get("exit_code", 0)

    if exit_code != 0:
        # Get last line of stderr or stdout for concise error
        error_lines = (stderr or stdout).strip().split('\n')
        return error_lines[-1] if error_lines else f"Exit code {exit_code}"
    return None


def extract_tool_error(result):
    """Extract error from tool result"""
    if isinstance(result, dict):
        return result.get("error") or result.get("stderr")
    return str(result) if result else None


# Load input
try:
    input_data = json.load(sys.stdin)
except Exception:  # Hook resilience requires catching all JSON errors
    sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse"}}))
    sys.exit(0)

tool_name = input_data.get("tool_name", "")
tool_result = input_data.get("toolResult", {})

lessons_learned = []

# Detect verify.py failures
if tool_name == "Bash":
    command = input_data.get("tool_input", {}).get("command", "")

    if "verify.py" in command:
        exit_code = tool_result.get("exit_code", 0)
        if exit_code == 1:
            # Extract verification type from command
            parts = command.split()
            if len(parts) >= 3:
                check_type = parts[2] if parts[2] != "python3" else parts[3]
                target = parts[3] if parts[2] != "python3" else parts[4] if len(parts) > 4 else "unknown"

                lesson = f"Verification failed: {check_type} check for '{target}' returned false"
                if auto_learn_failure("verify", command, lesson):
                    lessons_learned.append(f"📝 Auto-learned: {lesson}")

    # Detect general bash command failures
    elif tool_result.get("exit_code", 0) != 0:
        error = extract_bash_error(tool_result)
        if error and len(error) < 200:  # Avoid logging giant stack traces
            lesson = f"Bash command failed: `{command[:100]}` → {error}"
            if auto_learn_failure("bash", command, lesson):
                lessons_learned.append(f"📝 Auto-learned: {lesson}")

# Detect Edit tool rejections (file not read first)
elif tool_name == "Edit":
    error = extract_tool_error(tool_result)
    if error and "read" in error.lower():
        file_path = input_data.get("tool_input", {}).get("file_path", "unknown")
        
        # Validate file path (per official docs security best practices)
        if file_path and not validate_file_path(file_path):
            print(f"Security: Path traversal detected in {file_path}", file=sys.stderr)
            sys.exit(2)
        lesson = f"Edit rejected: Attempted to edit {file_path} without reading first"
        if auto_learn_failure("edit", file_path, lesson):
            lessons_learned.append(f"📝 Auto-learned: {lesson}")

# Detect Task agent failures
elif tool_name == "Task":
    error = extract_tool_error(tool_result)
    if error:
        agent_type = input_data.get("tool_input", {}).get("subagent_type", "unknown")
        # Only log if error is concise
        if len(str(error)) < 200:
            lesson = f"Agent {agent_type} failed: {error}"
            if auto_learn_failure("agent", agent_type, lesson):
                lessons_learned.append(f"📝 Auto-learned: {lesson}")

# Build output
if lessons_learned:
    additional_context = f"""
🧠 REFLEXION MEMORY: FAILURE AUTO-LEARNED

{chr(10).join(lessons_learned)}

Location: .claude/memory/lessons.md
Tag: [AUTO-LEARNED-FAILURE]

Why: System learns from failures automatically without manual intervention.
Consolidation: Run upkeep.py to merge duplicate patterns.
"""
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": additional_context,
                }
            }
        )
    )
else:
    sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse"}}))

sys.exit(0)
