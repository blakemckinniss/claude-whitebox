#!/usr/bin/env python3
"""
Synapse Fire Hook v3: Enhanced Associative Memory with Scoring & Error Triggers

IMPROVEMENTS (Oracle Judge ROI priorities):
1. CONTEXT BUDGETING: Score synapses, limit injection to top-N within token budget
2. ERROR-TYPE TRIGGERS: Detect specific errors in tool output, fire relevant synapses
3. TELEMETRY: Track synapse firing rates, hit/miss, latency for learning
4. FAST PATH: Skip analysis for low-value events (empty prompts, system tools)

PHILOSOPHY:
- Quality over quantity: inject 2-3 high-value associations, not 10 low-value
- Error-aware: stack traces and error messages trigger specific help
- Observable: every decision is logged for tuning
- Adaptive: scoring enables future learning loop
"""

import sys
import json
import subprocess
import hashlib
import time
import re
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# =============================================================================
# CONSTANTS & CONFIG
# =============================================================================

CACHE_DIR = Path("/tmp/claude_synapse_cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL = 300  # 5 minutes

MAX_TRANSCRIPT_CHUNK = 8000  # chars to analyze
MAX_CONTEXT_TOKENS = 800  # Max tokens to inject (~200 words)
MAX_ASSOCIATIONS = 4  # Max associations to inject
MAX_MEMORIES = 2  # Max memories to inject

# Tools that skip synapse analysis (internal/system tools)
SKIP_TOOLS = frozenset({
    "TodoWrite", "BashOutput", "KillShell",  # Internal tracking
})

# Error patterns with categories and priorities
ERROR_PATTERNS = [
    # Python errors (high priority - actionable)
    (r"TypeError.*'(\w+)'.*'(\w+)'", "type_error", 0.9, ["TypeError", "type", "wrong type"]),
    (r"KeyError:\s*['\"]?(\w+)", "key_error", 0.9, ["KeyError", "dict", "key"]),
    (r"AttributeError.*'(\w+)'.*'(\w+)'", "attribute_error", 0.85, ["AttributeError", "attribute"]),
    (r"IndexError", "index_error", 0.85, ["IndexError", "list", "index"]),
    (r"ModuleNotFoundError.*'(\w+)'", "import_error", 0.95, ["ImportError", "ModuleNotFoundError", "install"]),
    (r"FileNotFoundError", "file_error", 0.9, ["FileNotFoundError", "file", "path"]),
    (r"PermissionError|Permission denied", "permission_error", 0.85, ["PermissionError", "permission"]),
    (r"ConnectionError|ConnectionRefused|TimeoutError", "network_error", 0.85, ["ConnectionError", "timeout", "network"]),
    (r"SyntaxError", "syntax_error", 0.95, ["SyntaxError", "syntax"]),
    (r"ValueError", "value_error", 0.8, ["ValueError", "value"]),

    # Test failures
    (r"FAILED.*::", "test_failure", 0.9, ["test", "pytest", "fail"]),
    (r"AssertionError", "assertion_error", 0.85, ["assertion", "test", "expect"]),

    # Build/install errors
    (r"npm ERR!", "npm_error", 0.9, ["npm", "install", "package"]),
    (r"pip.*error|Could not find a version", "pip_error", 0.9, ["pip", "install", "dependency"]),

    # Generic errors (lower priority)
    (r"Traceback \(most recent call last\)", "traceback", 0.7, ["error", "traceback", "exception"]),
    (r"Error:|ERROR:|Exception:", "generic_error", 0.6, ["error", "exception"]),
]

# =============================================================================
# TELEMETRY
# =============================================================================

@dataclass
class SynapseTelemetry:
    """Track synapse firing metrics for learning"""
    total_fires: int = 0
    total_skips: int = 0
    error_triggers: int = 0
    cache_hits: int = 0
    patterns_matched: Dict[str, int] = field(default_factory=dict)
    errors_detected: Dict[str, int] = field(default_factory=dict)
    latency_samples: List[float] = field(default_factory=list)
    last_updated: str = ""

    def record_fire(self, patterns: List[str], latency_ms: float, from_cache: bool = False):
        self.total_fires += 1
        self.last_updated = datetime.now().isoformat()
        if from_cache:
            self.cache_hits += 1
        for p in patterns:
            self.patterns_matched[p] = self.patterns_matched.get(p, 0) + 1
        self.latency_samples.append(latency_ms)
        if len(self.latency_samples) > 100:
            self.latency_samples = self.latency_samples[-100:]

    def record_skip(self):
        self.total_skips += 1
        self.last_updated = datetime.now().isoformat()

    def record_error_trigger(self, error_type: str):
        self.error_triggers += 1
        self.errors_detected[error_type] = self.errors_detected.get(error_type, 0) + 1

    def get_stats(self) -> Dict:
        avg_latency = sum(self.latency_samples) / len(self.latency_samples) if self.latency_samples else 0
        hit_rate = self.cache_hits / self.total_fires if self.total_fires > 0 else 0
        return {
            "total_fires": self.total_fires,
            "total_skips": self.total_skips,
            "error_triggers": self.error_triggers,
            "cache_hit_rate": f"{hit_rate:.1%}",
            "avg_latency_ms": f"{avg_latency:.1f}",
            "top_patterns": dict(sorted(self.patterns_matched.items(), key=lambda x: -x[1])[:5]),
            "top_errors": dict(sorted(self.errors_detected.items(), key=lambda x: -x[1])[:5]),
        }

    def to_dict(self) -> Dict:
        return {
            "total_fires": self.total_fires,
            "total_skips": self.total_skips,
            "error_triggers": self.error_triggers,
            "cache_hits": self.cache_hits,
            "patterns_matched": self.patterns_matched,
            "errors_detected": self.errors_detected,
            "latency_samples": self.latency_samples,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SynapseTelemetry':
        return cls(
            total_fires=data.get("total_fires", 0),
            total_skips=data.get("total_skips", 0),
            error_triggers=data.get("error_triggers", 0),
            cache_hits=data.get("cache_hits", 0),
            patterns_matched=data.get("patterns_matched", {}),
            errors_detected=data.get("errors_detected", {}),
            latency_samples=data.get("latency_samples", []),
            last_updated=data.get("last_updated", ""),
        )


_telemetry: Optional[SynapseTelemetry] = None
_telemetry_file: Optional[Path] = None


def get_telemetry() -> SynapseTelemetry:
    global _telemetry, _telemetry_file
    if _telemetry is None:
        project_dir = Path.cwd()
        while not (project_dir / "scripts" / "lib").exists() and project_dir != project_dir.parent:
            project_dir = project_dir.parent
        _telemetry_file = project_dir / ".claude" / "memory" / "synapse_telemetry.json"
        if _telemetry_file.exists():
            try:
                with open(_telemetry_file) as f:
                    _telemetry = SynapseTelemetry.from_dict(json.load(f))
            except (json.JSONDecodeError, IOError):
                _telemetry = SynapseTelemetry()
        else:
            _telemetry = SynapseTelemetry()
    return _telemetry


def save_telemetry():
    global _telemetry, _telemetry_file
    if _telemetry and _telemetry_file:
        try:
            _telemetry_file.parent.mkdir(parents=True, exist_ok=True)
            with open(_telemetry_file, "w") as f:
                json.dump(_telemetry.to_dict(), f, indent=2)
        except (IOError, OSError):
            pass


# =============================================================================
# SCORING & BUDGETING
# =============================================================================

@dataclass
class ScoredAssociation:
    """An association with relevance score for budgeting"""
    text: str
    score: float  # 0.0-1.0 relevance
    category: str  # Source category
    source: str  # "pattern", "error", "memory", "constraint"
    tokens_estimate: int  # Rough token count

    def __lt__(self, other):
        return self.score > other.score  # Higher score = higher priority


def estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars per token)"""
    return len(text) // 4


def score_association(text: str, source: str, match_strength: float = 0.5) -> float:
    """
    Score an association for relevance and value.

    Factors:
    - Source type (error > pattern > memory > constraint)
    - Match strength (from regex/error detection)
    - Text quality (has actionable keywords)
    """
    # Base score by source
    source_scores = {
        "error": 0.9,      # Errors are highly relevant
        "pattern": 0.7,    # Pattern matches are good
        "memory": 0.5,     # Memories are contextual
        "constraint": 0.3, # Constraints are lateral/optional
    }
    base = source_scores.get(source, 0.5)

    # Boost for actionable keywords
    actionable = ["Tool:", "Pattern:", "Action:", "DANGER:", "WARNING:", "Protocol:"]
    boost = 0.1 if any(kw in text for kw in actionable) else 0

    # Boost for lessons (learned from pain)
    if "Lesson:" in text:
        boost += 0.1

    # Combine with match strength
    return min(1.0, (base + boost) * match_strength)


def budget_associations(associations: List[ScoredAssociation], max_tokens: int) -> List[ScoredAssociation]:
    """
    Select top associations within token budget.
    Ensures diversity by limiting per-category.
    """
    # Sort by score (highest first)
    sorted_assocs = sorted(associations)

    selected = []
    used_tokens = 0
    category_counts: Dict[str, int] = {}
    max_per_category = 3

    for assoc in sorted_assocs:
        # Check token budget
        if used_tokens + assoc.tokens_estimate > max_tokens:
            continue

        # Check category diversity
        cat_count = category_counts.get(assoc.category, 0)
        if cat_count >= max_per_category:
            continue

        selected.append(assoc)
        used_tokens += assoc.tokens_estimate
        category_counts[assoc.category] = cat_count + 1

        # Stop if we have enough
        if len(selected) >= MAX_ASSOCIATIONS + MAX_MEMORIES + 1:  # +1 for constraint
            break

    return selected


# =============================================================================
# ERROR DETECTION
# =============================================================================

def detect_errors(text: str) -> List[Tuple[str, float, List[str]]]:
    """
    Detect error patterns in text and return (error_type, priority, keywords).
    """
    if not text:
        return []

    detected = []
    for pattern, error_type, priority, keywords in ERROR_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            detected.append((error_type, priority, keywords))

    # Sort by priority (highest first)
    return sorted(detected, key=lambda x: -x[1])


# =============================================================================
# CACHING
# =============================================================================

def get_cache_key(session_id: str, text: str, lifecycle: str) -> str:
    text_prefix = text[:100].lower().strip()
    return hashlib.md5(f"{session_id}:{lifecycle}:{text_prefix}".encode()).hexdigest()


def get_cached_result(cache_key: str) -> Optional[Dict]:
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        if time.time() - cache_file.stat().st_mtime < CACHE_TTL:
            try:
                with open(cache_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
    return None


def set_cached_result(cache_key: str, result: Dict):
    cache_file = CACHE_DIR / f"{cache_key}.json"
    try:
        with open(cache_file, 'w') as f:
            json.dump(result, f)
    except (IOError, OSError):
        pass


# =============================================================================
# TRANSCRIPT EXTRACTION
# =============================================================================

def extract_claude_thoughts(transcript_path: str) -> str:
    """Extract Claude's recent thoughts from transcript."""
    if not transcript_path or not os.path.exists(transcript_path):
        return ""

    try:
        with open(transcript_path, 'r') as f:
            f.seek(0, 2)
            file_size = f.tell()
            read_start = max(0, file_size - MAX_TRANSCRIPT_CHUNK)
            f.seek(read_start)
            chunk = f.read()

        thoughts = []
        lines = chunk.split('\n')
        current_block = []

        for line in lines:
            if '<' in line or 'tool_result' in line.lower():
                if current_block:
                    thoughts.append(' '.join(current_block))
                    current_block = []
                continue

            if line.strip().startswith('Human:') or line.strip().startswith('user:'):
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
# SPARK INTEGRATION
# =============================================================================

def run_spark(text: str) -> Optional[Dict]:
    """Run spark.py on given text and return parsed output"""
    if not text or len(text.strip()) < 10:
        return None

    try:
        project_root = os.environ.get("CLAUDE_PROJECT_ROOT")
        if not project_root:
            current = Path(__file__).resolve().parent
            while current != current.parent:
                if (current / "scripts" / "lib" / "core.py").exists():
                    project_root = str(current)
                    break
                current = current.parent

        result = subprocess.run(
            ["python3", "scripts/ops/spark.py", text, "--json"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=project_root
        )

        if result.returncode != 0:
            return None

        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None


# =============================================================================
# CONTEXT BUILDING
# =============================================================================

def build_context_v3(
    spark_output: Optional[Dict],
    error_keywords: List[str],
    source: str,
    error_type: Optional[str] = None
) -> Tuple[str, List[str]]:
    """
    Build context string using scoring and budgeting.
    Returns (context_string, matched_patterns).
    """
    scored_associations: List[ScoredAssociation] = []
    matched_patterns = []

    # Add error-triggered associations (highest priority)
    if error_type and error_keywords:
        # Run spark with error keywords
        error_spark = run_spark(" ".join(error_keywords))
        if error_spark:
            for assoc in error_spark.get("associations", [])[:3]:
                scored_associations.append(ScoredAssociation(
                    text=assoc,
                    score=score_association(assoc, "error", 0.95),
                    category="error",
                    source="error",
                    tokens_estimate=estimate_tokens(assoc),
                ))
            matched_patterns.extend(error_spark.get("matched_patterns", []))

    # Add pattern-based associations
    if spark_output:
        for assoc in spark_output.get("associations", []):
            scored_associations.append(ScoredAssociation(
                text=assoc,
                score=score_association(assoc, "pattern", 0.8),
                category="pattern",
                source="pattern",
                tokens_estimate=estimate_tokens(assoc),
            ))
        matched_patterns.extend(spark_output.get("matched_patterns", []))

        # Add memories
        for memory in spark_output.get("memories", []):
            truncated = memory[:100] + "..." if len(memory) > 100 else memory
            scored_associations.append(ScoredAssociation(
                text=truncated,
                score=score_association(memory, "memory", 0.6),
                category="memory",
                source="memory",
                tokens_estimate=estimate_tokens(truncated),
            ))

        # Add constraint (low priority, optional)
        constraint = spark_output.get("constraint")
        if constraint:
            scored_associations.append(ScoredAssociation(
                text=constraint,
                score=score_association(constraint, "constraint", 0.4),
                category="constraint",
                source="constraint",
                tokens_estimate=estimate_tokens(constraint),
            ))

    # Budget and select
    selected = budget_associations(scored_associations, MAX_CONTEXT_TOKENS)

    if not selected:
        return "", matched_patterns

    # Build output grouped by source
    context_lines = [f"\n🧠 SUBCONSCIOUS RECALL ({source}):"]

    # Group by source type
    errors = [a for a in selected if a.source == "error"]
    patterns = [a for a in selected if a.source == "pattern"]
    memories = [a for a in selected if a.source == "memory"]
    constraints = [a for a in selected if a.source == "constraint"]

    if errors or patterns:
        context_lines.append("\n📚 Relevant Protocols & Tools:")
        for a in (errors + patterns)[:MAX_ASSOCIATIONS]:
            context_lines.append(f"   • {a.text}")

    if memories:
        context_lines.append("\n💭 Relevant Past Experiences:")
        for a in memories[:MAX_MEMORIES]:
            context_lines.append(f"   • {a.text}")

    if constraints:
        context_lines.append("\n💡 Lateral Thinking Spark:")
        context_lines.append(f"   • {constraints[0].text}")

    context_lines.append("")
    return "\n".join(context_lines), matched_patterns


# =============================================================================
# OUTPUT
# =============================================================================

def output_result(lifecycle: str, context: str = ""):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": lifecycle,
            "additionalContext": context,
        }
    }))
    sys.exit(0)


