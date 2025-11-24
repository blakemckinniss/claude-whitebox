#!/usr/bin/env python3
"""Verify prompt-based hooks are correctly installed"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SETTINGS_PATH = PROJECT_ROOT / ".claude" / "settings.json"

with open(SETTINGS_PATH) as f:
    settings = json.load(f)

print("🔍 HOOK VERIFICATION\n")
print("=" * 80)

# Check UserPromptSubmit
user_prompt_hooks = settings["hooks"]["UserPromptSubmit"][0]["hooks"]
prompt_hooks = [h for h in user_prompt_hooks if h.get("type") == "prompt"]

print(f"\n✅ UserPromptSubmit: {len(prompt_hooks)} prompt-based hooks")
for i, hook in enumerate(prompt_hooks, 1):
    prompt_preview = hook["prompt"][:80].replace("\n", " ")
    timeout = hook.get("timeout", "N/A")
    print(f"   {i}. {prompt_preview}... (timeout: {timeout}s)")

# Check PreToolUse
pre_tool_matchers = settings["hooks"].get("PreToolUse", [])
prompt_matchers = [
    m for m in pre_tool_matchers
    if any(h.get("type") == "prompt" for h in m.get("hooks", []))
]

print(f"\n✅ PreToolUse: {len(prompt_matchers)} prompt-based matcher(s)")
for matcher in prompt_matchers:
    pattern = matcher.get("matcher", "N/A")
    prompt_hooks_in_matcher = [h for h in matcher["hooks"] if h.get("type") == "prompt"]
    print(f"   Matcher: {pattern} ({len(prompt_hooks_in_matcher)} prompt hook(s))")

# Check removed hooks
print(f"\n🗑️  Removed Python hooks verification:")
removed_hooks = ["detect_batch.py", "check_knowledge.py", "sanity_check.py", 
                "force_playwright.py", "intervention.py"]

for hook_name in removed_hooks:
    found = False
    for matcher in settings["hooks"]["UserPromptSubmit"]:
        for hook in matcher.get("hooks", []):
            if hook_name in hook.get("command", ""):
                found = True
                break
    
    status = "❌ STILL PRESENT" if found else "✅ Removed"
    print(f"   {hook_name}: {status}")

print("\n" + "=" * 80)
print("\n✨ VERIFICATION COMPLETE")
