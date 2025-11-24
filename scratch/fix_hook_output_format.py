#!/usr/bin/env python3
"""
Fix PreToolUse hook output format
Replace allowExecution with permissionDecision (allow/deny)
"""
import re
from pathlib import Path

# Files to fix
hooks_to_fix = [
    ".claude/hooks/command_prerequisite_gate.py",
    ".claude/hooks/constitutional_guard.py",
    ".claude/hooks/file_operation_gate.py",
    ".claude/hooks/native_batching_enforcer.py",
    ".claude/hooks/performance_gate.py",
    ".claude/hooks/scratch_enforcer_gate.py",
]

def fix_hook_file(file_path: str):
    """Fix a single hook file"""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Not found: {file_path}")
        return False

    content = path.read_text()
    original = content

    # Pattern 1: "allowExecution": True -> "permissionDecision": "allow"
    content = re.sub(
        r'"allowExecution":\s*[Tt]rue',
        '"permissionDecision": "allow"',
        content
    )

    # Pattern 2: "allowExecution": False -> "permissionDecision": "deny"
    content = re.sub(
        r'"allowExecution":\s*[Ff]alse',
        '"permissionDecision": "deny"',
        content
    )

    # Pattern 3: blockMessage should be permissionDecisionReason
    # But only if we haven't already converted it
    if '"blockMessage"' in content and '"permissionDecisionReason"' not in content:
        content = content.replace('"blockMessage"', '"permissionDecisionReason"')

    if content != original:
        path.write_text(content)
        print(f"✅ Fixed: {file_path}")
        return True
    else:
        print(f"⏭️  No changes: {file_path}")
        return False

# Fix all hooks
fixed_count = 0
for hook in hooks_to_fix:
    if fix_hook_file(hook):
        fixed_count += 1

print(f"\n📊 Summary: Fixed {fixed_count}/{len(hooks_to_fix)} hooks")
