#!/usr/bin/env python3
"""
Epistemological Protocol Enforcement System
Generates three components:
1. State tracker (confidence_state.json)
2. Detection hook (detect_low_confidence.py) - UserPromptSubmit
3. Gating hook (confidence_gate.py) - PreToolUse
"""
import os
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = PROJECT_ROOT / ".claude" / "hooks"
MEMORY_DIR = PROJECT_ROOT / ".claude" / "memory"

# ============================================================================
# Component 1: Detection Hook (UserPromptSubmit)
# ============================================================================
DETECT_HOOK = '''#!/usr/bin/env python3
"""
Detect Low Confidence Hook: Warns when coding requests occur at insufficient confidence
Triggers on: write, implement, refactor, fix, modify, edit
"""
import sys
import json
from pathlib import Path

# Load confidence state
MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
STATE_FILE = MEMORY_DIR / "confidence_state.json"

def load_confidence():
    """Load current confidence level"""
    if not STATE_FILE.exists():
        return 0
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
            return data.get("current_confidence", 0)
    except:
        return 0

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ""
        }
    }))
    sys.exit(0)

prompt = input_data.get("prompt", "")
if not prompt:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ""
        }
    }))
    sys.exit(0)

prompt_lower = prompt.lower()

# Detect coding/action requests
coding_triggers = [
    "write", "implement", "create", "build", "make",
    "refactor", "fix", "modify", "edit", "update",
    "add a", "add the", "generate", "scaffold"
]

# Detect if this is a coding request
is_coding_request = any(trigger in prompt_lower for trigger in coding_triggers)

if is_coding_request:
    confidence = load_confidence()

    if confidence < 31:
        # Ignorance tier - blocked from coding
        additional_context = f"""
📉 EPISTEMOLOGICAL PROTOCOL: CONFIDENCE TOO LOW

Current Confidence: {confidence}% (IGNORANCE TIER)

⛔ CODING PROHIBITED AT <31% CONFIDENCE

You are attempting a coding task without sufficient evidence.

ALLOWED ACTIONS:
  • Ask questions
  • /research "<query>" - Gather documentation (+20%)
  • /xray --type <type> --name <Name> - Find code structure (+10%)
  • /probe "<object>" - Inspect runtime APIs (+30%)

FORBIDDEN ACTIONS:
  ❌ Writing code
  ❌ Proposing solutions
  ❌ Making changes

NEXT STEPS:
  1. Gather evidence using allowed tools
  2. Build context to 31%+ before attempting solutions
  3. Track: python3 scripts/ops/confidence.py status

**The Dunning-Kruger Checkpoint: Peak ignorance is not a license to code.**
"""
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": additional_context
            }
        }))
        sys.exit(0)

    elif confidence < 71:
        # Hypothesis tier - can scratch, not production
        additional_context = f"""
📉 EPISTEMOLOGICAL PROTOCOL: LIMITED CONFIDENCE

Current Confidence: {confidence}% (HYPOTHESIS TIER)

⚠️ PRODUCTION CODE BLOCKED - SCRATCH ONLY

You have documentation/context but no runtime verification.

ALLOWED ACTIONS:
  • /think "<problem>" - Decompose the task (+5%)
  • /skeptic "<proposal>" - Check for risks (+5%)
  • Write to scratch/ directory (experimentation)
  • /probe "<object>" - Verify APIs (+30%)
  • /verify <check> <target> - Confirm state (+40%)

FORBIDDEN ACTIONS:
  ❌ Modifying scripts/ or production files
  ❌ Claiming "I know how to do this"
  ❌ Committing code

THRESHOLD FOR PRODUCTION: 71%+

NEXT STEPS:
  1. Test your hypothesis in scratch/
  2. Run verification commands
  3. Reach 71%+ before modifying production code
"""
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": additional_context
            }
        }))
        sys.exit(0)

# Confidence sufficient or not a coding request
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": ""
    }
}))
sys.exit(0)
'''