# =============================================================================
# MAIN
# =============================================================================

def main():
    start_time = time.perf_counter()
    telemetry = get_telemetry()

    # Load input
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        output_result("UserPromptSubmit", "")

    # Detect lifecycle
    tool_name = input_data.get("tool_name")
    prompt = input_data.get("prompt")
    session_id = input_data.get("session_id", "")
    transcript_path = input_data.get("transcript_path", "")

    if "tool_response" in input_data or "toolResult" in input_data:
        lifecycle = "PostToolUse"
    elif tool_name:
        lifecycle = "PreToolUse"
    else:
        lifecycle = "UserPromptSubmit"

    # FAST PATH: Skip for system tools
    if tool_name in SKIP_TOOLS:
        telemetry.record_skip()
        save_telemetry()
        output_result(lifecycle, "")

    # Determine what text to analyze
    if lifecycle == "UserPromptSubmit":
        text_to_analyze = prompt or ""
        source = "User Prompt"
    else:
        text_to_analyze = extract_claude_thoughts(transcript_path)
        source = "Self-Thought Pattern"

        tool_input = input_data.get("tool_input", {})
        if isinstance(tool_input, dict):
            tool_text_parts = []
            for key, value in tool_input.items():
                if isinstance(value, str) and len(value) < 500:
                    tool_text_parts.append(value)
            if tool_text_parts:
                text_to_analyze = f"{text_to_analyze} {' '.join(tool_text_parts)}"

    # Also check tool output for errors (PostToolUse)
    tool_output = ""
    if lifecycle == "PostToolUse":
        tool_result = input_data.get("tool_response") or input_data.get("toolResult", {})
        if isinstance(tool_result, dict):
            content = tool_result.get("content")
            if isinstance(content, list) and content:
                tool_output = "\n".join(
                    item.get("text", "") for item in content if isinstance(item, dict)
                )
            elif isinstance(content, str):
                tool_output = content

    if not text_to_analyze and not tool_output:
        telemetry.record_skip()
        save_telemetry()
        output_result(lifecycle, "")

    if not session_id:
        output_result(lifecycle, "")

    # Check cache
    cache_key = get_cache_key(session_id, text_to_analyze + tool_output, lifecycle)
    cached = get_cached_result(cache_key)

    if cached:
        latency_ms = (time.perf_counter() - start_time) * 1000
        telemetry.record_fire(cached.get("patterns", []), latency_ms, from_cache=True)
        save_telemetry()
        output_result(lifecycle, cached.get("context", ""))

    # ERROR DETECTION (New feature)
    error_type = None
    error_keywords = []

    if tool_output:
        detected_errors = detect_errors(tool_output)
        if detected_errors:
            error_type, _, error_keywords = detected_errors[0]  # Take highest priority
            telemetry.record_error_trigger(error_type)

    # Run spark analysis on main text
    spark_output = run_spark(text_to_analyze) if text_to_analyze else None

    # Build context with scoring
    context, matched_patterns = build_context_v3(
        spark_output,
        error_keywords,
        source,
        error_type
    )

    # Record telemetry
    latency_ms = (time.perf_counter() - start_time) * 1000
    if context:
        telemetry.record_fire(matched_patterns, latency_ms)
    else:
        telemetry.record_skip()
    save_telemetry()

    # Cache and output
    set_cached_result(cache_key, {"context": context, "patterns": matched_patterns})
    output_result(lifecycle, context)


if __name__ == "__main__":
    main()
