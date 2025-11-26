#!/usr/bin/env python3
"""
Import Gate Hook: Verifies imports exist before allowing Write operations.

Hook Type: PreToolUse (Write only)
Latency Target: <50ms

Catches:
- Missing pip packages before code is written
- Typos in module names
- Deprecated module usage

Prevents the "ModuleNotFoundError" frustration loop.
"""

import sys
import json
from typing import List, Dict

from synapse_core import output_hook_result

# Try to import AST analyzer
try:
    from ast_analysis import ImportAnalyzer
    AST_AVAILABLE = True
except ImportError:
    AST_AVAILABLE = False


def check_imports(content: str, file_path: str) -> List[Dict]:
    """Check if imports in content exist. Returns list of issues."""
    if not AST_AVAILABLE:
        return []

    if not file_path.endswith('.py'):
        return []

    try:
        analyzer = ImportAnalyzer(content, file_path)
        # check_existence=True to actually verify modules are installed
        issues = analyzer.verify_imports(check_existence=True)

        results = []
        for issue in issues:
            if issue.severity in ('block', 'critical'):
                results.append({
                    'name': issue.name,
                    'severity': issue.severity,
                    'line': issue.line,
                    'message': issue.message,
                    'suggestion': issue.suggestion,
                })
        return results
    except Exception:
        return []


def format_issues(issues: List[Dict], file_path: str) -> str:
    """Format import issues for display."""
    lines = [f"IMPORT ISSUES in {file_path}\n"]

    for issue in issues[:5]:  # Limit to 5 issues
        lines.append(f"  L{issue['line']}: {issue['message']}")
        if issue.get('suggestion'):
            lines.append(f"    Fix: {issue['suggestion']}")

    return "\n".join(lines)


def main():
    """PreToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        output_hook_result("PreToolUse")
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only check Write tool for Python files
    if tool_name != "Write":
        output_hook_result("PreToolUse")
        sys.exit(0)

    if not isinstance(tool_input, dict):
        output_hook_result("PreToolUse")
        sys.exit(0)

    content = tool_input.get("content", "")
    file_path = tool_input.get("file_path", "")

    if not content or not file_path or not file_path.endswith('.py'):
        output_hook_result("PreToolUse")
        sys.exit(0)

    # Check imports
    issues = check_imports(content, file_path)

    if not issues:
        output_hook_result("PreToolUse")
        sys.exit(0)

    # Warn but don't block (missing imports can be installed)
    warning = format_issues(issues, file_path)
    output_hook_result(
        "PreToolUse",
        additional_context=f"⚠️ IMPORT WARNING:\n{warning}\nConsider: pip install <missing>"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
