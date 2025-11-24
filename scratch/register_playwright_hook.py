#!/usr/bin/env python3
"""Register the auto_playwright_setup hook in settings.json"""
import json
from pathlib import Path

settings_file = Path(".claude/settings.json")

with open(settings_file) as f:
    settings = json.load(f)

# Settings.json structure: {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [...]}]}}
pre_tool_use = settings.get("hooks", {}).get("PreToolUse", [])

# Find Bash matcher
bash_matcher = None
for matcher in pre_tool_use:
    if matcher.get("matcher") == "Bash":
        bash_matcher = matcher
        break

if not bash_matcher:
    # Create Bash matcher
    bash_matcher = {
        "matcher": "Bash",
        "hooks": []
    }
    pre_tool_use.append(bash_matcher)

# Check if auto_playwright_setup already registered
hook_command = "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/auto_playwright_setup.py"
existing = [h for h in bash_matcher["hooks"] if h.get("command") == hook_command]

if existing:
    print(f"✓ Hook already registered: auto_playwright_setup.py")
else:
    # Add the hook
    new_hook = {
        "type": "command",
        "command": hook_command
    }
    bash_matcher["hooks"].append(new_hook)

    # Update settings
    if "hooks" not in settings:
        settings["hooks"] = {}
    if "PreToolUse" not in settings["hooks"]:
        settings["hooks"]["PreToolUse"] = []

    settings["hooks"]["PreToolUse"] = pre_tool_use

    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=2)

    print(f"✓ Registered hook: auto_playwright_setup.py")
    print("  Event: PreToolUse")
    print("  Matcher: Bash")

print("\nPlaywright enforcement hooks active:")
print("  1. force_playwright.py (UserPromptSubmit) - warns against requests/BS4")
print("  2. auto_playwright_setup.py (PreToolUse) - auto-installs if needed")
