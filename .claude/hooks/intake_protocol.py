#!/usr/bin/env python3
"""
Intake Protocol Hook - Structured checklist for every user prompt.

Theory: Having a visible, structured artifact that Claude fills out creates
stronger protocol adherence than scattered hook messages. The checklist
becomes evidence in context, creating "correlation of existence/relevance."

Flow:
1. Ingest user request
2. Assert initial confidence (L/M/H)
3. Consider: ask user? research? oracle/groq?
4. Assert adjusted confidence
5. If below threshold → hard stop
6. Plan action → agents → tools → execute

Tiered activation:
- TRIVIAL: Single obvious action, skip checklist
- MEDIUM: Multi-step but familiar, abbreviated checklist
- COMPLEX: Architectural/unfamiliar, full protocol with threshold gate
"""

import json
import os
import re
import sys
from pathlib import Path

# Add lib to path for session_state import
LIB_DIR = Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(LIB_DIR))

from session_state import load_state, save_state

# =============================================================================
# COMPLEXITY DETECTION
# =============================================================================

class Complexity:
    TRIVIAL = "trivial"
    MEDIUM = "medium"
    COMPLEX = "complex"

# Signals that increase complexity
COMPLEX_SIGNALS = [
    # Architectural
    r"\b(architect|design|refactor|migrate|restructure)\b",
    r"\b(system|infrastructure|deploy|production)\b",
    r"\b(integrate|integration|api|endpoint)\b",

    # Multi-component
    r"\b(multiple|several|all|every|across)\b",
    r"\b(database|auth|security|permission)\b",

    # Uncertainty markers
    r"\b(how|why|should|could|best|optimal)\b",
    r"\b(investigate|debug|diagnose|figure out)\b",

    # Scale indicators
    r"\b(feature|implement|build|create|add)\b.*\b(new|from scratch)\b",
]

# Signals that indicate triviality
TRIVIAL_SIGNALS = [
    r"^(fix|typo|update|change|rename)\s+\w+$",
    r"^(run|execute|test)\s+",
    r"^(commit|push|pr|status)\b",
    r"^(hi|hello|thanks|ok|yes|no)\b",
    r"^/\w+",  # Slash commands
    r"^(what is|where is|show me)\s+\w+",
]

# Length thresholds
SHORT_PROMPT = 50   # chars
MEDIUM_PROMPT = 200


def detect_complexity(prompt: str) -> str:
    """Detect prompt complexity for tiered activation."""
    prompt_lower = prompt.lower().strip()
    prompt_len = len(prompt)

    # Check trivial signals first
    for pattern in TRIVIAL_SIGNALS:
        if re.search(pattern, prompt_lower):
            return Complexity.TRIVIAL

    # Very short prompts are usually trivial
    if prompt_len < SHORT_PROMPT:
        return Complexity.TRIVIAL

    # Count complex signals
    complex_score = 0
    for pattern in COMPLEX_SIGNALS:
        if re.search(pattern, prompt_lower):
            complex_score += 1

    # Long prompts with multiple complex signals
    if prompt_len > MEDIUM_PROMPT and complex_score >= 2:
        return Complexity.COMPLEX

    # Multiple complex signals
    if complex_score >= 3:
        return Complexity.COMPLEX

    # Some complexity but not overwhelming
    if complex_score >= 1 or prompt_len > SHORT_PROMPT:
        return Complexity.MEDIUM

    return Complexity.TRIVIAL


# =============================================================================
# CHECKLIST TEMPLATES
# =============================================================================

CHECKLIST_FULL = """
┌─ INTAKE PROTOCOL ────────────────────────────────────────────┐
│ 📋 Request: [1-line summary]                                 │
│ 🎯 Confidence: [L/M/H] because [reason]                      │
│ ❓ Gaps: [what I don't know / need to verify]                │
│ 🔍 Boost: [ ] research  [ ] oracle  [ ] groq  [ ] ask user   │
│ 📊 Adjusted: [L/M/H] after [action taken]                    │
│ 🚦 Gate: [PROCEED / STOP - need X to continue]               │
├──────────────────────────────────────────────────────────────┤
│ 📝 Plan: [numbered steps]                                    │
│ 🤖 Agents: [scout/digest/parallel/chore if needed]           │
│ 🛠️ Tools: [specific tools to use]                            │
└──────────────────────────────────────────────────────────────┘
"""

CHECKLIST_ABBREVIATED = """
┌─ INTAKE ─────────────────────────────────┐
│ Request: [summary] | Conf: [L/M/H]       │
│ Gaps: [unknowns] | Boost: [if needed]    │
└──────────────────────────────────────────┘
"""

CHECKLIST_MINIMAL = "📋 [task] | 🎯 [H] | ▶️ executing"


# =============================================================================
# STATE TRACKING
# =============================================================================

def track_intake(state, complexity: str, prompt_preview: str):
    """Track intake protocol activation in session state."""
    if not hasattr(state, 'intake_history'):
        state.intake_history = []

    state.intake_history.append({
        "turn": state.turn_count,
        "complexity": complexity,
        "prompt_preview": prompt_preview[:50],
    })

    # Keep last 10
    state.intake_history = state.intake_history[-10:]


def clear_stop_hook_flags():
    """Clear stop hook flags on new user message to allow fresh detection."""
    import os
    session_id = os.environ.get("CLAUDE_SESSION_ID", "default")[:16]
    memory_dir = Path(__file__).parent.parent / "memory"
    dismissal_flag = memory_dir / f"dismissal_shown_{session_id}.flag"
    if dismissal_flag.exists():
        try:
            dismissal_flag.unlink()
        except (IOError, OSError):
            pass


# =============================================================================
# MAIN
# =============================================================================

def main():
    # Clear stop hook flags on new user message (allows fresh detection each turn)
    clear_stop_hook_flags()

    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return  # Silent fail on bad input

    # Extract user prompt
    prompt = ""
    if hook_input.get("type") == "UserPromptSubmit":
        session_data = hook_input.get("session", {})
        messages = session_data.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if last_msg.get("role") == "user":
                content = last_msg.get("content", "")
                if isinstance(content, str):
                    prompt = content
                elif isinstance(content, list):
                    # Handle list of content blocks
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            prompt = block.get("text", "")
                            break
                        elif isinstance(block, str):
                            prompt = block
                            break

    if not prompt:
        return  # No prompt to analyze

    # Detect complexity
    complexity = detect_complexity(prompt)

    # Load state and track
    state = load_state()
    track_intake(state, complexity, prompt)
    save_state(state)

    # Output appropriate checklist template
    if complexity == Complexity.COMPLEX:
        print("🔬 COMPLEX TASK DETECTED - Full protocol required:")
        print(CHECKLIST_FULL)
        print("\n⚠️ THRESHOLD: If Confidence < M after boost attempts, STOP and clarify with user.")

    elif complexity == Complexity.MEDIUM:
        print("📋 Multi-step task - Abbreviated intake:")
        print(CHECKLIST_ABBREVIATED)

    # TRIVIAL: No output, don't clutter context


if __name__ == "__main__":
    main()
