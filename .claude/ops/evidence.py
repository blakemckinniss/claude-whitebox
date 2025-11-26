#!/usr/bin/env python3
"""
Evidence Ledger Viewer - Review evidence gathered during sessions
Commands: review, session <id>
"""
import sys
from pathlib import Path


# Find project root
def find_project_root():
    """Walk up directory tree to find project root"""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        marker = current / ".claude" / "lib" / "core.py"
        if marker.exists():
            return current
        current = current.parent
    raise RuntimeError("Cannot find project root (.claude/lib/core.py not found)")


PROJECT_ROOT = find_project_root()
MEMORY_DIR = PROJECT_ROOT / ".claude" / "memory"

# Add .claude/lib to path
sys.path.insert(0, str(PROJECT_ROOT / ".claude"))

from lib.epistemology import load_session_state, get_confidence_tier  # noqa: E402


def get_latest_session():
    """Find the most recent session state file"""
    session_files = list(MEMORY_DIR.glob("session_*_state.json"))
    if not session_files:
        return None

    # Sort by modification time, most recent first
    latest = max(session_files, key=lambda p: p.stat().st_mtime)
    session_id = latest.stem.replace("session_", "").replace("_state", "")
    return session_id


def cmd_review(session_id=None):
    """Review evidence ledger for a session"""
    # If no session specified, use latest
    if not session_id:
        session_id = get_latest_session()
        if not session_id:
            print("❌ No active sessions found")
            return

    state = load_session_state(session_id)
    if not state:
        print(f"❌ Session not found: {session_id}")
        return

    evidence_ledger = state.get("evidence_ledger", [])
    confidence = state.get("confidence", 0)
    tier_name, tier_desc = get_confidence_tier(confidence)

    print("\n📚 EVIDENCE LEDGER REVIEW\n")
    print(f"Session ID: {session_id[:16]}...")
    print(f"Current Confidence: {confidence}% ({tier_name})")
    print(f"Total Evidence Items: {len(evidence_ledger)}\n")

    if not evidence_ledger:
        print("   No evidence gathered yet in this session")
        print()
        return

    # Group evidence by type
    evidence_by_tool = {}
    for entry in evidence_ledger:
        tool = entry.get("tool", "Unknown")
        if tool not in evidence_by_tool:
            evidence_by_tool[tool] = []
        evidence_by_tool[tool].append(entry)

    # Show summary by tool type
    print("📊 Evidence Summary by Tool:\n")
    for tool, entries in sorted(evidence_by_tool.items()):
        total_boost = sum(e.get("boost", 0) for e in entries)
        count = len(entries)
        avg_boost = total_boost / count if count > 0 else 0
        icon = "📈" if total_boost > 0 else "📉" if total_boost < 0 else "📊"
        sign = "+" if total_boost >= 0 else ""
        print(f"   {icon} {tool:15s} {count:3d} items  {sign}{total_boost:4d}%  (avg: {sign}{avg_boost:.1f}%)")

    # Show detailed chronological evidence
    print("\n📜 Chronological Evidence (Last 20):\n")
    for i, entry in enumerate(evidence_ledger[-20:], 1):
        turn = entry.get("turn", "?")
        tool = entry.get("tool", "Unknown")
        boost = entry.get("boost", 0)
        target = entry.get("target", "")
        reason = entry.get("reason", "")

        icon = "📈" if boost > 0 else "📉" if boost < 0 else "📊"
        sign = "+" if boost >= 0 else ""

        # Format target (truncate if too long)
        target_str = f" → {target[:50]}" if target else ""
        if target and len(target) > 50:
            target_str += "..."

        print(f"{i:2d}. Turn {turn:3d} | {icon} {tool:10s} {sign}{boost:3d}% {target_str}")
        if reason and reason != f"{tool} usage":
            print(f"              └─ {reason[:70]}")

    print()

    # Show file reading stats
    read_files = state.get("read_files", {})
    if read_files:
        print(f"📖 Files Read ({len(read_files)} unique):\n")
        # Sort by read count (value)
        sorted_files = sorted(read_files.items(), key=lambda x: x[1], reverse=True)
        for file_path, read_count in sorted_files[:10]:
            # Diminishing returns indicator
            if read_count == 1:
                indicator = "✅ Fresh"
            elif read_count < 3:
                indicator = "🔄 Re-read"
            else:
                indicator = f"♻️  Re-read {read_count}x (diminishing returns)"

            file_name = file_path.split("/")[-1] if "/" in file_path else file_path
            print(f"   {indicator:30s} {file_name}")

        if len(read_files) > 10:
            print(f"\n   ... and {len(read_files) - 10} more files")

    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 .claude/ops/evidence.py review           # Review latest session")
        print("  python3 .claude/ops/evidence.py session <id>     # Review specific session")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "review":
        cmd_review()
    elif cmd == "session":
        if len(sys.argv) < 3:
            print("Usage: evidence.py session <session_id>")
            sys.exit(1)
        session_id = sys.argv[2]
        cmd_review(session_id)
    else:
        print(f"Unknown command: {cmd}")
        print("Available: review, session <id>")
        sys.exit(1)
