#!/usr/bin/env python3
"""
SUDO Accountability Protocol: Turns bypass into immediate hook improvement

PHILOSOPHY: SUDO shouldn't mean "skip the problem" - it means "FIX THIS NOW"

When SUDO is detected:
1. Log the false positive (which hook, what was blocked, context)
2. Create "debt" requiring hook fix before continuing
3. Inject fix requirement into context
4. Block further work until debt is paid

This creates a self-healing hook system where every FP = immediate improvement.
"""
import sys
import json
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Paths
HOOK_DIR = Path(__file__).resolve().parent
if ".claude/hooks" in str(HOOK_DIR):
    MEMORY_DIR = HOOK_DIR.parent / "memory"
    PROJECT_ROOT = HOOK_DIR.parent.parent
else:
    # Running from scratch
    PROJECT_ROOT = HOOK_DIR.parent
    MEMORY_DIR = PROJECT_ROOT / ".claude" / "memory"

FALSE_POSITIVES_LOG = MEMORY_DIR / "false_positives.json"
SUDO_DEBT_FILE = MEMORY_DIR / "sudo_debt.json"

# ============================================================================
# SUDO DETECTION
# ============================================================================

def detect_sudo_in_prompt(prompt: str) -> Tuple[bool, Optional[str]]:
    """
    Detect SUDO keyword and extract context about what's being bypassed.

    Returns: (sudo_detected, bypass_context)
    """
    # Negative patterns - SUDO mentioned but NOT being invoked
    negative_patterns = [
        r'\bwithout\s+SUDO\b',
        r'\bno\s+SUDO\b',
        r"\bdon't\s+SUDO\b",
        r"\bdidn't\s+SUDO\b",
        r'\bnot\s+using\s+SUDO\b',
        r'\bavoid\s+SUDO\b',
        r'\bSUDO\s+keyword\b',  # Discussing the keyword
        r'\bSUDO\s+protocol\b',  # Discussing the protocol
        r'\bwhat\s+is\s+SUDO\b',  # Asking about SUDO
        r'\bwhen\s+to\s+use\s+SUDO\b',
    ]

    # Check negative patterns first
    for pattern in negative_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            return False, None

    # Case-sensitive patterns (SUDO must be uppercase - it's a protocol keyword)
    case_sensitive_patterns = [
        r'\bSUDO\b',  # Exact SUDO keyword (uppercase only)
    ]

    # Case-insensitive patterns (clear bypass intent)
    case_insensitive_patterns = [
        r'\bforce\s+proceed\b',
        r'\boverride\s+block\b',
        r'\bbypass\s+hook\b',
        r'\bskip\s+enforcement\b',
    ]

    # Check case-sensitive patterns
    for pattern in case_sensitive_patterns:
        if re.search(pattern, prompt):  # No IGNORECASE
            match = re.search(r'.{0,100}\bSUDO\b.{0,100}', prompt, re.DOTALL)
            context = match.group(0) if match else prompt[:200]
            return True, context.strip()

    # Check case-insensitive patterns
    for pattern in case_insensitive_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            match = re.search(pattern, prompt, re.IGNORECASE)
            context = prompt[:200]
            return True, context.strip()

    return False, None

def extract_blocked_hook_info(prompt: str) -> Dict:
    """
    Try to extract which hook was blocked from the prompt context.

    Returns dict with hook_name, blocked_action, error_message if found.
    """
    info = {
        "hook_name": "unknown",
        "blocked_action": "unknown",
        "error_message": "",
    }

    # Common hook error patterns
    hook_patterns = [
        (r'(tier_gate|confidence_gate|hack_around_gate|assumption_firewall)\.py', 'hook_name'),
        (r'🚫\s*(\w+)\s*BLOCKED', 'blocked_action'),
        (r'⛔\s*(.+?)(?:\n|$)', 'error_message'),
        (r'BLOCKED:?\s*(.+?)(?:\n|$)', 'error_message'),
    ]

    for pattern, field in hook_patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            info[field] = match.group(1).strip()

    return info

# ============================================================================
# FALSE POSITIVE LOGGING
# ============================================================================

def load_false_positives() -> Dict:
    """Load false positives log."""
    if not FALSE_POSITIVES_LOG.exists():
        return {"false_positives": [], "unresolved_count": 0}
    try:
        with open(FALSE_POSITIVES_LOG) as f:
            return json.load(f)
    except Exception:
        return {"false_positives": [], "unresolved_count": 0}

