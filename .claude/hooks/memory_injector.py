#!/usr/bin/env python3
"""
Memory Injector Hook v3: Auto-surface relevant memories on every prompt.

Hook Type: UserPromptSubmit
Latency Target: <50ms

Automatically surfaces:
- Relevant lessons from lessons.md
- Spark associations (protocols, patterns, tools)
- Active DoD/scope status
- Recent decisions if relevant

THE INSIGHT: Memory should be ambient, not invoked.
When you think about "WebSocket", the heartbeat lesson should appear.
"""

import sys
import json
import re
from pathlib import Path

# Import synapse core for spark integration
from synapse_core import (
    run_spark,
    MAX_ASSOCIATIONS,
    MAX_MEMORIES,
)

# =============================================================================
# PATHS
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # .claude/hooks -> .claude -> root
MEMORY_DIR = PROJECT_ROOT / ".claude" / "memory"

LESSONS_FILE = MEMORY_DIR / "lessons.md"
DECISIONS_FILE = MEMORY_DIR / "decisions.md"
PUNCH_LIST_FILE = MEMORY_DIR / "punch_list.json"
SESSION_STATE_FILE = MEMORY_DIR / "session_state_v3.json"

# =============================================================================
# KEYWORD EXTRACTION
# =============================================================================

# Stop words to ignore
STOP_WORDS = frozenset([
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "each", "few",
    "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just",
    "and", "but", "if", "or", "because", "until", "while", "this",
    "that", "these", "those", "what", "which", "who", "whom",
    "i", "me", "my", "you", "your", "we", "our", "they", "them",
    "it", "its", "he", "she", "him", "her", "his", "hers",
])


def extract_keywords(text: str, min_length: int = 4) -> list[str]:
    """Extract meaningful keywords from text."""
    # Tokenize and normalize
    words = re.findall(r'\b[a-z_][a-z0-9_]*\b', text.lower())

    # Filter
    keywords = [
        w for w in words
        if len(w) >= min_length and w not in STOP_WORDS
    ]

    # Dedupe while preserving order
    seen = set()
    unique = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            unique.append(k)

    return unique[:15]  # Max 15 keywords


# =============================================================================
# MEMORY RETRIEVAL
# =============================================================================

def find_relevant_lessons(keywords: list[str], max_results: int = 3) -> list[str]:
    """Find lessons matching any of the keywords."""
    if not LESSONS_FILE.exists():
        return []

    matches = []
    try:
        content = LESSONS_FILE.read_text()
        lines = content.split('\n')

        for line in lines:
            # Skip headers and empty lines
            if not line.strip() or line.startswith('#'):
                continue

            line_lower = line.lower()

            # Score by keyword matches
            score = sum(1 for k in keywords if k in line_lower)
            if score > 0:
                matches.append((score, line.strip()))

        # Sort by score descending, take top N
        matches.sort(key=lambda x: -x[0])
        return [m[1] for m in matches[:max_results]]

    except Exception:
        return []


def find_relevant_decisions(keywords: list[str], max_results: int = 2) -> list[str]:
    """Find recent decisions matching keywords."""
    if not DECISIONS_FILE.exists():
        return []

    matches = []
    try:
        content = DECISIONS_FILE.read_text()
        # Split by decision entries (usually marked with dates or bullets)
        entries = re.split(r'\n(?=[-*•]|\d{4}-)', content)

        for entry in entries[-20:]:  # Only recent 20
            if not entry.strip():
                continue

            entry_lower = entry.lower()
            score = sum(1 for k in keywords if k in entry_lower)
            if score > 0:
                # Clean up entry
                clean = entry.strip()[:200]
                if len(entry) > 200:
                    clean += "..."
                matches.append((score, clean))

        matches.sort(key=lambda x: -x[0])
        return [m[1] for m in matches[:max_results]]

    except Exception:
        return []


