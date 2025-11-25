#!/usr/bin/env python3
"""
Reflexion Memory: Auto-Learn from Successes (PostToolUse hook)
Detects success after repeated failures, novel solutions, and auto-saves to lessons.md
"""
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

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
SESSION_FILE = MEMORY_DIR / "session_unknown_state.json"
REMEMBER_CMD = (
    Path(__file__).resolve().parent.parent.parent / "scripts" / "ops" / "remember.py"
)


def auto_learn_success(tool_name, context, lesson_text):
    """Automatically add success lesson to lessons.md"""
    try:
        lesson_with_tag = f"[AUTO-LEARNED-SUCCESS] {lesson_text}"
        subprocess.run(
            ["python3", str(REMEMBER_CMD), "add", "lessons", lesson_with_tag],
            capture_output=True,
            timeout=5,
        )
        return True
    except Exception:
        return False


def get_session_state():
    """Load session state to track failure counts"""
    try:
        if SESSION_FILE.exists():
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def update_session_state(state):
    """Save session state"""
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


# Load input
try:
    input_data = json.load(sys.stdin)
except Exception:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse"}}))
    sys.exit(0)

tool_name = input_data.get("tool_name", "")
tool_result = input_data.get("toolResult", {})
session_state = get_session_state()

lessons_learned = []

# Track verify.py successes after failures
if tool_name == "Bash":
    command = input_data.get("tool_input", {}).get("command", "")

    if "verify.py" in command:
        exit_code = tool_result.get("exit_code", 0)

        # Extract check identifier
        parts = command.split()
        check_id = "_".join(parts[2:5]) if len(parts) >= 5 else "unknown"

        # Initialize failure tracker
        if "verify_failures" not in session_state:
            session_state["verify_failures"] = {}

        if exit_code == 0:
            # Success - check if we had previous failures
            failure_count = session_state["verify_failures"].get(check_id, 0)
            if failure_count >= 2:
                # Success after 2+ failures = valuable lesson
                lesson = f"Verify success after {failure_count} failures: {' '.join(parts[2:6])}"
                if auto_learn_success("verify", command, lesson):
                    lessons_learned.append(f"✅ Auto-learned: {lesson}")
                # Reset counter
                session_state["verify_failures"][check_id] = 0
        else:
            # Failure - increment counter
            session_state["verify_failures"][check_id] = (
                session_state["verify_failures"].get(check_id, 0) + 1
            )

# Detect novel scratch scripts (potential promotion candidates)
elif tool_name == "Write":
    file_path = input_data.get("tool_input", {}).get("file_path", "")
    
    # Validate file path (per official docs security best practices)
    if file_path and not validate_file_path(file_path):
        print(f"Security: Path traversal detected in {file_path}", file=sys.stderr)
        sys.exit(2)
    if "/scratch/" in file_path and file_path.endswith(".py"):
        script_name = Path(file_path).name

        # Track script creation
        if "scratch_scripts" not in session_state:
            session_state["scratch_scripts"] = []

        if script_name not in session_state["scratch_scripts"]:
            session_state["scratch_scripts"].append(script_name)

            # Check if this is solving a repeated problem (heuristic: similar script names)
            similar_count = sum(1 for s in session_state["scratch_scripts"] if script_name[:5] in s)
            if similar_count >= 2:
                lesson = f"Novel solution: Created {script_name} (similar scripts: {similar_count})"
                if auto_learn_success("write", file_path, lesson):
                    lessons_learned.append(f"💡 Auto-learned: {lesson}")

# Detect successful agent delegation (agent returns without error)
elif tool_name == "Task":
    agent_type = input_data.get("tool_input", {}).get("subagent_type", "unknown")
    error = tool_result.get("error")

    # Track agent usage
    if "agent_successes" not in session_state:
        session_state["agent_successes"] = {}

    if not error:
        # Successful agent delegation
        session_state["agent_successes"][agent_type] = (
            session_state["agent_successes"].get(agent_type, 0) + 1
        )

        # If this agent has been useful 3+ times, note it
        if session_state["agent_successes"][agent_type] == 3:
            lesson = f"Agent {agent_type} proven useful (3+ successful delegations)"
            if auto_learn_success("agent", agent_type, lesson):
                lessons_learned.append(f"🤖 Auto-learned: {lesson}")

# Save updated session state
update_session_state(session_state)

# Build output
if lessons_learned:
    additional_context = f"""
🧠 REFLEXION MEMORY: SUCCESS AUTO-LEARNED

{chr(10).join(lessons_learned)}

Location: .claude/memory/lessons.md
Tag: [AUTO-LEARNED-SUCCESS]

Why: System learns from successful patterns after struggles.
Consolidation: Run upkeep.py to merge duplicate patterns.
"""
    print(
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
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse"}}))

sys.exit(0)
