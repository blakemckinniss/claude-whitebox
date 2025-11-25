#!/usr/bin/env python3
"""
Protocol Enforcer Hook: Unified Protocol Registry Integration
Multi-Event Hook: UserPromptSubmit, PreToolUse, PostToolUse

Integrates with the Protocol Registry to evaluate registered rules
against the current situation and enforce them according to their level.

PHILOSOPHY:
- Single source of truth: Protocol Registry defines rules
- Multi-event: Works across different lifecycle stages
- Graduated enforcement: observe → suggest → warn → block
- Fast and safe: Wrapped in try/except for graceful degradation

INPUT FORMATS BY EVENT:
1. UserPromptSubmit: {"prompt": "...", "turn": N, "session_id": "..."}
2. PreToolUse: {"tool_name": "...", "tool_input": {...}, "turn": N, "session_id": "..."}
3. PostToolUse: {"tool_name": "...", "tool_input": {...}, "toolResult": {...}, "turn": N}

OUTPUT FORMATS:
- Suggestions/Warnings: {"hookSpecificOutput": {"hookEventName": "<event>", "additionalContext": "..."}}
- Blocks: {"decision": "block", "reason": "..."}
"""

import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any

# Constants
SUDO_CHECK_BUFFER = 5000  # Characters to check for SUDO keyword
MAX_TRANSCRIPT_SIZE = 50 * 1024 * 1024  # 50MB limit for safety

# Add scripts/lib to path
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

sys.path.insert(0, str(PROJECT_DIR / "scripts" / "lib"))

try:
    from protocol_registry import (
        ProtocolRegistry, SituationSnapshot, RuleMatch, EnforcementLevel,
        get_enforcement_context, ProtocolCategory, PROTECTED_CATEGORIES
    )
    from epistemology import load_session_state, initialize_session_state
except ImportError as e:
    # If imports fail, allow everything and exit gracefully
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "Unknown",
            "additionalContext": f"⚠️ Protocol Enforcer: Import error - {e}"
        }
    }))
    sys.exit(0)