# ============================================================================
# Component 2: Gating Hook (PreToolUse)
# ============================================================================
GATE_HOOK = '''#!/usr/bin/env python3
"""
Confidence Gate Hook: Blocks Write/Edit to production files at <71% confidence
Allows scratch/ writes at any level (experimentation)
"""
import sys
import json
from pathlib import Path

# Load confidence state
MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
STATE_FILE = MEMORY_DIR / "confidence_state.json"

def load_confidence():
    """Load current confidence level"""
    if not STATE_FILE.exists():
        return 0
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
            return data.get("current_confidence", 0)
    except:
        return 0

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "action": "allow"
        }
    }))
    sys.exit(0)

tool_name = input_data.get("toolName", "")
tool_params = input_data.get("toolParams", {})

# Only intercept Write/Edit operations
if tool_name not in ["Write", "Edit"]:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "action": "allow"
        }
    }))
    sys.exit(0)

# Get file path
file_path = tool_params.get("file_path", "")
if not file_path:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "action": "allow"
        }
    }))
    sys.exit(0)

# Allow scratch/ writes at any confidence (experimentation)
if "/scratch/" in file_path or file_path.startswith("scratch/"):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "action": "allow"
        }
    }))
    sys.exit(0)

# Check confidence for production files
confidence = load_confidence()

if confidence < 71:
    additional_context = f"""
🚨 CONFIDENCE GATE: PRODUCTION WRITE BLOCKED

Current Confidence: {confidence}% (INSUFFICIENT)
Target File: {file_path}

⛔ PRODUCTION CODE MODIFICATION REQUIRES 71%+ CONFIDENCE

You are attempting to modify production code without runtime verification.

CURRENT TIER: {"IGNORANCE (0-30%)" if confidence < 31 else "HYPOTHESIS (31-70%)"}

REQUIRED EVIDENCE FOR 71%+:
  1. Read relevant code files (+10% each)
  2. Research documentation (/research, +20%)
  3. Inspect runtime APIs (/probe, +30%)
  4. Verify system state (/verify, +40%)

ALLOWED RIGHT NOW:
  ✅ Write to scratch/ (experimentation allowed)
  ✅ Gather evidence using investigation tools
  ✅ Test hypotheses in throwaway code

FORBIDDEN:
  ❌ Modify scripts/ at <71%
  ❌ Edit production files at <71%
  ❌ Commit unverified changes

NEXT STEPS:
  1. python3 scripts/ops/confidence.py status (check current state)
  2. Gather evidence to reach 71%
  3. Retry this operation after threshold met

**Earn the right to code. Evidence > Intuition.**
"""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "action": "deny",
            "denyReason": additional_context
        }
    }))
    sys.exit(0)

# Confidence sufficient, allow operation
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "action": "allow"
    }
}))
sys.exit(0)
'''

