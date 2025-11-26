#!/usr/bin/env python3
"""
Probe Gate Hook v3: Suggest probe before using unfamiliar library APIs.

Hook Type: PreToolUse (matcher: Bash)
Latency Target: <20ms

Detects when running Python code that imports libraries not yet probed.
Suggests (but doesn't block) running probe first.
"""

import sys
import json
import re
from pathlib import Path

# =============================================================================
# CONFIG
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
STATE_FILE = SCRIPT_DIR.parent / "memory" / "probe_gate_state.json"

# Libraries that benefit from runtime probing (complex APIs)
PROBEABLE_LIBS = {
    # Data
    "pandas": "DataFrame, Series methods",
    "polars": "LazyFrame, expressions",
    "numpy": "array operations",
    # Web
    "requests": "Response object",
    "httpx": "async client",
    "aiohttp": "session methods",
    # AWS
    "boto3": "client/resource methods",
    "botocore": "exceptions",
    # API clients
    "anthropic": "messages API",
    "openai": "chat completions",
    "langchain": "chain methods",
    # Automation
    "playwright": "page methods",
    "selenium": "webdriver",
    # FastAPI
    "fastapi": "app, router",
    "pydantic": "model methods",
    # DB
    "sqlalchemy": "session, query",
    "psycopg2": "cursor methods",
}

# Patterns to detect library usage in bash commands
PYTHON_RUN_PATTERNS = [
    r"python3?\s+(?:-c\s+['\"](.+?)['\"]|(\S+\.py))",
    r"pytest",
    r"ipython",
]


def load_state() -> dict:
    """Load probe gate state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {"probed_libs": [], "warned_libs": []}


def save_state(state: dict):
    """Save probe gate state."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except IOError:
        pass


def extract_imports_from_command(command: str) -> list[str]:
    """Extract library names from a bash command running Python."""
    imports = []

    # Check for inline python -c
    inline_match = re.search(r'python3?\s+-c\s+[\'"](.+?)[\'"]', command)
    if inline_match:
        code = inline_match.group(1)
        # Find imports in inline code
        import_matches = re.findall(r'(?:from|import)\s+(\w+)', code)
        imports.extend(import_matches)

    # Check for common library-specific commands
    for lib in PROBEABLE_LIBS:
        # Library mentioned in command
        if re.search(rf'\b{lib}\b', command, re.IGNORECASE):
            imports.append(lib)

    return list(set(imports))


def find_unprobed_libs(imports: list[str], state: dict) -> list[tuple[str, str]]:
    """Find imports that are probeable but not yet probed."""
    unprobed = []
    probed = set(state.get("probed_libs", []))
    warned = set(state.get("warned_libs", []))

    for imp in imports:
        imp_lower = imp.lower()
        if imp_lower in PROBEABLE_LIBS and imp_lower not in probed and imp_lower not in warned:
            unprobed.append((imp_lower, PROBEABLE_LIBS[imp_lower]))

    return unprobed


def main():
    """PreToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only check Bash tool
    if tool_name != "Bash":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    command = tool_input.get("command", "")
    if not command:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Check if this is a Python-related command
    is_python_cmd = any(re.search(p, command) for p in PYTHON_RUN_PATTERNS)
    if not is_python_cmd:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Extract imports
    imports = extract_imports_from_command(command)
    if not imports:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Load state and find unprobed libs
    state = load_state()
    unprobed = find_unprobed_libs(imports, state)

    if not unprobed:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Mark as warned (don't spam)
    for lib, _ in unprobed:
        if lib not in state["warned_libs"]:
            state["warned_libs"].append(lib)
    state["warned_libs"] = state["warned_libs"][-20:]  # Keep last 20
    save_state(state)

    # Build suggestion
    suggestions = []
    for lib, api_hint in unprobed[:2]:  # Max 2
        suggestions.append(
            f"   • `{lib}` ({api_hint})\n"
            f"     → python3 .claude/ops/probe.py \"{lib}.<object>\""
        )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": (
                "🔬 PROBE SUGGESTION: Unfamiliar library API detected\n"
                + "\n".join(suggestions) +
                "\n   Probing first prevents API guessing errors"
            ),
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
