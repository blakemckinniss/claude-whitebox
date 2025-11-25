#!/usr/bin/env python3
"""
SUDO Debt Enforcer: PreToolUse hook that blocks non-hook writes until SUDO debt is paid.

When SUDO is used, debt is created. This hook ensures that debt is paid
(hook is fixed) before allowing other production writes.

ALLOWED when debt exists:
- Read, Grep, Glob (always)
- Write/Edit to .claude/hooks/ (paying the debt)
- Write/Edit to scripts/lib/epistemology.py (tuning penalties)

BLOCKED when debt exists:
- All other Write/Edit/MultiEdit operations
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Paths
HOOK_DIR = Path(__file__).resolve().parent
MEMORY_DIR = HOOK_DIR.parent / "memory"
SUDO_DEBT_FILE = MEMORY_DIR / "sudo_debt.json"

def load_sudo_debt() -> Dict:
    """Load current SUDO debt."""
    if not SUDO_DEBT_FILE.exists():
        return {"debts": [], "total_debt": 0}
    try:
        with open(SUDO_DEBT_FILE) as f:
            return json.load(f)
    except Exception:
        return {"debts": [], "total_debt": 0}

def get_unpaid_debts() -> List[Dict]:
    """Get list of unpaid SUDO debts."""
    data = load_sudo_debt()
    return [d for d in data.get("debts", []) if not d.get("paid")]

def mark_debt_paid_for_hook(hook_name: str) -> Tuple[bool, str]:
    """
    Mark debt as paid when hook is edited.

    Returns: (was_modified, message)
    """
    data = load_sudo_debt()
    modified = False
    paid_hooks = []

    for debt in data.get("debts", []):
        if not debt.get("paid"):
            # Strict match by hook name, or clear unknown debts
            debt_hook = debt.get("hook_name", "")
            if hook_name == debt_hook or debt_hook == "unknown":
                debt["paid"] = True
                from datetime import datetime
                debt["paid_at"] = datetime.now().isoformat()
                modified = True
                paid_hooks.append(debt_hook)

    message = ""
    if modified:
        data["total_debt"] = sum(1 for d in data.get("debts", []) if not d.get("paid"))
        try:
            with open(SUDO_DEBT_FILE, "w") as f:
                json.dump(data, f, indent=2)
            remaining = data["total_debt"]
            message = f"✅ SUDO DEBT PAID: Editing {hook_name} cleared {len(paid_hooks)} debt(s). Remaining: {remaining}"
        except (IOError, OSError):
            message = "⚠️ Could not update debt file"

    return modified, message

def check_debt_blocking(tool_name: str, tool_input: Dict) -> Tuple[bool, str]:
    """
    Check if unpaid SUDO debt should block this operation.

    Returns: (should_block, message)
    """
    unpaid = get_unpaid_debts()
    if not unpaid:
        return False, ""

    # Always allow read operations
    if tool_name in ["Read", "Grep", "Glob", "Task", "WebFetch", "WebSearch"]:
        return False, ""

    file_path = tool_input.get("file_path", "")

    # Allow editing hooks (paying the debt)
    if ".claude/hooks" in file_path:
        # Extract hook name from path
        hook_name = Path(file_path).stem
        # Auto-mark debt as paid when hook is edited
        was_paid, payment_msg = mark_debt_paid_for_hook(hook_name)
        # Return the payment message as feedback (not blocking)
        return False, payment_msg if was_paid else ""

    # Allow editing epistemology (tuning system)
    if "scripts/lib/epistemology" in file_path:
        return False, ""

    # Allow scratch (experimentation)
    if "scratch/" in file_path or "/scratch/" in file_path:
        return False, ""

    # Block other write operations until debt is paid
    if tool_name in ["Write", "Edit", "MultiEdit"]:
        debt_list = "\n".join([f"  • {d.get('hook_name', 'unknown')}: {d.get('context', '')[:50]}..." for d in unpaid[:3]])
        message = f"""🚫 SUDO DEBT BLOCKING

You used SUDO to bypass hook enforcement, creating debt.

OUTSTANDING DEBT ({len(unpaid)} unpaid):
{debt_list}

⛔ CANNOT proceed with production writes until debt is paid.

REQUIRED ACTION:
1. Read the blocking hook: .claude/hooks/<hook_name>.py
2. Identify why it was a false positive
3. Fix the hook to prevent future FPs
4. Debt is auto-cleared when hook is edited

ALLOWED NOW:
  • Read/Grep/Glob (investigation)
  • Write to .claude/hooks/ (fix the hook)
  • Write to scratch/ (experimentation)

Debt is tracked. Unpaid debt = broken hooks = broken system.

To view all debts: cat .claude/memory/sudo_debt.json
To manually clear (SUDO CLEAR DEBT): Edit .claude/memory/sudo_debt.json
"""
        return True, message

    return False, ""

def main():
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"proceed": True}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    should_block, message = check_debt_blocking(tool_name, tool_input)

    if should_block:
        print(json.dumps({
            "proceed": False,
            "error": message,
        }))
    elif message:
        # Debt was paid - provide feedback
        print(json.dumps({
            "proceed": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": message,
            }
        }))
    else:
        print(json.dumps({"proceed": True}))

    sys.exit(0)

if __name__ == "__main__":
    main()