def log_false_positive(hook_name: str, blocked_action: str, context: str, error_message: str) -> int:
    """
    Log a false positive for later analysis and fix.

    Returns: Number of unresolved FPs in this session.
    """
    data = load_false_positives()
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")[:16]

    fp_entry = {
        "id": f"fp_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "hook_name": hook_name,
        "blocked_action": blocked_action,
        "context": context[:500],
        "error_message": error_message[:200],
        "resolved": False,
        "resolution": None,
    }

    data["false_positives"].append(fp_entry)
    data["unresolved_count"] = sum(1 for fp in data["false_positives"] if not fp.get("resolved"))

    # Prune to last 50
    if len(data["false_positives"]) > 50:
        data["false_positives"] = data["false_positives"][-50:]

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(FALSE_POSITIVES_LOG, "w") as f:
            json.dump(data, f, indent=2)
    except (IOError, OSError):
        pass  # Don't crash hook on write failure

    return data["unresolved_count"]

# ============================================================================
# SUDO DEBT TRACKING
# ============================================================================

def load_sudo_debt() -> Dict:
    """Load current SUDO debt."""
    if not SUDO_DEBT_FILE.exists():
        return {"debts": [], "total_debt": 0}
    try:
        with open(SUDO_DEBT_FILE) as f:
            return json.load(f)
    except Exception:
        return {"debts": [], "total_debt": 0}

def add_sudo_debt(hook_name: str, context: str) -> int:
    """
    Add SUDO debt that must be paid (hook must be fixed).

    Returns: Total outstanding debt count.
    """
    data = load_sudo_debt()
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")[:16]

    debt_entry = {
        "id": f"debt_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "hook_name": hook_name,
        "context": context[:300],
        "paid": False,
    }

    data["debts"].append(debt_entry)

    # Prune to last 50 entries (prevent infinite growth)
    if len(data["debts"]) > 50:
        data["debts"] = data["debts"][-50:]

    data["total_debt"] = sum(1 for d in data["debts"] if not d.get("paid"))

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(SUDO_DEBT_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except (IOError, OSError):
        pass  # Don't crash hook on write failure

    return data["total_debt"]

def mark_debt_paid(hook_name: str) -> bool:
    """Mark a debt as paid (hook was fixed)."""
    data = load_sudo_debt()

    for debt in reversed(data["debts"]):
        if debt["hook_name"] == hook_name and not debt.get("paid"):
            debt["paid"] = True
            debt["paid_at"] = datetime.now().isoformat()
            data["total_debt"] = sum(1 for d in data["debts"] if not d.get("paid"))

            with open(SUDO_DEBT_FILE, "w") as f:
                json.dump(data, f, indent=2)
            return True

    return False

def get_unpaid_debts() -> List[Dict]:
    """Get list of unpaid SUDO debts."""
    data = load_sudo_debt()
    return [d for d in data["debts"] if not d.get("paid")]

# ============================================================================
# DEBT ENFORCEMENT (PreToolUse hook)
# ============================================================================

def check_debt_blocking(tool_name: str, tool_input: Dict) -> Tuple[bool, str]:
    """
    Check if unpaid SUDO debt should block this operation.

    Non-fix operations are BLOCKED until debt is paid.

    Returns: (should_block, message)
    """
    unpaid = get_unpaid_debts()
    if not unpaid:
        return False, ""

    # Allow operations that are fixing hooks
    if tool_name in ["Read", "Grep", "Glob"]:
        # Always allow reading
        return False, ""

    file_path = tool_input.get("file_path", "")

    # Allow editing hooks (paying the debt)
    if ".claude/hooks" in file_path or "scripts/lib/epistemology" in file_path:
        return False, ""

    # Block other write operations until debt is paid
    if tool_name in ["Write", "Edit", "MultiEdit"]:
        debt_list = "\n".join([f"  • {d['hook_name']}: {d['context'][:50]}..." for d in unpaid[:3]])
        message = f"""🚫 SUDO DEBT BLOCKING

You used SUDO to bypass hook enforcement, creating debt.

OUTSTANDING DEBT ({len(unpaid)} unpaid):
{debt_list}

⛔ CANNOT proceed with production writes until debt is paid.

REQUIRED ACTION:
1. Read the hook that blocked you: .claude/hooks/<hook_name>.py
2. Identify why it was a false positive
3. Fix the hook to prevent future FPs
4. Then continue your work

Debt is tracked. Unpaid debt = broken hooks = broken system.

To view all debts: cat .claude/memory/sudo_debt.json
"""
        return True, message

    return False, ""

# ============================================================================
# MAIN HOOK (UserPromptSubmit)
# ============================================================================

def main():
    """
    UserPromptSubmit hook to detect SUDO and create accountability.
    """
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"proceed": True}))
        sys.exit(0)

    # Get user prompt
    prompt = input_data.get("prompt", "")
    if not prompt:
        # Try to get from messages
        messages = input_data.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if isinstance(last_msg, dict):
                prompt = last_msg.get("content", "")

    if not prompt:
        print(json.dumps({"proceed": True}))
        sys.exit(0)

    # Detect SUDO
    sudo_detected, sudo_context = detect_sudo_in_prompt(prompt)

    if not sudo_detected:
        print(json.dumps({"proceed": True}))
        sys.exit(0)

    # Extract what was blocked
    hook_info = extract_blocked_hook_info(prompt)

    # Log the false positive
    unresolved = log_false_positive(
        hook_name=hook_info["hook_name"],
        blocked_action=hook_info["blocked_action"],
        context=sudo_context or prompt[:200],
        error_message=hook_info["error_message"],
    )

    # Add SUDO debt
    total_debt = add_sudo_debt(
        hook_name=hook_info["hook_name"],
        context=sudo_context or prompt[:200],
    )

    # Inject accountability message
    message = f"""🔴 SUDO ACCOUNTABILITY TRIGGERED

You are bypassing hook enforcement with SUDO.

Hook Bypassed: {hook_info['hook_name']}
Blocked Action: {hook_info['blocked_action']}

📋 FALSE POSITIVE LOGGED
   • Unresolved FPs this session: {unresolved}
   • This FP ID: fp_{datetime.now().strftime('%Y%m%d_%H%M%S')}

💰 SUDO DEBT CREATED
   • Total outstanding debt: {total_debt}
   • Debt must be PAID before continuing other work

⚠️ SUDO MEANS "FIX THIS NOW" - NOT "SKIP THIS"

REQUIRED ACTIONS (before continuing main task):
1. Read the blocking hook: .claude/hooks/{hook_info['hook_name']}.py
2. Identify why this was a false positive
3. Fix the hook to prevent future FPs
4. Mark debt as paid (automatic when hook is edited)

DO NOT proceed with main task until hook is fixed.
The hook is blocking for a reason - if it's wrong, FIX IT.

Note: Further Write/Edit to non-hook files will be BLOCKED until debt is paid.
"""

    print(json.dumps({
        "proceed": True,  # Allow SUDO to work
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": message,
        }
    }))
    sys.exit(0)

