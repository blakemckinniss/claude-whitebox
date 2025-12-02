#!/usr/bin/env python3
"""
Stop Cleanup Hook: Fires when Claude stops responding.

Hook Type: Stop
Latency Target: <100ms

Checks:
- Files created with stubs/TODOs (abandoned work)
- Pending integration greps (incomplete verification)
- Unresolved errors
- **SESSION BLOCKS** - Forces reflection if hooks blocked during session

VALID OUTPUT SCHEMA (Stop hooks):
{
    "decision": "block",     # Forces Claude to continue
    "reason": string         # Why continuation is required
}

NOTE: Stop hooks can BLOCK task completion to force reflection.
"""

import _lib_path  # noqa: F401
import sys
import json
from pathlib import Path

from session_state import load_state
from synapse_core import get_session_blocks, clear_session_blocks

# =============================================================================
# CONFIGURATION
# =============================================================================

# Buffer sizes for transcript scanning
ACK_SCAN_BYTES = 20000      # 20KB for acknowledgment detection (need history)
DISMISSAL_SCAN_BYTES = 20000  # 20KB for dismissal detection (needs to see both claim and fix)

# Limits
MAX_CREATED_FILES_SCAN = 10  # How many recently created files to check

# Stub patterns to detect in created files
# Use comment markers to avoid false positives on docstring examples
STUB_PATTERNS = [
    b'# TODO',
    b'# FIXME',
    b'NotImplementedError',
    b'raise NotImplementedError',
    b'pass  #',
    b'...  #',
]

CODE_EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.rs', '.go', '.java'}

# Patterns that indicate Claude is dismissing hook feedback
DISMISSAL_PATTERNS = [
    (r"false positive", "false_positive"),
    (r"warning is (a )?false", "false_positive"),
    (r"hook (is )?(wrong|incorrect|mistaken)", "hook_dismissal"),
    (r"ignore (this|the) (warning|hook|gate)", "ignore_warning"),
    (r"(that|this) warning (is )?(incorrect|wrong)", "false_positive"),
]


def check_acknowledgments_in_transcript(transcript_path: str) -> tuple[bool, bool, list[str]]:
    """Check for acknowledgments in transcript.

    Returns: (has_substantive_ack, has_any_ack, lessons)
      - substantive: "Block valid: [actual lesson text]" (10+ chars after colon)
      - mechanical: just "Block valid" without lesson
      - lessons: list of extracted lesson strings
    """
    import re

    if not transcript_path or not Path(transcript_path).exists():
        return False, False, []

    try:
        with open(transcript_path, 'r') as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - ACK_SCAN_BYTES))
            content = f.read()

        # Substantive: "Block valid: [lesson with 10+ chars]"
        # Capture the lesson text (up to newline or 200 chars)
        substantive_matches = re.findall(
            r'[Bb]lock valid:\s*(.{10,200}?)(?:\n|$)',
            content
        )
        lessons = [m.strip() for m in substantive_matches if m.strip()]

        # Any acknowledgment (including mechanical)
        any_ack = re.search(r'[Bb]lock valid', content)

        return bool(lessons), bool(any_ack), lessons

    except (IOError, OSError):
        return False, False, []


def persist_lessons_to_memory(lessons: list[str], blocks: list[dict]) -> None:
    """Write block lessons to __lessons.md for cross-session persistence."""
    from datetime import datetime

    if not lessons:
        return

    # Get hook names from blocks for context
    hook_names = list(set(b.get("hook", "unknown") for b in blocks))
    hooks_str = ", ".join(hook_names[:3])

    lessons_file = Path(__file__).parent.parent / "memory" / "__lessons.md"
    if not lessons_file.exists():
        return

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entries = []
        for lesson in lessons:
            # Clean up the lesson text
            lesson = lesson.strip().rstrip('.')
            entries.append(
                f"\n### {timestamp}\n"
                f"[block-reflection:{hooks_str}] {lesson}\n"
            )

        with open(lessons_file, 'a') as f:
            f.writelines(entries)

    except (IOError, OSError):
        pass  # Don't crash hook if write fails


def check_dismissals_in_transcript(transcript_path: str) -> list[str]:
    """Check if Claude claimed any false positives without fixing them.

    Only checks the MOST RECENT portion of transcript (last 2KB) to avoid
    re-triggering on old addressed claims.

    If a hook/lib file was edited AFTER the claim, assume it was fixed.
    """
    import re

    if not transcript_path or not Path(transcript_path).exists():
        return []

    warnings = []
    try:
        with open(transcript_path, 'r') as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - DISMISSAL_SCAN_BYTES))
            content = f.read()

        content_lower = content.lower()

        # Check if a hook/lib file was edited (evidence of fix attempt)
        # Look for Edit tool calls to .claude/hooks/ or .claude/lib/
        fix_evidence = re.search(r'\.claude/(hooks|lib)/\w+\.py', content)

        # If hook/lib was edited in same window as claim, assume fix in progress
        if fix_evidence:
            return []

        for pattern, dismissal_type in DISMISSAL_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE):
                warnings.append(f"  • `{dismissal_type}`: Claude claimed hook feedback was wrong")

    except (IOError, OSError):
        pass

    return warnings


