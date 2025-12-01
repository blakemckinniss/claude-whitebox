#!/usr/bin/env python3
"""
Spark Core: In-process memory retrieval (no subprocess overhead).

Extracted from .claude/ops/spark.py for direct import.
Provides ~100-500ms latency reduction by eliminating subprocess spawn.
"""

import json
import os
import re
import random
from pathlib import Path
from typing import Optional

# Find project root
_LIB_DIR = Path(__file__).parent
_CLAUDE_DIR = _LIB_DIR.parent
_PROJECT_ROOT = _CLAUDE_DIR.parent
MEMORY_DIR = _CLAUDE_DIR / "memory"

# Synapse map location
SYNAPSE_FILE = MEMORY_DIR / "__synapses.json"
LESSONS_FILE = MEMORY_DIR / "__lessons.md"

# Cached synapse map (loaded once per process)
_SYNAPSE_CACHE: Optional[dict] = None


def _load_synapses() -> dict:
    """Load synapse map with caching."""
    global _SYNAPSE_CACHE
    if _SYNAPSE_CACHE is not None:
        return _SYNAPSE_CACHE

    try:
        if SYNAPSE_FILE.exists():
            _SYNAPSE_CACHE = json.loads(SYNAPSE_FILE.read_text())
        else:
            _SYNAPSE_CACHE = {"patterns": {}, "random_constraints": [], "meta": {}}
    except (json.JSONDecodeError, IOError):
        _SYNAPSE_CACHE = {"patterns": {}, "random_constraints": [], "meta": {}}

    return _SYNAPSE_CACHE


def query_lessons(keywords: list[str], max_results: int = 3) -> list[str]:
    """Scan lessons file for matches (same logic as spark.py)."""
    if not LESSONS_FILE.exists():
        return []

    matches = []
    try:
        lines = LESSONS_FILE.read_text().split('\n')

        for line in lines:
            if line.startswith("#") or not line.strip():
                continue

            line_lower = line.lower()
            if any(kw.lower() in line_lower for kw in keywords):
                cleaned = line.strip()
                if cleaned and cleaned not in matches:
                    matches.append(cleaned)
                    if len(matches) >= max_results:
                        break
    except (IOError, OSError):
        pass

    return matches


def extract_keywords_from_pattern(pattern: str) -> list[str]:
    """Extract keywords from regex pattern for lesson search."""
    keywords = (
        pattern.replace("(", "")
        .replace(")", "")
        .replace("|", " ")
        .replace("\\", "")
        .split()
    )
    return [k for k in keywords if len(k) > 3]


def fire_synapses(prompt: str, include_constraints: bool = True) -> dict:
    """
    Core synapse firing logic - returns associations and memories.

    This is the main function to call. Returns:
    {
        "has_associations": bool,
        "associations": list[str],
        "memories": list[str],
        "constraint": str | None,
        "matched_patterns": list[str]
    }
    """
    synapses = _load_synapses()
    patterns = synapses.get("patterns", {})
    random_constraints = synapses.get("random_constraints", [])
    meta = synapses.get("meta", {})

    max_associations = meta.get("max_associations", 5)
    max_memories = meta.get("max_memories", 3)
    constraint_probability = meta.get("constraint_probability", 0.10)

    prompt_lower = prompt.lower()

    # 1. Check Synapse Map (Static Associations)
    associations = []
    active_keywords = []
    matched_patterns = []

    for pattern, links in patterns.items():
        try:
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                matched_patterns.append(pattern)
                associations.extend(links[:max_associations])
                keywords = extract_keywords_from_pattern(pattern)
                active_keywords.extend(keywords)
        except re.error:
            continue  # Skip invalid patterns

    # Remove duplicates while preserving order
    associations = list(dict.fromkeys(associations))[:max_associations]

    # 2. Check Lessons (Dynamic Associations)
    memories = []
    if active_keywords:
        memories = query_lessons(active_keywords, max_results=max_memories)

    # 3. Random Constraint Injection (Lateral Thinking)
    constraint = None
    if include_constraints and random_constraints:
        if random.random() < constraint_probability:
            constraint = random.choice(random_constraints)

    return {
        "has_associations": len(associations) > 0 or len(memories) > 0 or constraint is not None,
        "associations": associations,
        "memories": memories,
        "constraint": constraint,
        "matched_patterns": matched_patterns,
    }


def invalidate_cache():
    """Clear synapse cache (call if synapses.json is updated)."""
    global _SYNAPSE_CACHE
    _SYNAPSE_CACHE = None
