#!/usr/bin/env python3
"""
PreCompact Hook: Fires before compaction.

Hook Type: PreCompact
Matcher: manual | auto
Latency Target: <50ms

Injects persistent context into compaction summary via stdout.
This context survives compaction and remains in Claude's memory.

Input: session_id, transcript_path, permission_mode, hook_event_name, trigger, custom_instructions
Output: stdout is added to compaction context
"""

import _lib_path  # noqa: F401
import sys
import json
from pathlib import Path

from session_state import load_state

PROJECT_ROOT = Path(__file__).parent.parent.parent


def get_critical_context(state) -> list[str]:
    """Extract context that MUST survive compaction."""
    context = []

    # Files modified this session
    if state.files_created:
        context.append(f"📁 CREATED: {len(state.files_created)} files")
        for f in state.files_created[-3:]:
            context.append(f"  • {Path(f).name}")

    if state.files_edited:
        context.append(f"✏️ EDITED: {len(state.files_edited)} files")

    # Pending work
    if state.pending_integration_greps:
        funcs = [p.get("function", "?") for p in state.pending_integration_greps[:3]]
        context.append(f"⚠️ UNVERIFIED: {', '.join(funcs)}")

    # Unresolved errors
    if state.errors_unresolved:
        context.append(f"❌ ERRORS: {len(state.errors_unresolved)} unresolved")

    # Libraries in use
    if state.libraries_used:
        context.append(f"📦 LIBS: {', '.join(state.libraries_used[:5])}")

    return context


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        data = {}

    trigger = data.get("trigger", "unknown")
    state = load_state()

    lines = [f"--- PreCompact ({trigger}) ---"]

    critical = get_critical_context(state)
    if critical:
        lines.extend(critical)
    else:
        lines.append("No critical context to preserve.")

    # Output goes to compaction context
    print("\n".join(lines))
    sys.exit(0)


if __name__ == "__main__":
    main()