def parse_input(data: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """
    Parse input data to determine event type and extract relevant fields.

    Returns:
        Tuple[str, Dict]: (event_type, parsed_data)
    """
    # Determine event type
    if "prompt" in data and "tool_name" not in data:
        event_type = "UserPromptSubmit"
    elif "tool_name" in data and "toolResult" not in data:
        event_type = "PreToolUse"
    elif "tool_name" in data and "toolResult" in data:
        event_type = "PostToolUse"
    else:
        event_type = "Unknown"

    return event_type, data


def extract_transcript_patterns(data: Dict[str, Any]) -> Optional[Dict]:
    """
    Extract patterns from recent transcript for context-aware rule evaluation.

    Returns dict with:
        - recent_tools: List of recent tool calls
        - error_count: Number of errors in recent transcript
        - fixed_claims: Whether "fixed/done/working" appeared recently
        - iteration_detected: Whether iteration patterns detected
    """
    transcript_path = data.get("transcript_path", "")
    if not transcript_path:
        return None

    try:
        import os
        import re
        if not os.path.exists(transcript_path):
            return None

        with open(transcript_path, 'r') as tf:
            transcript = tf.read()

        # Only analyze last 10000 chars for performance
        chunk = transcript[-10000:] if len(transcript) > 10000 else transcript

        # FIXED: Filter out tool output to avoid matching code patterns
        # Remove function_results blocks (tool output contains code)
        chunk = re.sub(r'<function_results>.*?</function_results>', '', chunk, flags=re.DOTALL)
        # Remove output blocks
        chunk = re.sub(r'<output>.*?</output>', '', chunk, flags=re.DOTALL)
        # Remove code blocks
        chunk = re.sub(r'```[\s\S]*?```', '', chunk)

        patterns = {
            "recent_tools": [],
            "error_count": 0,
            "fixed_claims": False,
            "iteration_detected": False,
        }

        # Count errors
        error_patterns = [r"Error:", r"FAILED", r"Exception", r"Traceback"]
        for ep in error_patterns:
            patterns["error_count"] += len(re.findall(ep, chunk, re.IGNORECASE))

        # Detect fixed claims
        fixed_patterns = [r"\b(fixed|done|working|complete|resolved)\b"]
        for fp in fixed_patterns:
            if re.search(fp, chunk, re.IGNORECASE):
                patterns["fixed_claims"] = True
                break

        # Detect iteration language
        iter_patterns = [r"for each", r"one by one", r"iterate", r"loop through"]
        for ip in iter_patterns:
            if re.search(ip, chunk, re.IGNORECASE):
                patterns["iteration_detected"] = True
                break

        # Extract recent tool names (simplified)
        tool_matches = re.findall(r'tool_name["\s:]+(\w+)', chunk)
        patterns["recent_tools"] = tool_matches[-10:] if tool_matches else []

        return patterns

    except (IOError, OSError):
        return None


def build_snapshot(event_type: str, data: Dict[str, Any], session_state: Optional[Dict]) -> SituationSnapshot:
    """
    Build SituationSnapshot from input data.

    Args:
        event_type: Event type (UserPromptSubmit, PreToolUse, PostToolUse)
        data: Raw input data
        session_state: Session state from epistemology

    Returns:
        SituationSnapshot for rule evaluation
    """
    turn = data.get("turn", 0)

    # Extract tool information
    tool_name = data.get("tool_name")
    tool_input = data.get("tool_input")

    # Extract tool output/error
    tool_result = data.get("tool_response") or data.get("toolResult", {})
    tool_output = None
    tool_error = None

    if isinstance(tool_result, dict):
        content = tool_result.get("content")
        if isinstance(content, list) and content:
            # Handle array format: [{"type": "text", "text": "..."}]
            tool_output = "\n".join(
                item.get("text", "") for item in content if isinstance(item, dict)
            )
        elif isinstance(content, str):
            tool_output = content

        tool_error = tool_result.get("error")

    # Extract prompt
    prompt = data.get("prompt")

    # Extract transcript patterns for context-aware rules
    transcript_summary = extract_transcript_patterns(data)

    # Build snapshot
    return SituationSnapshot(
        event_type=event_type,
        turn=turn,
        prompt=prompt,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output,
        tool_error=tool_error,
        session_state=session_state,
        transcript_summary=transcript_summary,
    )


def check_sudo_bypass(data: Dict[str, Any]) -> bool:
    """Check if SUDO keyword is in recent transcript."""
    transcript_path = data.get("transcript_path", "")
    if not transcript_path:
        return False

    try:
        import os
        if not os.path.exists(transcript_path):
            return False

        # Check file size to prevent memory exhaustion
        file_size = os.path.getsize(transcript_path)
        if file_size > MAX_TRANSCRIPT_SIZE:
            # For very large files, seek to end and read only last chunk
            with open(transcript_path, 'r') as tf:
                tf.seek(max(0, file_size - SUDO_CHECK_BUFFER))
                last_chunk = tf.read(SUDO_CHECK_BUFFER)
                return "SUDO" in last_chunk
        else:
            # For normal files, read and slice
            with open(transcript_path, 'r') as tf:
                transcript = tf.read()
                last_chunk = transcript[-SUDO_CHECK_BUFFER:] if len(transcript) > SUDO_CHECK_BUFFER else transcript
                return "SUDO" in last_chunk
    except (IOError, OSError) as e:
        # Log to stderr for debugging without corrupting JSON output
        print(f"⚠️ SUDO check failed: {type(e).__name__}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"⚠️ Unexpected error in SUDO check: {type(e).__name__}", file=sys.stderr)
        return False


def format_output(event_type: str, matches: list[RuleMatch], sudo_bypass: bool) -> Dict[str, Any]:
    """
    Format hook output based on rule matches.

    Args:
        event_type: Event type for hookEventName
        matches: List of rule matches (sorted by priority)
        sudo_bypass: Whether SUDO bypass is active

    Returns:
        Hook output dict
    """
    if not matches:
        # No violations, allow
        return {
            "hookSpecificOutput": {
                "hookEventName": event_type,
            }
        }

    # Get highest priority match
    highest_match = matches[0]

    # Check for SUDO bypass on blocks
    if sudo_bypass and highest_match.enforcement == EnforcementLevel.BLOCK:
        return {
            "hookSpecificOutput": {
                "hookEventName": event_type,
                "additionalContext": f"""⚠️ SUDO BYPASS: Protocol enforcement overridden

Rule: {highest_match.rule_id}
Original enforcement: BLOCK
Protocol: {highest_match.protocol}

{highest_match.message}

⚠️ Proceeding with SUDO override"""
            }
        }

    # Format messages by enforcement level
    if highest_match.enforcement == EnforcementLevel.BLOCK:
        # Hard block
        return {
            "decision": "block",
            "reason": highest_match.message
        }

    elif highest_match.enforcement == EnforcementLevel.WARN:
        # Warning - allow but inject strong message
        return {
            "hookSpecificOutput": {
                "hookEventName": event_type,
                "additionalContext": highest_match.message
            }
        }

    elif highest_match.enforcement == EnforcementLevel.SUGGEST:
        # Suggestion - allow with gentle message
        return {
            "hookSpecificOutput": {
                "hookEventName": event_type,
                "additionalContext": highest_match.message
            }
        }

    else:  # OBSERVE
        # Just track, don't inject anything
        return {
            "hookSpecificOutput": {
                "hookEventName": event_type,
            }
        }


def main():
    """Main hook logic"""
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Invalid JSON input - allow and exit gracefully
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "Unknown",
            }
        }))
        sys.exit(0)

    try:
        # Parse input
        event_type, parsed_data = parse_input(data)

        if event_type == "Unknown":
            # Unknown event type - allow
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "Unknown",
                }
            }))
            sys.exit(0)

        # Load session state
        session_id = data.get("session_id", "unknown")
        session_state = load_session_state(session_id)
        if not session_state:
            session_state = initialize_session_state(session_id)

        # Build situation snapshot
        snapshot = build_snapshot(event_type, data, session_state)

        # Get or create EnforcementContext for cross-event state sharing - SUDO
        # Use session_id + turn as request_id for context caching
        request_id = f"{session_id}_{data.get('turn', 0)}"
        context = get_enforcement_context(request_id)

        # Issue #3: Populate rolling aggregates from transcript patterns
        if snapshot.transcript_summary:
            ts = snapshot.transcript_summary
            context.error_count_rolling = ts.get("error_count", 0)
            context.tool_call_count = len(ts.get("recent_tools", []))

        # Issue #6: Track tool calls for risk assessment
        if event_type == "PreToolUse":
            context.increment_tool_calls()

        # Check for prior block in this request (short-circuit)
        if context.had_block():
            # A prior event already blocked - maintain consistency
            print(json.dumps({
                "decision": "block",
                "reason": "🚫 Prior event in this request was blocked. Maintaining consistency."
            }))
            sys.exit(0)

        # Initialize registry and evaluate with context (enables caching)
        registry = ProtocolRegistry()
        matches = registry.evaluate(snapshot, context=context)

        # Check for SUDO bypass
        sudo_bypass = check_sudo_bypass(data)

        # Record bypass for auto-tuning if SUDO used
        # CRITICAL: SAFETY category rules are NON-BYPASSABLE even with SUDO - SUDO
        if sudo_bypass and matches:
            for match in matches:
                # Check if this is a protected category (SAFETY, QUALITY)
                if match.category in PROTECTED_CATEGORIES and match.enforcement == EnforcementLevel.BLOCK:
                    # NON-BYPASSABLE: SAFETY/QUALITY blocks cannot be overridden
                    print(json.dumps({
                        "decision": "block",
                        "reason": f"""🛑 NON-BYPASSABLE SAFETY BLOCK

Rule: {match.rule_id}
Category: {match.category.value.upper()} (Protected)
Protocol: {match.protocol}

{match.message}

⛔ SUDO OVERRIDE DENIED: {match.category.value.upper()} category rules cannot be bypassed.
These rules protect against catastrophic failures and are immutable.
"""
                    }))
                    sys.exit(0)
                else:
                    # Record bypass for non-protected rules
                    registry.record_bypass(match.rule_id, "SUDO override")

        # Periodically run auto-tuning (every 50 evaluations)
        stats = registry.get_stats()
        if stats.get("total_evaluations", 0) % 50 == 0 and stats.get("total_evaluations", 0) > 0:
            tuning_changes = registry.auto_tune()
            if tuning_changes:
                # Log tuning changes to stderr (won't affect JSON output)
                import sys as _sys
                print(f"🔧 Auto-tuning applied: {tuning_changes}", file=_sys.stderr)

        # Format and output
        output = format_output(event_type, matches, sudo_bypass)
        print(json.dumps(output))
        sys.exit(0)

    except Exception as e:
        # Hook crashed - fail safe by allowing
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": data.get("tool_name", "Unknown"),
                "additionalContext": f"⚠️ Protocol Enforcer error (allowing): {type(e).__name__}"
            }
        }))
        sys.exit(0)


if __name__ == "__main__":
    main()
