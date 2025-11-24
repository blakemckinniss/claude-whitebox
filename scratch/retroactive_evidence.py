#!/usr/bin/env python3
"""
Retroactive Evidence Parser
===========================
Parses session transcript to rebuild evidence ledger when PostToolUse hooks fail.

Purpose: Fix confidence tracking when hooks don't fire for Read operations.
Problem: PostToolUse hooks don't fire for Read during live conversation.
Solution: Parse transcript JSONL, count tool uses, update session state.

Usage: python3 scratch/retroactive_evidence.py [session_id]
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import (
    load_session_state,
    save_session_state,
    initialize_session_state,
    get_session_state_file,
    get_confidence_tier,
    CONFIDENCE_GAINS,
)


def find_transcript(session_id):
    """Find transcript file for session by matching session_id"""
    # Check common locations
    project_dir = Path(__file__).resolve().parent.parent

    # Try .claude/projects/<uuid>/transcript.jsonl
    projects_dir = project_dir / ".claude" / "projects"
    if projects_dir.exists():
        try:
            for project in projects_dir.iterdir():
                if project.is_dir():
                    for transcript in project.glob("*.jsonl"):
                        # Check if session_id matches in transcript content
                        if session_matches_transcript(transcript, session_id):
                            return transcript
        except PermissionError:
            pass  # Skip directories we can't read

    # Try home directory
    home_projects = Path.home() / ".claude" / "projects"
    if home_projects.exists():
        try:
            for project in home_projects.iterdir():
                if project.is_dir():
                    # Get transcripts and check for session match
                    for transcript in project.glob("*.jsonl"):
                        if session_matches_transcript(transcript, session_id):
                            return transcript
        except PermissionError:
            pass  # Skip directories we can't read

    # Fallback: Get most recent transcript if no match found
    # (for "unknown" session or partial session IDs)
    if home_projects and home_projects.exists():
        for project in home_projects.iterdir():
            if project.is_dir():
                transcripts = sorted(project.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
                if transcripts:
                    return transcripts[0]

    return None


def session_matches_transcript(transcript_path, session_id):
    """Check if transcript belongs to the given session"""
    try:
        with open(transcript_path) as f:
            # Read first few lines to check session ID
            for i, line in enumerate(f):
                if i > 10:  # Only check first 10 lines
                    break
                try:
                    entry = json.loads(line)
                    if entry.get("sessionId") == session_id:
                        return True
                    # Also match partial session IDs (for "unknown")
                    if session_id in entry.get("sessionId", ""):
                        return True
                except json.JSONDecodeError:
                    continue
    except (FileNotFoundError, PermissionError):
        pass
    return False


def parse_transcript(transcript_path):
    """
    Parse transcript JSONL to extract tool uses

    Returns:
        Tuple of (tool_uses, stats)
        - tool_uses: List of tool use events: [(turn, tool_name, tool_input), ...]
        - stats: Dict with parsing statistics
    """
    tool_uses = []
    turn = 0
    stats = {
        "total_lines": 0,
        "skipped_lines": 0,
        "corrupt_lines": [],
        "user_turns": 0,
        "assistant_turns": 0,
    }

    try:
        with open(transcript_path) as f:
            for line_num, line in enumerate(f, 1):
                stats["total_lines"] += 1

                if not line.strip():
                    continue

                try:
                    entry = json.loads(line)

                    # Check for user messages (increment turn)
                    if entry.get("type") == "user":
                        turn += 1
                        stats["user_turns"] += 1

                    # Check for assistant messages with content
                    if entry.get("type") == "assistant":
                        stats["assistant_turns"] += 1
                        message = entry.get("message", {})
                        content = message.get("content", [])

                        # Look for tool_use blocks in content array
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "tool_use":
                                    tool_name = block.get("name", "")
                                    tool_input = block.get("input", {})

                                    if tool_name:
                                        tool_uses.append((turn, tool_name, tool_input))

                except json.JSONDecodeError as e:
                    stats["skipped_lines"] += 1
                    stats["corrupt_lines"].append(line_num)
                    continue  # Skip malformed lines

    except (FileNotFoundError, PermissionError) as e:
        raise Exception(f"Cannot read transcript: {e}")
    except Exception as e:
        raise Exception(f"Failed to parse transcript: {e}")

    return tool_uses, stats


def calculate_confidence(tool_uses):
    """
    Calculate confidence based on tool usage with diminishing returns

    Returns:
        Tuple of (total_confidence, evidence_ledger, read_files_map)
    """
    confidence = 0
    evidence_ledger = []
    read_files = defaultdict(int)

    for turn, tool_name, tool_input in tool_uses:
        boost = 0
        target = ""

        # Process by tool type
        if tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            target = file_path

            # Diminishing returns for repeated reads
            if file_path in read_files:
                boost = CONFIDENCE_GAINS["read_file_repeat"]
            else:
                boost = CONFIDENCE_GAINS["read_file_first"]

            read_files[file_path] += 1

        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            target = command[:100]

            # Detect specific commands
            if "scripts/ops/verify.py" in command or "/verify " in command:
                boost = CONFIDENCE_GAINS["verify_success"]
            elif "scripts/ops/research.py" in command or "/research" in command:
                boost = CONFIDENCE_GAINS["web_search"]
            elif "scripts/ops/probe.py" in command or "/probe" in command:
                boost = CONFIDENCE_GAINS["probe_api"]
            elif "scripts/ops/audit.py" in command:
                boost = CONFIDENCE_GAINS["run_audit"]
            elif "pytest" in command or "python -m pytest" in command:
                boost = CONFIDENCE_GAINS["run_tests"]
            elif "scripts/ops/council.py" in command or "scripts/ops/balanced_council.py" in command:
                boost = CONFIDENCE_GAINS["use_council"]
            else:
                boost = CONFIDENCE_GAINS["use_script"]

        elif tool_name == "Task":
            subagent_type = tool_input.get("subagent_type", "")
            target = subagent_type

            if subagent_type == "researcher":
                boost = CONFIDENCE_GAINS["use_researcher"]
            elif subagent_type == "script-smith":
                boost = CONFIDENCE_GAINS["use_script_smith"]
            else:
                boost = 10  # Generic delegation

        elif tool_name in ["Grep", "Glob"]:
            pattern = tool_input.get("pattern", "")
            target = pattern
            boost = CONFIDENCE_GAINS["grep_glob"]

        elif tool_name == "WebSearch":
            query = tool_input.get("query", "")
            target = query
            boost = CONFIDENCE_GAINS["web_search"]

        # Update confidence (cap at 100)
        confidence = min(100, confidence + boost)

        # Record evidence
        if boost > 0:
            evidence_ledger.append({
                "turn": turn,
                "tool": tool_name,
                "target": target,
                "boost": boost,
                "timestamp": datetime.now().isoformat(),
            })

    return confidence, evidence_ledger, dict(read_files)


def update_session_state(session_id, confidence, evidence_ledger, read_files):
    """Update session state with retroactive evidence (with backup)"""
    state = load_session_state(session_id)
    if not state:
        state = initialize_session_state(session_id)

    # Store old confidence for comparison
    old_confidence = state["confidence"]

    # BACKUP: Save current state before destructive update
    state_file = get_session_state_file(session_id)
    backup_file = state_file.parent / f"{state_file.stem}.backup.json"

    try:
        with open(backup_file, 'w') as f:
            json.dump(state, f, indent=2)
        print(f"💾 Backup created: {backup_file.name}")
    except Exception as e:
        print(f"⚠️  Warning: Could not create backup - {e}")
        # Continue anyway - backup failure shouldn't block update

    # Update state
    state["confidence"] = confidence
    state["evidence_ledger"] = evidence_ledger
    state["read_files"] = read_files

    # Add confidence history entry
    state["confidence_history"].append({
        "turn": state["turn_count"],
        "confidence": confidence,
        "reason": "retroactive_evidence_parsing",
        "timestamp": datetime.now().isoformat(),
    })

    # Save state
    save_session_state(session_id, state)

    return old_confidence, confidence


def main():
    # Get session ID from args or use 'unknown'
    session_id = sys.argv[1] if len(sys.argv) > 1 else "unknown"

    print(f"🔍 RETROACTIVE EVIDENCE PARSER")
    print(f"Session ID: {session_id}")
    print()

    # Find transcript
    print("📂 Locating transcript...")
    transcript_path = find_transcript(session_id)

    if not transcript_path:
        print("❌ ERROR: Could not find transcript file")
        print("\nSearched locations:")
        print("  - .claude/projects/*/")
        print("  - ~/.claude/projects/*/")
        sys.exit(1)

    print(f"✅ Found: {transcript_path}")
    print()

    # Parse transcript
    print("📖 Parsing transcript for tool uses...")
    try:
        tool_uses, stats = parse_transcript(transcript_path)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)

    # Show parsing statistics
    print(f"📊 Transcript Statistics:")
    print(f"   Total lines: {stats['total_lines']}")
    print(f"   User turns: {stats['user_turns']}")
    print(f"   Assistant turns: {stats['assistant_turns']}")

    if stats['skipped_lines'] > 0:
        print(f"   ⚠️  Skipped corrupt lines: {stats['skipped_lines']}")
        if len(stats['corrupt_lines']) <= 10:
            print(f"      Line numbers: {stats['corrupt_lines']}")
        else:
            print(f"      Line numbers: {stats['corrupt_lines'][:10]}... (+{len(stats['corrupt_lines']) - 10} more)")

    if not tool_uses:
        print("⚠️  WARNING: No tool uses found in transcript")
        sys.exit(0)

    print(f"✅ Found {len(tool_uses)} tool uses")
    print()

    # Calculate confidence
    print("🧮 Calculating confidence from evidence...")
    confidence, evidence_ledger, read_files = calculate_confidence(tool_uses)

    print(f"✅ Calculated confidence: {confidence}%")
    print(f"   - Evidence entries: {len(evidence_ledger)}")
    print(f"   - Unique files read: {len(read_files)}")
    print()

    # Show breakdown by tool type
    print("📊 Evidence Breakdown:")
    tool_counts = defaultdict(int)
    tool_boosts = defaultdict(int)

    for entry in evidence_ledger:
        tool_counts[entry["tool"]] += 1
        tool_boosts[entry["tool"]] += entry["boost"]

    for tool in sorted(tool_counts.keys()):
        count = tool_counts[tool]
        total_boost = tool_boosts[tool]
        print(f"   {tool:12s}: {count:3d} uses → +{total_boost}%")

    print()

    # Update session state
    print("💾 Updating session state...")
    old_confidence, new_confidence = update_session_state(
        session_id, confidence, evidence_ledger, read_files
    )

    old_tier, _ = get_confidence_tier(old_confidence)
    new_tier, tier_desc = get_confidence_tier(new_confidence)

    print(f"✅ Session state updated")
    print()
    print(f"📈 CONFIDENCE UPDATE:")
    print(f"   Before: {old_confidence}% ({old_tier})")
    print(f"   After:  {new_confidence}% ({new_tier})")
    print(f"   Change: +{new_confidence - old_confidence}%")
    print()
    print(f"🎯 Current Tier: {new_tier}")
    print(f"   {tier_desc}")
    print()

    # Show capabilities unlocked
    if new_tier == "HYPOTHESIS":
        print("✅ UNLOCKED: Can write to scratch/")
    elif new_tier == "CERTAINTY":
        print("✅ UNLOCKED: Full capabilities (production code, commits)")

    print()
    print("🎉 Retroactive evidence parsing complete!")


if __name__ == "__main__":
    main()