# ============================================================================
# PRE-TOOL-USE DEBT CHECK
# ============================================================================

def main_pretool():
    """
    PreToolUse hook to enforce SUDO debt payment.
    """
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
    else:
        print(json.dumps({"proceed": True}))

    sys.exit(0)

# ============================================================================
# TEST
# ============================================================================

def test_sudo_detection():
    """Test SUDO detection patterns."""
    test_cases = [
        ("I need to bypass this, SUDO", True),
        ("SUDO - the hook is wrong", True),
        ("bypass hook and continue", True),
        ("force proceed with the write", True),
        ("override block please", True),
        ("skip enforcement for this", True),
        ("just do it normally", False),
        ("I understand, let's fix it", False),
        ("the sudo command in linux", False),  # lowercase 'sudo' as Unix command
        ("use sudo apt install", False),  # Unix sudo command
    ]

    print("=" * 60)
    print("SUDO DETECTION TESTS")
    print("=" * 60)

    passed = 0
    for prompt, expected in test_cases:
        detected, _ = detect_sudo_in_prompt(prompt)
        status = "✅" if detected == expected else "❌"
        print(f"{status} '{prompt[:40]}...' -> {'detected' if detected else 'clean'} (expected: {'detected' if expected else 'clean'})")
        if detected == expected:
            passed += 1

    print(f"\nResults: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)

def test_debt_system():
    """Test debt tracking."""
    print("\n" + "=" * 60)
    print("DEBT SYSTEM TESTS")
    print("=" * 60)

    # Clear test state
    if SUDO_DEBT_FILE.exists():
        SUDO_DEBT_FILE.unlink()

    # Add debt
    total = add_sudo_debt("tier_gate.py", "test debt")
    print(f"✅ Added debt, total: {total}")

    # Check unpaid
    unpaid = get_unpaid_debts()
    print(f"✅ Unpaid debts: {len(unpaid)}")

    # Pay debt
    paid = mark_debt_paid("tier_gate.py")
    print(f"✅ Paid debt: {paid}")

    # Verify paid
    unpaid = get_unpaid_debts()
    print(f"✅ Unpaid after payment: {len(unpaid)}")

    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_sudo_detection()
            test_debt_system()
        elif sys.argv[1] == "pretool":
            main_pretool()
    else:
        main()
