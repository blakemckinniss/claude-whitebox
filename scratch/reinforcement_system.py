#!/usr/bin/env python3
"""
Epistemological Protocol - Reinforcement Layer
Adds positive/negative reinforcement to confidence tracking
Philosophy: Carrot (production access) + Stick (confidence loss)
"""
import os
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = PROJECT_ROOT / ".claude" / "hooks"
MEMORY_DIR = PROJECT_ROOT / ".claude" / "memory"

# ============================================================================
# Enhanced Confidence Tracker with Reinforcement
# ============================================================================
ENHANCED_CONFIDENCE_SCRIPT = '''#!/usr/bin/env python3
"""
Confidence Tracker with Reinforcement Learning
Commands: status, gain, loss, reset
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

# Reinforcement Schedule (Positive)
GAINS = {
    # Investigation
    "read_file": {"gain": 10, "desc": "Read a file"},
    "research_manual": {"gain": 20, "desc": "Manual research"},
    "research_agent": {"gain": 25, "desc": "Research via agent (better context isolation)"},
    "probe": {"gain": 30, "desc": "Runtime API inspection"},
    "verify": {"gain": 40, "desc": "State verification"},

    # Agents (Delegation bonus)
    "use_researcher": {"gain": 25, "desc": "Delegated to researcher agent"},
    "use_script_smith": {"gain": 15, "desc": "Delegated to script-smith agent"},
    "use_sherlock": {"gain": 20, "desc": "Delegated to sherlock agent"},
    "use_council": {"gain": 10, "desc": "Consulted council before decision"},
    "use_critic": {"gain": 10, "desc": "Consulted critic for review"},

    # Protocols
    "run_audit": {"gain": 15, "desc": "Ran audit.py before commit"},
    "run_void": {"gain": 15, "desc": "Ran void.py completeness check"},
    "run_drift": {"gain": 10, "desc": "Ran drift_check.py"},
    "run_tests": {"gain": 30, "desc": "Ran test suite"},

    # Meta-cognition
    "think_protocol": {"gain": 5, "desc": "Used /think to decompose problem"},
    "skeptic_review": {"gain": 5, "desc": "Used /skeptic to check risks"},
}

# Reinforcement Schedule (Negative)
LOSSES = {
    # Shortcuts
    "skip_verification": {"loss": 20, "desc": "Skipped verification after code change"},
    "guess_api": {"loss": 15, "desc": "Guessed API without probing"},
    "write_without_read": {"loss": 30, "desc": "Wrote code without reading existing code"},
    "claim_done_no_tests": {"loss": 25, "desc": "Claimed done without running tests"},
    "modify_unexamined": {"loss": 40, "desc": "Modified code not examined"},

    # Hallucinations
    "claim_knowledge": {"loss": 10, "desc": "Claimed knowledge without evidence"},
    "propose_without_context": {"loss": 15, "desc": "Proposed solution without gathering context"},

    # Workflow violations
    "skip_planning": {"loss": 10, "desc": "Skipped /think or /council for complex task"},
    "no_dry_run": {"loss": 15, "desc": "Ran script without --dry-run first"},
    "commit_no_audit": {"loss": 20, "desc": "Committed without running audit.py"},
}

def load_state():
    """Load confidence state"""
    if not STATE_FILE.exists():
        return {
            "current_confidence": 0,
            "reinforcement_log": [],
            "last_reset": datetime.now().isoformat(),
            "total_gains": 0,
            "total_losses": 0
        }
    with open(STATE_FILE) as f:
        data = json.load(f)
        # Migrate old format if needed
        if "reinforcement_log" not in data:
            data["reinforcement_log"] = data.get("evidence_log", [])
            data["total_gains"] = 0
            data["total_losses"] = 0
        return data

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
        tier_emoji = "🚫"
    elif confidence < 71:
        tier = "HYPOTHESIS (31-70%)"
        tier_icon = "🟡"
        tier_emoji = "🧪"
    else:
        tier = "CERTAINTY (71-100%)"
        tier_icon = "🟢"
        tier_emoji = "✅"

    print(f"\\n📉 EPISTEMOLOGICAL PROTOCOL STATUS\\n")
    print(f"{tier_icon} Current Confidence: {confidence}%")
    print(f"   Tier: {tier_emoji} {tier}")
    print(f"   Last Reset: {state['last_reset']}")

    # Reinforcement stats
    total_gains = state.get("total_gains", 0)
    total_losses = state.get("total_losses", 0)
    net = total_gains - total_losses

    print(f"\\n📊 Reinforcement Stats:")
    print(f"   Total Gains: +{total_gains}%")
    print(f"   Total Losses: -{total_losses}%")
    print(f"   Net Score: {'+'if net >= 0 else ''}{net}%")

    if state['reinforcement_log']:
        print(f"\\n📚 Recent Activity (Last 5):")
        for entry in state['reinforcement_log'][-5:]:
            action_type = entry.get('type', 'gain')
            value = entry.get('gain', entry.get('loss', 0))
            icon = "📈" if action_type == "gain" else "📉"
            sign = "+" if action_type == "gain" else "-"
            print(f"   {icon} {entry['action']}: {sign}{value}% - {entry['description']}")

    print(f"\\n🎯 Next Threshold:")
    if confidence < 31:
        needed = 31 - confidence
        print(f"   Need +{needed}% to reach HYPOTHESIS tier (scratch/ allowed)")
        print(f"   💡 Tip: Use /research (+20-25%) or /probe (+30%)")
    elif confidence < 71:
        needed = 71 - confidence
        print(f"   Need +{needed}% to reach CERTAINTY tier (production allowed)")
        print(f"   💡 Tip: Run /verify (+40%) to unlock production")
    else:
        print(f"   ✅ All tiers unlocked - Production code allowed")
        print(f"   ⚠️ Warning: Confidence can still drop from violations")

    print()

def cmd_gain(action_key, custom_desc=None):
    """Add positive reinforcement"""
    if action_key not in GAINS:
        print(f"❌ Unknown gain action: {action_key}")
        print(f"Available: {', '.join(GAINS.keys())}")
        return

    state = load_state()
    gain_data = GAINS[action_key]
    gain = gain_data["gain"]
    description = custom_desc or gain_data["desc"]

    # Cap at 100%
    new_confidence = min(100, state["current_confidence"] + gain)

    # Log entry
    entry = {
        "type": "gain",
        "action": action_key,
        "description": description,
        "gain": gain,
        "timestamp": datetime.now().isoformat()
    }
    state["reinforcement_log"].append(entry)
    state["current_confidence"] = new_confidence
    state["total_gains"] = state.get("total_gains", 0) + gain

    save_state(state)
    print(f"📈 Positive Reinforcement: {description} (+{gain}%) → Total: {new_confidence}%")

def cmd_loss(action_key, custom_desc=None):
    """Apply negative reinforcement"""
    if action_key not in LOSSES:
        print(f"❌ Unknown loss action: {action_key}")
        print(f"Available: {', '.join(LOSSES.keys())}")
        return

    state = load_state()
    loss_data = LOSSES[action_key]
    loss = loss_data["loss"]
    description = custom_desc or loss_data["desc"]

    # Floor at 0%
    new_confidence = max(0, state["current_confidence"] - loss)

    # Log entry
    entry = {
        "type": "loss",
        "action": action_key,
        "description": description,
        "loss": loss,
        "timestamp": datetime.now().isoformat()
    }
    state["reinforcement_log"].append(entry)
    state["current_confidence"] = new_confidence
    state["total_losses"] = state.get("total_losses", 0) + loss

    save_state(state)
    print(f"📉 Negative Reinforcement: {description} (-{loss}%) → Total: {new_confidence}%")

    # Warning if dropped below threshold
    if new_confidence < 71:
        print(f"⚠️ WARNING: Confidence dropped below production threshold (71%)")
        print(f"   Production writes are now BLOCKED")
        print(f"   Gather evidence to restore access")

def cmd_reset():
    """Reset confidence to 0% (new task)"""
    state = {
        "current_confidence": 0,
        "reinforcement_log": [],
        "last_reset": datetime.now().isoformat(),
        "total_gains": 0,
        "total_losses": 0
    }
    save_state(state)
    print("🔄 Confidence reset to 0% (new task started)")

def cmd_list_actions():
    """List all available reinforcement actions"""
    print("\\n📈 POSITIVE REINFORCEMENT ACTIONS:\\n")
    for key, data in sorted(GAINS.items()):
        print(f"  {key:25s} +{data['gain']:2d}%  {data['desc']}")

    print("\\n📉 NEGATIVE REINFORCEMENT ACTIONS:\\n")
    for key, data in sorted(LOSSES.items()):
        print(f"  {key:25s} -{data['loss']:2d}%  {data['desc']}")
    print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 scripts/ops/confidence.py status")
        print("  python3 scripts/ops/confidence.py gain <action_key> [description]")
        print("  python3 scripts/ops/confidence.py loss <action_key> [description]")
        print("  python3 scripts/ops/confidence.py reset")
        print("  python3 scripts/ops/confidence.py list")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "status":
        cmd_status()
    elif cmd == "gain":
        if len(sys.argv) < 3:
            print("Usage: confidence.py gain <action_key> [description]")
            print("Run 'confidence.py list' to see available actions")
            sys.exit(1)
        action_key = sys.argv[2]
        custom_desc = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else None
        cmd_gain(action_key, custom_desc)
    elif cmd == "loss":
        if len(sys.argv) < 3:
            print("Usage: confidence.py loss <action_key> [description]")
            print("Run 'confidence.py list' to see available actions")
            sys.exit(1)
        action_key = sys.argv[2]
        custom_desc = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else None
        cmd_loss(action_key, custom_desc)
    elif cmd == "reset":
        cmd_reset()
    elif cmd == "list":
        cmd_list_actions()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
'''