def get_active_scope() -> dict | None:
    """Get active DoD/scope if one exists."""
    if not PUNCH_LIST_FILE.exists():
        return None

    try:
        data = json.loads(PUNCH_LIST_FILE.read_text())

        # Check if there's an active task
        task = data.get("task", "")
        items = data.get("items", [])

        if not task or not items:
            return None

        # Count completed
        completed = sum(1 for i in items if i.get("status") == "done")
        total = len(items)

        # Get next pending item
        next_item = None
        for item in items:
            if item.get("status") != "done":
                next_item = item.get("description", "")[:60]
                break

        return {
            "task": task[:50],
            "progress": f"{completed}/{total}",
            "next": next_item,
        }

    except Exception:
        return None


def get_confidence_state() -> dict | None:
    """Get current confidence/evidence state."""
    if not SESSION_STATE_FILE.exists():
        return None

    try:
        data = json.loads(SESSION_STATE_FILE.read_text())

        confidence = data.get("confidence", 0)
        evidence_count = len(data.get("evidence_ledger", []))
        files_read = len(data.get("files_read", []))
        files_edited = len(data.get("files_edited", []))

        # Only return if meaningful activity
        if evidence_count == 0 and files_read == 0:
            return None

        return {
            "confidence": confidence,
            "evidence": evidence_count,
            "files_read": files_read,
            "files_edited": files_edited,
        }

    except Exception:
        return None


# =============================================================================
# FORMAT OUTPUT
# =============================================================================

def format_memory_context(
    lessons: list,
    decisions: list,
    scope: dict,
    confidence: dict,
    spark_associations: list = None
) -> str:
    """Format all memory context for injection."""
    parts = []

    # Spark associations (protocols, patterns, tools)
    if spark_associations:
        assoc_lines = "\n".join(f"   * {a[:100]}" for a in spark_associations[:MAX_ASSOCIATIONS])
        parts.append(f"SUBCONSCIOUS RECALL:\n{assoc_lines}")

    # Lessons (most important)
    if lessons:
        lesson_lines = "\n".join(f"   * {lesson[:100]}" for lesson in lessons)
        parts.append(f"RELEVANT LESSONS:\n{lesson_lines}")

    # Active scope/DoD
    if scope:
        scope_line = f"ACTIVE TASK: {scope['task']} [{scope['progress']}]"
        if scope['next']:
            scope_line += f"\n   Next: {scope['next']}"
        parts.append(scope_line)

    # Decisions (only if highly relevant)
    if decisions and len(decisions) > 0:
        dec_lines = "\n".join(f"   * {d[:80]}" for d in decisions[:1])
        parts.append(f"RELATED DECISION:\n{dec_lines}")

    # Confidence (brief)
    if confidence and confidence["confidence"] > 0:
        parts.append(
            f"Session: {confidence['confidence']}% confidence, "
            f"{confidence['evidence']} evidence items"
        )

    return "\n\n".join(parts)


def get_spark_associations(prompt: str) -> list[str]:
    """Get associations from spark for the prompt."""
    spark_result = run_spark(prompt)
    if not spark_result:
        return []

    associations = []

    # Get protocol/pattern associations
    for assoc in spark_result.get("associations", []):
        associations.append(assoc)

    # Get memories
    for memory in spark_result.get("memories", []):
        associations.append(memory)

    return associations[:MAX_ASSOCIATIONS + MAX_MEMORIES]


# =============================================================================
# MAIN
# =============================================================================

def main():
    """UserPromptSubmit hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({}))
        sys.exit(0)

    user_prompt = input_data.get("user_prompt", "") or input_data.get("prompt", "")
    if not user_prompt or len(user_prompt) < 10:
        print(json.dumps({}))
        sys.exit(0)

    # Extract keywords from prompt
    keywords = extract_keywords(user_prompt)

    # Get spark associations (runs in parallel conceptually)
    spark_associations = get_spark_associations(user_prompt) if len(user_prompt) > 20 else []

    # Retrieve relevant memories from files
    lessons = find_relevant_lessons(keywords) if keywords else []
    decisions = find_relevant_decisions(keywords) if len(keywords) > 2 else []
    scope = get_active_scope()
    confidence = get_confidence_state()

    # Only inject if we found something useful
    if not lessons and not scope and not decisions and not spark_associations:
        print(json.dumps({}))
        sys.exit(0)

    # Format output
    context = format_memory_context(
        lessons, decisions, scope, confidence, spark_associations
    )

    if context:
        output = {"additionalContext": context}
    else:
        output = {}

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