def check_stubs_in_created_files(state) -> list[str]:
    """Check created files for stubs."""
    warnings = []

    for filepath in state.files_created[-MAX_CREATED_FILES_SCAN:]:
        path = Path(filepath)
        if not path.exists() or path.suffix not in CODE_EXTENSIONS:
            continue

        try:
            content = path.read_bytes()
            stubs = [p.decode() for p in STUB_PATTERNS if p in content]
            if stubs:
                warnings.append(f"  • `{path.name}`: {', '.join(stubs[:2])}")
        except (OSError, PermissionError):
            pass

    return warnings


def main():
    input_data = {}
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        pass

    transcript_path = input_data.get("transcript_path", "")
    try:
        state = load_state()
    except Exception:
        # State corrupted - continue with defaults, don't crash hook
        from session_state import SessionState
        state = SessionState()
    messages = []
    must_reflect = False

    # Check for SESSION BLOCKS first (need blocks for lesson context)
    blocks = get_session_blocks()

    # Check for acknowledgments
    substantive_ack, any_ack, lessons = check_acknowledgments_in_transcript(transcript_path)

    if substantive_ack:
        # Substantive lesson provided - persist to memory, clear blocks
        persist_lessons_to_memory(lessons, blocks)
        clear_session_blocks()
    if blocks:
        # Group by hook AND function for better context
        hook_details = {}
        for b in blocks:
            hook = b.get("hook", "unknown")
            func = b.get("function", "")
            key = f"{hook}" + (f" ({func})" if func else "")
            hook_details[key] = hook_details.get(key, 0) + 1

        # If mechanical ack but no substantive lesson, show soft warning
        if any_ack and not substantive_ack:
            messages.append("⚠️ **BLOCKS ACKNOWLEDGED** - but no lesson captured:")
            for detail, count in sorted(hook_details.items(), key=lambda x: -x[1])[:3]:
                messages.append(f"  • `{detail}`: {count}x")
            messages.append("\n**TIP:** 'Block valid: [lesson]' captures why it happened.")
            clear_session_blocks()
        else:
            # No acknowledgment - require reflection
            must_reflect = True
            messages.append("🚨 **SESSION BLOCKS DETECTED** - Reflection required:")
            for detail, count in sorted(hook_details.items(), key=lambda x: -x[1])[:5]:
                messages.append(f"  • `{detail}`: {count}x")

            last_block = blocks[-1]
            reason_preview = last_block.get("reason", "")[:100]
            if reason_preview:
                messages.append(f"\n  Last block: {reason_preview}...")

            messages.append("\n**REFLECT:** Why did these blocks fire? How to avoid next time?")
            clear_session_blocks()

    # Check for FALSE POSITIVE claims - these require hook FIX, not just acknowledgment
    # Block keeps firing until Claude actually fixes the hook (stops claiming false positive)
    dismissals = check_dismissals_in_transcript(transcript_path)
    if dismissals:
        must_reflect = True
        messages.append("🔧 **FALSE POSITIVE CLAIMED** - Fix required:")
        messages.extend(dismissals)
        messages.append("\n**REQUIRED:** Fix the hook that fired incorrectly. This block repeats until fixed.")

    # Check for abandoned stubs
    stub_warnings = check_stubs_in_created_files(state)
    if stub_warnings:
        messages.append("⚠️ **ABANDONED WORK** - Files with stubs:")
        messages.extend(stub_warnings)

    # Check for pending integration greps
    pending = state.pending_integration_greps
    if pending:
        funcs = [p.get("function", "unknown") for p in pending[:3]]
        messages.append(f"⚠️ **UNVERIFIED EDITS** - Functions need grep: {', '.join(funcs)}")

    # Check for unresolved errors
    if state.errors_unresolved:
        error = state.errors_unresolved[-1]
        messages.append(f"⚠️ **UNRESOLVED ERROR**: {error.get('type', 'unknown')[:50]}")

    # Output
    if must_reflect:
        # BLOCK completion - force reflection
        output = {
            "decision": "block",
            "reason": "\n".join(messages)
        }
        print(json.dumps(output))
    elif messages:
        # Just warn
        output = {
            "stopReason": "\n".join(messages)
        }
        print(json.dumps(output))
    else:
        # Explicit success - no issues found
        print(json.dumps({"status": "pass", "message": "No cleanup issues detected"}))

    sys.exit(0)


if __name__ == "__main__":
    main()