# ============================================================================
# Penalty Detection Hook (UserPromptSubmit)
# ============================================================================
PENALTY_HOOK = '''#!/usr/bin/env python3
"""
Penalty Detection Hook: Applies negative reinforcement for violations
Detects: Hallucination patterns, workflow shortcuts, claim without evidence
"""
import sys
import json
import subprocess
from pathlib import Path

MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
CONFIDENCE_CMD = Path(__file__).resolve().parent.parent.parent / "scripts" / "ops" / "confidence.py"

def apply_penalty(action_key, reason):
    """Apply confidence penalty"""
    try:
        subprocess.run(
            ["python3", str(CONFIDENCE_CMD), "loss", action_key, reason],
            capture_output=True,
            timeout=5
        )
    except:
        pass  # Silent failure

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

# Detect hallucination patterns
hallucination_triggers = [
    ("i know how", "claim_knowledge", "Claimed 'I know how' without evidence"),
    ("this should work", "claim_knowledge", "Claimed 'this should work' without verification"),
    ("i'll just", "propose_without_context", "Proposed action without gathering context"),
    ("let me write", "propose_without_context", "Proposed writing without reading"),
]

# Detect workflow violations
workflow_triggers = [
    ("done", "claim_done_no_tests", "Claimed done (check if tests were run)"),
]

penalties_applied = []

for trigger, action_key, reason in hallucination_triggers:
    if trigger in prompt_lower:
        apply_penalty(action_key, reason)
        penalties_applied.append(f"📉 {reason}")

# Build warning if penalties applied
if penalties_applied:
    penalty_text = "\\n".join(penalties_applied)
    additional_context = f"""
⚠️ REINFORCEMENT PROTOCOL: CONFIDENCE PENALTY APPLIED

{penalty_text}

DETECTED PATTERN: Hallucination or workflow violation
IMPACT: Confidence reduced (may block production access)

REMEDY:
  • Gather evidence before claiming knowledge
  • Use investigation tools (/research, /probe, /verify)
  • Read existing code before proposing changes
  • Run verification after claiming completion

Check status: python3 scripts/ops/confidence.py status
"""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context
        }
    }))
else:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ""
        }
    }))

sys.exit(0)
'''

