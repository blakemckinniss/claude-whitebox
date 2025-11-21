#!/usr/bin/env python3
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

    print(f"\n📉 EPISTEMOLOGICAL PROTOCOL STATUS\n")
    print(f"{tier_icon} Current Confidence: {confidence}%")
    print(f"   Tier: {tier_emoji} {tier}")
    print(f"   Last Reset: {state['last_reset']}")

    # Reinforcement stats
    total_gains = state.get("total_gains", 0)
    total_losses = state.get("total_losses", 0)
    net = total_gains - total_losses

    print(f"\n📊 Reinforcement Stats:")
    print(f"   Total Gains: +{total_gains}%")
    print(f"   Total Losses: -{total_losses}%")
    print(f"   Net Score: {'+'if net >= 0 else ''}{net}%")

    if state['reinforcement_log']:
        print(f"\n📚 Recent Activity (Last 5):")
        for entry in state['reinforcement_log'][-5:]:
            action_type = entry.get('type', 'gain')
            value = entry.get('gain', entry.get('loss', 0))
            icon = "📈" if action_type == "gain" else "📉"
            sign = "+" if action_type == "gain" else "-"
            print(f"   {icon} {entry['action']}: {sign}{value}% - {entry['description']}")

    print(f"\n🎯 Next Threshold:")
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
    print("\n📈 POSITIVE REINFORCEMENT ACTIONS:\n")
    for key, data in sorted(GAINS.items()):
        print(f"  {key:25s} +{data['gain']:2d}%  {data['desc']}")

    print("\n📉 NEGATIVE REINFORCEMENT ACTIONS:\n")
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
