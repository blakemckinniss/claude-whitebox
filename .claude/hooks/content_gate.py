#!/usr/bin/env python3
"""
Content Gate Hook v4: AST-based semantic security blocking for Write/Edit operations.

Hook Type: PreToolUse (Edit, Write only)
Latency Target: <30ms (AST parsing adds ~10ms)

UPGRADE from v3: Uses AST analysis for Python files instead of regex.
Benefits:
- No false positives on strings/comments
- Detects aliased dangerous calls (f = eval; f(x))
- Catches indirect calls and SQL injection in execute()
- Falls back to regex for non-Python content

SEVERITY LEVELS:
- CRITICAL: No bypass allowed (eval, SQL injection)
- BLOCK: SUDO bypass allowed (shell=True, bare except)
"""

import sys
import json
import re
from typing import Dict, List, Optional

from synapse_core import (
    check_sudo_in_transcript,
    output_hook_result,
)

# Try to import AST analyzer, fall back to regex-only if unavailable
try:
    from ast_analysis import SecurityAnalyzer, has_critical_violations
    AST_AVAILABLE = True
except ImportError:
    AST_AVAILABLE = False

# =============================================================================
# CONTENT BLOCKING PATTERNS
# =============================================================================

CONTENT_BLOCKING_PATTERNS: Dict[str, Dict] = {
    # CRITICAL - Security vulnerabilities (no SUDO bypass)
    "eval_exec": {
        "pattern": r"\b(eval|exec)\s*\(",
        "severity": "critical",
        "message": "Code injection vulnerability (eval/exec)",
        "suggestion": "Use ast.literal_eval() for safe parsing",
        "exclusions": ["scratch/", "test_", ".md", "_test.py"]
    },
    "sql_injection": {
        "pattern": r'(f["\']SELECT|f["\']INSERT|f["\']UPDATE|f["\']DELETE|"SELECT.*"\s*\+)',
        "severity": "critical",
        "message": "SQL injection risk (string formatting in SQL)",
        "suggestion": "Use parameterized queries: cursor.execute('...?', (val,))",
        "exclusions": ["scratch/", ".md"]
    },

    # BLOCK - Should not reach production (SUDO bypass allowed)
    "shell_true": {
        "pattern": r"subprocess\.[^(]+\([^)]*shell\s*=\s*True",
        "severity": "block",
        "message": "Shell injection risk (shell=True)",
        "suggestion": "Use shell=False with list args",
        "exclusions": ["scratch/"]
    },
    "bare_except": {
        "pattern": r"except\s*:\s*$",
        "severity": "block",
        "message": "Bare except catches SystemExit/KeyboardInterrupt",
        "suggestion": "Use 'except Exception:'",
        "exclusions": []
    },
    "wildcard_import": {
        "pattern": r"from\s+\w+\s+import\s+\*",
        "severity": "block",
        "message": "Wildcard import pollutes namespace",
        "suggestion": "Import specific names",
        "exclusions": ["__init__.py", "scratch/"]
    },
    "log_secrets": {
        "pattern": r'(print|log|logger)\s*\([^)]*\b(password|token|secret|api_key|credential)\b',
        "severity": "block",
        "message": "Logging sensitive data",
        "suggestion": "Never log credentials",
        "exclusions": ["scratch/", ".md"]
    },
    "hardcoded_creds": {
        "pattern": r'(password|secret|api_key)\s*=\s*["\'][^"\']{8,}["\']',
        "severity": "block",
        "message": "Hardcoded credentials detected",
        "suggestion": "Use environment variables or secrets manager",
        "exclusions": ["scratch/", "test_", ".md", ".example"]
    },
    "pickle_loads": {
        "pattern": r"pickle\.loads?\s*\(",
        "severity": "block",
        "message": "pickle.load is unsafe with untrusted data",
        "suggestion": "Use JSON or validate source",
        "exclusions": ["scratch/", "test_"]
    },
    "yaml_unsafe": {
        "pattern": r"yaml\.(load|unsafe_load)\s*\([^)]*\)",
        "severity": "block",
        "message": "yaml.load without Loader is unsafe",
        "suggestion": "Use yaml.safe_load()",
        "exclusions": ["scratch/"]
    },
}

# =============================================================================
# ANALYSIS
# =============================================================================