# ============================================================================
# Component 3: Helper Script (scripts/ops/confidence.py)
# ============================================================================
HELPER_SCRIPT = '''#!/usr/bin/env python3
"""
Confidence Tracker: Manage epistemological protocol state
Commands: status, add, reset
"""
import sys
import json
from datetime import datetime
from pathlib import Path

# Find project root
def find_project_root():
    """Walk up directory tree to find project root"""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        marker = current / "scripts" / "lib" / "core.py"
        if marker.exists():
            return current
        current = current.parent
    raise RuntimeError("Cannot find project root (scripts/lib/core.py not found)")

PROJECT_ROOT = find_project_root()
MEMORY_DIR = PROJECT_ROOT / ".claude" / "memory"
STATE_FILE = MEMORY_DIR / "confidence_state.json"

def load_state():
    """Load confidence state"""
    if not STATE_FILE.exists():
        return {
            "current_confidence": 0,
            "evidence_log": [],
            "last_reset": datetime.now().isoformat()
        }
    with open(STATE_FILE) as f:
        return json.load(f)

def save_state(state):
    """Save confidence state"""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def cmd_status():
    """Show current confidence level"""
    state = load_state()
    confidence = state["current_confidence"]

    # Determine tier
    if confidence < 31:
        tier = "IGNORANCE (0-30%)"
        tier_icon = "🔴"
    elif confidence < 71:
        tier = "HYPOTHESIS (31-70%)"
        tier_icon = "🟡"
    else:
        tier = "CERTAINTY (71-100%)"
        tier_icon = "🟢"

    print(f"\\n📉 EPISTEMOLOGICAL PROTOCOL STATUS\\n")
    print(f"{tier_icon} Current Confidence: {confidence}%")
    print(f"   Tier: {tier}")
    print(f"   Last Reset: {state['last_reset']}")

    if state['evidence_log']:
        print(f"\\n📚 Evidence Log (Last 5):")
        for entry in state['evidence_log'][-5:]:
            print(f"   • {entry['action']}: +{entry['gain']}% ({entry['timestamp']})")

    print(f"\\n🎯 Next Threshold:")
    if confidence < 31:
        print(f"   Need +{31 - confidence}% to reach HYPOTHESIS tier (scratch/ allowed)")
    elif confidence < 71:
        print(f"   Need +{71 - confidence}% to reach CERTAINTY tier (production allowed)")
    else:
        print(f"   ✅ All tiers unlocked")
    print()

def cmd_add(action, description, gain):
    """Add evidence and increase confidence"""
    state = load_state()

    # Cap at 100%
    new_confidence = min(100, state["current_confidence"] + gain)

    # Log entry
    entry = {
        "action": action,
        "description": description,
        "gain": gain,
        "timestamp": datetime.now().isoformat()
    }
    state["evidence_log"].append(entry)
    state["current_confidence"] = new_confidence

    save_state(state)
    print(f"✅ Evidence added: {action} (+{gain}%) → Total: {new_confidence}%")

def cmd_reset():
    """Reset confidence to 0% (new task)"""
    state = {
        "current_confidence": 0,
        "evidence_log": [],
        "last_reset": datetime.now().isoformat()
    }
    save_state(state)
    print("🔄 Confidence reset to 0% (new task started)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 scripts/ops/confidence.py status")
        print("  python3 scripts/ops/confidence.py add <action> <description> <gain>")
        print("  python3 scripts/ops/confidence.py reset")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "status":
        cmd_status()
    elif cmd == "add":
        if len(sys.argv) < 5:
            print("Usage: confidence.py add <action> <description> <gain>")
            sys.exit(1)
        action = sys.argv[2]
        description = sys.argv[3]
        gain = int(sys.argv[4])
        cmd_add(action, description, gain)
    elif cmd == "reset":
        cmd_reset()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
'''

# ============================================================================
# Generate files
# ============================================================================
def main():
    print("📉 Generating Epistemological Protocol Enforcement System...")

    # 1. Create detection hook
    detect_file = HOOKS_DIR / "detect_low_confidence.py"
    with open(detect_file, 'w') as f:
        f.write(DETECT_HOOK)
    os.chmod(detect_file, 0o755)
    print(f"✅ Created: {detect_file}")

    # 2. Create gating hook
    gate_file = HOOKS_DIR / "confidence_gate.py"
    with open(gate_file, 'w') as f:
        f.write(GATE_HOOK)
    os.chmod(gate_file, 0o755)
    print(f"✅ Created: {gate_file}")

    # 3. Create helper script
    helper_file = PROJECT_ROOT / "scripts" / "ops" / "confidence.py"
    with open(helper_file, 'w') as f:
        f.write(HELPER_SCRIPT)
    os.chmod(helper_file, 0o755)
    print(f"✅ Created: {helper_file}")

    # 4. Initialize state file
    state_file = MEMORY_DIR / "confidence_state.json"
    if not state_file.exists():
        initial_state = {
            "current_confidence": 0,
            "evidence_log": [],
            "last_reset": datetime.now().isoformat()
        }
        with open(state_file, 'w') as f:
            json.dump(initial_state, f, indent=2)
        print(f"✅ Initialized: {state_file}")

    print("\\n📋 NEXT STEPS:")
    print("1. Add hooks to .claude/settings.json:")
    print("   UserPromptSubmit: detect_low_confidence.py")
    print("   PreToolUse (Write/Edit): confidence_gate.py")
    print("2. Test: python3 scripts/ops/confidence.py status")
    print("3. Manually track evidence: confidence.py add <action> <desc> <gain>")

if __name__ == "__main__":
    main()
