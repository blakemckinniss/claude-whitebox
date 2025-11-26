#!/usr/bin/env python3
"""
Epistemic Boundary Enforcer: Catches claims not backed by session evidence.

Hook Type: PreToolUse (on Edit/Write)
Purpose: Detect when Claude claims to "know" something without session evidence.

THE INSIGHT:
Claude confabulates from training data. "The function returns a dict" may be
plausible but NOT observed this session. This hook cross-references claims
in the code being written against files actually read.

Detection:
1. Extract identifiers being used in new code (function names, classes, variables)
2. Check if the file defining them was Read this session
3. If not: "UNVERIFIED CLAIM: You're using X but never read its definition"

Different from assumption_ledger:
- assumption_ledger: LLM-based analysis of implicit assumptions
- epistemic_boundary: Rule-based check of session evidence
"""

import sys
import json
import re
from pathlib import Path

# Import session state
from session_state import load_state

# =============================================================================
# CONFIG
# =============================================================================

# Common identifiers to SKIP (stdlib, builtins, common patterns)
SKIP_IDENTIFIERS = {
    # Python builtins
    "print", "len", "str", "int", "float", "list", "dict", "set", "tuple",
    "True", "False", "None", "self", "cls", "super", "type", "isinstance",
    "open", "range", "enumerate", "zip", "map", "filter", "sorted", "reversed",
    "min", "max", "sum", "any", "all", "abs", "round", "input", "format",
    "hasattr", "getattr", "setattr", "delattr", "callable", "iter", "next",
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "RuntimeError", "AttributeError", "ImportError", "FileNotFoundError",
    "OSError", "IOError", "StopIteration", "AssertionError",

    # Common stdlib
    "os", "sys", "json", "re", "time", "datetime", "pathlib", "Path",
    "subprocess", "typing", "dataclasses", "collections", "itertools",
    "functools", "contextlib", "logging", "unittest", "pytest",

    # JavaScript/TypeScript builtins
    "console", "window", "document", "Array", "Object", "String", "Number",
    "Boolean", "Date", "Math", "JSON", "Promise", "async", "await",
    "function", "const", "let", "var", "return", "if", "else", "for", "while",
    "try", "catch", "finally", "throw", "new", "this", "class", "extends",
    "import", "export", "default", "from", "require", "module",

    # Common patterns
    "result", "data", "response", "error", "err", "e", "i", "j", "k", "n",
    "args", "kwargs", "options", "config", "params", "props", "state",
    "value", "key", "item", "items", "index", "count", "name", "path",
    "file", "content", "output", "input", "msg", "message", "text",
    "main", "init", "setup", "run", "start", "stop", "get", "set",
    "update", "delete", "create", "read", "write", "load", "save",
}

# Min length for identifiers to check
MIN_IDENTIFIER_LENGTH = 4

# Max identifiers to check per edit
MAX_IDENTIFIERS_TO_CHECK = 10

# =============================================================================
# EXTRACTION
# =============================================================================

def extract_external_identifiers(code: str) -> list[str]:
    """Extract identifiers that likely come from external files.

    Focus on:
    - Function calls: something()
    - Attribute access: obj.something
    - Class instantiation: SomeClass()
    - Imported usage: from_something import X
    """
    identifiers = set()

    # Function/method calls: word followed by (
    calls = re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*\(', code)
    identifiers.update(calls)

    # Class-like names (PascalCase)
    pascal = re.findall(r'\b([A-Z][A-Za-z0-9]+)\b', code)
    identifiers.update(pascal)

    # Attribute access: .something
    attrs = re.findall(r'\.([A-Za-z_][A-Za-z0-9_]*)', code)
    identifiers.update(attrs)

    # Filter out common/skip identifiers
    filtered = [
        ident for ident in identifiers
        if ident not in SKIP_IDENTIFIERS
        and len(ident) >= MIN_IDENTIFIER_LENGTH
        and not ident.startswith('_')
        and not ident.isupper()  # Skip constants like MAX_SIZE
    ]

    return list(filtered)[:MAX_IDENTIFIERS_TO_CHECK]


def get_likely_source_files(identifier: str, files_read: list[str]) -> list[str]:
    """Guess which files might define an identifier."""
    likely = []

    ident_lower = identifier.lower()
    # Convert PascalCase/camelCase to snake_case for file matching
    snake = re.sub(r'([A-Z])', r'_\1', identifier).lower().strip('_')

    for filepath in files_read:
        if not filepath:
            continue
        filename = Path(filepath).stem.lower()

        # Direct match
        if ident_lower in filename or snake in filename:
            likely.append(filepath)
            continue

        # Common patterns
        if filename in [ident_lower, snake, f"{ident_lower}s", f"{snake}s"]:
            likely.append(filepath)

    return likely


# =============================================================================
# DETECTION
# =============================================================================

def check_epistemic_boundary(code: str, files_read: list[str], filepath: str) -> list[dict]:
    """Check for identifiers used without reading their definitions.

    Returns list of {identifier, warning} for unverified usages.
    """
    warnings = []

    # Extract identifiers from code
    identifiers = extract_external_identifiers(code)

    if not identifiers:
        return []

    # For each identifier, check if plausible source was read
    for ident in identifiers:
        likely_sources = get_likely_source_files(ident, files_read)

        # If we have likely sources, assume it's verified
        if likely_sources:
            continue

        # Check if the identifier might be defined in the same file being edited
        # (This is a heuristic - if editing foo.py and using FooClass, probably fine)
        editing_filename = Path(filepath).stem.lower() if filepath else ""
        ident_lower = ident.lower()
        if editing_filename and ident_lower.startswith(editing_filename[:4]):
            continue

        # This identifier wasn't found in read files
        warnings.append({
            "identifier": ident,
            "warning": f"Using `{ident}` - source file not read this session"
        })

    return warnings[:3]  # Limit to 3 warnings


def format_boundary_warning(warnings: list[dict], filepath: str) -> str:
    """Format epistemic boundary warnings."""
    if not warnings:
        return ""

    lines = [
        "\n🔬 EPISTEMIC BOUNDARY CHECK:",
        f"  Editing: {Path(filepath).name if filepath else 'file'}",
        "",
    ]

    for w in warnings:
        lines.append(f"  • {w['warning']}")

    lines.extend([
        "",
        "  **Verification options:**",
        "  - Read the source file defining these",
        "  - Run `/probe <module>` to verify API",
        "  - If from stdlib/package, verify via `/research`",
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
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only check Edit/Write
    if tool_name not in ("Edit", "Write"):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    filepath = tool_input.get("file_path", "")

    # Skip scratch and memory files
    if "scratch/" in filepath or ".claude/memory" in filepath:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Get code being written
    code = tool_input.get("new_string", "") or tool_input.get("content", "")
    if not code or len(code) < 50:  # Skip trivial edits
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Load session state to get files read
    try:
        state = load_state()
        files_read = state.files_read or []
    except Exception:
        files_read = []

    # Check epistemic boundary
    warnings = check_epistemic_boundary(code, files_read, filepath)

    output_context = format_boundary_warning(warnings, filepath) if warnings else ""

    result = {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}
    if output_context:
        result["hookSpecificOutput"]["additionalContext"] = output_context

    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
