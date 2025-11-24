#!/usr/bin/env python3
"""
Integrate Background Execution Hooks

Adds three background enforcement hooks:
1. detect_background_opportunity.py (PreToolUse:Bash) - Suggests background for slow commands
2. detect_parallel_bash.py (PreToolUse:Bash) - Detects multiple Bash calls
3. background_telemetry.py (PostToolUse:Bash) - Tracks usage
"""

import json
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
SETTINGS_FILE = PROJECT_ROOT / ".claude" / "settings.json"
HOOKS_DIR = PROJECT_ROOT / ".claude" / "hooks"

# Source files
SCRATCH_FILES = {
    "detect_background_opportunity.py": HOOKS_DIR / "detect_background_opportunity.py",
    "detect_parallel_bash.py": HOOKS_DIR / "detect_parallel_bash.py",
    "background_telemetry.py": HOOKS_DIR / "background_telemetry.py",
}


def copy_hooks():
    """Copy hooks from scratch/ to .claude/hooks/"""
    scratch_dir = PROJECT_ROOT / "scratch"

    for filename, dest_path in SCRATCH_FILES.items():
        src_path = scratch_dir / filename

        if not src_path.exists():
            print(f"❌ Source not found: {src_path}")
            return False

        # Copy file
        dest_path.write_text(src_path.read_text())
        dest_path.chmod(0o755)
        print(f"✅ Copied: {filename} → {dest_path}")

    return True


def integrate_hooks():
    """Add hooks to settings.json"""
    if not SETTINGS_FILE.exists():
        print(f"❌ Settings file not found: {SETTINGS_FILE}")
        return False

    # Load settings
    with open(SETTINGS_FILE) as f:
        settings = json.load(f)

    # Find PreToolUse:Bash section
    pretool_section = settings.setdefault("hooks", {}).setdefault("PreToolUse", [])

    # Find or create Bash matcher section
    bash_section = None
    for entry in pretool_section:
        if "Bash" in entry.get("matcher", ""):
            bash_section = entry
            break

    if not bash_section:
        # Create new Bash section
        bash_section = {
            "matcher": "Bash",
            "hooks": []
        }
        pretool_section.append(bash_section)

    bash_hooks = bash_section.setdefault("hooks", [])

    # Add background opportunity detector
    opportunity_exists = any(
        "detect_background_opportunity.py" in hook.get("command", "")
        for hook in bash_hooks
    )

    if not opportunity_exists:
        bash_hooks.append({
            "type": "command",
            "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/detect_background_opportunity.py"
        })
        print("✅ Added PreToolUse hook: detect_background_opportunity.py")
    else:
        print("⏭️  Opportunity detector hook already exists")

    # Add parallel bash detector
    parallel_exists = any(
        "detect_parallel_bash.py" in hook.get("command", "")
        for hook in bash_hooks
    )

    if not parallel_exists:
        bash_hooks.append({
            "type": "command",
            "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/detect_parallel_bash.py"
        })
        print("✅ Added PreToolUse hook: detect_parallel_bash.py")
    else:
        print("⏭️  Parallel bash detector hook already exists")

    # Add PostToolUse:Bash hook for telemetry
    posttool_section = settings["hooks"].setdefault("PostToolUse", [])

    if not posttool_section:
        posttool_section.append({"hooks": []})

    posttool_hooks = posttool_section[0].setdefault("hooks", [])

    telemetry_exists = any(
        "background_telemetry.py" in hook.get("command", "")
        for hook in posttool_hooks
    )

    if not telemetry_exists:
        posttool_hooks.append({
            "type": "command",
            "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/background_telemetry.py"
        })
        print("✅ Added PostToolUse hook: background_telemetry.py")
    else:
        print("⏭️  Telemetry hook already exists")

    # Save settings
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

    print(f"\n✅ Settings updated: {SETTINGS_FILE}")
    return True


def main():
    """Main integration logic"""
    print("🚀 Integrating Background Execution Hooks\n")

    # Step 1: Copy hooks
    print("Step 1: Copying hooks to .claude/hooks/")
    if not copy_hooks():
        print("\n❌ Failed to copy hooks")
        return 1

    print()

    # Step 2: Integrate into settings
    print("Step 2: Updating .claude/settings.json")
    if not integrate_hooks():
        print("\n❌ Failed to update settings")
        return 1

    print()
    print("=" * 60)
    print("✅ INTEGRATION COMPLETE")
    print("=" * 60)
    print()
    print("Hooks installed:")
    print("  1. detect_background_opportunity.py (PreToolUse:Bash)")
    print("     → Suggests background for slow commands")
    print()
    print("  2. detect_parallel_bash.py (PreToolUse:Bash)")
    print("     → Detects multiple Bash calls, suggests parallelism")
    print()
    print("  3. background_telemetry.py (PostToolUse:Bash)")
    print("     → Tracks background usage ratio, reports warnings")
    print()
    print("Next steps:")
    print("  1. Restart session to activate hooks")
    print("  2. Try slow command (pytest) to see suggestion")
    print("  3. Check telemetry: .claude/memory/background_telemetry.jsonl")
    print("  4. Update CLAUDE.md with background execution rules")
    print()

    return 0


if __name__ == "__main__":
    exit(main())
