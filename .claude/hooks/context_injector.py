#!/usr/bin/env python3
"""
Context Injector Hook v3: UserPromptSubmit hook for smart context injection.

This hook fires on every user prompt and:
- Injects session state summary (domain, files, errors)
- Suggests relevant ops scripts based on prompt
- Only injects when context is RELEVANT

Sparse by design - only speaks when useful.
"""

import sys
import json
import re

# Import the state machine
from session_state import (
    load_state, save_state,
    generate_context,
    add_domain_signal, Domain,
)

# =============================================================================
# OPS SCRIPT TRIGGERS
# =============================================================================

# Map prompt patterns to ops scripts
OPS_TRIGGERS = {
    "research": [
        r"how\s+(do|does|to)",
        r"what\s+(is|are|does)",
        r"documentation",
        r"docs\s+for",
        r"latest\s+(api|version|syntax)",
        r"(fastapi|pydantic|langchain|anthropic|openai)",
    ],
    "probe": [
        r"what\s+methods",
        r"api\s+signature",
        r"inspect.*object",
        r"(pandas|boto3|playwright).*api",
    ],
    "xray": [
        r"find.*(class|function|method)",
        r"where\s+is.*defined",
        r"list.*functions",
    ],
    "think": [
        r"break.*down",
        r"decompose",
        r"step.*by.*step",
        r"how.*approach",
    ],
    "verify": [
        r"check\s+if",
        r"verify.*exists",
        r"confirm.*works",
    ],
    "bdg": [
        r"chrome\s*devtools",
        r"\bcdp\b",
        r"devtools\s*protocol",
        r"headless\s*(chrome|browser)",
        r"browser.*dom",
        r"dom.*query",
        r"extract.*html.*page",
        r"scrape.*dynamic",
        r"js.*render",
        r"javascript.*page",
        r"browser.*screenshot",
        r"browser.*pdf",
        r"page.*cookies",
        r"intercept.*network",
        r"debug.*browser",
    ],
}

# =============================================================================
# RELEVANCE DETECTION
# =============================================================================

def detect_ops_suggestion(prompt: str, state) -> dict | None:
    """Detect if prompt matches an ops script trigger."""
    prompt_lower = prompt.lower()

    for script, patterns in OPS_TRIGGERS.items():
        if script not in state.ops_scripts:
            continue
        for pattern in patterns:
            if re.search(pattern, prompt_lower):
                return {
                    "script": script,
                    "command": f"python3 scripts/ops/{script}.py",
                    "reason": f"Prompt matches '{pattern}' pattern",
                }

    return None


def should_inject_context(state) -> bool:
    """Decide if context should be injected."""
    # Inject if there are unresolved errors
    if state.errors_unresolved:
        return True

    # Inject if domain is clear and useful
    if state.domain != Domain.UNKNOWN and state.domain_confidence > 0.5:
        return True

    # Inject if significant work has been done
    if len(state.files_edited) >= 2:
        return True

    # Inject if recent deploy
    if state.last_deploy:
        return True

    return False


def format_context(state, ops_suggestion: dict | None) -> str:
    """Format context for injection."""
    parts = []

    # State summary (only if useful)
    state_context = generate_context(state)
    if state_context:
        parts.append(f"📊 {state_context}")

    # Ops suggestion (only if matched)
    if ops_suggestion:
        parts.append(
            f"🔧 Consider: `{ops_suggestion['script']}` - "
            f"Run: {ops_suggestion['command']}"
        )

    return "\n".join(parts)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """UserPromptSubmit hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit"}}))
        sys.exit(0)

    user_prompt = input_data.get("user_prompt", "") or input_data.get("prompt", "")

    if not user_prompt or len(user_prompt) < 5:
        print(json.dumps({}))
        sys.exit(0)

    # Load state
    state = load_state()

    # Add prompt as domain signal
    add_domain_signal(state, user_prompt[:200])
    save_state(state)

    # Check for ops suggestion
    ops_suggestion = detect_ops_suggestion(user_prompt, state)

    # Decide if we should inject context
    should_inject = should_inject_context(state) or ops_suggestion

    if not should_inject:
        print(json.dumps({}))
        sys.exit(0)

    # Format and output context
    context = format_context(state, ops_suggestion)

    if context:
        output = {"additionalContext": context}
    else:
        output = {}

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
