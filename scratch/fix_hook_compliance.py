#!/usr/bin/env python3
"""
Hook Compliance Fixer - Automated fixes for common compliance issues.

Fixes:
1. Add path traversal validation for file_path handling
2. Add JSONDecodeError handling for stdin parsing
3. Add try/except blocks for graceful error handling
4. Document shell=True usage with security warnings
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Security snippet for path traversal validation
PATH_VALIDATION_SNIPPET = '''
def validate_file_path(file_path: str) -> bool:
    """Validate file path to prevent path traversal attacks."""
    if '..' in file_path:
        return False
    # Additional validation can be added here
    return True
'''

# JSONDecodeError handling wrapper
JSON_ERROR_HANDLING = '''try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
    sys.exit(1)'''


class HookFixer:
    def __init__(self, hooks_dir: Path):
        self.hooks_dir = hooks_dir
        self.fixes_applied = []

    def fix_all_hooks(self):
        """Apply fixes to all hooks."""
        hook_files = sorted(self.hooks_dir.glob("*.py"))

        # Skip backup files
        hook_files = [f for f in hook_files if '_backup' not in f.name]

        print(f"Fixing {len(hook_files)} hooks...\n")

        for hook_file in hook_files:
            self.fix_hook(hook_file)

        self.print_summary()

    def fix_hook(self, hook_path: Path):
        """Apply fixes to a single hook."""
        try:
            with open(hook_path, 'r') as f:
                content = f.read()

            original_content = content
            fixes_for_file = []

            # Fix 1: Add path traversal validation
            if 'file_path' in content and 'validate_file_path' not in content:
                content, fixed = self.add_path_validation(hook_path, content)
                if fixed:
                    fixes_for_file.append("Added path traversal validation")

            # Fix 2: Add JSONDecodeError handling
            if 'json.load(sys.stdin)' in content and 'JSONDecodeError' not in content:
                content, fixed = self.add_json_error_handling(hook_path, content)
                if fixed:
                    fixes_for_file.append("Added JSONDecodeError handling")

            # Fix 3: Document shell=True usage
            if 'shell=True' in content and '# SECURITY WARNING' not in content:
                content, fixed = self.document_shell_true(hook_path, content)
                if fixed:
                    fixes_for_file.append("Documented shell=True security risk")

            # Write back if changes were made
            if content != original_content:
                with open(hook_path, 'w') as f:
                    f.write(content)

                self.fixes_applied.append({
                    'file': hook_path.name,
                    'fixes': fixes_for_file
                })

        except Exception as e:
            print(f"Error fixing {hook_path.name}: {e}", file=sys.stderr)

    def add_path_validation(self, hook_path: Path, content: str) -> Tuple[str, bool]:
        """Add path traversal validation."""
        # Find where file_path is used
        file_path_pattern = r'file_path\s*=\s*[^=].*?["\']file_path["\']\s*,\s*["\']["\']'

        # Check if there's already validation
        if '..' in content and 'if' in content:
            return content, False  # Already has some validation

        # Add validation function if not present
        if 'def validate_file_path' not in content:
            # Insert before main execution (after imports)
            import_end = content.rfind('import ')
            if import_end == -1:
                import_end = 0
            else:
                import_end = content.find('\n', import_end) + 1

            # Find the next blank line after imports
            next_blank = content.find('\n\n', import_end)
            if next_blank == -1:
                next_blank = import_end

            content = (content[:next_blank] + '\n\n' +
                      PATH_VALIDATION_SNIPPET.strip() + '\n' +
                      content[next_blank:])

        # Add validation call after file_path extraction
        # Look for: file_path = input_data.get('tool_input', {}).get('file_path', '')
        pattern = r"(file_path\s*=\s*input_data\.get\([^)]+\)\.get\(['\"]file_path['\"][^)]*\))"

        def add_validation_check(match):
            original = match.group(1)
            return f"{original}\n\n    # Validate file path to prevent path traversal\n    if file_path and not validate_file_path(file_path):\n        print(f\"Security: Path traversal detected in {{file_path}}\", file=sys.stderr)\n        sys.exit(2)"

        new_content = re.sub(pattern, add_validation_check, content)

        return new_content, new_content != content

    def add_json_error_handling(self, hook_path: Path, content: str) -> Tuple[str, bool]:
        """Add JSONDecodeError handling to stdin parsing."""
        # Find json.load(sys.stdin) without error handling
        pattern = r'(\s*)(input_data\s*=\s*json\.load\(sys\.stdin\))'

        def wrap_with_try_except(match):
            indent = match.group(1)
            statement = match.group(2)

            return f'''{indent}try:
{indent}    {statement}
{indent}except json.JSONDecodeError as e:
{indent}    print(f"Error: Invalid JSON input: {{e}}", file=sys.stderr)
{indent}    sys.exit(1)'''

        # Only apply if not already in a try block
        if 'try:' not in content or content.find('json.load') < content.find('try:'):
            new_content = re.sub(pattern, wrap_with_try_except, content)
            return new_content, new_content != content

        return content, False

    def document_shell_true(self, hook_path: Path, content: str) -> Tuple[str, bool]:
        """Add security warning comment before shell=True usage."""
        # Find subprocess calls with shell=True
        pattern = r'(\s*)(subprocess\.[a-z]+\([^)]*shell=True)'

        def add_warning(match):
            indent = match.group(1)
            call = match.group(2)

            return f'''{indent}# SECURITY WARNING: shell=True is used here for command execution.
{indent}# This is intentional but requires careful input validation to prevent injection.
{indent}# Ensure all variables are properly validated before use.
{indent}{call}'''

        new_content = re.sub(pattern, add_warning, content)
        return new_content, new_content != content

    def print_summary(self):
        """Print summary of fixes applied."""
        print(f"\n{'='*80}")
        print(f"COMPLIANCE FIXES APPLIED")
        print(f"{'='*80}\n")

        if not self.fixes_applied:
            print("No fixes were needed.")
            return

        for fix in self.fixes_applied:
            print(f"✓ {fix['file']}:")
            for f in fix['fixes']:
                print(f"    - {f}")

        print(f"\n{'='*80}")
        print(f"Total files fixed: {len(self.fixes_applied)}")
        print(f"{'='*80}\n")


def main():
    # Find hooks directory
    project_root = Path(__file__).parent.parent
    hooks_dir = project_root / ".claude" / "hooks"

    if not hooks_dir.exists():
        print(f"Error: Hooks directory not found at {hooks_dir}", file=sys.stderr)
        sys.exit(1)

    fixer = HookFixer(hooks_dir)
    fixer.fix_all_hooks()


if __name__ == '__main__':
    main()
