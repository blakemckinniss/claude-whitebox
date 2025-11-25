#!/usr/bin/env python3
"""
Hook Documentation Enforcer: PreToolUse Hook
Validates hook code against official Claude Code documentation standards.

Triggers: Before Write/Edit to .claude/hooks/*.py
Blocks: Code that violates official hooks documentation

Official Documentation Requirements:
1. Exit code semantics (0=success, 2=blocking, other=non-blocking)
2. JSONDecodeError handling for stdin parsing
3. Path traversal validation for file_path handling
4. No shell=True without documentation
5. Proper hookSpecificOutput schema
6. stderr output for exit code 2

Per official docs:
- /en/hooks-guide (Best practices)
- /en/hooks (Event types, schemas, exit codes)
- /en/hooks#security-considerations (Security checklist)
"""

import sys
import json
import re
import ast
from pathlib import Path
from typing import List, Tuple, Optional

# Add scripts/lib to path
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

sys.path.insert(0, str(PROJECT_DIR / "scripts" / "lib"))


class HookValidator:
    """Validates hook code against official documentation."""

    def __init__(self, file_path: str, content: str):
        self.file_path = file_path
        self.content = content
        self.violations: List[Tuple[str, str]] = []  # (severity, message)
        self.warnings: List[str] = []

        try:
            self.tree = ast.parse(content)
        except SyntaxError as e:
            self.violations.append(("CRITICAL", f"Syntax error: {e}"))
            self.tree = None

    def validate_all(self) -> bool:
        """Run all validations. Returns True if valid."""
        if not self.tree:
            return False

        self.check_stdin_parsing()
        self.check_exit_codes()
        self.check_json_output_schema()
        self.check_security_practices()
        self.check_hook_event_compliance()

        return len(self.violations) == 0

    def check_stdin_parsing(self):
        """
        Requirement: Hooks must handle JSONDecodeError when parsing stdin.

        Official docs: "Validate and sanitize inputs - never trust blindly"
        """
        if 'json.load(sys.stdin)' not in self.content:
            # Check if this is a hook that should be parsing stdin
            # Most PreToolUse/PostToolUse/UserPromptSubmit hooks need input
            needs_input = any(event in self.content for event in [
                'PreToolUse', 'PostToolUse', 'UserPromptSubmit',
                'Stop', 'SubagentStop', 'SessionStart'
            ])

            if needs_input:
                self.warnings.append(
                    "Hook declares an event type that typically needs input, "
                    "but doesn't parse stdin\n"
                    "Most hooks need: input_data = json.load(sys.stdin)\n"
                    "If input is truly not needed, ignore this warning."
                )
            return  # Hook doesn't parse stdin

        # Check for JSONDecodeError handling
        has_json_error_handling = (
            'JSONDecodeError' in self.content or
            'json.decoder.JSONDecodeError' in self.content
        )

        if not has_json_error_handling:
            self.violations.append((
                "MEDIUM",
                "Missing JSONDecodeError handling for stdin parsing\n"
                "Per official docs: 'Validate and sanitize inputs'\n"
                "Required pattern:\n"
                "  try:\n"
                "      input_data = json.load(sys.stdin)\n"
                "  except json.JSONDecodeError as e:\n"
                "      print(f'Error: Invalid JSON: {e}', file=sys.stderr)\n"
                "      sys.exit(1)"
            ))

    def check_exit_codes(self):
        """
        Requirement: Exit code 2 must be paired with stderr output.

        Official docs:
        - Exit 0: Success (stdout in verbose)
        - Exit 2: Blocking error (only stderr used)
        - Other: Non-blocking error
        """
        # Find all sys.exit(2) calls
        exit_2_calls = []
        exit_calls_with_variables = []

        try:
            for node in ast.walk(self.tree):
                if isinstance(node, ast.Call):
                    if (isinstance(node.func, ast.Attribute) and
                        isinstance(node.func.value, ast.Name) and
                        node.func.value.id == 'sys' and
                        node.func.attr == 'exit'):
                        if node.args:
                            if isinstance(node.args[0], ast.Constant):
                                if node.args[0].value == 2:
                                    exit_2_calls.append(node)
                            else:
                                # sys.exit(variable) or sys.exit(func())
                                exit_calls_with_variables.append(node)
        except Exception:
            # AST traversal error - log but don't crash
            self.warnings.append(
                "Could not fully analyze exit code usage (complex AST structure)\n"
                "Manual review recommended for sys.exit() calls"
            )

        # For each exit(2), verify stderr is written before it
        if exit_2_calls:
            has_stderr = (
                'sys.stderr' in self.content or
                'file=sys.stderr' in self.content
            )

            if not has_stderr:
                self.violations.append((
                    "HIGH",
                    "Exit code 2 used without stderr output\n"
                    "Per official docs: Exit code 2 requires stderr message\n"
                    "Format: [command]: {stderr}\n"
                    "Required pattern:\n"
                    "  print(f'Error: {reason}', file=sys.stderr)\n"
                    "  sys.exit(2)"
                ))

    def check_json_output_schema(self):
        """
        Requirement: JSON output must use correct schema per hook type.

        Official docs define schemas for:
        - PreToolUse: hookSpecificOutput.permissionDecision
        - PostToolUse: hookSpecificOutput.additionalContext
        - UserPromptSubmit: hookSpecificOutput.additionalContext
        - Stop/SubagentStop: decision, reason
        """
        if 'json.dumps' not in self.content:
            return  # Hook doesn't output JSON

        # Check for deprecated 'decision' field in PreToolUse
        if 'PreToolUse' in self.content:
            # Look for old pattern
            if '"decision"' in self.content and 'permissionDecision' not in self.content:
                self.warnings.append(
                    "Uses deprecated 'decision' field for PreToolUse\n"
                    "Per official docs: Use 'hookSpecificOutput.permissionDecision' instead\n"
                    "Deprecated: {'decision': 'approve|block'}\n"
                    "Current:    {'hookSpecificOutput': {'permissionDecision': 'allow|deny|ask'}}"
                )

        # Check for proper hookSpecificOutput usage
        if any(event in self.content for event in ['PreToolUse', 'PostToolUse', 'UserPromptSubmit', 'SessionStart']):
            if 'hookSpecificOutput' not in self.content:
                self.warnings.append(
                    "Hook may not be using hookSpecificOutput schema\n"
                    "Per official docs: Use hookSpecificOutput for structured output"
                )

    def check_security_practices(self):
        """
        Requirement: Security best practices from official docs.

        Official docs security checklist:
        1. Path traversal prevention (check for ..)
        2. Input validation
        3. No shell=True without documentation
        4. Absolute paths
        """
        # Check 1: Path traversal validation
        if 'file_path' in self.content:
            has_traversal_check = (
                '".."' in self.content or
                "'..''" in self.content or
                'validate_file_path' in self.content
            )

            if not has_traversal_check:
                self.violations.append((
                    "HIGH",
                    "Missing path traversal validation for file_path\n"
                    "Per official docs: 'Block path traversal - Check for .. in file paths'\n"
                    "Required pattern:\n"
                    "  if '..' in file_path:\n"
                    "      print('Security: Path traversal detected', file=sys.stderr)\n"
                    "      sys.exit(2)"
                ))

        # Check 2: shell=True usage
        if 'shell=True' in self.content:
            # Check if documented
            has_security_warning = (
                'SECURITY WARNING' in self.content or
                'security' in self.content.lower()
            )

            if not has_security_warning:
                self.violations.append((
                    "HIGH",
                    "shell=True used without security documentation\n"
                    "Per official docs: 'Never use shell=True without validation'\n"
                    "Required: Add comment explaining security implications:\n"
                    "  # SECURITY WARNING: shell=True requires careful input validation\n"
                    "  # All variables are validated before use"
                ))

    def check_hook_event_compliance(self):
        """
        Requirement: Hook event names must be official.

        Official events:
        - PreToolUse, PermissionRequest, PostToolUse
        - Notification, UserPromptSubmit
        - Stop, SubagentStop, PreCompact
        - SessionStart, SessionEnd
        """
        official_events = {
            'PreToolUse', 'PermissionRequest', 'PostToolUse',
            'Notification', 'UserPromptSubmit',
            'Stop', 'SubagentStop', 'PreCompact',
            'SessionStart', 'SessionEnd'
        }

        # Look for hookEventName in code
        event_pattern = r'"hookEventName":\s*"(\w+)"'
        matches = re.findall(event_pattern, self.content)

        for event in matches:
            if event not in official_events:
                self.violations.append((
                    "CRITICAL",
                    f"Non-standard hook event: {event}\n"
                    f"Per official docs, valid events are:\n"
                    f"{', '.join(official_events)}"
                ))

    def get_validation_report(self) -> str:
        """Generate validation report."""
        report = []

        if self.violations:
            report.append("🚫 HOOK VALIDATION FAILED")
            report.append("")
            report.append(f"File: {Path(self.file_path).name}")
            report.append("")

            # Group by severity
            critical = [v for s, v in self.violations if s == "CRITICAL"]
            high = [v for s, v in self.violations if s == "HIGH"]
            medium = [v for s, v in self.violations if s == "MEDIUM"]

            if critical:
                report.append("CRITICAL VIOLATIONS:")
                for v in critical:
                    report.append(f"  ✗ {v}")
                report.append("")

            if high:
                report.append("HIGH PRIORITY VIOLATIONS:")
                for v in high:
                    report.append(f"  ✗ {v}")
                report.append("")

            if medium:
                report.append("MEDIUM PRIORITY VIOLATIONS:")
                for v in medium:
                    report.append(f"  ! {v}")
                report.append("")

        if self.warnings:
            report.append("⚠️ WARNINGS:")
            for w in self.warnings:
                report.append(f"  ⚠ {w}")
            report.append("")

        if self.violations:
            report.append("Per official Claude Code hooks documentation:")
            report.append("  - /en/hooks-guide (Best practices)")
            report.append("  - /en/hooks (Event types, schemas)")
            report.append("  - /en/hooks#security-considerations (Security)")
            report.append("")
            report.append("Fix violations before writing hook code.")

        return "\n".join(report)


