#!/usr/bin/env python3
"""
Goal Anchor Hook: Prevents drift from original user intent.

Hook Type: UserPromptSubmit
Purpose: Captures original goal, surfaces drift warnings, BLOCKS scope expansion.

THE INSIGHT:
Claude often solves the wrong problem. After 5 turns of "fixing" something,
the original ask ("fix the login bug") becomes "refactoring the auth module".
This hook anchors attention to the original goal.

AUTONOMOUS AGENT ENHANCEMENT (v3.6):
Implements the Anthropic "one feature per session" constraint:
https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Warns on drift
- BLOCKS on scope expansion (new major feature detected)

Behavior:
1. On first substantive prompt: Capture goal + keywords
2. On subsequent prompts: Check for drift
3. If drift detected: Inject reminder of original goal
4. If SCOPE EXPANSION detected: BLOCK until acknowledged
"""

import _lib_path  # noqa: F401
import sys
import json
import re

# Import state machine
from session_state import (
    load_state, save_state, set_goal, check_goal_drift,
    should_nudge, record_nudge,  # v3.4: Nudge tracking
    start_feature,  # v3.6: Feature tracking
)

# Import project-aware state management
try:
    from project_detector import get_current_project, ProjectContext
    PROJECT_AWARE = True
except ImportError:
    PROJECT_AWARE = False


def output_hook_result(context: str = "", decision: str = "allow", reason: str = ""):
    """Output hook result with optional blocking."""
    result = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit"}}
    if context:
        result["hookSpecificOutput"]["additionalContext"] = context
    if decision == "deny":
        result["hookSpecificOutput"]["permissionDecision"] = "deny"
        result["hookSpecificOutput"]["permissionDecisionReason"] = reason
    print(json.dumps(result))


# =============================================================================
# SCOPE EXPANSION DETECTION
# =============================================================================

# Patterns that indicate a new major feature/task (not continuation of current work)
SCOPE_EXPANSION_PATTERNS = [
    r"(?:now|also|next|then)\s+(?:let'?s?|we\s+should|i\s+want|can\s+you)\s+",
    r"(?:add|create|implement|build|write)\s+(?:a\s+)?(?:new|another)\s+",
    r"(?:before\s+we|while\s+we're|since\s+we're)\s+(?:here|at\s+it)",
    r"(?:one\s+more\s+thing|actually|wait)",
    r"(?:unrelated|different|separate)\s+(?:thing|task|feature)",
]

# Keywords indicating explicit scope switch
EXPLICIT_SWITCH_KEYWORDS = [
    "switch to", "move on to", "let's do", "new task", "different feature",
    "forget about", "instead of", "actually let's", "change of plans",
]


def detect_scope_expansion(state, prompt: str) -> tuple[bool, str]:
    """Detect if prompt is expanding scope beyond original goal.

    Returns: (is_expanding, reason)

    For autonomous agents, we want to enforce "one feature per session".
    This detects when the user/system is trying to add new features mid-stream.
    """
    if not state.original_goal:
        return False, ""

    prompt_lower = prompt.lower()

    # Check for explicit scope switch keywords
    for keyword in EXPLICIT_SWITCH_KEYWORDS:
        if keyword in prompt_lower:
            return True, f"Explicit scope switch detected: '{keyword}'"

    # Check for scope expansion patterns
    for pattern in SCOPE_EXPANSION_PATTERNS:
        if re.search(pattern, prompt_lower, re.IGNORECASE):
            return True, f"Scope expansion pattern detected"

    # Check for new feature introduction (lots of new keywords not in original goal)
    original_keywords = set(state.goal_keywords)
    prompt_words = set(re.findall(r'\b[a-z]{4,}\b', prompt_lower))

    # Exclude common words
    common = {"this", "that", "with", "from", "have", "been", "will", "would",
              "could", "should", "make", "just", "like", "want", "need", "some"}
    prompt_words -= common

    # If prompt introduces many new keywords (>3) not in original goal, suspect expansion
    new_keywords = prompt_words - original_keywords
    if len(new_keywords) > 5 and len(original_keywords) > 0:
        overlap = len(prompt_words & original_keywords)
        if overlap < 2:  # Very little overlap with original goal
            return True, f"Significant new scope detected ({len(new_keywords)} new terms)"

    return False, ""


