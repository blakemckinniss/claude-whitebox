#!/usr/bin/env python3
"""
Production Gate Hook v4: PreToolUse hook enforcing audit+void before .claude/ops writes.

Hook Type: PreToolUse (matcher: Write)
Latency Target: <100ms (runs external scripts)

UPGRADE from v3: Uses AST-based semantic stub detection.
- Catches return None stubs (semantic)
- Catches always-true validators
- Catches empty except handlers
- Falls back to regex if AST unavailable

Enforces CLAUDE.md rule: "No Production Write without audit AND void passing"
"""

import _lib_path  # noqa: F401
import sys
import json
import subprocess
from pathlib import Path

from synapse_core import log_block, format_block_acknowledgment

# Try to import AST stub analyzer
try:
    from ast_analysis import StubAnalyzer
    AST_AVAILABLE = True
except ImportError:
    AST_AVAILABLE = False

# =============================================================================
# CONFIG
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
PROTECTED_PATHS = [
    ".claude/ops/",
    ".claude/lib/",
]

# State file to track what's been audited/voided this session
STATE_FILE = SCRIPT_DIR.parent / "memory" / "production_gate_state.json"


def load_state() -> dict:
    """Load gate state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {"audited": {}, "voided": {}}


def save_state(state: dict):
    """Save gate state."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except IOError:
        pass


def is_protected_path(file_path: str) -> bool:
    """Check if path is in protected production zone."""
    # Normalize path
    try:
        path = Path(file_path)
        # Handle both absolute and relative paths
        if path.is_absolute():
            try:
                rel_path = path.relative_to(PROJECT_ROOT)
            except ValueError:
                return False
        else:
            rel_path = path

        rel_str = str(rel_path)
        return any(rel_str.startswith(p) for p in PROTECTED_PATHS)
    except Exception:
        return False


def run_audit(file_path: str) -> tuple[bool, str]:
    """Run audit.py on file. Returns (passed, message)."""
    try:
        result = subprocess.run(
            ["python3", str(PROJECT_ROOT / ".claude/ops/audit.py"), file_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=PROJECT_ROOT,
        )

        # Check for SECURITY issues only (not style issues)
        output = result.stdout + result.stderr

        # Only block on these specific dangerous patterns (actual vulnerabilities)
        # Note: shell=True warnings are acceptable for solo dev scripts
        blocking_patterns = [
            "sql injection",
            "hardcoded password",
            "hardcoded secret",
            "hardcoded api key",
            "xss vulnerability",
            "remote code execution",
        ]

        output_lower = output.lower()
        for pattern in blocking_patterns:
            if pattern.lower() in output_lower:
                return False, output[:300]

        # Other issues (subprocess warnings, style) are acceptable for solo dev
        return True, "passed"
    except subprocess.TimeoutExpired:
        return False, "audit timed out"
    except Exception as e:
        return False, str(e)[:100]


def run_void_regex(content: str, lines: list) -> list:
    """Regex-based stub detection (fallback)."""
    import re

    STUB_PATTERNS = [
        (r"#\s*TODO\b", "TODO comment"),
        (r"#\s*FIXME\b", "FIXME comment"),
        (r"def\s+\w+\([^)]*\):\s*pass\s*$", "pass stub"),
        (r"def\s+\w+\([^)]*\):\s*\.\.\.\s*$", "... stub"),
        (r"raise\s+NotImplementedError", "NotImplementedError"),
    ]

    issues = []
    for i, line in enumerate(lines, 1):
        for pattern, desc in STUB_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append(f"L{i}: {desc}")
                if len(issues) >= 3:
                    return issues
    return issues


def run_void_ast(content: str, file_path: str) -> list:
    """AST-based semantic stub detection. Catches more than regex."""
    if not AST_AVAILABLE:
        return []

    try:
        analyzer = StubAnalyzer(content, file_path)
        stubs = analyzer.find_stubs()

        issues = []
        for stub in stubs:
            if stub.severity in ('block', 'critical'):
                issues.append(f"L{stub.line}: {stub.message}")
                if len(issues) >= 3:
                    break
        return issues
    except Exception:
        return []


def run_void(file_path: str) -> tuple[bool, str]:
    """
    Fast local void check - scan file for stub patterns.

    Uses AST for semantic detection (return None, always-true validators).
    Falls back to regex for TODO/FIXME comments.
    """

    try:
        with open(file_path, "r") as f:
            content = f.read()
            lines = content.split("\n")

        issues = []

        # AST-based semantic stub detection (Python files only)
        if file_path.endswith('.py') and AST_AVAILABLE:
            issues.extend(run_void_ast(content, file_path))

        # Regex fallback for TODO/FIXME (AST can't see comments)
        if len(issues) < 3:
            regex_issues = run_void_regex(content, lines)
            # Dedupe by line number
            seen_lines = {i.split(':')[0] for i in issues}
            for ri in regex_issues:
                if ri.split(':')[0] not in seen_lines:
                    issues.append(ri)
                    if len(issues) >= 3:
                        break

        if issues:
            return False, "Stubs found: " + "; ".join(issues[:3])
        return True, "passed"

    except Exception as e:
        return False, str(e)[:100]


def main():
    """PreToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only check Write tool
    if tool_name != "Write":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    file_path = tool_input.get("file_path", "")

    # Only check protected paths
    if not is_protected_path(file_path):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # For new files, we can't audit/void yet - allow but warn
    if not Path(file_path).exists():
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": "⚠️ New production file - run audit+void after creation",
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Run audit
    audit_passed, audit_msg = run_audit(file_path)
    if not audit_passed:
        reason = f"🛑 AUDIT FAILED: {audit_msg}\nFix issues before writing to production."
        log_block("production_gate", reason, tool_name, tool_input)
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason + format_block_acknowledgment("production_gate"),
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Run void
    void_passed, void_msg = run_void(file_path)
    if not void_passed:
        reason = f"🛑 VOID FAILED: {void_msg}\nComplete all TODOs/stubs before writing to production."
        log_block("production_gate", reason, tool_name, tool_input)
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason + format_block_acknowledgment("production_gate"),
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Both passed
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": "✓ Production gate: audit+void passed",
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
