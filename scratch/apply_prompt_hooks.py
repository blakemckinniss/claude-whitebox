#!/usr/bin/env python3
"""
Apply Prompt-Based Hooks to .claude/settings.json

This script:
1. Loads current settings.json
2. Removes 5 Python hooks being replaced
3. Adds 9 prompt-based hooks
4. Validates JSON syntax
5. Writes updated configuration
"""
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent
SETTINGS_PATH = PROJECT_ROOT / ".claude" / "settings.json"
SNIPPET_PATH = PROJECT_ROOT / "scratch" / "settings_snippet.json"

# Hooks to remove (being replaced by prompt-based)
HOOKS_TO_REMOVE = [
    "detect_batch.py",
    "check_knowledge.py",
    "sanity_check.py",
    "force_playwright.py",
    "intervention.py",
]

def load_settings():
    """Load current settings.json"""
    with open(SETTINGS_PATH) as f:
        return json.load(f)

def load_prompt_hooks():
    """Load prompt-based hook configuration"""
    with open(SNIPPET_PATH) as f:
        return json.load(f)

def remove_python_hooks(settings):
    """Remove Python hooks that are being replaced"""
    removed_count = 0
    
    if "hooks" not in settings or "UserPromptSubmit" not in settings["hooks"]:
        print("⚠️ No UserPromptSubmit hooks found")
        return removed_count
    
    for matcher_block in settings["hooks"]["UserPromptSubmit"]:
        if "hooks" not in matcher_block:
            continue
            
        original_len = len(matcher_block["hooks"])
        
        # Filter out hooks that reference the files we're removing
        matcher_block["hooks"] = [
            hook for hook in matcher_block["hooks"]
            if not any(
                removed_hook in hook.get("command", "")
                for removed_hook in HOOKS_TO_REMOVE
            )
        ]
        
        removed_count += original_len - len(matcher_block["hooks"])
    
    return removed_count

def add_prompt_hooks(settings, prompt_hooks):
    """Add prompt-based hooks to configuration"""
    
    # Add UserPromptSubmit prompt hooks
    if "UserPromptSubmit" in prompt_hooks:
        # Find the UserPromptSubmit block (should be first one without matcher)
        for matcher_block in settings["hooks"]["UserPromptSubmit"]:
            if "matcher" not in matcher_block or not matcher_block.get("matcher"):
                # Add prompt hooks at the END (after state tracking hooks)
                matcher_block["hooks"].extend(
                    prompt_hooks["UserPromptSubmit"][0]["hooks"]
                )
                break
    
    # Add PreToolUse prompt hooks
    if "PreToolUse" in prompt_hooks:
        if "PreToolUse" not in settings["hooks"]:
            settings["hooks"]["PreToolUse"] = []
        
        # Add new PreToolUse matchers
        for new_matcher in prompt_hooks["PreToolUse"]:
            # Check if matcher already exists
            matcher_pattern = new_matcher["matcher"]
            existing = False
            
            for existing_matcher in settings["hooks"]["PreToolUse"]:
                if existing_matcher.get("matcher") == matcher_pattern:
                    # Append to existing matcher
                    existing_matcher["hooks"].extend(new_matcher["hooks"])
                    existing = True
                    break
            
            if not existing:
                # Add new matcher block
                settings["hooks"]["PreToolUse"].append(new_matcher)

def main():
    print("🔄 APPLYING PROMPT-BASED HOOKS\n")
    print("=" * 80)
    
    # Load configurations
    print("\n📖 Loading configurations...")
    settings = load_settings()
    prompt_hooks = load_prompt_hooks()
    
    print(f"✅ Loaded current settings from: {SETTINGS_PATH}")
    print(f"✅ Loaded prompt hooks from: {SNIPPET_PATH}")
    
    # Remove Python hooks
    print("\n🗑️  Removing Python hooks...")
    removed = remove_python_hooks(settings)
    print(f"✅ Removed {removed} Python hook references:")
    for hook in HOOKS_TO_REMOVE:
        print(f"   - {hook}")
    
    # Add prompt hooks
    print("\n➕ Adding prompt-based hooks...")
    add_prompt_hooks(settings, prompt_hooks)
    
    user_prompt_count = len(prompt_hooks["UserPromptSubmit"][0]["hooks"])
    pre_tool_count = len(prompt_hooks["PreToolUse"])
    
    print(f"✅ Added {user_prompt_count} UserPromptSubmit prompt hooks")
    print(f"✅ Added {pre_tool_count} PreToolUse prompt hook matchers")
    
    # Validate JSON
    print("\n🔍 Validating JSON syntax...")
    try:
        json_str = json.dumps(settings, indent=2)
        json.loads(json_str)  # Verify it's valid
        print("✅ JSON syntax valid")
    except json.JSONDecodeError as e:
        print(f"❌ JSON validation failed: {e}")
        sys.exit(1)
    
    # Write updated settings
    print("\n💾 Writing updated settings...")
    with open(SETTINGS_PATH, "w") as f:
        f.write(json_str)
    
    print(f"✅ Updated settings written to: {SETTINGS_PATH}")
    
    # Summary
    print("\n" + "=" * 80)
    print("\n✨ MIGRATION COMPLETE\n")
    
    print("📊 SUMMARY:")
    print(f"  Python hooks removed: {removed}")
    print(f"  Prompt hooks added: {user_prompt_count + pre_tool_count}")
    print(f"  Backup location: {SETTINGS_PATH}.backup_*")
    
    print("\n⚠️ NEXT STEPS:")
    print("  1. Restart Claude Code session to load new hooks")
    print("  2. Test with sample prompts:")
    print("     - 'write a script to process all files' (batch detection)")
    print("     - 'use pandas to analyze data' (API guessing prevention)")
    print("     - 'migrate to new framework' (bikeshedding detection)")
    print("  3. Monitor systemMessage outputs")
    print("  4. Iterate on prompt templates if needed")
    
    print("\n🔄 ROLLBACK (if needed):")
    print(f"  cp {SETTINGS_PATH}.backup_* {SETTINGS_PATH}")

if __name__ == "__main__":
    main()
