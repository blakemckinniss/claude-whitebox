#!/usr/bin/env python3
"""
Script to wire meta-learning into all enforcement hooks.

Adds override tracking to hooks that use MANUAL/SUDO bypass keywords.
"""

import sys
from pathlib import Path

PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

HOOKS_DIR = PROJECT_DIR / ".claude" / "hooks"

# Hooks that need meta-learning integration
ENFORCEMENT_HOOKS = [
    "scratch_enforcer.py",
    "scratch_enforcer_gate.py",
    "native_batching_enforcer.py",
    "command_prerequisite_gate.py",
    "tier_gate.py",
    "confidence_gate.py",
]

META_LEARNING_IMPORT = """
# Meta-learning integration
sys.path.insert(0, str(PROJECT_DIR / "scripts" / "lib"))
from meta_learning import record_manual_bypass, record_sudo_bypass, check_exception_rule
"""

def check_if_needs_integration(hook_path):
    """Check if hook already has meta-learning"""
    with open(hook_path) as f:
        content = f.read()
    return "meta_learning" not in content

def get_integration_points(hook_path):
    """Find where to add meta-learning calls"""
    with open(hook_path) as f:
        lines = f.readlines()

    # Find bypass detection points
    bypass_checks = []
    for i, line in enumerate(lines):
        if '"MANUAL"' in line or "'MANUAL'" in line:
            bypass_checks.append(("MANUAL", i))
        if '"SUDO MANUAL"' in line or "'SUDO MANUAL'" in line:
            bypass_checks.append(("SUDO", i))

    return bypass_checks

def main():
    """Wire meta-learning into enforcement hooks"""

    print("🔌 Wiring meta-learning into enforcement hooks...\n")

    for hook_name in ENFORCEMENT_HOOKS:
        hook_path = HOOKS_DIR / hook_name

        if not hook_path.exists():
            print(f"⚠️  {hook_name} not found, skipping")
            continue

        if not check_if_needs_integration(hook_path):
            print(f"✅ {hook_name} already has meta-learning")
            continue

        print(f"📝 {hook_name} needs integration")

        # For this script, just report - actual integration requires
        # manual review of each hook's structure
        bypass_checks = get_integration_points(hook_path)

        if bypass_checks:
            print(f"   Found {len(bypass_checks)} bypass check(s)")
            for bypass_type, line_num in bypass_checks:
                print(f"   - Line {line_num}: {bypass_type} keyword")
        else:
            print(f"   No bypass keywords found")

        print()

    print("\n💡 RECOMMENDATION:")
    print("Manual integration required for each hook.")
    print("Add after bypass detection:")
    print("  if 'MANUAL' in prompt:")
    print("      record_manual_bypass(hook_name, context, turn)")
    print("  elif 'SUDO MANUAL' in prompt:")
    print("      record_sudo_bypass(hook_name, context, turn)")

if __name__ == "__main__":
    main()
