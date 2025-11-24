#!/usr/bin/env python3
"""Update settings.json to register new auto-invocation hooks"""

import json
from pathlib import Path

def find_project_root():
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "scripts" / "lib" / "core.py").exists():
            return parent
    return Path.cwd()

ROOT = find_project_root()
SETTINGS_FILE = ROOT / ".claude" / "settings.json"

# Load current settings
with open(SETTINGS_FILE) as f:
    settings = json.load(f)

# Add block_main_write to Write matcher (first in list)
write_hooks = None
for section in settings["hooks"]["PreToolUse"]:
    if section.get("matcher") == "Write":
        write_hooks = section["hooks"]
        break

if write_hooks:
    block_main_write_hook = {
        "type": "command",
        "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/block_main_write.py"
    }
    # Insert at beginning
    if not any("block_main_write.py" in h.get("command", "") for h in write_hooks):
        write_hooks.insert(0, block_main_write_hook)
        print("✅ Added block_main_write.py to Write hooks")
    else:
        print("⏭️  block_main_write.py already in Write hooks")

# Add detect_install to Bash matcher (first in list)
bash_hooks = None
for section in settings["hooks"]["PreToolUse"]:
    if section.get("matcher") == "Bash":
        bash_hooks = section["hooks"]
        break

if bash_hooks:
    detect_install_hook = {
        "type": "command",
        "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/detect_install.py"
    }
    # Insert at beginning
    if not any("detect_install.py" in h.get("command", "") for h in bash_hooks):
        bash_hooks.insert(0, detect_install_hook)
        print("✅ Added detect_install.py to Bash hooks")
    else:
        print("⏭️  detect_install.py already in Bash hooks")

# Add auto_researcher to PostToolUse (first in list)
post_hooks = None
for section in settings["hooks"]["PostToolUse"]:
    post_hooks = section["hooks"]
    break

if post_hooks:
    auto_researcher_hook = {
        "type": "command",
        "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/auto_researcher.py"
    }
    # Insert at beginning
    if not any("auto_researcher.py" in h.get("command", "") for h in post_hooks):
        post_hooks.insert(0, auto_researcher_hook)
        print("✅ Added auto_researcher.py to PostToolUse hooks")
    else:
        print("⏭️  auto_researcher.py already in PostToolUse hooks")

# Write updated settings
with open(SETTINGS_FILE, "w") as f:
    json.dump(settings, f, indent=2)

print("\n✅ Settings updated successfully")
