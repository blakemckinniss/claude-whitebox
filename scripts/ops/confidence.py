#!/usr/bin/env python3
"""
Confidence Tracker - Session-based Epistemological Protocol
Commands: status, session <id>, list
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
STATE_FILE = MEMORY_DIR / "confidence_state.json"  # Legacy global state

# Add scripts/lib to path
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from lib.epistemology import (
    load_session_state,
    get_confidence_tier,
    get_risk_level,
)

def get_latest_session():
    """Find the most recent session state file"""
    session_files = list(MEMORY_DIR.glob("session_*_state.json"))
    if not session_files:
        return None

    # Sort by modification time, most recent first
    latest = max(session_files, key=lambda p: p.stat().st_mtime)
    session_id = latest.stem.replace("session_", "").replace("_state", "")
    return session_id


def cmd_status(session_id=None):
    """Show current confidence level for a session"""
    # If no session specified, use latest
    if not session_id:
        session_id = get_latest_session()
        if not session_id:
            print("❌ No active sessions found")
            print("   Sessions are created automatically when you interact with Claude")
            return

    state = load_session_state(session_id)
    if not state:
        print(f"❌ Session not found: {session_id}")
        return

    confidence = state.get("confidence", 0)
    risk = state.get("risk", 0)
    tokens = state.get("tokens_estimated", 0)
    token_pct = state.get("context_window_percent", 0)
    turn = state.get("turn_count", 0)

    # Get tier and risk level
    tier_name, tier_desc = get_confidence_tier(confidence)
    risk_level, risk_desc = get_risk_level(risk)

    # Determine tier icon
    if confidence < 31:
        tier_icon = "🔴"
    elif confidence < 71:
        tier_icon = "🟡"
    else:
        tier_icon = "🟢"

    # Risk icon
    if risk == 0:
        risk_icon = "🟢"
    elif risk < 50:
        risk_icon = "🟡"
    elif risk < 100:
        risk_icon = "🟠"
    else:
        risk_icon = "🔴"

    # Token icon
    if token_pct < 30:
        token_icon = "🟢"
    elif token_pct < 60:
        token_icon = "🟡"
    else:
        token_icon = "🔴"

    print("\n📊 EPISTEMOLOGICAL PROTOCOL STATUS\n")
    print(f"Session ID: {session_id[:16]}...")
    print(f"Turn: {turn}")
    print(f"Initialized: {state.get('initialized_at', 'Unknown')}\n")

    print(f"{tier_icon} Confidence: {confidence}%")
    print(f"   Tier: {tier_name}")
    print(f"   {tier_desc}\n")

    print(f"{risk_icon} Risk: {risk}%")
    print(f"   Level: {risk_level}")
    print(f"   {risk_desc}\n")

    print(f"{token_icon} Tokens: {token_pct}% ({tokens:,} / 200,000)")
    if token_pct >= 30 and confidence < 50:
        print("   ⚠️  WARNING: High token usage with low confidence")
        print("   Consider council consultation for context validation")

    # Evidence stats
    evidence_ledger = state.get("evidence_ledger", [])
    read_files = state.get("read_files", {})

    print("\n📚 Evidence Gathered:")
    print(f"   Files Read: {len(read_files)}")
    print(f"   Total Evidence Items: {len(evidence_ledger)}")

    if evidence_ledger:
        print("\n   Recent Evidence (Last 5):")
        for entry in evidence_ledger[-5:]:
            tool = entry.get("tool", "Unknown")
            boost = entry.get("boost", 0)
            target = entry.get("target", "")
            icon = "📈" if boost > 0 else "📉" if boost < 0 else "📊"
            sign = "+" if boost >= 0 else ""
            target_str = f" → {target[:40]}" if target else ""
            print(f"   {icon} {tool}{target_str}: {sign}{boost}%")

    # Risk events
    risk_events = state.get("risk_events", [])
    if risk_events:
        print("\n⚠️  Risk Events:")
        for event in risk_events[-3:]:
            turn_num = event.get("turn", "?")
            amount = event.get("amount", 0)
            reason = event.get("reason", "Unknown")
            print(f"   Turn {turn_num}: +{amount}% - {reason[:60]}")

    print("\n🎯 Next Threshold:")
    if confidence < 31:
        needed = 31 - confidence
        print(f"   Need +{needed}% to reach HYPOTHESIS tier (scratch/ allowed)")
        print("   💡 Tip: Read files (+10%), Research (+20%), Probe (+15%)")
    elif confidence < 71:
        needed = 71 - confidence
        print(f"   Need +{needed}% to reach CERTAINTY tier (production allowed)")
        print("   💡 Tip: Run verification (+15%) to unlock production")
    else:
        print("   ✅ All tiers unlocked - Production code allowed")
        print("   ⚠️  Confidence can still drop from violations")

    print()


def cmd_list_sessions():
    """List all available sessions"""
    session_files = list(MEMORY_DIR.glob("session_*_state.json"))

    if not session_files:
        print("❌ No sessions found")
        return

    print(f"\n📂 Available Sessions ({len(session_files)} total):\n")

    # Sort by modification time, most recent first
    session_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for i, session_file in enumerate(session_files[:10], 1):  # Show last 10
        session_id = session_file.stem.replace("session_", "").replace("_state", "")
        state = load_session_state(session_id)

        if state:
            confidence = state.get("confidence", 0)
            risk = state.get("risk", 0)
            turn = state.get("turn_count", 0)
            initialized = state.get("initialized_at", "Unknown")[:10]  # Just date

            tier_icon = "🔴" if confidence < 31 else "🟡" if confidence < 71 else "🟢"
            risk_icon = "🟢" if risk == 0 else "🟡" if risk < 50 else "🔴"

            print(
                f"{i:2d}. {session_id[:16]}... [{initialized}] T:{turn:3d} {tier_icon}{confidence:3d}% {risk_icon}R:{risk:3d}%"
            )

    if len(session_files) > 10:
        print(f"\n   ... and {len(session_files) - 10} more sessions")

    print("\nUse: /confidence session <id> to view specific session")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 scripts/ops/confidence.py status         # Show latest session")
        print("  python3 scripts/ops/confidence.py session <id>   # Show specific session")
        print("  python3 scripts/ops/confidence.py list           # List all sessions")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "status":
        cmd_status()
    elif cmd == "session":
        if len(sys.argv) < 3:
            print("Usage: confidence.py session <session_id>")
            sys.exit(1)
        session_id = sys.argv[2]
        cmd_status(session_id)
    elif cmd == "list":
        cmd_list_sessions()
    else:
        print(f"Unknown command: {cmd}")
        print("Available: status, session <id>, list")
        sys.exit(1)
