#!/usr/bin/env python3
"""
Hook System Health Check
Validates all hooks are functional and properly registered
"""

import json
import sys
import subprocess
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = ROOT / ".claude/hooks"
SETTINGS_FILE = ROOT / ".claude/settings.json"

def load_settings():
    """Load settings.json"""
    with open(SETTINGS_FILE) as f:
        return json.load(f)

def get_all_hook_files():
    """Get all .py files in hooks directory"""
    return sorted(HOOKS_DIR.glob("*.py"))

def extract_registered_hooks(settings):
    """Extract all hook file paths from settings"""
    registered = set()
    for event_type, event_hooks in settings.get("hooks", {}).items():
        for hook_group in event_hooks:
            for hook_def in hook_group.get("hooks", []):
                if hook_def.get("type") == "command":
                    cmd = hook_def["command"]
                    # Extract filename from command
                    if ".claude/hooks/" in cmd:
                        filename = cmd.split(".claude/hooks/")[1].split()[0]
                        registered.add(filename)
    return registered

def test_hook_syntax(hook_file):
    """Test if hook has valid Python syntax"""
    result = subprocess.run(
        ["python3", "-m", "py_compile", str(hook_file)],
        capture_output=True,
        text=True
    )
    return result.returncode == 0, result.stderr

def test_hook_execution(hook_file):
    """Test if hook can execute without crashing (dry run)"""
    # Most hooks expect CLAUDE_TOOL_INPUT env var
    result = subprocess.run(
        ["python3", str(hook_file)],
        capture_output=True,
        text=True,
        env={"CLAUDE_TOOL_INPUT": "{}"}
    )
    # Exit code 0 = success, 1 = block (intentional), >1 = error
    return result.returncode in [0, 1], result.stderr

def categorize_hooks():
    """Categorize hooks by function"""
    categories = {
        "gates": [],  # Hard blockers
        "detectors": [],  # Pattern detection
        "telemetry": [],  # Data collection
        "auto": [],  # Automation
        "analyzers": [],  # Analysis/suggestions
        "other": []
    }

    for hook_file in get_all_hook_files():
        name = hook_file.name
        if "gate" in name or "block" in name or "enforcer" in name:
            categories["gates"].append(name)
        elif "detect" in name or "trigger" in name or "check" in name:
            categories["detectors"].append(name)
        elif "telemetry" in name or "tracker" in name or "monitor" in name:
            categories["telemetry"].append(name)
        elif "auto" in name:
            categories["auto"].append(name)
        elif "analyzer" in name or "suggester" in name or "mapper" in name:
            categories["analyzers"].append(name)
        else:
            categories["other"].append(name)

    return categories

def main():
    print("🔍 HOOK SYSTEM HEALTH CHECK\n")
    print("=" * 60)

    # 1. File counts
    all_hooks = get_all_hook_files()
    print(f"\n📊 INVENTORY:")
    print(f"   • Total hook files: {len(all_hooks)}")

    # 2. Registration check
    settings = load_settings()
    registered = extract_registered_hooks(settings)
    print(f"   • Registered in settings.json: {len(registered)}")

    unregistered = []
    for hook_file in all_hooks:
        if hook_file.name not in registered:
            # Skip backups
            if "backup" not in hook_file.name and "test" not in hook_file.name:
                unregistered.append(hook_file.name)

    if unregistered:
        print(f"   ⚠️  Unregistered hooks: {len(unregistered)}")
        for name in unregistered[:5]:
            print(f"      - {name}")
        if len(unregistered) > 5:
            print(f"      ... and {len(unregistered) - 5} more")

    # 3. Hook event distribution
    print(f"\n📍 HOOK EVENT DISTRIBUTION:")
    event_counts = {}
    for event_type, event_hooks in settings.get("hooks", {}).items():
        count = sum(len(hg.get("hooks", [])) for hg in event_hooks)
        event_counts[event_type] = count
        print(f"   • {event_type}: {count} hooks")

    # 4. Categorization
    print(f"\n🏷️  HOOK CATEGORIES:")
    categories = categorize_hooks()
    for cat_name, hooks in categories.items():
        if hooks:
            print(f"   • {cat_name.upper()}: {len(hooks)}")

    # 5. Syntax validation
    print(f"\n✅ SYNTAX VALIDATION:")
    syntax_errors = []
    for hook_file in all_hooks:
        valid, error = test_hook_syntax(hook_file)
        if not valid:
            syntax_errors.append((hook_file.name, error))

    if syntax_errors:
        print(f"   ❌ Syntax errors: {len(syntax_errors)}")
        for name, error in syntax_errors[:3]:
            print(f"      - {name}")
            print(f"        {error[:100]}...")
    else:
        print(f"   ✅ All hooks have valid syntax")

    # 6. Execution test (sample)
    print(f"\n🚀 EXECUTION TEST (Sample):")
    test_hooks = [
        "confidence_init.py",
        "synapse_fire.py",
        "sanity_check.py",
        "performance_gate.py"
    ]

    execution_errors = []
    for hook_name in test_hooks:
        hook_file = HOOKS_DIR / hook_name
        if hook_file.exists():
            can_run, error = test_hook_execution(hook_file)
            status = "✅" if can_run else "❌"
            print(f"   {status} {hook_name}")
            if not can_run:
                execution_errors.append((hook_name, error))
        else:
            print(f"   ⚠️  {hook_name} (not found)")

    # 7. Critical hooks check
    print(f"\n🛡️  CRITICAL HOOKS:")
    critical = [
        "session_init.py",
        "confidence_init.py",
        "command_prerequisite_gate.py",
        "tier_gate.py",
        "performance_gate.py",
        "native_batching_enforcer.py",
        "scratch_enforcer_gate.py"
    ]

    missing_critical = []
    for hook_name in critical:
        hook_file = HOOKS_DIR / hook_name
        if not hook_file.exists():
            missing_critical.append(hook_name)
            print(f"   ❌ {hook_name} (MISSING)")
        else:
            valid, _ = test_hook_syntax(hook_file)
            status = "✅" if valid else "❌"
            print(f"   {status} {hook_name}")

    # 8. Summary
    print("\n" + "=" * 60)
    print("📋 SUMMARY:")

    issues = []
    if syntax_errors:
        issues.append(f"{len(syntax_errors)} syntax errors")
    if execution_errors:
        issues.append(f"{len(execution_errors)} execution errors")
    if missing_critical:
        issues.append(f"{len(missing_critical)} missing critical hooks")
    if unregistered:
        issues.append(f"{len(unregistered)} unregistered hooks")

    if issues:
        print(f"   ⚠️  Issues found: {', '.join(issues)}")
        return 1
    else:
        print(f"   ✅ Hook system healthy!")
        print(f"   • {len(all_hooks)} hooks installed")
        print(f"   • {len(registered)} registered")
        print(f"   • {sum(event_counts.values())} total registrations")
        return 0

if __name__ == "__main__":
    sys.exit(main())
