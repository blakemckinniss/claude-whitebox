#!/usr/bin/env python3
"""
Proactive Nudge Hook: Surfaces actionable suggestions based on session state.

Hook Type: UserPromptSubmit
Purpose: Make Claude take initiative by surfacing what SHOULD be done.

THE INSIGHT:
Claude is reactive. It waits for problems instead of anticipating them.
This hook analyzes session state and suggests proactive actions:
- Pending files mentioned but not read
- Tests not run in a while
- No verification after edits
- Complex problems without /think

Different from gap_detector (which warns about violations). This hook
suggests POSITIVE actions, not just blocks negative ones.
"""

import sys
import json
from pathlib import Path

from session_state import (
    load_state, get_turns_since_op,
)


def output_hook_result(context: str = ""):
    """Output hook result."""
    result = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit"}}
    if context:
        result["hookSpecificOutput"]["additionalContext"] = context
    print(json.dumps(result))


def generate_suggestions(state) -> list[str]:
    """Generate proactive suggestions based on state."""
    suggestions = []

    # 1. Pending files mentioned but not read
    if state.pending_files:
        pending = state.pending_files[:3]
        names = [Path(f).name for f in pending]
        suggestions.append(f"📂 Mentioned but unread: {names}")

    # 2. Pending searches
    if state.pending_searches:
        pending = state.pending_searches[:3]
        suggestions.append(f"🔍 Mentioned searches not run: {pending}")

    # 3. Edits without verification
    if state.files_edited and not state.last_verify:
        edited_count = len(state.files_edited)
        if edited_count >= 2:
            suggestions.append(f"✅ {edited_count} files edited, no /verify run")

    # 4. Tests not run after multiple edits
    edit_heavy = any(count >= 3 for count in state.edit_counts.values())
    if edit_heavy and not state.tests_run:
        suggestions.append("🧪 Multiple edits without test run")

    # 5. Long time since /think on complex work
    turns_since_think = get_turns_since_op(state, "think")
    # Only suggest if: many turns, many edits, and no recent think
    if state.turn_count > 15 and len(state.files_edited) > 3 and turns_since_think > 10:
        suggestions.append("🧠 Complex session, consider /think for clarity")

    # 6. Integration greps pending
    if state.pending_integration_greps:
        funcs = [p["function"] for p in state.pending_integration_greps[:2]]
        suggestions.append(f"🔗 Grep callers for: {funcs}")

    # 7. Consecutive failures without pivot
    if state.consecutive_failures >= 2:
        suggestions.append(f"⚠️ {state.consecutive_failures} failures - consider different approach")

    return suggestions


def main():
    """UserPromptSubmit hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        output_hook_result()
        sys.exit(0)

    prompt = input_data.get("prompt", "")

    # Skip for meta prompts (short acknowledgments, slash commands)
    if not prompt or len(prompt) < 10 or prompt.startswith("/"):
        output_hook_result()
        sys.exit(0)

    state = load_state()

    # Only show after a few turns (not on fresh sessions)
    if state.turn_count < 5:
        output_hook_result()
        sys.exit(0)

    suggestions = generate_suggestions(state)

    # Limit to top 3 most relevant
    suggestions = suggestions[:3]

    if not suggestions:
        output_hook_result()
        sys.exit(0)

    # Format output
    lines = ["💡 **PROACTIVE CHECKLIST:**"]
    for s in suggestions:
        lines.append(f"  • {s}")
    lines.append("  → Act on these or consciously skip them.")

    output_hook_result("\n".join(lines))
    sys.exit(0)


if __name__ == "__main__":
    main()
