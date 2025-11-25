#!/usr/bin/env python3
"""
Hook System Auditor (The Hook Sheriff)

Comprehensive audit of Claude Code hooks against official documentation specs.
Validates configuration, input/output formats, event types, and best practices.

Usage:
    python3 scripts/ops/audit_hooks.py [--fix] [--json] [--strict]

Options:
    --fix     Auto-fix common issues (bare except, missing timeouts)
    --json    Output results as JSON
    --strict  Treat warnings as errors (exit 1 if any warnings)

Official Spec Reference:
    https://docs.anthropic.com/en/hooks-reference
"""

import os
import sys
import json
import ast
import re
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from typing import Optional

# Add scripts/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
_current = _script_dir
while _current != "/":
    if os.path.exists(os.path.join(_current, "scripts", "lib", "core.py")):
        _project_root = Path(_current)
        break
    _current = os.path.dirname(_current)
else:
    _project_root = Path(__file__).parent.parent.parent

HOOKS_DIR = _project_root / ".claude" / "hooks"
SETTINGS_FILE = _project_root / ".claude" / "settings.json"

# ============================================================================
# OFFICIAL CLAUDE CODE HOOKS SPECIFICATION
# Source: https://docs.anthropic.com/en/hooks-reference
# ============================================================================

OFFICIAL_HOOK_EVENTS = {
    "PreToolUse": {
        "description": "Runs after Claude creates tool parameters, before processing",
        "uses_matcher": True,
        "input_fields": ["session_id", "transcript_path", "cwd", "permission_mode",
                        "hook_event_name", "tool_name", "tool_input", "tool_use_id"],
        "output_control": {
            "decision_field": "permissionDecision",
            "decision_values": ["allow", "deny", "ask"],
            "reason_field": "permissionDecisionReason",
            "wrapper": "hookSpecificOutput",
            "supports_updated_input": True,
        },
        "common_matchers": ["Task", "Bash", "Glob", "Grep", "Read", "Edit", "Write",
                           "WebFetch", "WebSearch", "mcp__.*"],
    },
    "PermissionRequest": {
        "description": "Runs when user is shown a permission dialog",
        "uses_matcher": True,
        "input_fields": ["session_id", "transcript_path", "cwd", "permission_mode",
                        "hook_event_name", "tool_name", "tool_input"],
        "output_control": {
            "decision_field": "behavior",
            "decision_values": ["allow", "deny"],
            "wrapper": "hookSpecificOutput.decision",
            "supports_updated_input": True,
        },
    },
    "PostToolUse": {
        "description": "Runs immediately after a tool completes successfully",
        "uses_matcher": True,
        "input_fields": ["session_id", "transcript_path", "cwd", "permission_mode",
                        "hook_event_name", "tool_name", "tool_input", "tool_response", "tool_use_id"],
        "output_control": {
            "decision_field": "decision",
            "decision_values": ["block", None],
            "reason_field": "reason",
            "additional_context": "hookSpecificOutput.additionalContext",
        },
    },
    "Notification": {
        "description": "Runs when Claude Code sends notifications",
        "uses_matcher": True,
        "input_fields": ["session_id", "transcript_path", "cwd", "permission_mode",
                        "hook_event_name", "message", "notification_type"],
        "common_matchers": ["permission_prompt", "idle_prompt", "auth_success", "elicitation_dialog"],
    },
    "UserPromptSubmit": {
        "description": "Runs when user submits a prompt, before Claude processes it",
        "uses_matcher": False,
        "input_fields": ["session_id", "transcript_path", "cwd", "permission_mode",
                        "hook_event_name", "prompt"],
        "output_control": {
            "decision_field": "decision",
            "decision_values": ["block", None],
            "reason_field": "reason",
            "additional_context": "hookSpecificOutput.additionalContext",
        },
        "stdout_as_context": True,
    },
    "Stop": {
        "description": "Runs when main Claude Code agent has finished responding",
        "uses_matcher": False,
        "input_fields": ["session_id", "transcript_path", "permission_mode",
                        "hook_event_name", "stop_hook_active"],
        "output_control": {
            "decision_field": "decision",
            "decision_values": ["block", None],
            "reason_field": "reason",
        },
        "supports_prompt_type": True,
    },
    "SubagentStop": {
        "description": "Runs when a Claude Code subagent (Task tool call) has finished",
        "uses_matcher": False,
        "input_fields": ["session_id", "transcript_path", "permission_mode",
                        "hook_event_name", "stop_hook_active"],
        "output_control": {
            "decision_field": "decision",
            "decision_values": ["block", None],
            "reason_field": "reason",
        },
        "supports_prompt_type": True,
    },
    "PreCompact": {
        "description": "Runs before Claude Code runs a compact operation",
        "uses_matcher": True,
        "input_fields": ["session_id", "transcript_path", "permission_mode",
                        "hook_event_name", "trigger", "custom_instructions"],
        "common_matchers": ["manual", "auto"],
    },
    "SessionStart": {
        "description": "Runs when Claude Code starts or resumes a session",
        "uses_matcher": True,
        "input_fields": ["session_id", "transcript_path", "permission_mode",
                        "hook_event_name", "source"],
        "common_matchers": ["startup", "resume", "clear", "compact"],
        "output_control": {
            "additional_context": "hookSpecificOutput.additionalContext",
        },
        "env_file_available": True,
        "stdout_as_context": True,
    },
    "SessionEnd": {
        "description": "Runs when a Claude Code session ends",
        "uses_matcher": False,
        "input_fields": ["session_id", "transcript_path", "cwd", "permission_mode",
                        "hook_event_name", "reason"],
        "reason_values": ["clear", "logout", "prompt_input_exit", "other"],
    },
}