# ============================================================================
# Reward Detection Hook (PostToolUse)
# ============================================================================
REWARD_HOOK = '''#!/usr/bin/env python3
"""
Reward Detection Hook: Applies positive reinforcement for good practices
Detects: Agent usage, protocol execution, verification
"""
import sys
import json
import subprocess
from pathlib import Path

CONFIDENCE_CMD = Path(__file__).resolve().parent.parent.parent / "scripts" / "ops" / "confidence.py"

def apply_reward(action_key, reason):
    """Apply confidence reward"""
    try:
        subprocess.run(
            ["python3", str(CONFIDENCE_CMD), "gain", action_key, reason],
            capture_output=True,
            timeout=5
        )
    except:
        pass  # Silent failure

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ""
        }
    }))
    sys.exit(0)

tool_name = input_data.get("toolName", "")
tool_params = input_data.get("toolParams", {})

# Detect Read operations
if tool_name == "Read":
    file_path = tool_params.get("file_path", "")
    if file_path:
        apply_reward("read_file", f"Read {Path(file_path).name}")

# Detect Bash commands (protocol execution)
if tool_name == "Bash":
    command = tool_params.get("command", "")

    # Detect protocol scripts
    if "scripts/ops/verify.py" in command:
        apply_reward("verify", "Ran verification")
    elif "scripts/ops/audit.py" in command:
        apply_reward("run_audit", "Ran audit.py")
    elif "scripts/ops/void.py" in command:
        apply_reward("run_void", "Ran void.py")
    elif "scripts/ops/drift_check.py" in command:
        apply_reward("run_drift", "Ran drift_check.py")
    elif "scripts/ops/research.py" in command:
        apply_reward("research_manual", "Used research.py")
    elif "scripts/ops/probe.py" in command:
        apply_reward("probe", "Used probe.py")
    elif "scripts/ops/council.py" in command:
        apply_reward("use_council", "Consulted council")
    elif "scripts/ops/critic.py" in command:
        apply_reward("use_critic", "Consulted critic")
    elif "pytest" in command or "python -m pytest" in command:
        apply_reward("run_tests", "Ran test suite")

# Detect Task tool (agent delegation)
if tool_name == "Task":
    subagent_type = tool_params.get("subagent_type", "")

    if subagent_type == "researcher":
        apply_reward("use_researcher", "Delegated to researcher agent")
    elif subagent_type == "script-smith":
        apply_reward("use_script_smith", "Delegated to script-smith agent")
    elif subagent_type == "sherlock":
        apply_reward("use_sherlock", "Delegated to sherlock agent")

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": ""
    }
}))
sys.exit(0)
'''

