#!/usr/bin/env python3
"""
Gap Detector Hook v3: PreToolUse hook with directive injection system.

This hook fires BEFORE every tool call and:
- Checks if editing file without reading (HARD BLOCK)
- Checks if using library without research (WARN)
- Checks workflow compliance (upkeep, verify)
- Injects historical patterns (trauma prevention)
- Detects iteration loops (scratch-first enforcement)

THE CORE INSIGHT:
"STOP. Read the file first." (blocks immediately) >
"Consider reading the file." (ignored)
"""

import _lib_path  # noqa: F401
import sys
import json
import re

# Import the state machine
from session_state import (
    load_state, save_state,
    detect_gaps, surface_gap, Gap,
    track_tool_usage, track_ops_command,
    get_turns_since_op, is_iteration_detected,
    should_nudge, record_nudge,  # v3.4: Nudge tracking
)

# Import synapse core
from synapse_core import (
    Directive, DirectiveStrength,
    check_historical_patterns,
    format_directives,
    output_hook_result,
    UPKEEP_TURN_THRESHOLD,
    VERIFY_TURN_THRESHOLD,
)

# =============================================================================
# CONSTANTS
# =============================================================================

# Tools that don't need gap checking
SKIP_TOOLS = frozenset({"TodoWrite", "BashOutput", "KillShell"})

# Tools where gaps result in BLOCK vs WARN
BLOCK_ON_GAP = frozenset({"Edit", "Write"})

# Claim patterns that require verify
CLAIM_PATTERNS = [
    r"\b(fixed|done|complete|finished|working|solved)\b",
    r"\bi('ve| have) (fixed|done|completed)",
    r"\bthat should (work|fix|solve)",
]

# Architecture decision patterns
ARCH_PATTERNS = [
    r"\b(architect|design|refactor|rewrite|migrate)\b",
    r"\bshould (i|we) (use|choose|pick)\b",
    r"\bwhat('s| is) the best (way|approach|pattern)\b",
]

# =============================================================================
# DIRECTIVE GENERATORS
# =============================================================================


def check_claim_without_verify(prompt: str, state) -> Directive | None:
    """Check if claiming 'fixed' without recent verify."""
    if not any(re.search(p, prompt, re.IGNORECASE) for p in CLAIM_PATTERNS):
        return None

    turns_since = get_turns_since_op(state, "verify")
    if turns_since <= VERIFY_TURN_THRESHOLD:
        return None

    return Directive(
        strength=DirectiveStrength.BLOCK,
        category="workflow",
        message="**STOP.** Cannot claim 'fixed' without `/verify`. Hard Block #3.",
        time_saved="Prevents false confidence"
    )


def check_commit_without_upkeep(command: str, state) -> Directive | None:
    """Check if committing without recent upkeep."""
    if "git commit" not in command:
        return None

    turns_since = get_turns_since_op(state, "upkeep")
    if turns_since <= UPKEEP_TURN_THRESHOLD:
        return None

    return Directive(
        strength=DirectiveStrength.BLOCK,
        category="workflow",
        message=f"**BLOCKED.** Run `/upkeep` first. Last: {turns_since} turns ago.",
        time_saved="Prevents tech debt"
    )


def check_architecture_decision(prompt: str, state) -> Directive | None:
    """Check if making architecture decision without think/council."""
    if not any(re.search(p, prompt, re.IGNORECASE) for p in ARCH_PATTERNS):
        return None

    think_turns = get_turns_since_op(state, "think")
    council_turns = get_turns_since_op(state, "council")

    if think_turns <= 10 or council_turns <= 10:
        return None

    return Directive(
        strength=DirectiveStrength.WARN,
        category="workflow",
        message="**ARCHITECTURE.** Run `/think` then `/council` for major decisions.",
        time_saved="~1-5 days"
    )


def check_iteration_loop(state) -> Directive | None:
    """Check if in iteration loop (should use scratch script)."""
    if not is_iteration_detected(state):
        return None

    message = "**REDIRECT.** 4+ similar tool calls detected. Write script to `.claude/tmp/`."

    # v3.4: Check nudge history
    show, severity = should_nudge(state, "iteration_loop", message)
    if not show:
        return None

    record_nudge(state, "iteration_loop", message)

    # Escalate if repeatedly ignored
    if severity == "escalate":
        return Directive(
            strength=DirectiveStrength.BLOCK,  # Escalate to block!
            category="trajectory",
            message="🚨 **ITERATION LOOP BLOCKED** (ignored 3x). MUST write to `.claude/tmp/` now.",
            time_saved="~15 min"
        )

    return Directive(
        strength=DirectiveStrength.WARN,
        category="trajectory",
        message=message,
        time_saved="~15 min"
    )