def check_content_violations_ast(
    content: str,
    file_path: str,
    has_sudo: bool
) -> List[Dict]:
    """AST-based security analysis for Python files. More accurate than regex."""
    if not AST_AVAILABLE:
        return []

    try:
        analyzer = SecurityAnalyzer(content, file_path)
        violations = analyzer.analyze()
    except Exception:
        return []  # Fall back to regex on AST failure

    result = []
    for v in violations:
        # Critical = no bypass, Block = SUDO bypass
        if v.severity == "critical" or (v.severity == "block" and not has_sudo):
            result.append({
                "name": v.name,
                "severity": v.severity,
                "line": v.line,
                "message": v.message,
                "suggestion": v.suggestion,
                "matched": v.context[:40] if v.context else ""
            })

    return result


def check_content_violations_regex(
    content: str,
    file_path: str,
    has_sudo: bool
) -> List[Dict]:
    """Regex-based security analysis. Fallback for non-Python files."""
    if not content or not file_path:
        return []

    violations = []

    for name, config in CONTENT_BLOCKING_PATTERNS.items():
        # Check exclusions
        if any(excl in file_path for excl in config.get("exclusions", [])):
            continue

        matches = list(re.finditer(config["pattern"], content, re.MULTILINE | re.IGNORECASE))

        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            severity = config["severity"]

            # Critical = no bypass, Block = SUDO bypass
            if severity == "critical" or (severity == "block" and not has_sudo):
                violations.append({
                    "name": name,
                    "severity": severity,
                    "line": line_num,
                    "message": config["message"],
                    "suggestion": config.get("suggestion", ""),
                    "matched": match.group(0)[:40]
                })

    return violations


def check_content_violations(
    content: str,
    file_path: str,
    has_sudo: bool
) -> List[Dict]:
    """
    Check content for security violations.

    Uses AST analysis for Python files (more accurate).
    Falls back to regex for other file types.
    """
    if not content or not file_path:
        return []

    # Use AST for Python files (no false positives on strings/comments)
    is_python = file_path.endswith('.py')

    if is_python and AST_AVAILABLE:
        violations = check_content_violations_ast(content, file_path, has_sudo)
        # Also run regex to catch patterns AST doesn't handle (log_secrets, hardcoded_creds)
        regex_violations = check_content_violations_regex(content, file_path, has_sudo)
        # Merge and deduplicate by line number
        seen_lines = {v["line"] for v in violations}
        for rv in regex_violations:
            if rv["line"] not in seen_lines:
                violations.append(rv)
        return violations

    # Regex fallback for non-Python files
    return check_content_violations_regex(content, file_path, has_sudo)


def format_violations(violations: List[Dict], file_path: str) -> str:
    """Format violations for block message."""
    lines = [f"CONTENT VIOLATIONS in {file_path}\n"]

    critical = [v for v in violations if v["severity"] == "critical"]
    blocking = [v for v in violations if v["severity"] == "block"]

    if critical:
        lines.append("CRITICAL (no bypass):")
        for v in critical:
            lines.append(f"  L{v['line']}: {v['message']}")
            lines.append(f"    Fix: {v['suggestion']}")

    if blocking:
        lines.append("\nBLOCKED (say SUDO to bypass):")
        for v in blocking:
            lines.append(f"  L{v['line']}: {v['message']}")
            lines.append(f"    Fix: {v['suggestion']}")

    return "\n".join(lines)


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
    tool_input = input_data.get("tool_input", {})
    transcript_path = input_data.get("transcript_path", "")

    # Only check Write and Edit
    if tool_name not in ("Write", "Edit"):
        output_hook_result("PreToolUse")
        sys.exit(0)

    # Extract content and file path
    if not isinstance(tool_input, dict):
        output_hook_result("PreToolUse")
        sys.exit(0)

    content = tool_input.get("content", "") or tool_input.get("new_string", "")
    file_path = tool_input.get("file_path", "")

    if not content or not file_path:
        output_hook_result("PreToolUse")
        sys.exit(0)

    # Check for SUDO bypass
    has_sudo = check_sudo_in_transcript(transcript_path)

    # Check for violations
    violations = check_content_violations(content, file_path, has_sudo)

    if not violations:
        output_hook_result("PreToolUse")
        sys.exit(0)

    # Block with formatted message
    reason = format_violations(violations, file_path)
    output_hook_result("PreToolUse", decision="deny", reason=reason)
    sys.exit(0)


if __name__ == "__main__":
    main()