# ============================================================================
# Generate files
# ============================================================================
def main():
    print("🎮 Generating Reinforcement Layer for Epistemological Protocol...")

    # 1. Replace confidence.py with enhanced version
    confidence_file = PROJECT_ROOT / "scripts" / "ops" / "confidence.py"
    with open(confidence_file, 'w') as f:
        f.write(ENHANCED_CONFIDENCE_SCRIPT)
    os.chmod(confidence_file, 0o755)
    print(f"✅ Enhanced: {confidence_file}")

    # 2. Create penalty detection hook
    penalty_file = HOOKS_DIR / "detect_confidence_penalty.py"
    with open(penalty_file, 'w') as f:
        f.write(PENALTY_HOOK)
    os.chmod(penalty_file, 0o755)
    print(f"✅ Created: {penalty_file}")

    # 3. Create reward detection hook
    reward_file = HOOKS_DIR / "detect_confidence_reward.py"
    with open(reward_file, 'w') as f:
        f.write(REWARD_HOOK)
    os.chmod(reward_file, 0o755)
    print(f"✅ Created: {reward_file}")

    print("\n📋 NEXT STEPS:")
    print("1. Add hooks to .claude/settings.json:")
    print("   UserPromptSubmit: detect_confidence_penalty.py")
    print("   PostToolUse: detect_confidence_reward.py")
    print("2. Test: python3 scripts/ops/confidence.py list")
    print("3. Test: python3 scripts/ops/confidence.py status")

if __name__ == "__main__":
    main()
