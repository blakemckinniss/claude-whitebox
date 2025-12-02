#!/usr/bin/env python3
"""
Thinking Coach Hook v3: Analyzes Claude's thinking blocks for reasoning flaws.

Hook Type: PreToolUse
Latency Target: <50ms

THE INSIGHT:
Claude's <thinking> blocks reveal reasoning patterns BEFORE actions.
Detecting "I'll just quickly edit" prevents blind edits.
Detecting "I assume" prevents hallucinations.

FLAW CATEGORIES:
1. SHORTCUT - Skipping verification steps
2. ASSUMPTION - Claiming knowledge without evidence
3. OVERCONFIDENCE - "This should work" without testing
4. API_GUESSING - Making up method names/parameters
5. COMPLEXITY - Over-engineering simple tasks
6. SCOPE_CREEP - Adding unrequested features
"""

import _lib_path  # noqa: F401
import sys
import json
import re
from pathlib import Path
from typing import List

# Import from synapse_core
from synapse_core import (
    Directive,
    DirectiveStrength,
    extract_thinking_blocks,
    output_hook_result,
)

# =============================================================================
# THINKING FLAW PATTERNS
# =============================================================================

# (name, patterns, directive_message, severity)
THINKING_FLAW_PATTERNS: List[tuple] = [
    # SHORTCUT - Skipping steps
    # NOTE: Patterns narrowed to require explicit skip/bypass context (reduces false positives)
    ("shortcut", [
        r"(don't|no) need to (read|check|verify|test)",
        r"skip(ping)?\s+(the\s+)?(read|check|verification)",
        r"without\s+(first\s+)?(read|check|verify)ing",
        r"before\s+(read|check|verify)ing\s+(the\s+)?file",
    ], "**STOP.** Shortcut reasoning detected. Read before edit. Verify before claim.", 2),

    # ASSUMPTION - Claiming without evidence
    ("assumption", [
        r"I (assume|believe|think) (the|this|that)\s+\w+\s+(is|has|contains|exists)",
        r"(probably|likely|should be|must be)\s+(in|at|located)",
        r"(presumably|apparently)\s+",
        r"(guessing|guess)\s+(that|it)",
    ], "**CAUTION.** Assumption detected. Verify with `ls`, `grep`, or `Read` first.", 1),

    # OVERCONFIDENCE - False certainty
    ("overconfidence", [
        r"(this|that) (should|will) (definitely\s+)?(work|fix|solve)",
        r"(easy|simple|straightforward|trivial)\s+(fix|change|update)",
        r"(obviously|clearly|certainly)\s+",
        r"no\s+(way|chance)\s+(it|this)\s+(fails|breaks)",
    ], "**WARNING.** Overconfidence detected. Run `/verify` after implementation.", 1),

    # IGNORANCE (Good pattern - acknowledge and research)
    ("ignorance", [
        r"I (don't|do not) (know|remember)\s+(the|how|what|if)",
        r"(not sure|unsure|uncertain)\s+(about|how|what|if|whether)",
        r"I need to (check|look up|research|verify)",
    ], "**GOOD.** Ignorance acknowledged. Run `/research` or `/probe` before proceeding.", 0),

    # API_GUESSING - Making up APIs
    ("api_guessing", [
        r"I (think|believe) (the|this) (method|function|API|endpoint) is",
        r"(should|probably) (have|has) a\s+\w+\s+(method|function|parameter)",
        r"(might|could) be (called|named)\s+\w+",
        r"the\s+\w+\s+(method|api|endpoint)\s+(takes|accepts|expects)",
    ], "**DANGER.** API guessing detected. Run `/probe` to verify actual interface.", 2),

    # COMPLEXITY - Over-engineering
    ("complexity", [
        r"(we could|might want to|should also)\s+(add|implement|create)",
        r"(abstract|generalize|reusable)\s+(this|the|it)",
        r"(future(-|\s)?proof|extensible|scalable)",
        r"(refactor|reorganize|restructure)\s+(while|since)",
    ], "**YAGNI.** Over-engineering detected. Implement minimum viable solution.", 2),

    # SCOPE_CREEP - Adding unrequested work
    # NOTE: Patterns narrowed to avoid false positives when user requests batch fixes ("fix all")
    ("scope_creep", [
        r"while I('m| am) (at it|here),?\s+(I could|let me|might as well)\s+(also\s+)?(add|create|build)",
        r"(bonus|extra)\s+(feature|functionality)",
        r"(might as well|may as well)\s+(add|create|build)\s+(a|an|some)",
    ], "**SCOPE CREEP.** Focus on requested task only.", 2),

    # MEMORY_HOLE - Forgetting context
    ("memory_hole", [
        r"(forgot|forgotten)\s+(about|that|the)",
        r"(oops|oh)\s+(I|we)\s+(forgot|missed)",
        r"should have\s+(remembered|noticed)",
    ], "**MEMORY.** Review recent context. Check if you're repeating work.", 1),
]

