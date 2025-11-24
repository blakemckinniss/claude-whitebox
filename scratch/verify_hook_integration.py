#!/usr/bin/env python3
"""Verify scratch context hook is properly integrated"""
import json
import os

print("🔍 SCRATCH CONTEXT HOOK INTEGRATION VERIFICATION")
print("=" * 60)

# 1. Check hook file exists
hook_path = ".claude/hooks/scratch_context_hook.py"
if os.path.exists(hook_path):
    print(f"✅ Hook file exists: {hook_path}")
else:
    print(f"❌ Hook file missing: {hook_path}")
    exit(1)

# 2. Check settings.json registration
with open(".claude/settings.json") as f:
    settings = json.load(f)

hooks = settings.get("hooks", {}).get("UserPromptSubmit", [])
registered = False
for hook_group in hooks:
    for hook in hook_group.get("hooks", []):
        if "scratch_context_hook.py" in hook.get("command", ""):
            registered = True
            break

if registered:
    print("✅ Hook registered in .claude/settings.json")
else:
    print("❌ Hook not registered in settings.json")
    exit(1)

# 3. Check index exists
index_path = ".claude/memory/scratch_index.json"
if os.path.exists(index_path):
    with open(index_path) as f:
        index = json.load(f)
    print(f"✅ Scratch index exists: {len(index)} files indexed")
else:
    print(f"⚠️  Index not yet built (run upkeep.py)")

# 4. Test hook execution
import subprocess
test_query = {"prompt": "test oracle parallel execution"}
result = subprocess.run(
    ["python3", hook_path],
    input=json.dumps(test_query),
    capture_output=True,
    text=True
)

if result.returncode == 0 and result.stdout:
    try:
        response = json.loads(result.stdout)
        context = response.get("hookSpecificOutput", {}).get("additionalContext", "")
        if context:
            print(f"✅ Hook execution successful")
            print(f"   Sample output: {context[:100]}...")
        else:
            print("⚠️  Hook executed but returned no context (may be normal)")
    except:
        print("❌ Hook output parse failed")
        exit(1)
else:
    print(f"❌ Hook execution failed: {result.stderr}")
    exit(1)

print("=" * 60)
print("✅ ALL CHECKS PASSED - Scratch context hook is active!")
print("\nNext session will automatically inject associative memory.")
