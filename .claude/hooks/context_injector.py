#!/usr/bin/env python3
"""
Context Injector Hook v3: UserPromptSubmit hook for smart context injection.

This hook fires on every user prompt and:
- Injects session state summary (domain, files, errors)
- Suggests relevant ops scripts based on prompt
- Only injects when context is RELEVANT

Sparse by design - only speaks when useful.
"""

import _lib_path  # noqa: F401
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
# RELEVANCE DETECTION
# =============================================================================
# NOTE: Ops script suggestions moved to ops_awareness.py to avoid duplication


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


def format_context(state) -> str:
    """Format context for injection."""
    parts = []

    # State summary (only if useful)
    state_context = generate_context(state)
    if state_context:
        parts.append(f"📊 {state_context}")

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

    # Decide if we should inject context (ops suggestions handled by ops_awareness.py)
    if not should_inject_context(state):
        print(json.dumps({}))
        sys.exit(0)

    # Format and output context
    context = format_context(state)

    if context:
        output = {"additionalContext": context}
    else:
        output = {}

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