def main():
    """UserPromptSubmit hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        output_hook_result()
        sys.exit(0)

    prompt = input_data.get("prompt", "")
    if not prompt:
        output_hook_result()
        sys.exit(0)

    # Load state
    state = load_state()

    # === PROJECT-AWARE GOAL ISOLATION ===
    # If project changed since goal was set, reset goal to avoid cross-project drift warnings
    current_project_id = ""
    if PROJECT_AWARE:
        try:
            context = get_current_project()
            current_project_id = context.project_id
        except Exception:
            pass

    if state.original_goal and state.goal_project_id and current_project_id:
        if current_project_id != state.goal_project_id:
            # Project changed! Reset goal-related state
            state.original_goal = ""
            state.goal_keywords = []
            state.goal_set_turn = 0
            state.goal_project_id = ""
            # Clear scope expansion nudge history (project-specific)
            if "scope_expansion" in state.nudge_history:
                del state.nudge_history["scope_expansion"]
            if "goal_drift" in state.nudge_history:
                del state.nudge_history["goal_drift"]

    # Set goal if not already set
    if not state.original_goal:
        set_goal(state, prompt)
        # v3.6: Start tracking this as the current feature
        start_feature(state, prompt[:100])
        # Track which project this goal belongs to
        state.goal_project_id = current_project_id
        save_state(state)
        output_hook_result()
        sys.exit(0)

    # === v3.6: SCOPE EXPANSION CHECK (Anthropic pattern: one feature per session) ===
    # For autonomous agents, block scope expansion to prevent incomplete work

    # SUDO SCOPE bypass - allows explicit scope override
    if "SUDO SCOPE" in prompt.upper():
        # User explicitly overriding scope - reset goal to new task
        state.original_goal = ""
        state.goal_keywords = []
        state.goal_set_turn = 0
        state.goal_project_id = ""
        # Clear scope nudge history
        if "scope_expansion" in state.nudge_history:
            del state.nudge_history["scope_expansion"]
        # Set new goal from this prompt (strip the SUDO SCOPE marker)
        clean_prompt = re.sub(r'\bSUDO\s+SCOPE\b', '', prompt, flags=re.IGNORECASE).strip()
        set_goal(state, clean_prompt)
        start_feature(state, clean_prompt[:100])
        state.goal_project_id = current_project_id
        save_state(state)
        output_hook_result()
        sys.exit(0)

    is_expanding, expansion_reason = detect_scope_expansion(state, prompt)

    if is_expanding:
        # Check if this has been warned about multiple times
        show, severity = should_nudge(state, "scope_expansion", expansion_reason)

        if show:
            record_nudge(state, "scope_expansion", expansion_reason)
            save_state(state)

            # After 2 warnings, BLOCK instead of just warn
            times_warned = state.nudge_history.get("scope_expansion", {}).get("times_shown", 0)

            if times_warned >= 2 or severity == "escalate":
                # BLOCK: Require explicit acknowledgment to switch scope
                block_message = (
                    f"**SCOPE EXPANSION BLOCKED** (One-Feature-Per-Session)\n\n"
                    f"🎯 **Current goal**: {state.original_goal[:80]}\n"
                    f"🚫 **Detected**: {expansion_reason}\n\n"
                    f"**Options:**\n"
                    f"1. Complete current feature first, then start new session\n"
                    f"2. Add 'SUDO SCOPE' to explicitly override\n"
                    f"3. Rephrase request as continuation of current goal\n\n"
                    f"*This enforces the Anthropic pattern: finish one feature before starting another.*"
                )
                output_hook_result(context="", decision="deny", reason=block_message)
                sys.exit(0)
            else:
                # WARN first time
                warn_message = (
                    f"⚠️ **SCOPE EXPANSION DETECTED**\n"
                    f"🎯 Current goal: \"{state.original_goal[:60]}...\"\n"
                    f"🔀 {expansion_reason}\n\n"
                    f"Finish current feature before switching. (Will block after {2 - times_warned} more attempts)"
                )
                output_hook_result(context=warn_message)
                sys.exit(0)

    # Check for drift (use prompt as current activity indicator)
    is_drifting, drift_message = check_goal_drift(state, prompt)

    if is_drifting:
        # v3.4: Check nudge history before showing
        show, severity = should_nudge(state, "goal_drift", drift_message)
        if show:
            record_nudge(state, "goal_drift", drift_message)
            # Escalate if repeatedly ignored
            if severity == "escalate":
                drift_message = f"🚨 **REPEATED DRIFT WARNING** (ignored {state.nudge_history.get('goal_drift', {}).get('times_ignored', 0)}x)\n{drift_message}"
            save_state(state)
            output_hook_result(context=f"\n{drift_message}\n")
            sys.exit(0)

    save_state(state)
    output_hook_result()
    sys.exit(0)


if __name__ == "__main__":
    main()
