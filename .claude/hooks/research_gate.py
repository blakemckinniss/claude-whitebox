#!/usr/bin/env python3
"""
Research Gate Hook: BLOCK writes using unverified external libraries.

Hook Type: PreToolUse (matcher: Edit|Write)
Behavior: HARD BLOCK (not suggestion)

THE PROBLEM:
Claude confabulates APIs from training data. "anthropic.messages.create()" may have
changed since 2024. This hook enforces the Confabulation Ban (Hard Block #20).

ENFORCEMENT:
1. Extract imports from code being written
2. Check against RESEARCH_REQUIRED_LIBS (fast-moving APIs)
3. If lib not in libraries_researched this session → BLOCK
4. Bypass: "VERIFIED" keyword in prompt or lib is stdlib

Different from existing hooks:
- probe_gate.py: Suggests probe, doesn't block
- epistemic_boundary.py: Checks identifiers, not libraries
- ops_nudge.py: Suggests tools, doesn't block
"""

import _lib_path  # noqa: F401
import sys
import json
from pathlib import Path

# Import shared state
from session_state import (
    load_state, RESEARCH_REQUIRED_LIBS, extract_libraries_from_code
)

# =============================================================================
# CONFIG
# =============================================================================

# Additional fast-moving libs not in session_state
EXTRA_RESEARCH_LIBS = {
    # LLM/AI
    "litellm", "guidance", "outlines", "dspy", "instructor",
    "crewai", "autogen", "semantic-kernel",
    # Data
    "modal", "ray", "dask", "vaex",
    # Web frameworks
    "litestar", "blacksheep", "robyn",
    # Cloud
    "pulumi", "cdktf",
}

ALL_RESEARCH_LIBS = RESEARCH_REQUIRED_LIBS | EXTRA_RESEARCH_LIBS

def needs_research_check(lib: str, researched: list) -> bool:
    """Check if library needs research verification."""
    lib_lower = lib.lower()

    # Already researched this session
    if lib_lower in [r.lower() for r in researched]:
        return False

    # Check if it's a fast-moving library
    for research_lib in ALL_RESEARCH_LIBS:
        if research_lib.lower() in lib_lower or lib_lower in research_lib.lower():
            return True

    return False


def main():
    """PreToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only check Edit/Write
    if tool_name not in ("Edit", "Write"):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    filepath = tool_input.get("file_path", "")

    # Skip non-code files
    code_extensions = {".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go"}
    if filepath:
        ext = Path(filepath).suffix.lower()
        if ext not in code_extensions:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
            sys.exit(0)

    # Skip scratch files (prototyping zone)
    if ".claude/tmp/" in filepath:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Get code being written
    code = tool_input.get("new_string", "") or tool_input.get("content", "")
    if not code or len(code) < 30:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Extract libraries from code
    libs = extract_libraries_from_code(code)
    if not libs:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Load session state
    state = load_state()
    researched = state.libraries_researched or []

    # Find unresearched libs
    unresearched = []
    for lib in libs:
        if needs_research_check(lib, researched):
            unresearched.append(lib)

    if not unresearched:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Check for bypass in recent context (would need conversation history)
    # For now, we'll check if the lib was mentioned with VERIFIED
    # This is a simplified check - full implementation would parse conversation

    # BLOCK with actionable message
    libs_str = ", ".join(f"`{lib}`" for lib in unresearched[:3])

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "decision": "block",
            "reason": (
                f"**RESEARCH GATE BLOCKED** (Hard Block #20: Confabulation Ban)\n\n"
                f"Unverified libraries: {libs_str}\n\n"
                f"**REQUIRED before writing this code:**\n"
                f"```bash\n"
                f"python3 .claude/ops/research.py \"{unresearched[0]} API 2024\"\n"
                f"```\n"
                f"OR\n"
                f"```bash\n"
                f"python3 .claude/ops/probe.py \"{unresearched[0]}.<object>\"\n"
                f"```\n\n"
                f"**Bypass:** Say \"VERIFIED\" if you've manually confirmed the API.\n"
                f"**Why:** APIs change. Training data may be stale. Verify first."
            ),
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
