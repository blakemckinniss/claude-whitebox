#!/usr/bin/env python3
"""
Assumption Ledger: Surface hidden assumptions before code changes.

Hook Type: PreToolUse (on Edit/Write)
Target Latency: <500ms via Groq
Purpose: Ask Claude to pause and verify what it's assuming.

THE INSIGHT:
Before modifying code, Claude makes implicit assumptions about:
- Data types and shapes
- Input validation already done
- Edge cases handled elsewhere
- API behavior and return types

This hook uses Groq to extract those assumptions and surface them
as questions, forcing verification before the edit proceeds.

Output: 1-3 assumption questions injected as additionalContext.
"""

import sys
import os
import json
import time
from pathlib import Path

# Add .claude/ops to path for groq.py import
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "ops"))

from groq import call_groq_api, GroqAPIError  # noqa: E402

# =============================================================================
# CONFIG
# =============================================================================

MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")  # Fast model for hooks
MAX_TOKENS = 150
TIMEOUT = 2  # Fast timeout (int for groq.py)

MEMORY_DIR = PROJECT_ROOT / ".claude" / "memory"

# Cooldown to avoid spamming (seconds between analyses)
COOLDOWN = 45
LAST_ANALYSIS_FILE = MEMORY_DIR / "assumption_ledger_last.json"

# Skip these (low-risk or scratch work)
SKIP_PATHS = (".claude/tmp/", ".claude/memory/", "node_modules/", "__pycache__/")

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """You analyze code changes to surface hidden assumptions.

Given: A code edit (old_string -> new_string) or file write (content).

YOUR TASK: Identify 1-3 IMPLICIT assumptions the coder is making.

FOCUS ON:
1. Data type assumptions (expecting list but could be None?)
2. State assumptions (file exists? connection open? initialized?)
3. API behavior (return type correct? exceptions thrown?)
4. Edge cases (empty input? negative numbers? unicode?)
5. Concurrency (thread-safe? race conditions?)

OUTPUT FORMAT (JSON only):
{
  "assumptions": [
    "Assuming X is always Y - verify: <specific check>",
    "Assuming Z handles W - verify: <specific check>"
  ],
  "risk": "low" | "medium" | "high"
}

RULES:
- Be SPECIFIC, not generic ("Assuming list is non-empty" not "check edge cases")
- Only 1-3 assumptions, prioritize by risk
- If code is trivial (logging, comments), return {"assumptions": [], "risk": "low"}
- Reference actual code elements when possible"""

# =============================================================================
# HELPERS
# =============================================================================

def check_cooldown() -> bool:
    """Return True if cooldown has passed."""
    if not LAST_ANALYSIS_FILE.exists():
        return True
    try:
        with open(LAST_ANALYSIS_FILE) as f:
            data = json.load(f)
        last_time = data.get("timestamp", 0)
        return (time.time() - last_time) > COOLDOWN
    except (json.JSONDecodeError, IOError):
        return True


def update_cooldown():
    """Update cooldown timestamp (atomic write for concurrency safety)."""
    try:
        import fcntl
        import tempfile

        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

        # Use file locking for atomic write
        lock_path = LAST_ANALYSIS_FILE.with_suffix('.lock')
        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)

            # Atomic write: temp file + rename
            fd, tmp_path = tempfile.mkstemp(dir=MEMORY_DIR, suffix='.json')
            with os.fdopen(fd, 'w') as f:
                json.dump({"timestamp": time.time()}, f)
            os.replace(tmp_path, LAST_ANALYSIS_FILE)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
    except (IOError, OSError):
        pass


def should_skip(filepath: str) -> bool:
    """Check if filepath should be skipped."""
    if not filepath:
        return True
    for skip in SKIP_PATHS:
        if skip in filepath:
            return True
    return False


def extract_code_change(tool_name: str, tool_input: dict) -> str:
    """Extract the code being changed for analysis."""
    if tool_name == "Edit":
        old = tool_input.get("old_string", "")[:400]
        new = tool_input.get("new_string", "")[:400]
        return f"REPLACING:\n{old}\n\nWITH:\n{new}"
    elif tool_name == "Write":
        content = tool_input.get("content", "")[:800]
        return f"WRITING:\n{content}"
    return ""


# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def analyze_assumptions(filepath: str, code_change: str) -> dict | None:
    """Call Groq to analyze assumptions."""
    user_prompt = f"""FILE: {filepath}

{code_change}

Extract 1-3 hidden assumptions in this code change."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    try:
        result = call_groq_api(
            messages=messages,
            model=MODEL,
            temperature=0.2,
            max_tokens=MAX_TOKENS,
            timeout=TIMEOUT
        )
        content = result['choices'][0]['message']['content']
        return json.loads(content)

    except (GroqAPIError, json.JSONDecodeError, KeyError, IndexError) as e:
        try:
            from hook_logging import log_hook_error
            log_hook_error("assumption_ledger", e, {"model": MODEL})
        except ImportError:
            pass
        return None


def format_output(analysis: dict) -> str:
    """Format assumptions as injected context."""
    assumptions = analysis.get("assumptions", [])
    risk = analysis.get("risk", "low")

    if not assumptions or risk == "low":
        return ""

    emoji = "⚠️" if risk == "high" else "🤔"
    lines = [f"\n{emoji} ASSUMPTION CHECK ({risk} risk):"]

    for i, assumption in enumerate(assumptions[:3], 1):
        lines.append(f"  {i}. {assumption}")

    lines.append("")
    return "\n".join(lines)


# =============================================================================
# HOOK INTERFACE
# =============================================================================

def main():
    """PreToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only analyze Edit/Write
    if tool_name not in ("Edit", "Write"):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    filepath = tool_input.get("file_path", "")

    # Skip low-risk paths
    if should_skip(filepath):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Check cooldown
    if not check_cooldown():
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Extract code change
    code_change = extract_code_change(tool_name, tool_input)
    if len(code_change) < 50:  # Too small to analyze
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Analyze
    analysis = analyze_assumptions(filepath, code_change)

    # Format output
    context = ""
    if analysis:
        update_cooldown()  # Update cooldown after any successful analysis
        context = format_output(analysis)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": context
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