def main():
    """Main enforcement logic."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # FAIL-OPEN SAFETY: If validator crashes, allow with warning
        # This prevents the meta-hook from blocking legitimate operations due to bugs
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": (
                    f"⚠️ VALIDATION ERROR: Meta-hook enforcer failed internally\n\n"
                    f"Error: {str(e)[:200]}\n\n"
                    f"The hook write is ALLOWED but validation could not run.\n"
                    f"Manual review recommended.\n\n"
                    f"This is a bug in the meta-hook enforcer - please report."
                ),
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    prompt = input_data.get("prompt", "")

    # Only enforce on Write/Edit to .claude/hooks/*.py
    if tool_name not in ["Write", "Edit"]:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    file_path = tool_input.get("file_path", "")

    # Only enforce on hook files
    if not file_path or '.claude/hooks/' not in file_path or not file_path.endswith('.py'):
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Skip enforcement for this enforcer itself
    if 'hook_documentation_enforcer.py' in file_path:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Get content being written
    if tool_name == "Write":
        content = tool_input.get("content", "")
    else:  # Edit
        # For Edit, read the current file and warn about re-validation
        # We can't predict the final content, but we can remind the user
        file_path_obj = Path(file_path)
        if file_path_obj.exists():
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": (
                        "⚠️ EDIT OPERATION: Hook validation cannot verify edits\n\n"
                        "The meta-hook enforcer can only validate Write operations.\n"
                        "For Edit operations, consider:\n"
                        "  1. Read the file\n"
                        "  2. Make your changes\n"
                        "  3. Write the result (which will be validated)\n\n"
                        "Alternatively, use SUDO to bypass for edits you trust."
                    ),
                }
            }
        else:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                }
            }
        print(json.dumps(output))
        sys.exit(0)

    if not content:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Validate hook code
    validator = HookValidator(file_path, content)
    is_valid = validator.validate_all()

    # Check for SUDO bypass
    if "SUDO" in prompt:
        # Allow with warning
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": f"⚠️ Hook validation bypassed with SUDO\n\n{validator.get_validation_report()}",
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    if not is_valid:
        # Block the write
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": validator.get_validation_report() + "\n\n(Use SUDO keyword to bypass)",
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Show warnings but allow
    if validator.warnings:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "✓ Hook validation passed with warnings\n\n" + validator.get_validation_report(),
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # All good
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
