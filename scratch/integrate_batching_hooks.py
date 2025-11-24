#!/usr/bin/env python3
"""
Integrate Batching Hooks into Settings

Adds three batching enforcement hooks:
1. native_batching_enforcer.py (PreToolUse) - Blocks sequential tool calls
2. batching_analyzer.py (UserPromptSubmit) - Detects opportunities
3. batching_telemetry.py (PostToolUse) - Tracks compliance
"""

import json
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
SETTINGS_FILE = PROJECT_ROOT / ".claude" / "settings.json"
HOOKS_DIR = PROJECT_ROOT / ".claude" / "hooks"

# Source files (scratch)
SCRATCH_FILES = {
    "native_batching_enforcer.py": HOOKS_DIR / "native_batching_enforcer.py",
    "batching_analyzer.py": HOOKS_DIR / "batching_analyzer.py",
    "batching_telemetry.py": HOOKS_DIR / "batching_telemetry.py",
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
        dest_path.chmod(0o755)  # Make executable
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

    # Add PreToolUse hook for Read/Grep/Glob/WebFetch/WebSearch
    pretool_section = settings.setdefault("hooks", {}).setdefault("PreToolUse", [])

    # Check if already exists
    enforcer_exists = any(
        "native_batching_enforcer.py" in hook.get("command", "")
        for entry in pretool_section
        for hook in entry.get("hooks", [])
    )

    if not enforcer_exists:
        pretool_section.append({
            "matcher": "(Read|Grep|Glob|WebFetch|WebSearch)",
            "hooks": [
                {
                    "type": "command",
                    "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/native_batching_enforcer.py"
                }
            ]
        })
        print("✅ Added PreToolUse hook: native_batching_enforcer.py")
    else:
        print("⏭️  PreToolUse hook already exists")

    # Add UserPromptSubmit hook
    prompt_section = settings["hooks"].setdefault("UserPromptSubmit", [])

    if not prompt_section:
        prompt_section.append({"hooks": []})

    prompt_hooks = prompt_section[0].setdefault("hooks", [])

    analyzer_exists = any(
        "batching_analyzer.py" in hook.get("command", "")
        for hook in prompt_hooks
    )

    if not analyzer_exists:
        prompt_hooks.append({
            "type": "command",
            "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/batching_analyzer.py"
        })
        print("✅ Added UserPromptSubmit hook: batching_analyzer.py")
    else:
        print("⏭️  UserPromptSubmit hook already exists")

    # Add PostToolUse hook
    posttool_section = settings["hooks"].setdefault("PostToolUse", [])

    if not posttool_section:
        posttool_section.append({"hooks": []})

    posttool_hooks = posttool_section[0].setdefault("hooks", [])

    telemetry_exists = any(
        "batching_telemetry.py" in hook.get("command", "")
        for hook in posttool_hooks
    )

    if not telemetry_exists:
        posttool_hooks.append({
            "type": "command",
            "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/batching_telemetry.py"
        })
        print("✅ Added PostToolUse hook: batching_telemetry.py")
    else:
        print("⏭️  PostToolUse hook already exists")

    # Save settings
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

    print(f"\n✅ Settings updated: {SETTINGS_FILE}")
    return True


def main():
    """Main integration logic"""
    print("🚀 Integrating Batching Enforcement Hooks\n")

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
    print("  1. native_batching_enforcer.py (PreToolUse) - Blocks sequential tools")
    print("  2. batching_analyzer.py (UserPromptSubmit) - Detects opportunities")
    print("  3. batching_telemetry.py (PostToolUse) - Tracks compliance")
    print()
    print("Next steps:")
    print("  1. Restart session to activate hooks")
    print("  2. Test with multi-file read operations")
    print("  3. Check telemetry: .claude/memory/batching_telemetry.jsonl")
    print("  4. Update CLAUDE.md with batching rules")
    print()

    return 0


if __name__ == "__main__":
    exit(main())