def generate_all_directives(
    prompt: str,
    tool_name: str,
    tool_input: dict,
    state
) -> list[Directive]:
    """Generate all applicable directives."""
    directives = []

    # Workflow checks
    if d := check_claim_without_verify(prompt, state):
        directives.append(d)

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if d := check_commit_without_upkeep(command, state):
            directives.append(d)

    if d := check_architecture_decision(prompt, state):
        directives.append(d)

    if d := check_iteration_loop(state):
        directives.append(d)

    # Historical patterns (trauma injection)
    text_to_check = f"{prompt} {json.dumps(tool_input) if tool_input else ''}"
    directives.extend(check_historical_patterns(text_to_check))

    # Sort by severity, limit to 3
    directives.sort(key=lambda x: x.strength.value, reverse=True)
    return directives[:3]


# =============================================================================
# GAP FORMATTING
# =============================================================================


def format_gap_message(gap: Gap) -> str:
    """Format a gap for display."""
    icon = "STOP" if gap.severity == "block" else "!"
    return f"[{icon}] GAP: {gap.message}\n   Fix: {gap.suggestion}"


# =============================================================================
# MAIN
# =============================================================================


def main():
    """PreToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        output_hook_result("PreToolUse")
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Note: PreToolUse does NOT receive 'prompt' - read from transcript if needed
    # For now, use empty string (prompt-based checks rely on session state)
    prompt = ""

    # Skip low-risk tools
    if tool_name in SKIP_TOOLS:
        output_hook_result("PreToolUse")
        sys.exit(0)

    # Load state
    state = load_state()

    # Track tool usage for iteration detection
    track_tool_usage(state, tool_name)

    # Track ops commands
    if tool_name == "Bash":
        track_ops_command(state, tool_input.get("command", ""))

    # Generate directives
    directives = generate_all_directives(prompt, tool_name, tool_input, state)

    # Detect structural gaps (edit without read, etc.)
    context = {"tool_name": tool_name, "tool_input": tool_input}
    gaps = detect_gaps(state, context)

    # Check for blocking gaps
    blocking_gaps = [g for g in gaps if g.severity == "block"]
    warning_gaps = [g for g in gaps if g.severity == "warn"]

    # SANITY CHECK: If state tracking appears corrupted, demote blocks to warnings
    # Signs of corruption: files_read empty but session has activity (approach_history, tool_counts)
    state_appears_corrupted = (
        not state.files_read
        and (state.approach_history or state.tool_counts or state.turn_count > 2)
    )
    if state_appears_corrupted and blocking_gaps:
        # Log the corruption for debugging
        import logging
        logging.warning(
            f"[gap_detector] STATE CORRUPTION: files_read empty but turn_count={state.turn_count}, "
            f"tool_counts={len(state.tool_counts)}, approach_history={len(state.approach_history)}. "
            f"Demoting {len(blocking_gaps)} blocks to warnings."
        )
        # Also add to output so Claude sees it
        output_parts.append(
            "⚠️ **STATE TRACKING ISSUE**: files_read is empty despite session activity. "
            "Blocks demoted to warnings. Check .claude/memory/session_state_v3.json"
        )
        # Demote to warning - state tracking is unreliable
        for gap in blocking_gaps:
            gap.severity = "warn"
            gap.message = f"[STATE UNCERTAIN] {gap.message}"
        warning_gaps.extend(blocking_gaps)
        blocking_gaps = []

    # HARD BLOCK: Editing without reading
    if blocking_gaps and tool_name in BLOCK_ON_GAP:
        gap = blocking_gaps[0]
        surface_gap(state, gap)
        save_state(state)

        output_hook_result(
            "PreToolUse",
            decision="deny",
            reason=format_gap_message(gap)
        )
        sys.exit(0)

    # HARD BLOCK: Workflow violations
    blocking_directives = [d for d in directives if d.strength == DirectiveStrength.BLOCK]
    if blocking_directives:
        state.directives_fired += 1
        # Save state to persist ops_turns tracking even when blocking
        save_state(state)

        output_hook_result(
            "PreToolUse",
            decision="deny",
            reason=blocking_directives[0].format()
        )
        sys.exit(0)

    # Collect all warnings
    output_parts = []

    # Warning directives
    warning_directives = [d for d in directives if d.strength.value < DirectiveStrength.BLOCK.value]
    if warning_directives:
        state.directives_fired += len(warning_directives)
        output_parts.append(format_directives(warning_directives))

    # Warning gaps (only new ones)
    if warning_gaps:
        new_gaps = []
        surfaced_types = [g.get("type") for g in state.gaps_surfaced]
        for gap in warning_gaps:
            if gap.type not in surfaced_types:
                new_gaps.append(gap)
                surface_gap(state, gap)

        if new_gaps:
            gap_messages = [format_gap_message(g) for g in new_gaps[:2]]
            output_parts.append("\n".join(gap_messages))

    save_state(state)

    if output_parts:
        output_hook_result("PreToolUse", context="\n\n".join(output_parts))
    else:
        output_hook_result("PreToolUse")

    sys.exit(0)


if __name__ == "__main__":
    main()
