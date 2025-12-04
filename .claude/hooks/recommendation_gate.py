#!/usr/bin/env python3
"""
Recommendation Gate Hook: Blocks duplicate functionality creation.

Hook Type: PreToolUse (on Edit|Write)
Purpose: Prevent creating infrastructure/functionality that already exists.

THE PROBLEM:
Claude forgets what exists between sessions and proposes "new" functionality
that duplicates existing capabilities. This creates organizational debt.

THE FIX:
1. Check for similar FILENAMES (setup*.sh when setup_claude.sh exists)
2. Check for similar FUNCTIONALITY using capabilities.json (semantic match)
3. Block with list of existing capabilities to read first

Targets:
- setup*.sh, bootstrap*.sh, init*.sh
- *_gate.py, *_hook.py, *_injector.py, *_tracker.py
- *.py in .claude/ops/
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
MEMORY_DIR = CLAUDE_DIR / "memory"
CAPABILITIES_FILE = MEMORY_DIR / "__capabilities.json"

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


def load_capabilities() -> list[dict]:
    """Load capabilities index for functional similarity checking."""
    if not CAPABILITIES_FILE.exists():
        return []
    try:
        return json.loads(CAPABILITIES_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return []


def find_functional_overlaps(filepath: str) -> list[dict]:
    """Find existing capabilities that might overlap functionally.

    Extracts keywords from the proposed filename and finds capabilities
    with matching terms in their name or summary.
    """
    capabilities = load_capabilities()
    if not capabilities:
        return []

    proposed_name = Path(filepath).stem.lower()

    # Extract meaningful keywords from proposed name
    # e.g., "security_validator_gate" -> ["security", "validator", "gate"]
    keywords = re.split(r"[_\-]", proposed_name)
    keywords = [k for k in keywords if len(k) > 2]  # Skip short words

    # Also check for compound concepts
    compound_concepts = {
        "security": ["audit", "vulnerability", "injection", "xss"],
        "validate": ["check", "verify", "gate"],
        "track": ["monitor", "velocity", "state"],
        "inject": ["context", "surface", "pointer"],
        "memory": ["remember", "lesson", "decision", "spark"],
        "scope": ["goal", "drift", "anchor"],
        "error": ["suppression", "resolve", "fix"],
    }

    # Expand keywords with related concepts
    expanded = set(keywords)
    for kw in keywords:
        if kw in compound_concepts:
            expanded.update(compound_concepts[kw])

    # Find matching capabilities
    matches = []
    for cap in capabilities:
        cap_text = f"{cap.get('name', '')} {cap.get('summary', '')}".lower()
        score = sum(1 for kw in expanded if kw in cap_text)
        if score >= 2:  # Require at least 2 keyword matches
            matches.append({
                "name": cap.get("name", ""),
                "summary": cap.get("summary", "")[:60],
                "category": cap.get("category", ""),
                "score": score,
            })

    # Sort by score and return top matches
    matches.sort(key=lambda x: -x["score"])
    return matches[:5]


def format_block_message(filepath: str, similar: list[str], functional: list[dict] = None) -> str:
    """Format the blocking message."""
    lines = [
        "",
        "🛑 **DUPLICATE FUNCTIONALITY BLOCKED**",
        f"   Proposed: `{filepath}`",
        "",
    ]

    if similar:
        lines.append("   **Similar FILES already exist:**")
        for s in similar:
            lines.append(f"   - `{s}`")
        lines.append("")

    if functional:
        lines.append("   **Similar FUNCTIONALITY already exists:**")
        for f in functional:
            lines.append(f"   - `{f['name']}` - {f['summary']}")
        lines.append("")

    lines.extend([
        "   **Before creating new functionality:**",
        "   1. Read `.claude/memory/__capabilities.md` for full index",
        "   2. Read the existing implementations listed above",
        "   3. Verify they don't already solve the problem",
        "   4. If extending needed, edit existing file",
        "   5. Only create new if truly DIFFERENT purpose",
        "",
        "   To proceed: state which existing capability is insufficient and why.",
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

    # Find functionally similar capabilities
    functional = find_functional_overlaps(filepath)

    if similar or functional:
        # Block with verification requirement
        message = format_block_message(filepath, similar, functional)
        result = {
            "decision": "block",
            "reason": message,
        }
        print(json.dumps(result))
        sys.exit(0)

    # No similar files or functionality found - allow but warn
    result = {
        "decision": "allow",
        "message": f"⚠️ Creating new: {Path(filepath).name}. Read __capabilities.md first.",
    }
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
