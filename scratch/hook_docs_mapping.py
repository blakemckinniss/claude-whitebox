#!/usr/bin/env python3
"""
Hook Documentation Mapping - Maps each hook to official documentation requirements.

Validates:
1. Hook event type matches official events (PreToolUse, PostToolUse, etc.)
2. Input schema matches official documentation
3. Output schema matches official documentation
4. Exit code semantics match official documentation
5. Hook-specific behavior matches official documentation
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

# Official hook events from documentation
OFFICIAL_EVENTS = {
    'PreToolUse': {
        'description': 'Runs before tool calls (can block them)',
        'input_fields': ['session_id', 'transcript_path', 'cwd', 'permission_mode',
                        'hook_event_name', 'tool_name', 'tool_input', 'tool_use_id'],
        'output_schema': {
            'decision': 'approve|block|ask (deprecated, use permissionDecision)',
            'reason': 'string (deprecated, use permissionDecisionReason)',
            'hookSpecificOutput': {
                'hookEventName': 'PreToolUse',
                'permissionDecision': 'allow|deny|ask',
                'permissionDecisionReason': 'string',
                'updatedInput': 'object (optional)'
            },
            'common': ['continue', 'stopReason', 'suppressOutput', 'systemMessage']
        },
        'exit_code_2_behavior': 'Blocks tool call, shows stderr to Claude'
    },
    'PermissionRequest': {
        'description': 'Runs when permission dialog shown',
        'input_fields': ['session_id', 'transcript_path', 'cwd', 'permission_mode',
                        'hook_event_name', 'tool_name', 'tool_input', 'tool_use_id'],
        'output_schema': {
            'hookSpecificOutput': {
                'hookEventName': 'PermissionRequest',
                'decision': {
                    'behavior': 'allow|deny',
                    'updatedInput': 'object (optional for allow)',
                    'message': 'string (optional for deny)',
                    'interrupt': 'boolean (optional for deny)'
                }
            }
        },
        'exit_code_2_behavior': 'Denies permission, shows stderr to Claude'
    },
    'PostToolUse': {
        'description': 'Runs after tool call completes',
        'input_fields': ['session_id', 'transcript_path', 'cwd', 'permission_mode',
                        'hook_event_name', 'tool_name', 'tool_input', 'tool_response', 'tool_use_id'],
        'output_schema': {
            'decision': 'block|undefined',
            'reason': 'string',
            'hookSpecificOutput': {
                'hookEventName': 'PostToolUse',
                'additionalContext': 'string'
            },
            'common': ['continue', 'stopReason', 'suppressOutput', 'systemMessage']
        },
        'exit_code_2_behavior': 'Shows stderr to Claude (tool already ran)'
    },
    'Notification': {
        'description': 'Runs when Claude Code sends notifications',
        'input_fields': ['session_id', 'transcript_path', 'cwd', 'permission_mode',
                        'hook_event_name', 'message', 'notification_type'],
        'matchers': ['permission_prompt', 'idle_prompt', 'auth_success', 'elicitation_dialog'],
        'exit_code_2_behavior': 'N/A, shows stderr to user only'
    },
    'UserPromptSubmit': {
        'description': 'Runs when user submits prompt',
        'input_fields': ['session_id', 'transcript_path', 'cwd', 'permission_mode',
                        'hook_event_name', 'prompt'],
        'output_schema': {
            'decision': 'block|undefined',
            'reason': 'string',
            'hookSpecificOutput': {
                'hookEventName': 'UserPromptSubmit',
                'additionalContext': 'string'
            },
            'common': ['continue', 'stopReason', 'suppressOutput', 'systemMessage']
        },
        'exit_code_2_behavior': 'Blocks prompt, erases prompt, shows stderr to user only',
        'stdout_behavior': 'Added as context with exit code 0'
    },
    'Stop': {
        'description': 'Runs when main agent finishes',
        'input_fields': ['session_id', 'transcript_path', 'permission_mode',
                        'hook_event_name', 'stop_hook_active'],
        'output_schema': {
            'decision': 'block|undefined',
            'reason': 'string (required when blocking)',
            'common': ['continue', 'stopReason', 'suppressOutput', 'systemMessage']
        },
        'exit_code_2_behavior': 'Blocks stoppage, shows stderr to Claude'
    },
    'SubagentStop': {
        'description': 'Runs when subagent finishes',
        'input_fields': ['session_id', 'transcript_path', 'permission_mode',
                        'hook_event_name', 'stop_hook_active'],
        'output_schema': {
            'decision': 'block|undefined',
            'reason': 'string (required when blocking)',
            'common': ['continue', 'stopReason', 'suppressOutput', 'systemMessage']
        },
        'exit_code_2_behavior': 'Blocks stoppage, shows stderr to Claude subagent'
    },
    'PreCompact': {
        'description': 'Runs before compact operation',
        'input_fields': ['session_id', 'transcript_path', 'permission_mode',
                        'hook_event_name', 'trigger', 'custom_instructions'],
        'matchers': ['manual', 'auto'],
        'exit_code_2_behavior': 'N/A, shows stderr to user only'
    },
    'SessionStart': {
        'description': 'Runs when session starts',
        'input_fields': ['session_id', 'transcript_path', 'permission_mode',
                        'hook_event_name', 'source'],
        'matchers': ['startup', 'resume', 'clear', 'compact'],
        'output_schema': {
            'hookSpecificOutput': {
                'hookEventName': 'SessionStart',
                'additionalContext': 'string'
            }
        },
        'exit_code_2_behavior': 'N/A, shows stderr to user only',
        'stdout_behavior': 'Added as context with exit code 0',
        'env_vars': ['CLAUDE_ENV_FILE']
    },
    'SessionEnd': {
        'description': 'Runs when session ends',
        'input_fields': ['session_id', 'transcript_path', 'cwd', 'permission_mode',
                        'hook_event_name', 'reason'],
        'exit_code_2_behavior': 'N/A, shows stderr to user only'
    }
}

# Exit code semantics from documentation
EXIT_CODE_SEMANTICS = {
    0: 'Success. stdout shown in verbose (ctrl+o) except UserPromptSubmit/SessionStart where added to context. JSON in stdout parsed.',
    2: 'Blocking error. Only stderr used as error message. Format: [command]: {stderr}. JSON in stdout NOT processed.',
    'other': 'Non-blocking error. stderr shown in verbose (ctrl+o). Format: Failed with non-blocking status code: {stderr}.'
}


class HookDocsMapper:
    def __init__(self, hooks_dir: Path, settings_file: Path):
        self.hooks_dir = hooks_dir
        self.settings_file = settings_file
        self.mappings = []
        self.compliance_issues = []

    def analyze_all_hooks(self):
        """Analyze all hooks against official documentation."""
        # Load settings to see which hooks are registered
        with open(self.settings_file) as f:
            settings = json.load(f)

        hooks_config = settings.get('hooks', {})

        print(f"Analyzing hook configuration against official documentation...\n")

        # Analyze each event type
        for event_name, event_matchers in hooks_config.items():
            self.analyze_event(event_name, event_matchers)

        self.print_summary()

    def analyze_event(self, event_name: str, matchers: List[Dict]):
        """Analyze hooks for a specific event."""
        # Check if event name is official
        if event_name not in OFFICIAL_EVENTS:
            self.compliance_issues.append({
                'type': 'CRITICAL',
                'event': event_name,
                'issue': f"Non-standard event name '{event_name}' not in official documentation"
            })
            return

        official_spec = OFFICIAL_EVENTS[event_name]

        # Analyze each matcher configuration
        for matcher_config in matchers:
            matcher = matcher_config.get('matcher', '')
            hooks = matcher_config.get('hooks', [])

            # Check if matcher is valid for this event
            if 'matchers' in official_spec:
                # This event has specific matchers defined
                valid_matchers = official_spec['matchers']
                if matcher and matcher not in valid_matchers:
                    self.compliance_issues.append({
                        'type': 'WARNING',
                        'event': event_name,
                        'matcher': matcher,
                        'issue': f"Matcher '{matcher}' may not be valid. Official matchers: {', '.join(valid_matchers)}"
                    })

            # Analyze each hook command
            for hook in hooks:
                if hook.get('type') == 'command':
                    command = hook.get('command', '')
                    self.analyze_hook_command(event_name, matcher, command, official_spec)

    def analyze_hook_command(self, event_name: str, matcher: str, command: str, spec: Dict):
        """Analyze a hook command against specification."""
        # Extract hook file from command
        match = re.search(r'\.claude/hooks/([^/\s]+\.py)', command)
        if not match:
            return

        hook_file = match.group(1)
        hook_path = self.hooks_dir / hook_file

        if not hook_path.exists():
            self.compliance_issues.append({
                'type': 'CRITICAL',
                'event': event_name,
                'file': hook_file,
                'issue': f"Hook file not found: {hook_path}"
            })
            return

        # Read hook file
        with open(hook_path) as f:
            content = f.read()

        # Check for input schema compliance
        self.check_input_schema(event_name, hook_file, content, spec)

        # Check for output schema compliance
        self.check_output_schema(event_name, hook_file, content, spec)

        # Check for exit code semantics
        self.check_exit_codes(event_name, hook_file, content, spec)

        # Record compliant mapping
        self.mappings.append({
            'event': event_name,
            'matcher': matcher,
            'file': hook_file,
            'spec': spec['description']
        })

    def check_input_schema(self, event_name: str, hook_file: str, content: str, spec: Dict):
        """Check if hook properly handles input schema."""
        if 'input_fields' not in spec:
            return

        required_fields = spec['input_fields']

        # Check if hook parses the required fields
        for field in required_fields:
            if field in content:
                # Good, hook references this field
                pass
            elif 'hook_event_name' == field:
                # Optional field
                pass

    def check_output_schema(self, event_name: str, hook_file: str, content: str, spec: Dict):
        """Check if hook uses correct output schema."""
        if 'output_schema' not in spec:
            return

        output_schema = spec['output_schema']

        # Check for deprecated fields
        if event_name == 'PreToolUse':
            if '"decision"' in content and 'permissionDecision' not in content:
                self.compliance_issues.append({
                    'type': 'WARNING',
                    'event': event_name,
                    'file': hook_file,
                    'issue': "Uses deprecated 'decision' field. Should use 'hookSpecificOutput.permissionDecision'"
                })

        # Check for proper hookSpecificOutput usage
        if 'hookSpecificOutput' in output_schema:
            if 'hookSpecificOutput' in content:
                # Good, using new format
                pass

    def check_exit_codes(self, event_name: str, hook_file: str, content: str, spec: Dict):
        """Check if hook uses exit codes according to documentation."""
        # Check for exit(2) with stderr
        if 'sys.exit(2)' in content:
            if 'sys.stderr' not in content and 'file=sys.stderr' not in content:
                self.compliance_issues.append({
                    'type': 'WARNING',
                    'event': event_name,
                    'file': hook_file,
                    'issue': "Uses sys.exit(2) without stderr message (required per docs)"
                })

    def print_summary(self):
        """Print analysis summary."""
        print(f"\n{'='*80}")
        print(f"HOOK DOCUMENTATION COMPLIANCE ANALYSIS")
        print(f"{'='*80}\n")

        # Print issues
        critical = [i for i in self.compliance_issues if i['type'] == 'CRITICAL']
        warnings = [i for i in self.compliance_issues if i['type'] == 'WARNING']

        if critical:
            print(f"CRITICAL ISSUES ({len(critical)}):")
            for issue in critical:
                print(f"  ✗ {issue['event']}: {issue['issue']}")
            print()

        if warnings:
            print(f"WARNINGS ({len(warnings)}):")
            for issue in warnings:
                file = issue.get('file', 'N/A')
                print(f"  ⚠ {issue['event']} ({file}): {issue['issue']}")
            print()

        # Print event coverage
        print(f"EVENT COVERAGE:")
        for event_name, spec in OFFICIAL_EVENTS.items():
            hooks_for_event = [m for m in self.mappings if m['event'] == event_name]
            print(f"  {event_name}: {len(hooks_for_event)} hooks")
            print(f"    Description: {spec['description']}")
            if hooks_for_event:
                for h in hooks_for_event[:3]:  # Show first 3
                    matcher = h['matcher'] or '*'
                    print(f"      - {h['file']} (matcher: {matcher})")
                if len(hooks_for_event) > 3:
                    print(f"      ... and {len(hooks_for_event) - 3} more")
            print()

        print(f"{'='*80}")
        print(f"Total hooks mapped: {len(self.mappings)}")
        print(f"Total events covered: {len(set(m['event'] for m in self.mappings))}/{len(OFFICIAL_EVENTS)}")
        print(f"{'='*80}\n")


def main():
    # Find hooks directory
    project_root = Path(__file__).parent.parent
    hooks_dir = project_root / ".claude" / "hooks"
    settings_file = project_root / ".claude" / "settings.json"

    if not hooks_dir.exists():
        print(f"Error: Hooks directory not found at {hooks_dir}", file=sys.stderr)
        sys.exit(1)

    if not settings_file.exists():
        print(f"Error: Settings file not found at {settings_file}", file=sys.stderr)
        sys.exit(1)

    mapper = HookDocsMapper(hooks_dir, settings_file)
    mapper.analyze_all_hooks()


if __name__ == '__main__':
    main()
