#!/usr/bin/env python3
"""
Hook Compliance Auditor - Validates all .claude/hooks against official documentation standards.

Checks:
1. Exit code usage (0 for success, 2 for blocking, non-zero for non-blocking)
2. JSON output schema validation
3. Hook input parsing (stdin JSON)
4. Proper error messaging (stderr for exit code 2)
5. Environment variable usage ($CLAUDE_PROJECT_DIR)
6. Security best practices (path validation, input sanitization)
7. Hook-specific output formats (PreToolUse, PostToolUse, etc.)
"""

import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Color codes for output
RED = '\033[91m'
YELLOW = '\033[93m'
GREEN = '\033[92m'
BLUE = '\033[94m'
RESET = '\033[0m'

class HookAuditor:
    def __init__(self, hooks_dir: Path):
        self.hooks_dir = hooks_dir
        self.issues: List[Dict] = []
        self.warnings: List[Dict] = []
        self.successes: List[Dict] = []

    def audit_all_hooks(self):
        """Audit all Python hooks in the directory."""
        hook_files = sorted(self.hooks_dir.glob("*.py"))

        print(f"{BLUE}Auditing {len(hook_files)} hooks for compliance...{RESET}\n")

        for hook_file in hook_files:
            self.audit_hook(hook_file)

        self.print_summary()

        # Return exit code based on critical issues
        return 2 if any(i['severity'] == 'CRITICAL' for i in self.issues) else 0

    def audit_hook(self, hook_path: Path):
        """Audit a single hook file."""
        try:
            with open(hook_path, 'r') as f:
                content = f.read()

            # Parse AST for analysis
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                self.add_issue(hook_path, 'CRITICAL', f"Syntax error: {e}")
                return

            # Run all checks
            self.check_stdin_parsing(hook_path, content, tree)
            self.check_exit_codes(hook_path, content, tree)
            self.check_json_output(hook_path, content, tree)
            self.check_error_handling(hook_path, content, tree)
            self.check_security(hook_path, content)
            self.check_environment_vars(hook_path, content)
            self.check_hook_specific_output(hook_path, content)

        except Exception as e:
            self.add_issue(hook_path, 'CRITICAL', f"Failed to audit: {e}")

    def check_stdin_parsing(self, hook_path: Path, content: str, tree: ast.AST):
        """Check if hook properly parses stdin JSON."""
        # Look for json.load(sys.stdin) pattern
        has_stdin_load = 'json.load(sys.stdin)' in content or 'json.loads(sys.stdin.read())' in content

        if not has_stdin_load:
            self.add_warning(hook_path, "No stdin JSON parsing detected (may not need hook input)")
        else:
            # Check for JSONDecodeError handling
            has_error_handling = 'JSONDecodeError' in content or 'except' in content
            if not has_error_handling:
                self.add_issue(hook_path, 'MEDIUM', "Missing JSONDecodeError handling for stdin parsing")
            else:
                self.add_success(hook_path, "Properly handles stdin JSON parsing with error handling")

    def check_exit_codes(self, hook_path: Path, content: str, tree: ast.AST):
        """Check exit code usage compliance."""
        # Extract all sys.exit() calls
        exit_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if (isinstance(node.func.value, ast.Name) and
                        node.func.value.id == 'sys' and
                        node.func.attr == 'exit'):
                        if node.args:
                            if isinstance(node.args[0], ast.Constant):
                                exit_calls.append(node.args[0].value)

        # Check for proper usage
        has_exit_0 = 0 in exit_calls
        has_exit_2 = 2 in exit_calls
        has_other_exits = any(c not in [0, 1, 2] for c in exit_calls if isinstance(c, int))

        if has_other_exits:
            self.add_warning(hook_path, "Uses non-standard exit codes (only 0, 2 recommended per docs)")

        # Check exit(2) has stderr message
        if has_exit_2:
            # Look for stderr writes before exit(2)
            if 'sys.stderr.write' in content or 'file=sys.stderr' in content:
                self.add_success(hook_path, "Exit code 2 properly paired with stderr output")
            else:
                self.add_issue(hook_path, 'MEDIUM', "Exit code 2 used without stderr message (required per docs)")

    def check_json_output(self, hook_path: Path, content: str, tree: ast.AST):
        """Check JSON output format compliance."""
        has_json_dumps = 'json.dumps' in content

        if not has_json_dumps:
            # Not all hooks need JSON output
            return

        # Check for proper JSON schema fields
        required_fields = {
            'decision', 'reason', 'continue', 'stopReason',
            'systemMessage', 'hookSpecificOutput', 'suppressOutput'
        }

        found_fields = set()
        for field in required_fields:
            if f'"{field}"' in content or f"'{field}'" in content:
                found_fields.add(field)

        if found_fields:
            self.add_success(hook_path, f"Uses JSON output with fields: {', '.join(found_fields)}")

        # Check for deprecated fields (decision/reason in PreToolUse)
        if 'PreToolUse' in content or 'pre_tool' in hook_path.stem.lower():
            if '"decision"' in content and 'permissionDecision' not in content:
                self.add_warning(hook_path,
                    "May be using deprecated 'decision' field for PreToolUse (use 'permissionDecision')")

    def check_error_handling(self, hook_path: Path, content: str, tree: ast.AST):
        """Check error handling patterns."""
        has_try_except = any(isinstance(node, ast.Try) for node in ast.walk(tree))

        if not has_try_except:
            self.add_warning(hook_path, "No try/except blocks found (may fail ungracefully)")
        else:
            # Check if exceptions write to stderr
            has_stderr_in_except = 'sys.stderr' in content and 'except' in content
            if has_stderr_in_except:
                self.add_success(hook_path, "Proper exception handling with stderr output")

    def check_security(self, hook_path: Path, content: str):
        """Check security best practices."""
        issues_found = []

        # Check for path traversal prevention
        if 'file_path' in content:
            if '..' not in content or 'path traversal' not in content.lower():
                issues_found.append("May not validate against path traversal (.. in paths)")

        # Check for shell injection risks
        if 'subprocess' in content or 'os.system' in content:
            if 'shell=True' in content:
                issues_found.append("Uses shell=True (potential command injection)")
            else:
                self.add_success(hook_path, "Subprocess calls avoid shell=True")

        # Check for variable quoting in shell commands
        if re.search(r'f["\'].*\{[^}]+\}.*["\']', content):
            # Has f-strings, check if they're in shell commands
            if 'command' in content or 'bash' in content.lower():
                self.add_warning(hook_path, "Uses f-strings in commands (verify variable quoting)")

        # Report security issues
        for issue in issues_found:
            self.add_issue(hook_path, 'HIGH', f"Security: {issue}")

    def check_environment_vars(self, hook_path: Path, content: str):
        """Check environment variable usage."""
        # Check if CLAUDE_PROJECT_DIR is used properly
        if 'CLAUDE_PROJECT_DIR' in content:
            # Should use os.environ.get or os.getenv
            if 'os.environ.get' in content or 'os.getenv' in content:
                self.add_success(hook_path, "Properly accesses CLAUDE_PROJECT_DIR environment variable")
            else:
                self.add_warning(hook_path, "References CLAUDE_PROJECT_DIR but may not retrieve it properly")

    def check_hook_specific_output(self, hook_path: Path, content: str):
        """Check hook-specific output format requirements."""
        hook_name = hook_path.stem.lower()

        # Map hook types to expected patterns
        hook_patterns = {
            'pretooluse': ['permissionDecision', 'permissionDecisionReason', 'updatedInput'],
            'posttooluse': ['decision', 'reason', 'additionalContext'],
            'userpromptsubmit': ['decision', 'additionalContext'],
            'stop': ['decision', 'reason'],
            'sessionstart': ['additionalContext'],
        }

        # Check if hook matches any pattern
        for hook_type, expected_fields in hook_patterns.items():
            if hook_type in hook_name or hook_type.replace('_', '') in hook_name:
                found_fields = [f for f in expected_fields if f in content]
                if found_fields:
                    self.add_success(hook_path,
                        f"Uses {hook_type} specific fields: {', '.join(found_fields)}")

    def add_issue(self, hook_path: Path, severity: str, message: str):
        """Add a compliance issue."""
        self.issues.append({
            'file': hook_path.name,
            'severity': severity,
            'message': message
        })

    def add_warning(self, hook_path: Path, message: str):
        """Add a compliance warning."""
        self.warnings.append({
            'file': hook_path.name,
            'message': message
        })

    def add_success(self, hook_path: Path, message: str):
        """Add a compliance success."""
        self.successes.append({
            'file': hook_path.name,
            'message': message
        })

    def print_summary(self):
        """Print audit summary."""
        print(f"\n{'='*80}")
        print(f"{BLUE}HOOK COMPLIANCE AUDIT SUMMARY{RESET}")
        print(f"{'='*80}\n")

        # Critical and high issues
        critical_issues = [i for i in self.issues if i['severity'] == 'CRITICAL']
        high_issues = [i for i in self.issues if i['severity'] == 'HIGH']
        medium_issues = [i for i in self.issues if i['severity'] == 'MEDIUM']

        if critical_issues:
            print(f"{RED}CRITICAL ISSUES ({len(critical_issues)}):{RESET}")
            for issue in critical_issues:
                print(f"  {RED}✗{RESET} {issue['file']}: {issue['message']}")
            print()

        if high_issues:
            print(f"{RED}HIGH PRIORITY ISSUES ({len(high_issues)}):{RESET}")
            for issue in high_issues:
                print(f"  {RED}✗{RESET} {issue['file']}: {issue['message']}")
            print()

        if medium_issues:
            print(f"{YELLOW}MEDIUM PRIORITY ISSUES ({len(medium_issues)}):{RESET}")
            for issue in medium_issues:
                print(f"  {YELLOW}!{RESET} {issue['file']}: {issue['message']}")
            print()

        if self.warnings:
            print(f"{YELLOW}WARNINGS ({len(self.warnings)}):{RESET}")
            # Group warnings by file
            warnings_by_file = {}
            for w in self.warnings:
                warnings_by_file.setdefault(w['file'], []).append(w['message'])

            for file, messages in sorted(warnings_by_file.items()):
                print(f"  {YELLOW}⚠{RESET} {file}:")
                for msg in messages:
                    print(f"      {msg}")
            print()

        # Success summary
        print(f"{GREEN}COMPLIANT PATTERNS ({len(self.successes)}):{RESET}")
        success_files = set(s['file'] for s in self.successes)
        print(f"  {len(success_files)} hooks follow official documentation patterns")
        print()

        # Overall score
        total_hooks = len(list(self.hooks_dir.glob("*.py")))
        total_issues = len(critical_issues) + len(high_issues) + len(medium_issues)
        compliance_score = max(0, 100 - (total_issues * 5) - (len(self.warnings) * 2))

        print(f"{'='*80}")
        print(f"{BLUE}COMPLIANCE SCORE: {compliance_score}/100{RESET}")
        print(f"Total Hooks: {total_hooks}")
        print(f"Critical Issues: {len(critical_issues)}")
        print(f"High Priority: {len(high_issues)}")
        print(f"Medium Priority: {len(medium_issues)}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"{'='*80}\n")


def main():
    # Find hooks directory
    project_root = Path(__file__).parent.parent
    hooks_dir = project_root / ".claude" / "hooks"

    if not hooks_dir.exists():
        print(f"{RED}Error: Hooks directory not found at {hooks_dir}{RESET}")
        sys.exit(1)

    auditor = HookAuditor(hooks_dir)
    exit_code = auditor.audit_all_hooks()

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
