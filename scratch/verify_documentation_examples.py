#!/usr/bin/env python3
"""
Verify hooks match official documentation examples.

Cross-references actual hook implementations against code snippets
from the official Claude Code hooks documentation.
"""

import re
from pathlib import Path
from typing import Dict, List

# Official documentation examples (verbatim from docs)
OFFICIAL_EXAMPLES = {
    'exit_code_simple': {
        'name': 'Simple Exit Code Usage',
        'pattern': r'sys\.exit\((0|1|2)\)',
        'description': 'Exit code 0 (success), 2 (blocking), other (non-blocking)',
        'compliant_hooks': []
    },

    'stdin_parsing': {
        'name': 'Stdin JSON Parsing',
        'pattern': r'json\.load\(sys\.stdin\)',
        'description': 'Hooks receive JSON via stdin',
        'compliant_hooks': []
    },

    'json_error_handling': {
        'name': 'JSONDecodeError Handling',
        'pattern': r'except json\.JSONDecodeError',
        'description': 'Validate and sanitize inputs - never trust blindly',
        'compliant_hooks': []
    },

    'stderr_output': {
        'name': 'Stderr for Errors',
        'pattern': r'(sys\.stderr|file=sys\.stderr)',
        'description': 'Exit code 2 requires stderr message',
        'compliant_hooks': []
    },

    'path_validation': {
        'name': 'Path Traversal Prevention',
        'pattern': r"'\.\.'|\"\.\.\"",
        'description': 'Block path traversal - check for .. in file paths',
        'compliant_hooks': []
    },

    'environment_vars': {
        'name': 'CLAUDE_PROJECT_DIR Usage',
        'pattern': r'CLAUDE_PROJECT_DIR',
        'description': 'Use $CLAUDE_PROJECT_DIR for project-relative paths',
        'compliant_hooks': []
    },

    'hook_specific_output_pretooluse': {
        'name': 'PreToolUse Output Schema',
        'pattern': r'permissionDecision|hookSpecificOutput',
        'description': 'Use hookSpecificOutput.permissionDecision (not deprecated decision)',
        'compliant_hooks': []
    },

    'hook_specific_output_posttooluse': {
        'name': 'PostToolUse Output Schema',
        'pattern': r'additionalContext|hookSpecificOutput',
        'description': 'Use hookSpecificOutput.additionalContext for feedback',
        'compliant_hooks': []
    },

    'continue_field': {
        'name': 'Continue Field Usage',
        'pattern': r'"continue":|\'continue\':',
        'description': 'Common field: continue (whether Claude should continue)',
        'compliant_hooks': []
    },

    'decision_field': {
        'name': 'Decision Field Usage',
        'pattern': r'"decision":|\'decision\':',
        'description': 'Decision field (block|undefined for most events)',
        'compliant_hooks': []
    },

    'reason_field': {
        'name': 'Reason Field Usage',
        'pattern': r'"reason":|\'reason\':',
        'description': 'Reason field (explanation for decision)',
        'compliant_hooks': []
    },

    'try_except': {
        'name': 'Exception Handling',
        'pattern': r'try:|except\s+',
        'description': 'Graceful error handling',
        'compliant_hooks': []
    },
}


def analyze_hooks_against_docs():
    """Analyze all hooks against official documentation patterns."""
    project_root = Path(__file__).parent.parent
    hooks_dir = project_root / ".claude" / "hooks"

    if not hooks_dir.exists():
        print(f"Error: Hooks directory not found")
        return

    hook_files = sorted(hooks_dir.glob("*.py"))

    # Skip backup files
    hook_files = [f for f in hook_files if '_backup' not in f.name]

    print("Verifying hooks against official documentation examples...\n")

    # Check each hook against patterns
    for hook_file in hook_files:
        with open(hook_file) as f:
            content = f.read()

        for example_key, example in OFFICIAL_EXAMPLES.items():
            pattern = example['pattern']
            if re.search(pattern, content):
                example['compliant_hooks'].append(hook_file.name)

    # Print results
    print(f"{'='*80}")
    print("DOCUMENTATION PATTERN COMPLIANCE")
    print(f"{'='*80}\n")

    for example_key, example in OFFICIAL_EXAMPLES.items():
        count = len(example['compliant_hooks'])
        total = len(hook_files)
        percentage = (count / total) * 100 if total > 0 else 0

        print(f"✓ {example['name']}")
        print(f"  Description: {example['description']}")
        print(f"  Coverage: {count}/{total} hooks ({percentage:.0f}%)")

        if count > 0:
            # Show first 3 examples
            for hook in example['compliant_hooks'][:3]:
                print(f"    - {hook}")
            if count > 3:
                print(f"    ... and {count - 3} more")
        else:
            print(f"    ⚠ No hooks use this pattern")

        print()

    # Summary
    print(f"{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    total_patterns = len(OFFICIAL_EXAMPLES)
    patterns_with_hooks = sum(1 for e in OFFICIAL_EXAMPLES.values() if e['compliant_hooks'])

    print(f"Total Documentation Patterns: {total_patterns}")
    print(f"Patterns Used by Hooks: {patterns_with_hooks}/{total_patterns}")
    print(f"Pattern Coverage: {(patterns_with_hooks/total_patterns)*100:.0f}%")
    print()

    # Specific recommendations
    print("RECOMMENDATIONS:")
    print()

    for example_key, example in OFFICIAL_EXAMPLES.items():
        if not example['compliant_hooks']:
            print(f"⚠ No hooks implement: {example['name']}")
            print(f"   {example['description']}")
            print()

    # Check for anti-patterns
    print(f"\n{'='*80}")
    print("ANTI-PATTERN DETECTION")
    print(f"{'='*80}\n")

    anti_patterns = {
        'shell_true': {
            'pattern': r'shell=True',
            'severity': 'HIGH',
            'message': 'Uses shell=True (potential injection)',
            'hooks': []
        },
        'no_path_validation': {
            'pattern': r'file_path.*=.*get\(',
            'anti_pattern': r'\.\.',
            'severity': 'HIGH',
            'message': 'Handles file_path without .. validation',
            'hooks': []
        },
        'no_json_error_handling': {
            'pattern': r'json\.load\(sys\.stdin\)',
            'anti_pattern': r'JSONDecodeError',
            'severity': 'MEDIUM',
            'message': 'Parses JSON without error handling',
            'hooks': []
        },
    }

    for hook_file in hook_files:
        with open(hook_file) as f:
            content = f.read()

        # Check shell=True
        if 'shell=True' in content:
            anti_patterns['shell_true']['hooks'].append(hook_file.name)

        # Check file_path without validation
        if re.search(r'file_path.*=.*get\(', content) and '..' not in content:
            anti_patterns['no_path_validation']['hooks'].append(hook_file.name)

        # Check JSON parsing without error handling
        if 'json.load(sys.stdin)' in content and 'JSONDecodeError' not in content:
            anti_patterns['no_json_error_handling']['hooks'].append(hook_file.name)

    for ap_key, ap in anti_patterns.items():
        if ap['hooks']:
            print(f"⚠ {ap['severity']}: {ap['message']}")
            print(f"  Affected hooks: {len(ap['hooks'])}")
            for hook in ap['hooks'][:5]:
                print(f"    - {hook}")
            if len(ap['hooks']) > 5:
                print(f"    ... and {len(ap['hooks']) - 5} more")
            print()


if __name__ == '__main__':
    analyze_hooks_against_docs()
