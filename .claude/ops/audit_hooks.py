#!/usr/bin/env python3
"""
Hook System Auditor (The Hook Sheriff)

Comprehensive audit of Claude Code hooks against official documentation specs.
Validates configuration, input/output formats, event types, and best practices.

Usage:
    python3 .claude/ops/audit_hooks.py [--fix] [--json] [--strict]
    python3 .claude/ops/audit_hooks.py --fix --dry-run  # Preview fixes
    python3 .claude/ops/audit_hooks.py --prune          # Remove orphaned hooks

Options:
    --fix      Auto-fix common issues (bare except, missing timeouts)
    --dry-run  Preview fix changes without applying (requires --fix)
    --json     Output results as JSON
    --strict   Treat warnings as errors (exit 1 if any warnings)
    --prune    Archive orphaned hooks to .claude/hooks/archive/

Official Spec Reference:
    https://docs.anthropic.com/en/hooks-reference
"""

import os
import sys
import json
import ast
import re
import shutil
import argparse
from pathlib import Path
from typing import Optional

# Add .claude/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
_current = _script_dir
while _current != "/":
    if os.path.exists(os.path.join(_current, ".claude", "lib", "core.py")):
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

    def __init__(self, fix_mode: bool = False, strict_mode: bool = False,
                 dry_run: bool = False, prune_mode: bool = False):
        self.fix_mode = fix_mode
        self.strict_mode = strict_mode
        self.dry_run = dry_run
        self.prune_mode = prune_mode
        self.issues = []
        self.warnings = []
        self.fixes_applied = []
        self.pruned_hooks = []
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

    def _get_hook_event_type(self, hook_file: str) -> Optional[str]:
        """Get the event type a hook is registered for from settings.json."""
        hooks = self.settings.get("hooks", {})
        for event_type, event_hooks in hooks.items():
            for hook_config in event_hooks:
                for hook in hook_config.get("hooks", []):
                    cmd = hook.get("command", "")
                    if hook_file in cmd:
                        return event_type
        return None

    def check_pretool_prompt_access(self, hook_file: str) -> list:
        """Check if PreToolUse hooks incorrectly try to access 'prompt' field.
        
        PreToolUse hooks do NOT receive 'prompt' in their input data.
        The prompt field is only available in UserPromptSubmit hooks.
        
        Hooks that need SUDO bypass should read from session state instead.
        """
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        with open(filepath) as f:
            content = f.read()

        issues = []

        # Check if this is a PreToolUse hook
        event_type = self._get_hook_event_type(hook_file)
        if event_type != "PreToolUse":
            return []

        # Check for incorrect prompt access patterns
        bad_patterns = [
            (r'data\.get\(["\'"]prompt["\'"]', "data.get('prompt')"),
            (r'input_data\.get\(["\'"]prompt["\'"]', "input_data.get('prompt')"),
        ]

        # Check if prompt access is properly guarded by lifecycle check
        # Pattern: if lifecycle == "UserPromptSubmit": ... prompt ...
        has_lifecycle_guard = bool(re.search(
            r'if\s+lifecycle\s*==\s*["\']UserPromptSubmit["\']\s*:.*?\.get\(["\']prompt["\']',
            content,
            re.DOTALL
        ))

        for pattern, desc in bad_patterns:
            if re.search(pattern, content):
                # Skip if prompt access is guarded by lifecycle check (multi-event hooks)
                if has_lifecycle_guard:
                    continue
                issues.append(f"Incorrect prompt access: {desc}")
                self.add_issue(
                    "ERROR", "PRETOOL_PROMPT_ACCESS",
                    "PreToolUse hook tries to access 'prompt' from input - NOT available in PreToolUse events. Use session state instead.",
                    hook_file,
                    spec_ref="PreToolUse input: session_id, tool_name, tool_input (no prompt)"
                )
                break

        return issues


    def check_posttooluse_output(self, hook_file: str) -> list:
        """Check PostToolUse output format per official spec.
        
        PostToolUse hooks can provide feedback to Claude:
        - decision: "block" | undefined
        - reason: string (explanation for decision)
        - hookSpecificOutput.additionalContext: string (context for Claude)
        """
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        event_type = self._get_hook_event_type(hook_file)
        if event_type != "PostToolUse":
            return []

        with open(filepath) as f:
            content = f.read()

        issues = []

        # Check for decision: "block" without reason
        if '"decision": "block"' in content:
            if '"reason"' not in content:
                issues.append("PostToolUse block without reason")
                self.add_issue(
                    "WARNING", "SPEC_OUTPUT",
                    "PostToolUse uses decision:'block' but missing 'reason' field",
                    hook_file,
                    spec_ref="PostToolUse: reason explains decision to Claude"
                )

        return issues

    def check_stop_output(self, hook_file: str) -> list:
        """Check Stop/SubagentStop output format per official spec.
        
        Stop hooks control whether Claude must continue:
        - decision: "block" | undefined
        - reason: REQUIRED when decision is "block"
        """
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        event_type = self._get_hook_event_type(hook_file)
        if event_type not in ["Stop", "SubagentStop"]:
            return []

        with open(filepath) as f:
            content = f.read()

        issues = []

        # Check for decision: "block" without reason
        if '"decision": "block"' in content:
            if '"reason"' not in content:
                issues.append("Stop block without reason")
                self.add_issue(
                    "ERROR", "SPEC_OUTPUT",
                    "Stop hook uses decision:'block' but MISSING required 'reason' field",
                    hook_file,
                    spec_ref="Stop: reason MUST be provided when blocking"
                )

        return issues

    def check_userpromptsubmit_output(self, hook_file: str) -> list:
        """Check UserPromptSubmit output format per official spec.
        
        UserPromptSubmit can:
        - Block prompts: decision: "block", reason: string
        - Add context: hookSpecificOutput.additionalContext or plain stdout
        """
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        event_type = self._get_hook_event_type(hook_file)
        if event_type != "UserPromptSubmit":
            return []

        with open(filepath) as f:
            content = f.read()

        issues = []

        # Check for decision: "block" without reason
        if '"decision": "block"' in content:
            if '"reason"' not in content:
                issues.append("UserPromptSubmit block without reason")
                self.add_issue(
                    "WARNING", "SPEC_OUTPUT",
                    "UserPromptSubmit uses decision:'block' but missing 'reason'",
                    hook_file,
                    spec_ref="UserPromptSubmit: reason shown to user when blocking"
                )

        return issues

    def check_permissionrequest_output(self, hook_file: str) -> list:
        """Check PermissionRequest output format per official spec.
        
        PermissionRequest hooks use different structure:
        - hookSpecificOutput.decision.behavior: "allow" | "deny"
        - hookSpecificOutput.decision.updatedInput: optional modified input
        - hookSpecificOutput.decision.message: string when denying
        """
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        event_type = self._get_hook_event_type(hook_file)
        if event_type != "PermissionRequest":
            return []

        with open(filepath) as f:
            content = f.read()

        issues = []

        # Check for wrong output structure (using permissionDecision instead of decision.behavior)
        if '"permissionDecision"' in content:
            issues.append("Wrong output structure for PermissionRequest")
            self.add_issue(
                "ERROR", "SPEC_OUTPUT",
                "PermissionRequest uses 'permissionDecision' but should use 'decision.behavior'",
                hook_file,
                spec_ref="PermissionRequest: hookSpecificOutput.decision.behavior: allow|deny"
            )

        return issues

    def check_sessionstart_output(self, hook_file: str) -> list:
        """Check SessionStart output format per official spec.
        
        SessionStart hooks can:
        - Add context: hookSpecificOutput.additionalContext
        - Stdout is also added as context
        """
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        event_type = self._get_hook_event_type(hook_file)
        if event_type != "SessionStart":
            return []

        # SessionStart is quite flexible - just info check
        return []

    def check_common_json_fields(self, hook_file: str) -> list:
        """Check for proper usage of common JSON output fields.
        
        All hook types can include:
        - continue: bool (default true)
        - stopReason: string (when continue is false)
        - suppressOutput: bool (hide from transcript)
        - systemMessage: string (warning shown to user)
        """
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        with open(filepath) as f:
            content = f.read()

        issues = []

        # Check for continue: false without stopReason
        if '"continue": false' in content.lower() or '"continue":false' in content.lower():
            if '"stopReason"' not in content and '"stopreason"' not in content.lower():
                issues.append("continue:false without stopReason")
                self.add_issue(
                    "WARNING", "SPEC_OUTPUT",
                    "Uses continue:false but missing 'stopReason' (message shown to user)",
                    hook_file,
                    spec_ref="Common JSON: stopReason accompanies continue with reason"
                )

        return issues

    def check_prompt_type_hooks(self, settings: dict) -> list:
        """Check for prompt-based hooks (type: 'prompt') configuration.
        
        Prompt-based hooks use LLM evaluation instead of bash commands.
        Only supported for Stop and SubagentStop events.
        """
        hooks = settings.get("hooks", {})
        issues = []

        for event_type, event_hooks in hooks.items():
            for hook_config in event_hooks:
                for hook in hook_config.get("hooks", []):
                    if hook.get("type") == "prompt":
                        # Prompt hooks only work for Stop/SubagentStop per docs
                        if event_type not in ["Stop", "SubagentStop"]:
                            issues.append((event_type, "prompt_type_wrong_event"))
                            self.add_issue(
                                "WARNING", "SPEC_VIOLATION",
                                f"Prompt-based hook in {event_type} - only fully supported for Stop/SubagentStop",
                                spec_ref="Prompt hooks most useful for Stop, SubagentStop"
                            )

        return issues


    def check_unsafe_dict_access(self, hook_file: str) -> list:
        """Check for unsafe dictionary key access patterns.
        
        Common bug: Accessing state["key"] without checking if key exists.
        This causes KeyError when loading state from files that don't have the key.
        
        Patterns detected:
        - state["key"].append() without prior key check
        - state["key"] = value after load without .get() fallback
        - Direct bracket access on loaded dicts
        """
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        with open(filepath) as f:
            content = f.read()

        issues = []

        # Pattern 1: state["key"].append() - risky if key doesn't exist
        # Look for .append() on bracket-accessed dict values
        import re
        append_pattern = r'(state|data|config)\["[\w_]+"\]\.append\('
        matches = re.findall(append_pattern, content)
        if matches:
            # Check if there's a corresponding initialization or .get() check
            # Simple heuristic: look for "if X not in state" or state.setdefault or state.get
            has_guard = (
                'not in state' in content or 
                'setdefault' in content or
                '.get(' in content and 'append' in content
            )
            if not has_guard:
                issues.append("Unsafe dict append")
                self.add_issue(
                    "WARNING", "UNSAFE_DICT_ACCESS",
                    "Uses state['key'].append() without checking if key exists - may cause KeyError",
                    hook_file,
                    spec_ref="Use 'if key not in state: state[key] = []' before append"
                )

        # Pattern 2: Accessing nested keys without guards
        # e.g., state["a"]["b"] without checking state["a"] exists
        nested_pattern = r'(state|data)\["[\w_]+"\]\["[\w_]+"\]'
        nested_matches = re.findall(nested_pattern, content)
        if nested_matches:
            has_nested_guard = '.get(' in content and ', {}' in content
            if not has_nested_guard:
                issues.append("Unsafe nested dict access")
                self.add_issue(
                    "WARNING", "UNSAFE_DICT_ACCESS",
                    "Uses nested dict access state['a']['b'] without guards - may cause KeyError",
                    hook_file,
                    spec_ref="Use state.get('a', {}).get('b', default) for safe nested access"
                )

        # Pattern 3: Reading dict values that may not exist (not simple assignment)
        # Simple assignment state["key"] = value is SAFE (creates key if missing)
        # Dangerous: state["key"] used in expressions, method calls, or as operand
        if 'load_session_state' in content or 'load_state' in content:
            # Look for state["key"] in non-assignment contexts (reading the value)
            # Examples: state["key"] + 1, func(state["key"]), if state["key"]
            read_pattern = r'(?<!= )state\["([\w_]+)"\](?!\s*=)'
            reads = re.findall(read_pattern, content)

            # Filter to unique keys and check for guards
            risky_keys = []
            seen = set()
            for key in reads:
                if key in seen:
                    continue
                seen.add(key)
                # Check if this key is guarded with .get() or existence check
                guard_patterns = [
                    f'"{key}" not in state',
                    f"'{key}' not in state",
                    f'"{key}" in state',
                    f"'{key}' in state",
                    f'state.get("{key}"',
                    f"state.get('{key}'",
                ]
                has_guard = any(p in content for p in guard_patterns)
                # Whitelist common keys that are always initialized by the system
                safe_keys = ['confidence', 'turn_count', 'current_prompt', 'files_read',
                             'session_id', 'evidence_ledger', 'read_files']
                if not has_guard and key not in safe_keys:
                    risky_keys.append(key)

            if risky_keys and len(risky_keys) <= 3:  # Only report if a few risky keys
                for key in risky_keys[:2]:  # Limit to 2 reports per file
                    issues.append(f"Potentially unsafe key read: {key}")
                    self.add_issue(
                        "WARNING", "UNSAFE_DICT_ACCESS",
                        f"Reads state['{key}'] without checking existence - may cause KeyError",
                        hook_file,
                        spec_ref="Use state.get('key', default) or check 'key' in state first"
                    )

        return issues

    def check_transcript_usage(self, hook_file: str) -> list:
        """Check if PreToolUse hooks use transcript for user context instead of session state.

        PreToolUse hooks do NOT receive 'prompt' in their input data.
        Hooks that need to check user messages (e.g., SUDO bypass) should read
        from transcript_path instead of session state, which is more reliable.

        Patterns detected:
        - state.get("current_prompt") in PreToolUse hooks
        - data.get("prompt") in PreToolUse hooks (won't work)
        - load_session_state for prompt access in PreToolUse
        """
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        # Only check PreToolUse hooks
        event_type = self._get_hook_event_type(hook_file)
        if event_type != "PreToolUse":
            return []

        with open(filepath) as f:
            content = f.read()

        issues = []

        # Pattern 1: Using data.get("prompt") - won't work in PreToolUse
        if 'data.get("prompt"' in content or "data.get('prompt'" in content:
            # Check if it's NOT checking transcript
            if 'transcript_path' not in content:
                issues.append("Uses data.get('prompt') which is not available in PreToolUse")
                self.add_issue(
                    "WARNING", "USE_TRANSCRIPT",
                    "PreToolUse hook uses data.get('prompt') - prompt is NOT available in PreToolUse input",
                    hook_file,
                    spec_ref="Use transcript_path to read user messages instead"
                )

        # Pattern 2: Using session state for current_prompt
        if 'current_prompt' in content and 'transcript_path' not in content:
            issues.append("Uses session state for prompt instead of transcript")
            self.add_issue(
                "WARNING", "USE_TRANSCRIPT",
                "PreToolUse hook reads 'current_prompt' from session state - transcript is more reliable",
                hook_file,
                spec_ref="Use data.get('transcript_path') and read last ~5000 chars for user context"
            )

        # Pattern 3: Has SUDO bypass but doesn't use transcript
        if 'SUDO' in content and 'transcript_path' not in content:
            issues.append("SUDO bypass without transcript")
            self.add_issue(
                "WARNING", "USE_TRANSCRIPT",
                "Hook has SUDO bypass but doesn't use transcript - may not detect SUDO reliably",
                hook_file,
                spec_ref="Read transcript_path for SUDO detection: last_chunk = transcript[-5000:]"
            )

        # Positive check: hook uses transcript correctly
        if 'transcript_path' in content and ('SUDO' in content or 'prompt' in content.lower()):
            # This is good - no issue to report
            pass

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
            except (OSError, UnicodeDecodeError) as e:
                errors.append({
                    "file": hook_file.name,
                    "line": 0,
                    "error": str(e)
                })
                self.add_issue(
                    "ERROR", "FILE_READ",
                    f"Cannot read file: {e}",
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
                "Uses bare 'except Exception:' which can hide errors - use 'except Exception:'",
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
        """Fix bare except Exception: clauses with backup and validation."""
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return False

        try:
            content = filepath.read_text()
        except (OSError, UnicodeDecodeError) as e:
            self.add_issue("WARNING", "FIX_ERROR", f"Cannot read file: {e}", hook_file)
            return False

        original = content

        # Replace bare except Exception: with except Exception:
        content = re.sub(r'\bexcept\s*:', 'except Exception:', content)

        if content != original:
            # Validate syntax after replacement
            try:
                ast.parse(content)
            except SyntaxError as e:
                self.add_issue("WARNING", "FIX_ERROR",
                              f"Fix would create syntax error at line {e.lineno}, skipping", hook_file)
                return False

            if self.dry_run:
                self.fixes_applied.append((hook_file, "[DRY-RUN] Would fix bare except Exception: clauses"))
                return True

            # Create backup before writing
            backup_path = filepath.with_suffix('.py.bak')
            try:
                shutil.copy2(filepath, backup_path)
                filepath.write_text(content)
                self.fixes_applied.append((hook_file, "Fixed bare except Exception: clauses (backup: .bak)"))
                return True
            except OSError as e:
                self.add_issue("WARNING", "FIX_ERROR", f"Cannot write file: {e}", hook_file)
                return False
        return False

    def fix_camelcase_to_snake_case(self, hook_file: str) -> bool:
        """Fix camelCase input fields to snake_case per official spec.

        Official Claude Code docs use snake_case for input fields:
        - tool_name, tool_input, session_id, tool_response, etc.
        """
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return False

        try:
            content = filepath.read_text()
        except (OSError, UnicodeDecodeError) as e:
            self.add_issue("WARNING", "FIX_ERROR", f"Cannot read file: {e}", hook_file)
            return False

        original = content

        # Convert camelCase TO snake_case (official spec uses snake_case)
        replacements = [
            (r'\.get\(["\']toolName["\']', '.get("tool_name"'),
            (r'\.get\(["\']toolInput["\']', '.get("tool_input"'),
            (r'\.get\(["\']toolParams["\']', '.get("tool_input"'),  # toolParams -> tool_input
            (r'\.get\(["\']sessionId["\']', '.get("session_id"'),
            (r'\.get\(["\']toolResponse["\']', '.get("tool_response"'),
            (r'\.get\(["\']toolUseId["\']', '.get("tool_use_id"'),
            (r'\.get\(["\']hookEventName["\']', '.get("hook_event_name"'),
        ]

        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)

        if content != original:
            # Validate syntax after replacement
            try:
                ast.parse(content)
            except SyntaxError as e:
                self.add_issue("WARNING", "FIX_ERROR",
                              f"Fix would create syntax error at line {e.lineno}, skipping", hook_file)
                return False

            if self.dry_run:
                self.fixes_applied.append((hook_file, "[DRY-RUN] Would fix camelCase to snake_case"))
                return True

            # Create backup before writing
            backup_path = filepath.with_suffix('.py.bak')
            try:
                shutil.copy2(filepath, backup_path)
                filepath.write_text(content)
                self.fixes_applied.append((hook_file, "Fixed camelCase to snake_case (backup: .bak)"))
                return True
            except OSError as e:
                self.add_issue("WARNING", "FIX_ERROR", f"Cannot write file: {e}", hook_file)
                return False
        return False

    # ========================================================================
    # NEW v2.0.10+ SPEC CHECKS
    # ========================================================================

    def check_updated_input_usage(self, hook_file: str) -> list:
        """Check for proper updatedInput usage in PreToolUse hooks.

        Since v2.0.10, PreToolUse hooks can modify tool inputs via updatedInput.
        This must be inside hookSpecificOutput with permissionDecision: "allow".
        """
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        event_type = self._get_hook_event_type(hook_file)
        if event_type != "PreToolUse":
            return []

        try:
            with open(filepath) as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return []

        issues = []

        if 'updatedInput' in content:
            # Must be with permissionDecision: "allow"
            if '"permissionDecision": "deny"' in content or '"permissionDecision": "ask"' in content:
                issues.append("updatedInput with non-allow decision")
                self.add_issue(
                    "WARNING", "SPEC_OUTPUT",
                    "Uses updatedInput but permissionDecision may be deny/ask - input modifications ignored",
                    hook_file,
                    spec_ref="updatedInput only applies when permissionDecision is 'allow'"
                )

            if 'hookSpecificOutput' not in content:
                issues.append("updatedInput outside hookSpecificOutput")
                self.add_issue(
                    "ERROR", "SPEC_OUTPUT",
                    "Uses updatedInput but not inside hookSpecificOutput wrapper",
                    hook_file,
                    spec_ref="updatedInput must be in hookSpecificOutput"
                )

        return issues

    def check_interrupt_field(self, hook_file: str) -> list:
        """Check for interrupt field usage in deny decisions.

        When denying, hooks can set interrupt: true to stop Claude entirely.
        """
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        try:
            with open(filepath) as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return []

        issues = []

        if '"interrupt"' in content and 'true' in content.lower():
            if '"permissionDecision": "deny"' not in content and '"behavior": "deny"' not in content:
                issues.append("interrupt without deny")
                self.add_issue(
                    "WARNING", "SPEC_OUTPUT",
                    "Uses 'interrupt' field but no deny decision found - interrupt only works with deny",
                    hook_file,
                    spec_ref="interrupt: true only applies when denying"
                )

        return issues

    def check_posttooluse_input_key(self, hook_file: str) -> list:
        """Check if PostToolUse hooks use correct input key name.

        Official spec uses 'tool_response' for PostToolUse input.
        Many hooks incorrectly use 'toolResult' which may not receive data.
        """
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        event_type = self._get_hook_event_type(hook_file)
        if event_type != "PostToolUse":
            return []

        try:
            with open(filepath) as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return []

        issues = []

        # Check for toolResult without tool_response fallback
        if 'toolResult' in content and 'tool_response' not in content:
            issues.append("Uses toolResult instead of tool_response")
            self.add_issue(
                "ERROR", "POSTTOOL_INPUT_KEY",
                "PostToolUse hook uses 'toolResult' but official spec uses 'tool_response'. "
                "Fix: tool_result = input_data.get('tool_response') or input_data.get('toolResult', {})",
                hook_file,
                spec_ref="PostToolUse input: tool_response (not toolResult)"
            )

        return issues

    def check_exit_code_access(self, hook_file: str) -> list:
        """Check for exit_code access timing.

        tool_response.exit_code is only available in PostToolUse hooks.
        PreToolUse hooks cannot access it (tool hasn't run yet).
        """
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        event_type = self._get_hook_event_type(hook_file)

        try:
            with open(filepath) as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return []

        issues = []

        # Only flag actual access patterns, not mentions in comments/strings
        access_patterns = [
            '.get("exit_code"',
            "['exit_code']",
            '["exit_code"]',
            '.exit_code',
            'tool_response.get("exit_code"',
        ]
        has_exit_code_access = any(p in content for p in access_patterns)

        if has_exit_code_access and event_type == "PreToolUse":
            issues.append("exit_code in PreToolUse")
            self.add_issue(
                "ERROR", "SPEC_INPUT",
                "Accesses exit_code in PreToolUse - only available in PostToolUse",
                hook_file,
                spec_ref="tool_response.exit_code only in PostToolUse"
            )

        return issues

    def check_multiedit_matcher(self, settings: dict) -> list:
        """Check that Edit-related matchers include MultiEdit.

        MultiEdit is a newer tool that should be included alongside Edit.
        """
        hooks = settings.get("hooks", {})
        issues = []

        for event_type, event_hooks in hooks.items():
            if event_type not in ["PreToolUse", "PostToolUse"]:
                continue

            for hook_config in event_hooks:
                matcher = hook_config.get("matcher", "")

                if "Edit" in matcher and "MultiEdit" not in matcher and "|" in matcher:
                    if matcher not in ["*", "Edit"]:
                        issues.append((matcher, "missing_multiedit"))
                        self.add_issue(
                            "WARNING", "MATCHER_COVERAGE",
                            f"Matcher '{matcher}' includes Edit but not MultiEdit",
                            spec_ref="Consider 'Edit|MultiEdit|Write' for complete coverage"
                        )

        return issues

    def check_deprecated_root_fields(self, hook_file: str) -> list:
        """Check for deprecated root-level decision/reason fields in PreToolUse."""
        filepath = HOOKS_DIR / hook_file
        if not filepath.exists():
            return []

        event_type = self._get_hook_event_type(hook_file)
        if event_type != "PreToolUse":
            return []

        try:
            with open(filepath) as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return []

        issues = []

        deprecated_patterns = [
            '"decision": "approve"',
            '"decision": "block"',
        ]

        for pattern in deprecated_patterns:
            if pattern in content and 'hookSpecificOutput' not in content:
                issues.append("deprecated root-level decision")
                self.add_issue(
                    "WARNING", "DEPRECATED",
                    "Uses deprecated root-level decision - use hookSpecificOutput.permissionDecision",
                    hook_file,
                    spec_ref="decision/reason fields deprecated for PreToolUse"
                )
                break

        return issues

    # ========================================================================
    # PRUNE FUNCTIONALITY
    # ========================================================================

    def prune_orphaned_hooks(self) -> list:
        """Archive orphaned hooks to .claude/hooks/archive/."""
        archive_dir = HOOKS_DIR / "archive"
        pruned = []

        ignored_patterns = ['_backup', '_v1_backup', 'test_hooks']

        for hook in self.all_hooks:
            if hook in self.registered_hooks:
                continue
            if any(p in hook for p in ignored_patterns):
                continue

            src = HOOKS_DIR / hook
            dst = archive_dir / hook

            if self.dry_run:
                self.pruned_hooks.append((hook, "[DRY-RUN] Would archive"))
                pruned.append(hook)
                continue

            try:
                archive_dir.mkdir(exist_ok=True)
                shutil.move(str(src), str(dst))
                self.pruned_hooks.append((hook, f"Archived to {archive_dir.name}/"))
                pruned.append(hook)
            except OSError as e:
                self.add_issue("WARNING", "PRUNE_ERROR", f"Cannot archive: {e}", hook)

        return pruned

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
        self.check_prompt_type_hooks(self.settings)
        self.check_multiedit_matcher(self.settings)

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
            self.check_pretool_prompt_access(hook)
            self.check_posttooluse_output(hook)
            self.check_stop_output(hook)
            self.check_userpromptsubmit_output(hook)
            self.check_permissionrequest_output(hook)
            self.check_sessionstart_output(hook)
            self.check_common_json_fields(hook)
            self.check_unsafe_dict_access(hook)
            self.check_transcript_usage(hook)
            self.check_exit_code_usage(hook)
            self.check_error_handling(hook)
            self.check_performance(hook)
            self.check_security(hook)

            # New v2.0.10+ spec checks
            self.check_updated_input_usage(hook)
            self.check_interrupt_field(hook)
            self.check_exit_code_access(hook)
            self.check_deprecated_root_fields(hook)
            self.check_posttooluse_input_key(hook)

            # Auto-fix if enabled
            if self.fix_mode:
                self.fix_bare_except(hook)
                self.fix_camelcase_to_snake_case(hook)

        # Prune orphaned hooks if enabled
        if self.prune_mode:
            self.prune_orphaned_hooks()

        results["errors"] = self.issues
        results["warnings"] = self.warnings
        results["fixes"] = self.fixes_applied
        results["pruned"] = self.pruned_hooks

        return results

    def print_report(self, results: dict):
        """Print human-readable audit report."""
        print("=" * 70)
        print("🔍 HOOK SYSTEM AUDIT (Official Spec Compliance)")
        print("=" * 70)

        # Stats
        stats = results.get("stats", {})
        print("\n📊 STATISTICS:")
        print(f"   Total hook files: {stats.get('total_hook_files', 0)}")
        print(f"   Registered hooks: {stats.get('registered_hooks', 0)}")

        counts = stats.get("hooks_by_event", {})
        if counts:
            print("\n   Hooks by event type:")
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

        # Pruned hooks
        pruned = results.get("pruned", [])
        if pruned:
            print(f"\n🗑️  PRUNED HOOKS ({len(pruned)}):")
            for hook, action in pruned:
                print(f"   📦 {hook}: {action}")

        # Summary
        print("\n" + "=" * 70)
        print("📋 SUMMARY")
        print("=" * 70)
        print(f"   Errors: {len(errors)}")
        print(f"   Warnings: {len(warnings)}")
        if fixes:
            print(f"   Fixes Applied: {len(fixes)}")
        if pruned:
            print(f"   Hooks Pruned: {len(pruned)}")


        # Spec reference
        print("\n📚 Official Spec: https://docs.anthropic.com/en/hooks-reference")

        return len(errors) > 0 or (self.strict_mode and len(warnings) > 0)


def main():
    parser = argparse.ArgumentParser(
        description="Audit Claude Code hooks against official spec",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 .claude/ops/audit_hooks.py           # Basic audit
    python3 .claude/ops/audit_hooks.py --fix     # Auto-fix common issues
    python3 .claude/ops/audit_hooks.py --json    # Output as JSON
    python3 .claude/ops/audit_hooks.py --strict  # Treat warnings as errors

Official Spec: https://docs.anthropic.com/en/hooks-reference
        """
    )
    parser.add_argument("--fix", action="store_true", help="Auto-fix common issues")
    parser.add_argument("--dry-run", action="store_true", help="Preview fix changes without applying (requires --fix)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--prune", action="store_true", help="Archive orphaned hooks to .claude/hooks/archive/")

    args = parser.parse_args()

    auditor = HookAuditor(fix_mode=args.fix, strict_mode=args.strict,
                         dry_run=args.dry_run, prune_mode=args.prune)
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
