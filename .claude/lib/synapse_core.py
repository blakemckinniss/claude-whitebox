#!/usr/bin/env python3
"""
Synapse Core v3: Shared utilities for the directive injection system.

THE CORE INSIGHT:
A single well-timed directive saves more time than 100 informative contexts.
"Lesson: WebSockets need heartbeat" (ignored) vs
"STOP. Add heartbeat NOW. You forgot 3x before." (acts immediately)

This module provides:
- Directive system (strengths, formatting)
- Association scoring and budgeting
- Historical pattern detection
- Error pattern detection
- Transcript analysis utilities
"""

import json
import os
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# =============================================================================
# CONSTANTS
# =============================================================================

MAX_CONTEXT_TOKENS = 800
MAX_ASSOCIATIONS = 4
MAX_MEMORIES = 2
MAX_DIRECTIVES = 3

CACHE_TTL = 300  # 5 minutes
UPKEEP_TURN_THRESHOLD = 20
VERIFY_TURN_THRESHOLD = 3

# =============================================================================
# DIRECTIVE SYSTEM
# =============================================================================


class DirectiveStrength(Enum):
    INFO = 1
    WARN = 2
    BLOCK = 3
    HARD_BLOCK = 4


@dataclass
class Directive:
    strength: DirectiveStrength
    category: str
    message: str
    time_saved: str = ""

    def format(self) -> str:
        icons = {
            DirectiveStrength.INFO: "i",
            DirectiveStrength.WARN: "!",
            DirectiveStrength.BLOCK: "STOP",
            DirectiveStrength.HARD_BLOCK: "BLOCKED",
        }
        icon = icons.get(self.strength, "!")
        lines = [f"[{icon}] [{self.category.upper()}]", self.message]
        if self.time_saved:
            lines.append(f"Saves: {self.time_saved}")
        return "\n".join(lines)


def format_directives(directives: List[Directive]) -> str:
    """Format multiple directives for output."""
    if not directives:
        return ""
    lines = ["ASSERTIVE DIRECTIVES:"]
    for d in directives:
        lines.append("")
        lines.append(d.format())
    return "\n".join(lines)


# =============================================================================
# HISTORICAL PATTERNS (Trauma Injection)
# =============================================================================

HISTORICAL_PATTERNS: Dict[str, Dict] = {
    r"websocket|socket\.io|realtime|ws://": {
        "count": 3,
        "message": "**HISTORICAL:** You forgot heartbeat/ping 3x before.\n"
                   "Add keepalive with 30s interval. Connections die silently without it.",
        "time_saved": "~2 hours"
    },
    r"mock|unittest\.mock|@patch": {
        "count": 2,
        "message": "**HISTORICAL:** Over-mocking broke tests 2x.\n"
                   "Mock at BOUNDARIES only (APIs, DB, filesystem).",
        "time_saved": "~1 hour"
    },
    r"async.*except|try.*await|asyncio": {
        "count": 2,
        "message": "**HISTORICAL:** Async error handling forgotten 2x.\n"
                   "Wrap await calls in try/except.",
        "time_saved": "~30 min"
    },
    r"subprocess|os\.system|shell=True": {
        "count": 2,
        "message": "**HISTORICAL:** Shell injection risk.\n"
                   "Use shell=False with list args. Sanitize all user input.",
        "time_saved": "security"
    },
    r"\.env|environ|getenv.*api.*key": {
        "count": 1,
        "message": "**REMINDER:** Check .env.example exists and secrets aren't committed.",
        "time_saved": "~15 min"
    },
}


def check_historical_patterns(text: str) -> List[Directive]:
    """Check text against historical patterns, return directives."""
    directives = []
    text_lower = text.lower()

    for pattern, data in HISTORICAL_PATTERNS.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            directives.append(Directive(
                strength=DirectiveStrength.WARN,
                category="historical",
                message=data["message"],
                time_saved=data["time_saved"]
            ))

    return directives


# =============================================================================
# ERROR DETECTION
# =============================================================================