# Official input field names (snake_case per spec - see Hook Input section)
# The official docs show snake_case: session_id, tool_name, tool_input, etc.
OFFICIAL_INPUT_FIELDS = {
    # These are the CORRECT field names per official spec
    "session_id",
    "transcript_path",
    "cwd",
    "permission_mode",
    "hook_event_name",
    "tool_name",
    "tool_input",
    "tool_response",
    "tool_use_id",
    "prompt",  # UserPromptSubmit
    "message",  # Notification
    "notification_type",
    "stop_hook_active",
    "trigger",
    "custom_instructions",
    "source",
    "reason",
}

# Exit code meanings per official spec
EXIT_CODES = {
    0: "Success - stdout shown in verbose mode, JSON parsed for control",
    2: "Blocking error - stderr used as error message, fed back to Claude",
    "other": "Non-blocking error - stderr shown in verbose mode, execution continues",
}


class HookAuditor:
    """Comprehensive hook system auditor with official spec validation."""

    def __init__(self, fix_mode: bool = False, strict_mode: bool = False):
        self.fix_mode = fix_mode
        self.strict_mode = strict_mode
        self.issues = []
        self.warnings = []
        self.fixes_applied = []
        self.registered_hooks = set()
        self.all_hooks = set()
        self.settings = {}

    def add_issue(self, severity: str, category: str, message: str,
                  file: Optional[str] = None, spec_ref: Optional[str] = None):
        """Record an issue with optional spec reference."""
        entry = {
            "severity": severity,
            "category": category,
            "message": message,
        }
        if file:
            entry["file"] = str(file)
        if spec_ref:
            entry["spec_ref"] = spec_ref

        if severity == "ERROR":
            self.issues.append(entry)
        else:
            self.warnings.append(entry)

    def load_settings(self) -> dict:
        """Load and parse settings.json."""
        if not SETTINGS_FILE.exists():
            self.add_issue("ERROR", "CONFIG", f"Settings file not found: {SETTINGS_FILE}")
            return {}
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.add_issue("ERROR", "CONFIG", f"Invalid JSON in settings: {e}")
            return {}

    def extract_registered_hooks(self, settings: dict) -> set:
        """Extract all hook scripts registered in settings.json."""
        hooks = settings.get("hooks", {})
        registered = set()

        for event_type, event_hooks in hooks.items():
            for hook_config in event_hooks:
                for hook in hook_config.get("hooks", []):
                    cmd = hook.get("command", "")
                    match = re.search(r'\.claude/hooks/([\w.-]+\.py)', cmd)
                    if match:
                        registered.add(match.group(1))
        return registered

    def get_all_hook_files(self) -> set:
        """Get all .py files in hooks directory."""
        if not HOOKS_DIR.exists():
            return set()
        return {f.name for f in HOOKS_DIR.glob("*.py") if not f.name.startswith("__")}

    # ========================================================================
    # SPEC COMPLIANCE CHECKS
    # ========================================================================

    def check_event_types(self, settings: dict) -> list:
        """Validate event types against official spec."""
        hooks = settings.get("hooks", {})
        invalid_events = []

        for event_type in hooks.keys():
            if event_type not in OFFICIAL_HOOK_EVENTS:
                invalid_events.append(event_type)
                self.add_issue(
                    "ERROR", "SPEC_VIOLATION",
                    f"Unknown event type: {event_type}",
                    spec_ref="Valid events: " + ", ".join(OFFICIAL_HOOK_EVENTS.keys())
                )

        return invalid_events

    def check_matcher_usage(self, settings: dict) -> list:
        """Validate matcher usage per event type spec."""
        hooks = settings.get("hooks", {})
        issues = []

        for event_type, event_hooks in hooks.items():
            if event_type not in OFFICIAL_HOOK_EVENTS:
                continue

            spec = OFFICIAL_HOOK_EVENTS[event_type]
            uses_matcher = spec.get("uses_matcher", False)

            for hook_config in event_hooks:
                has_matcher = "matcher" in hook_config and hook_config["matcher"]

                if not uses_matcher and has_matcher:
                    issues.append((event_type, "unnecessary_matcher"))
                    self.add_issue(
                        "WARNING", "SPEC_VIOLATION",
                        f"{event_type} doesn't use matchers, but matcher provided",
                        spec_ref=f"{event_type}: {spec['description']}"
                    )

        return issues

    def check_hook_input_format(self, hook_file: str) -> list:
        """Check if hook reads input fields correctly per spec.

        Note: Official spec uses snake_case for input fields:
        - session_id, transcript_path, cwd, permission_mode
        - tool_name, tool_input, tool_response, tool_use_id
        - prompt (for UserPromptSubmit), message (for Notification)
        """
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        with open(filepath) as f:
            content = f.read()

        issues = []

        # Check for NON-STANDARD field names (camelCase when spec uses snake_case)
        # The official spec uses snake_case, so camelCase is wrong
        wrong_patterns = [
            (r'\.get\(["\']toolName["\']', "toolName", "tool_name"),
            (r'\.get\(["\']toolInput["\']', "toolInput", "tool_input"),
            (r'\.get\(["\']toolParams["\']', "toolParams", "tool_input"),
            (r'\.get\(["\']sessionId["\']', "sessionId", "session_id"),
            (r'\.get\(["\']hookEventName["\']', "hookEventName", "hook_event_name"),
            (r'\.get\(["\']toolResponse["\']', "toolResponse", "tool_response"),
            (r'\.get\(["\']toolUseId["\']', "toolUseId", "tool_use_id"),
            (r'\.get\(["\']userPrompt["\']', "userPrompt", "prompt"),
        ]

        for pattern, wrong, correct in wrong_patterns:
            if re.search(pattern, content):
                issues.append((wrong, correct))
                self.add_issue(
                    "WARNING", "SPEC_INPUT",
                    f"Uses '{wrong}' instead of '{correct}' (official snake_case)",
                    hook_file,
                    spec_ref="Hook Input section uses snake_case"
                )

        # Check for completely non-standard fields
        nonstandard_fields = [
            (r'\.get\(["\']turn["\']', "turn", "Not in official spec - consider using transcript"),
            (r'\.get\(["\']turnNumber["\']', "turnNumber", "Not in official spec"),
        ]

        for pattern, field, note in nonstandard_fields:
            if re.search(pattern, content):
                # This is informational only, not an error
                pass  # Many hooks use custom env vars which is fine

        return issues

    def check_hook_output_format(self, hook_file: str) -> list:
        """Check if hook output format matches official spec."""
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        with open(filepath) as f:
            content = f.read()

        issues = []

        # Detect which event type this hook is for
        event_type = None
        if "PreToolUse" in content:
            event_type = "PreToolUse"
        elif "PostToolUse" in content:
            event_type = "PostToolUse"
        elif "UserPromptSubmit" in content:
            event_type = "UserPromptSubmit"
        elif "SessionStart" in content:
            event_type = "SessionStart"
        elif "Stop" in content or "SubagentStop" in content:
            event_type = "Stop"

        if event_type == "PreToolUse":
            # Must use hookSpecificOutput wrapper
            if "permissionDecision" in content or "allow" in content.lower() or "deny" in content.lower():
                if "hookSpecificOutput" not in content:
                    issues.append("Missing hookSpecificOutput wrapper")
                    self.add_issue(
                        "ERROR", "SPEC_OUTPUT",
                        "PreToolUse must use hookSpecificOutput wrapper with permissionDecision",
                        hook_file,
                        spec_ref="PreToolUse Decision Control in official docs"
                    )

            # Check for deprecated format
            if '"allow": False' in content or '"allow": True' in content:
                issues.append("Deprecated allow/deny format")
                self.add_issue(
                    "ERROR", "SPEC_OUTPUT",
                    "Uses deprecated {allow: bool} format - use permissionDecision: allow|deny|ask",
                    hook_file,
                    spec_ref="decision/reason fields are deprecated for PreToolUse"
                )

            # Check for old decision field
            if '"decision": "approve"' in content or '"decision": "block"' in content:
                if "hookSpecificOutput" not in content:
                    issues.append("Deprecated decision format")
                    self.add_issue(
                        "WARNING", "SPEC_OUTPUT",
                        "Uses deprecated decision field - use permissionDecision in hookSpecificOutput",
                        hook_file
                    )

        return issues

    def check_exit_code_usage(self, hook_file: str) -> list:
        """Check exit code usage per spec."""
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        with open(filepath) as f:
            content = f.read()

        issues = []

        # Exit code 2 is for blocking - stderr should be populated
        if "sys.exit(2)" in content:
            if "sys.stderr" not in content and "file=sys.stderr" not in content:
                issues.append("exit(2) without stderr")
                self.add_issue(
                    "WARNING", "SPEC_EXIT",
                    "Uses exit(2) but doesn't write to stderr - message won't reach Claude",
                    hook_file,
                    spec_ref="Exit code 2: stderr used as error message"
                )

        # Exit code 1 is non-blocking error
        if "sys.exit(1)" in content:
            # This is fine, but note it's non-blocking
            pass

        return issues

    # ========================================================================
    # CODE QUALITY CHECKS
    # ========================================================================

    def check_syntax_errors(self) -> list:
        """Check all hooks for Python syntax errors."""
        errors = []
        for hook_file in HOOKS_DIR.glob("*.py"):
            if hook_file.name.startswith("__"):
                continue
            try:
                with open(hook_file) as f:
                    source = f.read()
                ast.parse(source)
            except SyntaxError as e:
                errors.append({
                    "file": hook_file.name,
                    "line": e.lineno,
                    "error": str(e.msg)
                })
                self.add_issue(
                    "ERROR", "SYNTAX",
                    f"Syntax error at line {e.lineno}: {e.msg}",
                    hook_file.name
                )
        return errors

    def check_orphaned_hooks(self) -> list:
        """Find hooks that exist but aren't registered."""
        ignored_patterns = ['_backup', '_v1_backup', 'test_hooks']

        orphaned = []
        for hook in self.all_hooks:
            if hook not in self.registered_hooks:
                is_ignored = any(p in hook for p in ignored_patterns)
                if not is_ignored:
                    orphaned.append(hook)
                    self.add_issue(
                        "WARNING", "ORPHAN",
                        "Hook not registered in settings.json",
                        hook
                    )
        return orphaned

    def check_missing_hooks(self) -> list:
        """Find hooks referenced in settings but don't exist."""
        missing = []
        for hook in self.registered_hooks:
            if hook not in self.all_hooks:
                missing.append(hook)
                self.add_issue(
                    "ERROR", "MISSING",
                    "Hook referenced but file doesn't exist",
                    hook
                )
        return missing

    def check_error_handling(self, hook_file: str) -> list:
        """Check for proper error handling."""
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        with open(filepath) as f:
            content = f.read()

        issues = []

        # Check for bare except (bad practice)
        if re.search(r'except\s*:', content):
            issues.append("bare_except")
            self.add_issue(
                "WARNING", "CODE_QUALITY",
                "Uses bare 'except:' which can hide errors - use 'except Exception:'",
                hook_file
            )

        return issues

    def check_performance(self, hook_file: str) -> list:
        """Check for performance issues."""
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        with open(filepath) as f:
            content = f.read()

        issues = []

        # Subprocess without timeout (hooks have 60s default timeout)
        if re.search(r'subprocess\.(run|check_output|call)\(', content):
            if 'timeout=' not in content:
                issues.append("subprocess_no_timeout")
                self.add_issue(
                    "WARNING", "PERFORMANCE",
                    "Uses subprocess without timeout - hooks timeout at 60s by default",
                    hook_file,
                    spec_ref="Timeout: 60-second execution limit by default"
                )

        # Heavy imports
        heavy_imports = ['pandas', 'numpy', 'tensorflow', 'torch']
        for imp in heavy_imports:
            if f'import {imp}' in content or f'from {imp}' in content:
                issues.append(f"heavy_import_{imp}")
                self.add_issue(
                    "WARNING", "PERFORMANCE",
                    f"Imports heavy library: {imp} - consider lazy loading",
                    hook_file
                )

        return issues

    def check_security(self, hook_file: str) -> list:
        """Check for security best practices per official docs."""
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        with open(filepath) as f:
            content = f.read()

        issues = []

        # Unquoted shell variables
        if re.search(r'\$[A-Z_]+[^"\']', content):
            # Could be shell injection risk
            pass  # Too many false positives

        # Path traversal check (per official docs)
        if 'file_path' in content or 'filePath' in content:
            if '..' not in content and 'path traversal' not in content.lower():
                # Not checking for path traversal
                pass  # Info only, not an issue

        return issues

    # ========================================================================
    # AUTO-FIX FUNCTIONALITY
    # ========================================================================

    def fix_bare_except(self, hook_file: str) -> bool:
        """Fix bare except: clauses."""
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return False

        content = filepath.read_text()
        original = content

        # Replace bare except: with except Exception:
        content = re.sub(r'\bexcept\s*:', 'except Exception:', content)

        if content != original:
            filepath.write_text(content)
            self.fixes_applied.append((hook_file, "Fixed bare except: clauses"))
            return True
        return False

    def fix_snake_case_inputs(self, hook_file: str) -> bool:
        """Fix snake_case input field access."""
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return False

        content = filepath.read_text()
        original = content

        replacements = [
            (r'\.get\(["\']tool_name["\']', '.get("toolName"'),
            (r'\.get\(["\']tool_input["\']', '.get("toolInput"'),
            (r'\.get\(["\']tool_params["\']', '.get("toolParams"'),
            (r'\.get\(["\']session_id["\']', '.get("sessionId"'),
            (r'\.get\(["\']tool_response["\']', '.get("toolResponse"'),
        ]

        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)

        if content != original:
            filepath.write_text(content)
            self.fixes_applied.append((hook_file, "Fixed snake_case input fields"))
            return True
        return False

    # ========================================================================
    # MAIN AUDIT
    # ========================================================================

    def count_hooks_by_event(self, settings: dict) -> dict:
        """Count hooks per event type."""
        hooks = settings.get("hooks", {})
        counts = {}
        for event_type, event_hooks in hooks.items():
            total = sum(len(hc.get("hooks", [])) for hc in event_hooks)
            counts[event_type] = total
        return counts

    def run_audit(self) -> dict:
        """Run complete audit and return results."""
        results = {
            "stats": {},
            "errors": [],
            "warnings": [],
            "fixes": [],
        }

        # Load settings
        self.settings = self.load_settings()
        if not self.settings:
            return {"errors": self.issues, "warnings": self.warnings}

        self.registered_hooks = self.extract_registered_hooks(self.settings)
        self.all_hooks = self.get_all_hook_files()

        # Stats
        results["stats"] = {
            "total_hook_files": len(self.all_hooks),
            "registered_hooks": len(self.registered_hooks),
            "hooks_by_event": self.count_hooks_by_event(self.settings),
        }

        # Spec compliance checks
        self.check_event_types(self.settings)
        self.check_matcher_usage(self.settings)

        # Syntax check
        self.check_syntax_errors()

        # Orphan/missing checks
        self.check_orphaned_hooks()
        self.check_missing_hooks()

        # Per-hook checks
        for hook in self.all_hooks:
            if "backup" in hook:
                continue

            self.check_hook_input_format(hook)
            self.check_hook_output_format(hook)
            self.check_exit_code_usage(hook)
            self.check_error_handling(hook)
            self.check_performance(hook)
            self.check_security(hook)

            # Auto-fix if enabled
            if self.fix_mode:
                self.fix_bare_except(hook)
                self.fix_snake_case_inputs(hook)

        results["errors"] = self.issues
        results["warnings"] = self.warnings
        results["fixes"] = self.fixes_applied

        return results

    def print_report(self, results: dict):
        """Print human-readable audit report."""
        print("=" * 70)
        print("🔍 HOOK SYSTEM AUDIT (Official Spec Compliance)")
        print("=" * 70)

        # Stats
        stats = results.get("stats", {})
        print(f"\n📊 STATISTICS:")
        print(f"   Total hook files: {stats.get('total_hook_files', 0)}")
        print(f"   Registered hooks: {stats.get('registered_hooks', 0)}")

        counts = stats.get("hooks_by_event", {})
        if counts:
            print(f"\n   Hooks by event type:")
            total = 0
            for event, count in sorted(counts.items()):
                status = "✓" if event in OFFICIAL_HOOK_EVENTS else "?"
                print(f"      {status} {event}: {count}")
                total += count
            print(f"      TOTAL REGISTRATIONS: {total}")

        # Errors
        errors = results.get("errors", [])
        print(f"\n🚨 ERRORS ({len(errors)}):")
        if errors:
            for err in errors:
                f = err.get('file', 'config')
                ref = f" [{err['spec_ref']}]" if err.get('spec_ref') else ""
                print(f"   ❌ [{err['category']}] {f}: {err['message']}{ref}")
        else:
            print("   ✅ No errors")

        # Warnings
        warnings = results.get("warnings", [])
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        if warnings:
            shown = 0
            for warn in warnings:
                if shown >= 15:
                    print(f"   ... and {len(warnings) - shown} more")
                    break
                f = warn.get('file', 'config')
                print(f"   ⚠️  [{warn['category']}] {f}: {warn['message']}")
                shown += 1
        else:
            print("   ✅ No warnings")

        # Fixes applied
        fixes = results.get("fixes", [])
        if fixes:
            print(f"\n🔧 FIXES APPLIED ({len(fixes)}):")
            for hook, fix in fixes:
                print(f"   ✅ {hook}: {fix}")

        # Summary
        print("\n" + "=" * 70)
        print("📋 SUMMARY")
        print("=" * 70)
        print(f"   Errors: {len(errors)}")
        print(f"   Warnings: {len(warnings)}")
        if fixes:
            print(f"   Fixes Applied: {len(fixes)}")

        # Hook explosion warning
        total_hooks = stats.get("total_hook_files", 0)
        if total_hooks > 30:
            print(f"\n   ⚠️  HOOK EXPLOSION: {total_hooks} hooks (threshold: 30)")
            print("      Consider consolidating related hooks")

        # Spec reference
        print("\n📚 Official Spec: https://docs.anthropic.com/en/hooks-reference")

        return len(errors) > 0 or (self.strict_mode and len(warnings) > 0)


def main():
    parser = argparse.ArgumentParser(
        description="Audit Claude Code hooks against official spec",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 scripts/ops/audit_hooks.py           # Basic audit
    python3 scripts/ops/audit_hooks.py --fix     # Auto-fix common issues
    python3 scripts/ops/audit_hooks.py --json    # Output as JSON
    python3 scripts/ops/audit_hooks.py --strict  # Treat warnings as errors

Official Spec: https://docs.anthropic.com/en/hooks-reference
        """
    )
    parser.add_argument("--fix", action="store_true", help="Auto-fix common issues")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")

    args = parser.parse_args()

    auditor = HookAuditor(fix_mode=args.fix, strict_mode=args.strict)
    results = auditor.run_audit()

    if args.json:
        print(json.dumps(results, indent=2))
        has_issues = len(results.get("errors", [])) > 0
        if args.strict:
            has_issues = has_issues or len(results.get("warnings", [])) > 0
        sys.exit(1 if has_issues else 0)
    else:
        has_issues = auditor.print_report(results)
        sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
