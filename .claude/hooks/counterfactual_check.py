#!/usr/bin/env python3
"""
Counterfactual Pre-Check: Force contingency planning BEFORE action.

Hook Type: PreToolUse (on Edit/Write)
Target Latency: <500ms via Groq
Purpose: Break tunnel vision by asking "what if this fails?"

THE INSIGHT:
Claude commits to approaches without considering alternatives. When the
approach fails, sunk cost kicks in. This hook asks BEFORE the first attempt:
"What's your fallback if this doesn't work?"

This surfaces:
1. Whether Claude HAS a fallback (often: no)
2. Whether the fallback is actually better (sometimes: yes)
3. Implicit assumptions about why current approach will work

Different from assumption_ledger:
- assumption_ledger: "What are you assuming about the code?"
- counterfactual: "What will you do if this approach fails?"

Output: Fallback prompt injected as additionalContext (non-blocking nudge).
"""

import sys
import os
import json
import time
from pathlib import Path

# Add scripts/ops to path for groq.py import
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "ops"))

from groq import call_groq_api, GroqAPIError  # noqa: E402

# =============================================================================
# CONFIG
# =============================================================================

MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")  # Fast model for quick check
MAX_TOKENS = 100
TIMEOUT = 2  # Fast timeout (int for groq.py)

MEMORY_DIR = PROJECT_ROOT / ".claude" / "memory"

# Cooldown between checks (seconds) - don't spam
COOLDOWN = 90
LAST_CHECK_FILE = MEMORY_DIR / "counterfactual_last.json"

# Skip low-risk paths
SKIP_PATHS = ("scratch/", ".claude/memory/", "node_modules/", "__pycache__", ".git/")

# Only trigger on substantial changes
MIN_CHANGE_SIZE = 100  # characters

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """You analyze code changes to surface missing contingency plans.

Given a code change, identify:
1. What approach is being taken
2. What could go wrong
3. What the fallback would be if it fails

OUTPUT FORMAT (JSON only):
{
  "approach": "Brief description of what's being attempted",
  "risk": "What could cause this to fail",
  "fallback": "What to try if this fails (or 'none identified')",
  "should_prompt": true/false
}

RULES:
- should_prompt = true ONLY if: no clear fallback AND risk is non-trivial
- should_prompt = false for: trivial changes, obvious fixes, low-risk edits
- Keep all fields under 50 words
- Be specific about the risk and fallback"""

# =============================================================================
# HELPERS
# =============================================================================

def check_cooldown() -> bool:
    """Return True if cooldown has passed."""
    if not LAST_CHECK_FILE.exists():
        return True
    try:
        with open(LAST_CHECK_FILE) as f:
            data = json.load(f)
        last_time = data.get("timestamp", 0)
        return (time.time() - last_time) > COOLDOWN
    except (json.JSONDecodeError, IOError):
        return True


def update_cooldown():
    """Update cooldown timestamp."""
    try:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        with open(LAST_CHECK_FILE, 'w') as f:
            json.dump({"timestamp": time.time()}, f)
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


def extract_change_context(tool_name: str, tool_input: dict) -> tuple[str, int]:
    """Extract the change context and size.

    Returns: (context_string, change_size)
    """
    if tool_name == "Edit":
        old = tool_input.get("old_string", "")[:300]
        new = tool_input.get("new_string", "")[:300]
        change_size = len(new) - len(old)
        return f"REPLACING:\n{old}\n\nWITH:\n{new}", abs(change_size) + len(new)
    elif tool_name == "Write":
        content = tool_input.get("content", "")[:600]
        return f"WRITING NEW FILE:\n{content}", len(content)
    return "", 0


# =============================================================================
# ANALYSIS
# =============================================================================

def analyze_counterfactual(filepath: str, change_context: str) -> dict | None:
    """Call Groq to analyze counterfactual."""
    user_prompt = f"""FILE: {filepath}

{change_context}

Analyze: What's the approach, risk, and fallback?"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    try:
        result = call_groq_api(
            messages=messages,
            model=MODEL,
            temperature=0.1,
            max_tokens=MAX_TOKENS,
            timeout=TIMEOUT
        )
        content = result['choices'][0]['message']['content']
        return json.loads(content)

    except (GroqAPIError, json.JSONDecodeError, KeyError, IndexError):
        return None


def format_output(analysis: dict) -> str:
    """Format counterfactual as injected context."""
    if not analysis:
        return ""

    should_prompt = analysis.get("should_prompt", False)
    if not should_prompt:
        return ""

    approach = analysis.get("approach", "unknown")[:60]
    risk = analysis.get("risk", "unknown")[:60]
    fallback = analysis.get("fallback", "none identified")[:60]

    lines = [
        "\n🔮 COUNTERFACTUAL CHECK:",
        f"  Approach: {approach}",
        f"  Risk: {risk}",
        f"  Fallback: {fallback}",
        "  → If this fails, is the fallback better than persisting?",
        ""
    ]

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

    # Extract change context
    change_context, change_size = extract_change_context(tool_name, tool_input)

    # Skip small changes
    if change_size < MIN_CHANGE_SIZE:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Analyze
    analysis = analyze_counterfactual(filepath, change_context)

    # Format output
    context = ""
    if analysis:
        context = format_output(analysis)
        if context:
            update_cooldown()

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
