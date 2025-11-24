#!/usr/bin/env python3
"""
Hook Registry: Auto-discovery and validation of Claude Code hooks.

Scans .claude/hooks/ directory, validates each hook, and maintains registry.
Used by test suite and monitoring systems.
"""
import json
import subprocess
import ast
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class HookRegistry:
    """Manages hook discovery, validation, and registry persistence."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.hooks_dir = project_root / ".claude" / "hooks"
        self.registry_path = project_root / ".claude" / "memory" / "hook_registry.json"

    def scan_hooks(self) -> Dict[str, dict]:
        """
        Auto-discover all Python hooks in .claude/hooks/.

        Returns:
            Dict mapping filename to hook metadata
        """
        hooks = {}

        if not self.hooks_dir.exists():
            return hooks

        for hook_file in self.hooks_dir.glob("*.py"):
            # Skip __pycache__ and hidden files
            if hook_file.name.startswith("_"):
                continue

            metadata = self._extract_metadata(hook_file)
            hooks[hook_file.name] = metadata

        return hooks

    def _extract_metadata(self, hook_path: Path) -> dict:
        """Extract metadata from hook file (docstring, event type, etc.)"""
        metadata = {
            "path": str(hook_path.relative_to(self.project_root)),
            "filename": hook_path.name,
            "event_type": self._infer_event_type(hook_path),
            "last_scan": datetime.now().isoformat(),
            "health": self.validate_hook(hook_path)
        }

        # Extract docstring
        try:
            with open(hook_path, 'r') as f:
                content = f.read()
                tree = ast.parse(content)
                docstring = ast.get_docstring(tree)
                if docstring:
                    # First line only
                    metadata["description"] = docstring.split('\n')[0].strip()
        except Exception:
            pass

        return metadata

    def _infer_event_type(self, hook_path: Path) -> Optional[str]:
        """
        Infer event type from hook content or settings.json.

        Priority:
        1. Check settings.json hook configuration
        2. Parse hook file for event type hints
        3. Return None if unclear
        """
        # Try reading settings.json
        settings_path = self.project_root / ".claude" / "settings.json"
        if settings_path.exists():
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    hooks_config = settings.get("hooks", {})

                    # Search all event types for this hook
                    for event_type, hook_list in hooks_config.items():
                        if isinstance(hook_list, list):
                            for matcher_group in hook_list:
                                # Handle nested hook arrays (matcher groups)
                                if isinstance(matcher_group, dict) and 'hooks' in matcher_group:
                                    for hook_entry in matcher_group['hooks']:
                                        if isinstance(hook_entry, dict):
                                            command = hook_entry.get('command', '')
                                            if hook_path.name in command:
                                                return event_type
                                # Handle direct hook entries (legacy)
                                elif isinstance(matcher_group, dict):
                                    hook_file = matcher_group.get("file", "")
                                    if hook_path.name in hook_file:
                                        return event_type
                                # Handle string paths
                                elif isinstance(matcher_group, str) and hook_path.name in matcher_group:
                                    return event_type
            except Exception:
                pass

        # Fallback: check hook content for hints
        try:
            with open(hook_path, 'r') as f:
                content = f.read()

                # Look for event type in comments or docstrings
                if "SessionStart" in content:
                    return "SessionStart"
                elif "UserPromptSubmit" in content:
                    return "UserPromptSubmit"
                elif "PostToolUse" in content:
                    return "PostToolUse"
                elif "PreToolUse" in content:
                    return "PreToolUse"
                elif "SessionEnd" in content:
                    return "SessionEnd"
        except Exception:
            pass

        return None

    def validate_hook(self, hook_path: Path) -> dict:
        """
        Validate hook health: syntax, imports, structure.

        Returns:
            Dict with validation results
        """
        health = {
            "syntax_valid": False,
            "imports_valid": False,
            "has_main": False,
            "has_proper_return": False,
            "errors": []
        }

        # 1. Syntax check
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(hook_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            health["syntax_valid"] = result.returncode == 0
            if result.returncode != 0:
                health["errors"].append(f"Syntax error: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            health["errors"].append("Syntax check timeout")
        except Exception as e:
            health["errors"].append(f"Syntax check failed: {e}")

        if not health["syntax_valid"]:
            return health  # Skip further checks if syntax invalid

        # 2. Import check (try importing the module)
        sys.path.insert(0, str(self.hooks_dir))
        try:
            module_name = hook_path.stem
            # Provide empty stdin to prevent hooks from blocking/failing on json.load(sys.stdin)
            result = subprocess.run(
                [sys.executable, "-c", f"import sys; sys.path.insert(0, '{self.hooks_dir}'); import {module_name}"],
                input="",  # Provide empty stdin
                capture_output=True,
                text=True,
                timeout=5
            )

            health["imports_valid"] = result.returncode == 0
            if result.returncode != 0:
                # Check if error is just stdin-related (acceptable for hooks)
                stderr = result.stderr.strip()
                if "Expecting value" in stderr and "json" in stderr.lower():
                    # This is acceptable - hook expects JSON input which is normal
                    health["imports_valid"] = True
                    health["errors"].append("Import warning: Hook reads stdin (expected behavior)")
                else:
                    health["errors"].append(f"Import error: {stderr}")

        except subprocess.TimeoutExpired:
            health["errors"].append("Import check timeout")
        except Exception as e:
            health["errors"].append(f"Import check failed: {e}")
        finally:
            # Always clean up sys.path, even if exception occurred
            try:
                sys.path.remove(str(self.hooks_dir))
            except ValueError:
                pass  # Already removed

        # 3. Structure check (has main function)
        try:
            with open(hook_path, 'r') as f:
                content = f.read()
                tree = ast.parse(content)

                # Check for main() function
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == "main":
                        health["has_main"] = True
                        break

                # Check for proper return statement in main
                if health["has_main"]:
                    # Look for return with dict/hookSpecificOutput
                    if "hookSpecificOutput" in content or "return {" in content:
                        health["has_proper_return"] = True
        except Exception as e:
            health["errors"].append(f"Structure check failed: {e}")

        return health

    def categorize_by_event(self, hooks: Dict[str, dict]) -> Dict[str, List[str]]:
        """
        Group hooks by event type.

        Returns:
            Dict mapping event type to list of hook filenames
        """
        categorized = {}

        for filename, metadata in hooks.items():
            event_type = metadata.get("event_type")
            if event_type:
                if event_type not in categorized:
                    categorized[event_type] = []
                categorized[event_type].append(filename)

        return categorized

    def save_registry(self, hooks: Dict[str, dict]) -> bool:
        """
        Persist registry to disk.

        Returns:
            bool: True if save succeeded, False otherwise
        """
        try:
            registry = {
                "last_updated": datetime.now().isoformat(),
                "total_hooks": len(hooks),
                "hooks": hooks,
                "by_event_type": self.categorize_by_event(hooks)
            }

            # Ensure directory exists
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.registry_path, 'w') as f:
                json.dump(registry, f, indent=2)

            return True

        except (IOError, OSError, PermissionError) as e:
            # Log error but don't crash
            print(f"Error saving registry: {e}", file=sys.stderr)
            return False

    def load_registry(self) -> Optional[dict]:
        """Load registry from disk."""
        if not self.registry_path.exists():
            return None

        try:
            with open(self.registry_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def get_health_summary(self, hooks: Dict[str, dict]) -> dict:
        """
        Generate health summary across all hooks.

        Returns:
            Dict with counts of passing/warning/failing hooks
        """
        passing = 0
        warnings = 0
        failing = 0
        failed_hooks = []
        warned_hooks = []

        for filename, metadata in hooks.items():
            health = metadata.get("health", {})

            # Failing: syntax or import errors
            if not health.get("syntax_valid") or not health.get("imports_valid"):
                failing += 1
                errors = health.get("errors", ["Unknown error"])
                failed_hooks.append({"filename": filename, "errors": errors})
            # Warning: missing structure
            elif not health.get("has_main") or not health.get("has_proper_return"):
                warnings += 1
                issues = []
                if not health.get("has_main"):
                    issues.append("Missing main() function")
                if not health.get("has_proper_return"):
                    issues.append("Missing proper return statement")
                warned_hooks.append({"filename": filename, "issues": issues})
            else:
                passing += 1

        return {
            "total": len(hooks),
            "passing": passing,
            "warnings": warnings,
            "failing": failing,
            "failed_hooks": failed_hooks,
            "warned_hooks": warned_hooks
        }


def main():
    """CLI interface for hook registry."""
    import argparse

    # Find project root
    current = Path.cwd()
    while current != Path("/"):
        if (current / "scripts" / "lib" / "core.py").exists():
            project_root = current
            break
        current = current.parent
    else:
        print("❌ Could not find project root", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Hook Registry Management")
    parser.add_argument("--scan", action="store_true", help="Scan and update registry")
    parser.add_argument("--show", action="store_true", help="Show current registry")
    parser.add_argument("--validate", metavar="HOOK", help="Validate specific hook")
    parser.add_argument("--health", action="store_true", help="Show health summary")

    args = parser.parse_args()

    registry = HookRegistry(project_root)

    if args.scan:
        print("🔍 Scanning hooks...")
        hooks = registry.scan_hooks()
        registry.save_registry(hooks)
        print(f"✅ Scanned {len(hooks)} hooks")
        print(f"📝 Registry saved: {registry.registry_path}")

    elif args.show:
        data = registry.load_registry()
        if not data:
            print("❌ No registry found. Run --scan first.")
            sys.exit(1)

        print(json.dumps(data, indent=2))

    elif args.health:
        hooks = registry.scan_hooks()
        summary = registry.get_health_summary(hooks)

        print(f"\n🧪 Hook Health Summary ({summary['total']} hooks)")
        print(f"✅ {summary['passing']} passing")
        print(f"⚠️  {summary['warnings']} warnings")
        print(f"❌ {summary['failing']} failing\n")

        if summary["failed_hooks"]:
            print("FAILURES:")
            for hook in summary["failed_hooks"]:
                print(f"  ❌ {hook['filename']}")
                for error in hook["errors"]:
                    print(f"     {error}")

        if summary["warned_hooks"]:
            print("\nWARNINGS:")
            for hook in summary["warned_hooks"]:
                print(f"  ⚠️  {hook['filename']}")
                for issue in hook["issues"]:
                    print(f"     {issue}")

    elif args.validate:
        hook_path = registry.hooks_dir / args.validate
        if not hook_path.exists():
            print(f"❌ Hook not found: {args.validate}")
            sys.exit(1)

        print(f"🔍 Validating {args.validate}...")
        health = registry.validate_hook(hook_path)
        print(json.dumps(health, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
