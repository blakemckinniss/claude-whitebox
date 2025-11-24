#!/usr/bin/env python3
"""
THE INTROSPECTOR HOOK
=====================
Meta-cognition injection system for proactive tool/protocol suggestions
and self-reflective prompts based on semantic analysis.

TRIGGER: UserPromptSubmit
OUTPUT: additionalContext with semantic nudges and meta-questions

Philosophy: Inject "Aha!" moments and self-questioning before Claude starts coding.
            Prevent common failure modes (XY problems, iteration loops, unverified claims).
            Suggest the RIGHT tool/protocol BEFORE user asks.

Examples of injected context:
  • "🎭 PLAYWRIGHT SIGNAL: This requires browser automation..."
  • "🤔 What is the user REALLY trying to achieve?"
  • "⚠️ VERIFICATION GAP: Claims require proof..."
  • "🔬 RESEARCH SIGNAL: Your knowledge may be stale..."
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def find_project_root():
    """Find project root by looking for scripts/lib/core.py"""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "scripts" / "lib" / "core.py").exists():
            return current
        current = current.parent

    # Fallback: Log warning
    fallback = Path.cwd()
    print(f"WARNING: Could not find project root (scripts/lib/core.py), using cwd: {fallback}", file=sys.stderr)
    return fallback


PROJECT_ROOT = find_project_root()
PATTERNS_FILE = PROJECT_ROOT / ".claude" / "memory" / "metacognition_patterns.json"
CONFIDENCE_STATE = PROJECT_ROOT / ".claude" / "memory" / "confidence_state.json"


def load_patterns() -> Dict:
    """Load metacognition patterns"""
    if not PATTERNS_FILE.exists():
        print(f"WARNING: Pattern file not found: {PATTERNS_FILE}", file=sys.stderr)
        return {"semantic_signals": {}, "context_aware_nudges": {}, "metacognitive_questions": []}
    try:
        with open(PATTERNS_FILE) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Malformed pattern JSON: {e}", file=sys.stderr)
        return {"semantic_signals": {}, "context_aware_nudges": {}, "metacognitive_questions": []}
    except Exception as e:
        print(f"ERROR: Failed to load patterns: {type(e).__name__}: {e}", file=sys.stderr)
        return {"semantic_signals": {}, "context_aware_nudges": {}, "metacognitive_questions": []}


def load_confidence() -> int:
    """Load current confidence level"""
    if not CONFIDENCE_STATE.exists():
        return 0
    try:
        with open(CONFIDENCE_STATE) as f:
            data = json.load(f)
            return data.get("confidence", 0)
    except json.JSONDecodeError as e:
        print(f"ERROR: Malformed confidence JSON: {e}", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"ERROR: Failed to load confidence: {type(e).__name__}: {e}", file=sys.stderr)
        return 0


def load_session_state(session_id: str) -> Dict:
    """Load session state for context-aware nudges"""
    state_file = PROJECT_ROOT / ".claude" / "memory" / f"session_{session_id}_state.json"
    default_state = {"tools_used": [], "read_files": [], "turn_count": 0}

    if not state_file.exists():
        return default_state

    try:
        with open(state_file) as f:
            state = json.load(f)

            # Schema validation: ensure expected keys exist and are correct types
            if not isinstance(state.get("tools_used", []), list):
                print(f"WARNING: session_state.tools_used is not a list, using default", file=sys.stderr)
                state["tools_used"] = []
            if not isinstance(state.get("read_files", []), list):
                print(f"WARNING: session_state.read_files is not a list, using default", file=sys.stderr)
                state["read_files"] = []
            if not isinstance(state.get("turn_count", 0), int):
                print(f"WARNING: session_state.turn_count is not an int, using default", file=sys.stderr)
                state["turn_count"] = 0

            return state
    except json.JSONDecodeError as e:
        print(f"ERROR: Malformed session state JSON: {e}", file=sys.stderr)
        return default_state
    except Exception as e:
        print(f"ERROR: Failed to load session state: {type(e).__name__}: {e}", file=sys.stderr)
        return default_state


def detect_semantic_signals(prompt: str, confidence: int, patterns: Dict) -> List[Tuple[str, str, int]]:
    """
    Detect semantic signals in user prompt.
    Returns: List of (signal_name, nudge, priority_score)
    """
    signals = []
    prompt_lower = prompt.lower()

    for signal_name, config in patterns.get("semantic_signals", {}).items():
        # Check confidence threshold
        threshold = config.get("confidence_threshold", 0)
        if confidence < threshold:
            continue

        # Check pattern matches
        pattern_list = config.get("patterns", [])
        matched = False
        for pattern in pattern_list:
            try:
                if re.search(pattern, prompt_lower, re.IGNORECASE):
                    matched = True
                    break
            except re.error as e:
                # Log regex errors for debugging
                print(f"WARNING: Invalid regex in signal '{signal_name}': {pattern} - {e}", file=sys.stderr)
                continue

        if matched:
            nudge = config.get("nudge_template", "")
            priority = config.get("priority", "medium")

            # Convert priority to score
            priority_score = {"critical": 3, "high": 2, "medium": 1, "low": 0}.get(priority, 1)

            # Safe format: Try to format with common placeholders
            try:
                nudge = nudge.format(
                    query=prompt[:50],
                    task=prompt[:100],
                    library=extract_library(prompt),
                    file=extract_file(prompt),
                    proposal=prompt[:80],
                    object=extract_library(prompt),  # for probe patterns
                    test="<test command>",  # default placeholder
                    test_command="<test command>",
                )
            except (KeyError, ValueError) as e:
                # Log formatting failure but continue with raw template
                print(f"WARNING: Format error in signal '{signal_name}': {e}", file=sys.stderr)
                # nudge stays as raw template string

            signals.append((signal_name, nudge, priority_score))

    return signals


def extract_library(prompt: str) -> str:
    """Extract library name from prompt"""
    libs = ["playwright", "fastapi", "pandas", "boto3", "sqlalchemy", "requests", "anthropic", "openai"]
    prompt_lower = prompt.lower()
    for lib in libs:
        if lib in prompt_lower:
            return lib
    return "library"


def extract_file(prompt: str) -> str:
    """Extract file path from prompt"""
    match = re.search(r'[\w/]+\.py', prompt)
    if match:
        return match.group(0)
    return "file"


def check_context_aware_nudges(session_state: Dict, confidence: int, patterns: Dict, prompt: str) -> List[Tuple[str, str, int]]:
    """
    Check context-aware conditions (session state, tool usage, etc.)
    Returns: List of (condition_name, nudge, priority_score)
    """
    nudges = []
    tools_used = session_state.get("tools_used", [])
    read_files = session_state.get("read_files", [])
    turn_count = session_state.get("turn_count", 0)

    # Low confidence coding
    if confidence < 30 and ("Write" in tools_used[-5:] or "Edit" in tools_used[-5:]):
        nudge = patterns.get("context_aware_nudges", {}).get("low_confidence_coding", {}).get("nudge_template", "")
        try:
            nudge = nudge.format(confidence=confidence)
        except (KeyError, ValueError) as e:
            print(f"WARNING: Format error in low_confidence_coding nudge: {e}", file=sys.stderr)
        nudges.append(("low_confidence_coding", nudge, 3))

    # Tool loop detection
    if len(tools_used) >= 5:
        recent_tools = tools_used[-5:]
        for tool_name in set(recent_tools):
            count = recent_tools.count(tool_name)
            if count >= 4:
                nudge = patterns.get("context_aware_nudges", {}).get("tool_loop", {}).get("nudge_template", "")
                try:
                    nudge = nudge.format(tool_name=tool_name, count=count)
                except (KeyError, ValueError) as e:
                    print(f"WARNING: Format error in tool_loop nudge: {e}", file=sys.stderr)
                nudges.append(("tool_loop", nudge, 2))

    # Unverified claim (check if prompt contains "fixed"/"done" and no recent verify)
    if re.search(r'\b(fixed|done|completed|working|solved)\b', prompt.lower()):
        recent_verify = any("verify" in tool.lower() for tool in tools_used[-10:])
        if not recent_verify:
            nudge = patterns.get("context_aware_nudges", {}).get("unverified_claim", {}).get("nudge_template", "")
            try:
                nudge = nudge.format(test_command="<your test command>")
            except (KeyError, ValueError) as e:
                print(f"WARNING: Format error in unverified_claim nudge: {e}", file=sys.stderr)
            nudges.append(("unverified_claim", nudge, 3))

    # External budget (swarm/oracle in prompt)
    if re.search(r'\b(swarm|oracle|council)\b', prompt.lower()) and turn_count < 5:
        tool_match = re.search(r'\b(swarm|oracle|council)\b', prompt.lower())
        if tool_match:
            nudge = patterns.get("context_aware_nudges", {}).get("external_budget", {}).get("nudge_template", "")
            try:
                nudge = nudge.format(tool=tool_match.group(1))
            except (KeyError, ValueError) as e:
                print(f"WARNING: Format error in external_budget nudge: {e}", file=sys.stderr)
            nudges.append(("external_budget", nudge, 2))

    # Missing upkeep (commit in prompt, no upkeep in recent tools)
    if re.search(r'\b(commit|push|pr|pull request)\b', prompt.lower()):
        recent_upkeep = any("upkeep" in tool.lower() for tool in tools_used[-20:])
        if not recent_upkeep:
            nudge = patterns.get("context_aware_nudges", {}).get("missing_upkeep", {}).get("nudge_template", "")
            # No formatting needed for this nudge
            nudges.append(("missing_upkeep", nudge, 3))

    return nudges


def select_metacognitive_question(patterns: Dict) -> Optional[str]:
    """
    Select a random metacognitive question to inject (15% probability).
    Returns: Question string or None
    """
    import random

    questions = patterns.get("metacognitive_questions", [])
    if not questions:
        return None

    probability = patterns.get("meta", {}).get("question_rotation_probability", 0.15)
    if random.random() < probability:
        return random.choice(questions)

    return None


def build_context_message(signals: List[Tuple], context_nudges: List[Tuple], meta_question: Optional[str], max_nudges: int = 3) -> str:
    """
    Build the final additional context message.
    Prioritize by score, limit to max_nudges.
    """
    # Combine and sort by priority
    all_nudges = signals + context_nudges
    all_nudges.sort(key=lambda x: x[2], reverse=True)  # Sort by priority score

    # Limit to top N
    top_nudges = all_nudges[:max_nudges]

    if not top_nudges and not meta_question:
        return ""

    lines = ["\n🧠 META-COGNITION INTROSPECTION:"]

    # Add nudges
    for _, nudge, _ in top_nudges:
        lines.append(f"\n{nudge}")

    # Add meta-question if present
    if meta_question:
        lines.append(f"\n{meta_question}")

    lines.append("")  # Blank line at end

    return "\n".join(lines)


def output_context(context: str):
    """Output the hook result with context"""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }))
    sys.exit(0)


def main():
    # Load input
    try:
        input_data = json.load(sys.stdin)
    except:
        output_context("")

    prompt = input_data.get("prompt", "")
    session_id = input_data.get("session_id", "")

    if not prompt:
        output_context("")

    # Load patterns and state
    patterns = load_patterns()
    confidence = load_confidence()
    session_state = load_session_state(session_id)

    # Detect semantic signals
    semantic_signals = detect_semantic_signals(prompt, confidence, patterns)

    # Check context-aware nudges
    context_nudges = check_context_aware_nudges(session_state, confidence, patterns, prompt)

    # Select metacognitive question
    meta_question = select_metacognitive_question(patterns)

    # Build final context message
    max_nudges = patterns.get("meta", {}).get("max_nudges_per_turn", 3)
    context = build_context_message(semantic_signals, context_nudges, meta_question, max_nudges)

    # Output
    output_context(context)


if __name__ == "__main__":
    main()