ERROR_PATTERNS = [
    (r"TypeError.*'(\w+)'.*'(\w+)'", "type_error", 0.9, ["TypeError", "type"]),
    (r"KeyError:\s*['\"]?(\w+)", "key_error", 0.9, ["KeyError", "dict"]),
    (r"AttributeError.*'(\w+)'.*'(\w+)'", "attribute_error", 0.85, ["AttributeError"]),
    (r"ModuleNotFoundError.*'(\w+)'", "import_error", 0.95, ["ImportError", "install"]),
    (r"FileNotFoundError", "file_error", 0.9, ["FileNotFoundError", "path"]),
    (r"SyntaxError", "syntax_error", 0.95, ["SyntaxError"]),
    (r"FAILED.*::", "test_failure", 0.9, ["test", "pytest"]),
    (r"Traceback \(most recent call last\)", "traceback", 0.7, ["error", "traceback"]),
    (r"AssertionError", "assertion_error", 0.9, ["assert", "test"]),
    (r"PermissionError|EACCES", "permission_error", 0.9, ["permission", "access"]),
    (r"ConnectionError|ConnectionRefused", "connection_error", 0.85, ["connection", "network"]),
]


def detect_errors(text: str) -> List[Tuple[str, float, List[str]]]:
    """Detect errors in text, return (type, priority, keywords)."""
    if not text:
        return []

    detected = []
    for pattern, error_type, priority, keywords in ERROR_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            detected.append((error_type, priority, keywords))

    return sorted(detected, key=lambda x: -x[1])


# =============================================================================
# ASSOCIATION SCORING & BUDGETING
# =============================================================================


@dataclass
class ScoredAssociation:
    text: str
    score: float
    category: str
    source: str
    tokens_estimate: int

    def __lt__(self, other):
        return self.score > other.score


def estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars per token)."""
    return len(text) // 4


def score_association(text: str, source: str, match_strength: float = 0.5) -> float:
    """Score an association by relevance."""
    source_scores = {
        "error": 0.9,
        "pattern": 0.7,
        "memory": 0.5,
        "constraint": 0.3
    }
    base = source_scores.get(source, 0.5)

    # Boost for actionable keywords
    boost = 0.0
    if any(kw in text for kw in ["Tool:", "Pattern:", "Action:", "DANGER:", "Protocol:"]):
        boost += 0.1
    if "Lesson:" in text:
        boost += 0.1
    if "STOP" in text or "BLOCK" in text:
        boost += 0.15

    return min(1.0, (base + boost) * match_strength)


def budget_associations(
    associations: List[ScoredAssociation],
    max_tokens: int = MAX_CONTEXT_TOKENS
) -> List[ScoredAssociation]:
    """Select associations within token budget."""
    sorted_assocs = sorted(associations)
    selected = []
    used_tokens = 0
    category_counts: Dict[str, int] = {}

    for assoc in sorted_assocs:
        if used_tokens + assoc.tokens_estimate > max_tokens:
            continue
        if category_counts.get(assoc.category, 0) >= 3:
            continue

        selected.append(assoc)
        used_tokens += assoc.tokens_estimate
        category_counts[assoc.category] = category_counts.get(assoc.category, 0) + 1

        if len(selected) >= MAX_ASSOCIATIONS + MAX_MEMORIES + 1:
            break

    return selected


# =============================================================================
# SPARK INTEGRATION
# =============================================================================

# Spark result cache: keyword_hash -> (timestamp, result)
_SPARK_CACHE: Dict[str, Tuple[float, Optional[Dict]]] = {}
SPARK_CACHE_TTL = 300  # 5 minutes


def _get_cache_key(text: str) -> str:
    """Generate cache key from text (normalized keywords)."""
    import hashlib
    # Normalize: lowercase, sorted words, first 200 chars
    words = sorted(set(text.lower().split()))[:20]
    normalized = " ".join(words)
    return hashlib.md5(normalized.encode()).hexdigest()[:16]


def run_spark(text: str, timeout: float = 3.0) -> Optional[Dict]:
    """Run spark in-process for memory retrieval with caching.

    v2: Uses spark_core.fire_synapses() directly instead of subprocess.
    This eliminates 100-500ms subprocess spawn overhead.
    """
    import time as _time

    if not text or len(text.strip()) < 10:
        return None

    # Check cache first
    cache_key = _get_cache_key(text)
    if cache_key in _SPARK_CACHE:
        cached_time, cached_result = _SPARK_CACHE[cache_key]
        if _time.time() - cached_time < SPARK_CACHE_TTL:
            return cached_result

    try:
        # Import spark_core for in-process execution (lazy import)
        from spark_core import fire_synapses

        # Fire synapses in-process (no subprocess overhead)
        result = fire_synapses(text[:500], include_constraints=True)

        # Cache successful result
        _SPARK_CACHE[cache_key] = (_time.time(), result)
        return result

    except Exception:
        pass

    # Cache failures too (avoid repeated errors)
    _SPARK_CACHE[cache_key] = (_time.time(), None)
    return None


# =============================================================================
# TRANSCRIPT UTILITIES
# =============================================================================


def validate_file_path(file_path: str) -> bool:
    """Block path traversal attacks."""
    if not file_path:
        return True
    if '..' in file_path:
        return False
    return True


def extract_thinking_blocks(transcript_path: str, max_bytes: int = 15000) -> List[str]:
    """Extract thinking blocks from transcript JSONL."""
    if not transcript_path or not validate_file_path(transcript_path):
        return []
    if not os.path.exists(transcript_path):
        return []

    thinking_blocks = []
    try:
        with open(transcript_path, 'r') as f:
            f.seek(0, 2)
            file_size = f.tell()
            f.seek(max(0, file_size - max_bytes))
            content = f.read()

        for line in content.split('\n'):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if entry.get("type") != "assistant":
                    continue
                message = entry.get("message", {})
                content_blocks = message.get("content", [])
                if isinstance(content_blocks, list):
                    for block in content_blocks:
                        if isinstance(block, dict) and block.get("type") == "thinking":
                            thinking = block.get("thinking", "")
                            if thinking and len(thinking) > 50:
                                thinking_blocks.append(thinking)
            except json.JSONDecodeError:
                continue

        return thinking_blocks[-3:]  # Last 3 thinking blocks
    except (IOError, OSError):
        return []


def check_sudo_in_transcript(transcript_path: str, lookback: int = 3000) -> bool:
    """Check if SUDO keyword is in recent transcript."""
    if not transcript_path or not validate_file_path(transcript_path):
        return False
    try:
        if os.path.exists(transcript_path):
            with open(transcript_path) as f:
                f.seek(0, 2)
                f.seek(max(0, f.tell() - lookback))
                return "SUDO" in f.read()
    except (IOError, OSError):
        pass
    return False


def extract_recent_text(transcript_path: str, max_chars: int = 8000) -> str:
    """Extract recent Claude text from transcript."""
    if not transcript_path or not validate_file_path(transcript_path):
        return ""
    if not os.path.exists(transcript_path):
        return ""

    try:
        with open(transcript_path, 'r') as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - max_chars))
            chunk = f.read()

        thoughts = []
        current_block = []

        for line in chunk.split('\n'):
            # Skip tool results and user messages
            if '<' in line or 'tool_result' in line.lower():
                if current_block:
                    thoughts.append(' '.join(current_block))
                    current_block = []
                continue
            if line.strip().startswith(('Human:', 'user:')):
                if current_block:
                    thoughts.append(' '.join(current_block))
                    current_block = []
                continue

            stripped = line.strip()
            if stripped and len(stripped) > 20:
                current_block.append(stripped)

        if current_block:
            thoughts.append(' '.join(current_block))

        return ' '.join(thoughts[-3:])[:2000]
    except (IOError, OSError):
        return ""


# =============================================================================
# OUTPUT HELPERS
# =============================================================================


def log_block(hook_name: str, reason: str, tool_name: str = "", tool_input: dict = None):
    """Log a hook block for later reflection.

    Blocks are logged to .claude/memory/block_log.jsonl with metadata
    for post-session analysis.
    """
    import time
    import os

    log_file = Path(__file__).parent.parent / "memory" / "block_log.jsonl"

    entry = {
        "timestamp": time.time(),
        "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown"),
        "hook": hook_name,
        "reason": reason[:500],  # Truncate long reasons
        "tool_name": tool_name,
        "tool_input_summary": str(tool_input)[:200] if tool_input else "",
    }

    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except (IOError, OSError):
        pass  # Don't fail hook on logging error


def format_block_acknowledgment(hook_name: str) -> str:
    """Format the acknowledgment prompt to append to block messages.

    Returns text asking Claude to acknowledge if block was valid or false positive.
    """
    return (
        f"\n\n**ACKNOWLEDGE:** Was this block valid or a false positive?\n"
        f"- If VALID: Say 'Block valid: [lesson learned]' (clears from Stop reflection)\n"
        f"- If FALSE POSITIVE: Say 'False positive: [which hook needs fixing]' (requires investigation)"
    )


def clear_acknowledged_block(hook_name: str, session_id: str = None):
    """Clear a specific hook's blocks after acknowledgment.

    Called when Claude admits the block was valid (no need for Stop reflection).
    """
    import os

    if session_id is None:
        session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

    log_file = Path(__file__).parent.parent / "memory" / "block_log.jsonl"

    if not log_file.exists():
        return

    try:
        # Read all entries, filter out acknowledged hook for this session
        remaining = []
        with open(log_file) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    # Keep if different session or different hook
                    if entry.get("session_id") != session_id or entry.get("hook") != hook_name:
                        remaining.append(line)
                except json.JSONDecodeError:
                    remaining.append(line)

        with open(log_file, 'w') as f:
            f.writelines(remaining)
    except (IOError, OSError):
        pass


def get_session_blocks(session_id: str = None) -> list[dict]:
    """Get all blocks for current or specified session."""
    import os

    if session_id is None:
        session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

    log_file = Path(__file__).parent.parent / "memory" / "block_log.jsonl"
    blocks = []

    if not log_file.exists():
        return blocks

    try:
        with open(log_file) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("session_id") == session_id:
                        blocks.append(entry)
                except json.JSONDecodeError:
                    continue
    except (IOError, OSError):
        pass

    return blocks


def clear_session_blocks(session_id: str = None):
    """Clear blocks for current session after reflection is shown.

    This prevents the stop hook from repeatedly demanding reflection
    for the same blocks.
    """
    import os

    if session_id is None:
        session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

    log_file = Path(__file__).parent.parent / "memory" / "block_log.jsonl"

    if not log_file.exists():
        return

    try:
        # Read all entries, filter out current session
        remaining = []
        with open(log_file) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("session_id") != session_id:
                        remaining.append(line)
                except json.JSONDecodeError:
                    remaining.append(line)  # Keep malformed lines

        # Write back filtered entries
        with open(log_file, 'w') as f:
            f.writelines(remaining)
    except (IOError, OSError):
        pass


def output_hook_result(
    lifecycle: str,
    context: str = "",
    decision: Optional[str] = None,
    reason: str = "",
    hook_name: str = "",
    tool_name: str = "",
    tool_input: dict = None
):
    """Output standardized hook result.

    If decision is "deny", automatically logs the block for later reflection.
    """
    result = {
        "hookSpecificOutput": {
            "hookEventName": lifecycle,
        }
    }

    if context:
        result["hookSpecificOutput"]["additionalContext"] = context

    if decision:
        result["hookSpecificOutput"]["permissionDecision"] = decision
        if reason:
            # Append acknowledgment prompt for blocks
            if decision == "deny":
                reason = reason + format_block_acknowledgment(hook_name or "hook")
            result["hookSpecificOutput"]["permissionDecisionReason"] = reason

        # Auto-log blocks
        if decision == "deny":
            # Extract hook name from reason if not provided
            effective_hook = hook_name
            if not effective_hook and reason:
                # Try to extract from reason like "**COMMIT BLOCKED**"
                import re
                match = re.search(r'\*\*(\w+(?:\s+\w+)?)\s+BLOCKED\*\*', reason)
                if match:
                    effective_hook = match.group(1).lower().replace(" ", "_") + "_gate"

            log_block(effective_hook or "unknown", reason, tool_name, tool_input)

    print(json.dumps(result))
