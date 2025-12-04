#!/usr/bin/env python3
"""
Recommendation Gate Hook: Blocks "create X" suggestions without verification.

Hook Type: PreToolUse (on Edit|Write)
Purpose: Prevent recommending creation of infrastructure that already exists.

THE PROBLEM:
Claude makes confident recommendations like "create bootstrap.sh" without
checking if similar infrastructure already exists. This erodes user trust.

THE FIX:
Before writing files with names suggesting new infrastructure, check if
similar files exist. Block with "VERIFY FIRST" if patterns match.

Targets:
- setup*.sh, bootstrap*.sh, init*.sh
- *_gate.py, *_hook.py (new hooks)
- INFRASTRUCTURE.md, MANIFEST.md (meta docs)
"""

import sys
import json
import re
from pathlib import Path

# =============================================================================
# CONFIG
# =============================================================================

CLAUDE_DIR = Path(__file__).parent.parent
PROJECT_ROOT = CLAUDE_DIR.parent

# Patterns that suggest infrastructure creation (case-insensitive)
INFRASTRUCTURE_PATTERNS = [
    # Setup/bootstrap scripts
    r"setup[_-]?\w*\.sh$",
    r"bootstrap[_-]?\w*\.sh$",
    r"init[_-]?\w*\.sh$",
    r"install[_-]?\w*\.sh$",

    # Hook creation
    r"\.claude/hooks/\w+_gate\.py$",
    r"\.claude/hooks/\w+_hook\.py$",
    r"\.claude/hooks/\w+_injector\.py$",
    r"\.claude/hooks/\w+_tracker\.py$",

    # Ops tool creation
    r"\.claude/ops/\w+\.py$",

    # Meta documentation
    r"INFRASTRUCTURE\.md$",
    r"MANIFEST\.md$",
    r"BOOTSTRAP\.md$",
]

# Directories to check for existing similar files
SEARCH_DIRS = [
    CLAUDE_DIR / "config",
    CLAUDE_DIR / "hooks",
    CLAUDE_DIR / "ops",
    PROJECT_ROOT,
]

# =============================================================================
# DETECTION
# =============================================================================

def matches_infrastructure_pattern(filepath: str) -> bool:
    """Check if filepath matches infrastructure creation patterns."""
    for pattern in INFRASTRUCTURE_PATTERNS:
        if re.search(pattern, filepath, re.IGNORECASE):
            return True
    return False


def find_similar_files(filepath: str) -> list[str]:
    """Find existing files similar to the proposed one."""
    similar = set()  # Use set to avoid duplicates
    proposed_name = Path(filepath).name.lower()
    proposed_ext = Path(filepath).suffix.lower()

    # Extract base concept (e.g., "setup" from "setup_new.sh")
    base_match = re.match(r"(\w+)[_-]", proposed_name)
    base_concept = base_match.group(1) if base_match else proposed_name.split(".")[0]

    # Extract suffix pattern (e.g., "_gate" from "new_gate.py")
    suffix_match = re.search(r"[_-](\w+)\.py$", proposed_name)
    suffix_pattern = suffix_match.group(1) if suffix_match else None

    for search_dir in SEARCH_DIRS:
        if not search_dir.exists():
            continue
        try:
            for f in search_dir.rglob("*"):
                if not f.is_file():
                    continue
                fname = f.name.lower()

                # Skip files without same extension
                if f.suffix.lower() != proposed_ext:
                    continue

                # Skip very short filenames (like "py")
                if len(fname) < 4:
                    continue

                # Check for concept overlap
                concept_match = base_concept in fname and len(base_concept) > 2
                # Check for suffix pattern match (e.g., both are *_gate.py)
                suffix_match = suffix_pattern and f"_{suffix_pattern}." in fname

                if concept_match or suffix_match:
                    try:
                        rel_path = f.relative_to(PROJECT_ROOT)
                    except ValueError:
                        rel_path = f
                    similar.add(str(rel_path))
        except (PermissionError, OSError):
            continue

    return sorted(similar)[:5]  # Limit to 5 matches


def format_block_message(filepath: str, similar: list[str]) -> str:
    """Format the blocking message."""
    lines = [
        "",
        "🛑 **INFRASTRUCTURE CREATION BLOCKED**",
        f"   Proposed: `{filepath}`",
        "",
        "   **Similar files already exist:**",
    ]
    for s in similar:
        lines.append(f"   - `{s}`")

    lines.extend([
        "",
        "   **Before creating new infrastructure:**",
        "   1. Read the existing files above",
        "   2. Verify they don't already solve the problem",
        "   3. If modification needed, edit existing file",
        "   4. Only create new if truly different purpose",
        "",
        "   To proceed anyway: acknowledge you've read the existing files.",
        "",
    ])
    return "\n".join(lines)


# =============================================================================
# HOOK INTERFACE
# =============================================================================

def main():
    """PreToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only check Write tool (Edit implies file exists)
    if tool_name != "Write":
        print(json.dumps({}))
        sys.exit(0)

    filepath = tool_input.get("file_path", "")
    if not filepath:
        print(json.dumps({}))
        sys.exit(0)

    # Check if this looks like infrastructure creation
    if not matches_infrastructure_pattern(filepath):
        print(json.dumps({}))
        sys.exit(0)

    # Find similar existing files
    similar = find_similar_files(filepath)

    if similar:
        # Block with verification requirement
        message = format_block_message(filepath, similar)
        result = {
            "decision": "block",
            "reason": message,
        }
        print(json.dumps(result))
        sys.exit(0)

    # No similar files found - allow but warn
    result = {
        "decision": "allow",
        "message": f"⚠️ Creating new infrastructure: {Path(filepath).name}. Verify no similar exists.",
    }
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