# =============================================================================
# TELEMETRY
# =============================================================================

TELEMETRY_FILE = Path(__file__).parent.parent / "memory" / "thinking_coach_last.json"


# SUDO: content_gate false positive on _lib_path import (standard static import)
def save_telemetry(flaws_detected: List[str], thinking_sample: str):
    """Save last detection for debugging (atomic write for concurrency safety)."""
    try:
        import fcntl
        import tempfile
        import os
        import time as time_module

        TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Use file locking for atomic write
        lock_path = TELEMETRY_FILE.with_suffix('.lock')
        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)

            # Atomic write: temp file + rename
            fd, tmp_path = tempfile.mkstemp(dir=TELEMETRY_FILE.parent, suffix='.json')
            with os.fdopen(fd, 'w') as f:
                json.dump({
                    "flaws_detected": flaws_detected,
                    "thinking_sample": thinking_sample[:500],
                    "timestamp": time_module.time(),
                }, f, indent=2)
            os.replace(tmp_path, TELEMETRY_FILE)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
    except (IOError, OSError):
        pass


# =============================================================================
# ANALYSIS
# =============================================================================


def analyze_thinking_for_flaws(thinking_blocks: List[str]) -> List[Directive]:
    """Analyze thinking content for reasoning flaws, return directives."""
    if not thinking_blocks:
        return []

    # Combine recent thinking blocks
    combined = " ".join(thinking_blocks[-2:])[-2000:]
    detected_directives = []
    seen_names = set()
    flaws_detected = []

    for name, patterns, directive_msg, severity in THINKING_FLAW_PATTERNS:
        if name in seen_names:
            continue

        for pattern in patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                # Map severity to DirectiveStrength
                if severity == 0:
                    strength = DirectiveStrength.INFO
                elif severity == 1:
                    strength = DirectiveStrength.WARN
                else:
                    strength = DirectiveStrength.BLOCK

                detected_directives.append(Directive(
                    strength=strength,
                    category="thinking",
                    message=directive_msg,
                    time_saved="~15-30 min"
                ))
                seen_names.add(name)
                flaws_detected.append(name)
                break

    # Save telemetry
    if flaws_detected:
        save_telemetry(flaws_detected, combined)

    # Max 2 thinking-based directives (most severe)
    detected_directives.sort(key=lambda d: d.strength.value, reverse=True)
    return detected_directives[:2]


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
    transcript_path = input_data.get("transcript_path", "")

    # Skip for read-only tools (no risk of damage from flawed reasoning)
    if tool_name in {"Read", "Glob", "Grep", "TodoWrite", "BashOutput"}:
        output_hook_result("PreToolUse")
        sys.exit(0)

    # Skip if no transcript
    if not transcript_path:
        output_hook_result("PreToolUse")
        sys.exit(0)

    # Extract and analyze thinking blocks
    thinking_blocks = extract_thinking_blocks(transcript_path)

    if not thinking_blocks:
        output_hook_result("PreToolUse")
        sys.exit(0)

    # Analyze for flaws
    directives = analyze_thinking_for_flaws(thinking_blocks)

    if not directives:
        output_hook_result("PreToolUse")
        sys.exit(0)

    # Check for blocking directives (severity 2 = BLOCK)
    blocking = [d for d in directives if d.strength == DirectiveStrength.BLOCK]

    if blocking:
        # ENFORCE: Block on severe reasoning flaws
        output_hook_result(
            "PreToolUse",
            decision="deny",
            reason=(
                f"**THINKING COACH BLOCKED** (Severe reasoning flaw)\n\n"
                f"{blocking[0].format()}\n\n"
                f"Fix the reasoning issue before proceeding."
            )
        )
        sys.exit(0)

    # Format warnings
    context_lines = ["THINKING COACH:"]
    for d in directives:
        context_lines.append(d.format())

    output_hook_result("PreToolUse", context="\n\n".join(context_lines))
    sys.exit(0)


if __name__ == "__main__":
    main()
