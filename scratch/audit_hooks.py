#!/usr/bin/env python3
"""
Hook System Audit Script
Comprehensive analysis of the .claude/hooks system for issues
"""

import os
import sys
import json
import ast
import re
from pathlib import Path
from collections import defaultdict, Counter

PROJECT_ROOT = Path(__file__).parent.parent
HOOKS_DIR = PROJECT_ROOT / ".claude" / "hooks"
SETTINGS_FILE = PROJECT_ROOT / ".claude" / "settings.json"

class HookAuditor:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.stats = {}
        self.registered_hooks = set()
        self.all_hooks = set()

    def add_issue(self, severity, category, message, file=None):
        entry = {"severity": severity, "category": category, "message": message}
        if file:
            entry["file"] = str(file)
        if severity == "ERROR":
            self.issues.append(entry)
        else:
            self.warnings.append(entry)

    def load_settings(self):
        """Load and parse settings.json"""
        with open(SETTINGS_FILE) as f:
            return json.load(f)

    def extract_registered_hooks(self, settings):
        """Extract all hook scripts registered in settings.json"""
        hooks = settings.get("hooks", {})
        registered = set()

        for event_type, event_hooks in hooks.items():
            for hook_config in event_hooks:
                for hook in hook_config.get("hooks", []):
                    cmd = hook.get("command", "")
                    # Extract python script path
                    match = re.search(r'\.claude/hooks/(\w+\.py)', cmd)
                    if match:
                        registered.add(match.group(1))
        return registered

    def get_all_hook_files(self):
        """Get all .py files in hooks directory"""
        return {f.name for f in HOOKS_DIR.glob("*.py") if not f.name.startswith("__")}

    def check_syntax_errors(self):
        """Check all hooks for Python syntax errors"""
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
                self.add_issue("ERROR", "SYNTAX", f"Syntax error at line {e.lineno}: {e.msg}", hook_file.name)
        return errors

    def check_orphaned_hooks(self):
        """Find hooks that exist but aren't registered"""
        all_hooks = self.get_all_hook_files()
        registered = self.registered_hooks

        # Exclude backup files and test files
        ignored_patterns = ['_backup', '_v1_backup', 'test_hooks']

        orphaned = []
        for hook in all_hooks:
            if hook not in registered:
                # Check if it's a backup or test file
                is_ignored = any(p in hook for p in ignored_patterns)
                if not is_ignored:
                    orphaned.append(hook)
                    self.add_issue("WARNING", "ORPHAN", f"Hook not registered in settings.json", hook)
        return orphaned

    def check_missing_hooks(self):
        """Find hooks referenced in settings but don't exist"""
        all_hooks = self.get_all_hook_files()
        missing = []
        for hook in self.registered_hooks:
            if hook not in all_hooks:
                missing.append(hook)
                self.add_issue("ERROR", "MISSING", f"Hook referenced but file doesn't exist", hook)
        return missing

    def check_duplicate_registrations(self, settings):
        """Find hooks registered multiple times for same event"""
        hooks = settings.get("hooks", {})
        duplicates = defaultdict(list)

        for event_type, event_hooks in hooks.items():
            hook_counts = Counter()
            for hook_config in event_hooks:
                matcher = hook_config.get("matcher", "*")
                for hook in hook_config.get("hooks", []):
                    cmd = hook.get("command", "")
                    match = re.search(r'\.claude/hooks/(\w+\.py)', cmd)
                    if match:
                        key = f"{event_type}:{matcher}:{match.group(1)}"
                        hook_counts[match.group(1)] += 1

            for hook_name, count in hook_counts.items():
                if count > 1:
                    duplicates[event_type].append((hook_name, count))
                    self.add_issue("WARNING", "DUPLICATE",
                        f"Registered {count} times in {event_type}", hook_name)

        return duplicates

    def check_output_format(self, hook_file):
        """Check if hook has proper output format for its type"""
        with open(HOOKS_DIR / hook_file) as f:
            content = f.read()

        issues = []

        # Check for PreToolUse hooks
        if "PreToolUse" in content or "permissionDecision" in content:
            # Should have hookSpecificOutput structure
            if "hookSpecificOutput" not in content:
                if "allow" in content.lower() or "deny" in content.lower():
                    issues.append("Missing hookSpecificOutput wrapper for PreToolUse")

            # Check for old format mistakes
            if '"allow": False' in content or '"allow": True' in content:
                issues.append("Uses old {allow: bool} format instead of permissionDecision")

            if 'tool_name' in content and 'toolName' not in content:
                issues.append("Uses snake_case (tool_name) instead of camelCase (toolName)")

        # Check for proper JSON output
        if "json.dumps" in content:
            # Good - using proper JSON
            pass
        elif 'print(' in content:
            # Check if printing raw strings that should be JSON
            if re.search(r'print\([\'"][^{]', content):
                # Might be printing non-JSON for hooks that need JSON
                pass

        for issue in issues:
            self.add_issue("WARNING", "FORMAT", issue, hook_file)

        return issues

    def check_error_handling(self, hook_file):
        """Check if hook has proper error handling"""
        with open(HOOKS_DIR / hook_file) as f:
            content = f.read()

        issues = []

        # Check for bare except
        if re.search(r'except\s*:', content):
            issues.append("Uses bare 'except:' which can hide errors")

        # Check for sys.exit without proper return
        if 'sys.exit(1)' in content and 'except' not in content:
            issues.append("Uses sys.exit(1) without exception handling context")

        # Check for missing main guard
        if 'if __name__' not in content and 'def main' in content:
            issues.append("Has main() function but no __name__ guard")

        for issue in issues:
            self.add_issue("WARNING", "ERROR_HANDLING", issue, hook_file)

        return issues

    def check_performance_issues(self, hook_file):
        """Check for potential performance issues"""
        with open(HOOKS_DIR / hook_file) as f:
            content = f.read()

        issues = []

        # Check for subprocess without timeout - only blocking calls need timeout
        # Popen is intentionally async/background, so timeout doesn't apply
        if re.search(r'subprocess\.(run|check_output|call)\(', content):
            if 'timeout=' not in content:
                issues.append("Uses subprocess without timeout parameter")

        # Check for heavy imports
        heavy_imports = ['pandas', 'numpy', 'tensorflow', 'torch']
        for imp in heavy_imports:
            if f'import {imp}' in content or f'from {imp}' in content:
                issues.append(f"Imports heavy library: {imp}")

        # Check for actual requests HTTP calls (not just string references in docs)
        # Must be at start of line or after = (assignment), not in quotes
        if re.search(r'^[^"\'#]*requests\.(get|post|put|delete|patch|head)\(', content, re.MULTILINE):
            if 'timeout=' not in content:
                issues.append("Uses requests without timeout")

        for issue in issues:
            self.add_issue("WARNING", "PERFORMANCE", issue, hook_file)

        return issues

    def count_hooks_by_event(self, settings):
        """Count hooks per event type"""
        hooks = settings.get("hooks", {})
        counts = {}
        for event_type, event_hooks in hooks.items():
            total = 0
            for hook_config in event_hooks:
                total += len(hook_config.get("hooks", []))
            counts[event_type] = total
        return counts

    def analyze_hook_dependencies(self):
        """Analyze dependencies between hooks and lib scripts"""
        deps = {}
        for hook_file in HOOKS_DIR.glob("*.py"):
            if hook_file.name.startswith("__"):
                continue
            with open(hook_file) as f:
                content = f.read()

            # Find imports from scripts/lib
            lib_imports = re.findall(r'from scripts\.lib\.(\w+) import|import scripts\.lib\.(\w+)', content)
            lib_imports = [x[0] or x[1] for x in lib_imports]

            # Find imports from other hooks
            hook_imports = re.findall(r'from \.(\w+) import|from \.claude\.hooks\.(\w+)', content)

            if lib_imports:
                deps[hook_file.name] = {"lib": lib_imports}

        return deps

    def run_audit(self):
        """Run complete audit"""
        print("=" * 60)
        print("🔍 HOOK SYSTEM AUDIT")
        print("=" * 60)

        # Load settings
        settings = self.load_settings()
        self.registered_hooks = self.extract_registered_hooks(settings)
        self.all_hooks = self.get_all_hook_files()

        # Stats
        print(f"\n📊 STATISTICS:")
        print(f"   Total hook files: {len(self.all_hooks)}")
        print(f"   Registered hooks: {len(self.registered_hooks)}")

        counts = self.count_hooks_by_event(settings)
        print(f"\n   Hooks by event type:")
        total_registered = 0
        for event, count in sorted(counts.items()):
            print(f"      {event}: {count}")
            total_registered += count
        print(f"      TOTAL REGISTRATIONS: {total_registered}")

        # Syntax check
        print(f"\n🔧 SYNTAX CHECK:")
        syntax_errors = self.check_syntax_errors()
        if syntax_errors:
            for err in syntax_errors:
                print(f"   ❌ {err['file']}:{err['line']} - {err['error']}")
        else:
            print("   ✅ All hooks pass syntax check")

        # Orphaned hooks
        print(f"\n👻 ORPHANED HOOKS (not registered):")
        orphaned = self.check_orphaned_hooks()
        if orphaned:
            for hook in sorted(orphaned):
                print(f"   ⚠️  {hook}")
        else:
            print("   ✅ No orphaned hooks")

        # Missing hooks
        print(f"\n❓ MISSING HOOKS (registered but don't exist):")
        missing = self.check_missing_hooks()
        if missing:
            for hook in sorted(missing):
                print(f"   ❌ {hook}")
        else:
            print("   ✅ All registered hooks exist")

        # Duplicate registrations
        print(f"\n🔄 DUPLICATE REGISTRATIONS:")
        duplicates = self.check_duplicate_registrations(settings)
        if duplicates:
            for event, dups in duplicates.items():
                for hook, count in dups:
                    print(f"   ⚠️  {hook} registered {count}x in {event}")
        else:
            print("   ✅ No duplicate registrations")

        # Output format checks
        print(f"\n📤 OUTPUT FORMAT ISSUES:")
        format_issues = []
        for hook in self.all_hooks:
            issues = self.check_output_format(hook)
            if issues:
                format_issues.extend([(hook, i) for i in issues])
        if format_issues:
            for hook, issue in format_issues:
                print(f"   ⚠️  {hook}: {issue}")
        else:
            print("   ✅ No format issues detected")

        # Error handling
        print(f"\n🛡️ ERROR HANDLING ISSUES:")
        error_issues = []
        for hook in self.all_hooks:
            issues = self.check_error_handling(hook)
            if issues:
                error_issues.extend([(hook, i) for i in issues])
        if error_issues:
            for hook, issue in error_issues[:10]:  # Limit output
                print(f"   ⚠️  {hook}: {issue}")
            if len(error_issues) > 10:
                print(f"   ... and {len(error_issues) - 10} more")
        else:
            print("   ✅ No error handling issues")

        # Performance
        print(f"\n⚡ PERFORMANCE ISSUES:")
        perf_issues = []
        for hook in self.all_hooks:
            issues = self.check_performance_issues(hook)
            if issues:
                perf_issues.extend([(hook, i) for i in issues])
        if perf_issues:
            for hook, issue in perf_issues[:10]:
                print(f"   ⚠️  {hook}: {issue}")
            if len(perf_issues) > 10:
                print(f"   ... and {len(perf_issues) - 10} more")
        else:
            print("   ✅ No performance issues detected")

        # Summary
        print(f"\n" + "=" * 60)
        print(f"📋 SUMMARY")
        print(f"=" * 60)
        print(f"   ERRORS: {len(self.issues)}")
        print(f"   WARNINGS: {len(self.warnings)}")

        if self.issues:
            print(f"\n   🚨 CRITICAL ISSUES:")
            for issue in self.issues:
                f = issue.get('file', 'N/A')
                print(f"      [{issue['category']}] {f}: {issue['message']}")

        # Hook explosion warning
        if len(self.all_hooks) > 30:
            print(f"\n   ⚠️  HOOK EXPLOSION WARNING: {len(self.all_hooks)} hooks detected!")
            print(f"      Consider consolidating related hooks")

        # Return exit code
        return 1 if self.issues else 0


if __name__ == "__main__":
    auditor = HookAuditor()
    exit_code = auditor.run_audit()
    sys.exit(exit_code)
