#!/usr/bin/env python3
"""
Resource Pointer Hook: Surface availability, not content.

Hook Type: UserPromptSubmit
Latency Target: <30ms

THE INSIGHT: Bad RAG pushes content. Good assistance points to shelves.

This hook surfaces *pointers* to possibly relevant resources:
- Files/folders that match prompt keywords
- Tools that might help
- Lesson line numbers (not content)
- Commands available

Claude decides whether to investigate. No context pollution.

Output budget: <100 tokens. If we exceed, we're doing it wrong.
"""

import _lib_path  # noqa: F401
import sys
import json
import re
from pathlib import Path
from typing import NamedTuple

# =============================================================================
# PATHS
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
CLAUDE_DIR = PROJECT_ROOT / ".claude"
MEMORY_DIR = CLAUDE_DIR / "memory"
OPS_DIR = CLAUDE_DIR / "ops"

LESSONS_FILE = MEMORY_DIR / "__lessons.md"
FILE_INDEX_CACHE = MEMORY_DIR / ".file_index.json"

# =============================================================================
# CONFIG
# =============================================================================

# Max pointers per category (keeps output sparse)
MAX_FILE_POINTERS = 3
MAX_TOOL_POINTERS = 2
MAX_LESSON_POINTERS = 2
MAX_TOTAL_POINTERS = 6

# Minimum keyword match score to surface
MIN_RELEVANCE_SCORE = 2

# =============================================================================
# KEYWORD EXTRACTION (fast, no deps)
# =============================================================================

STOP_WORDS = frozenset([
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "can", "need", "want", "like", "just", "get", "make", "use",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "and", "but", "if", "or", "so", "then", "this", "that", "what", "how",
    "i", "me", "my", "you", "your", "we", "it", "they", "them", "there",
    "please", "thanks", "help", "know", "think", "look", "see", "try",
])


def extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from prompt. Fast path."""
    words = re.findall(r'\b[a-z][a-z0-9_]{2,}\b', text.lower())
    keywords = [w for w in words if w not in STOP_WORDS]
    # Dedupe, preserve order, limit
    seen = set()
    return [k for k in keywords if not (k in seen or seen.add(k))][:12]


# =============================================================================
# TOOL INDEX (static, fast)
# =============================================================================

# Tool -> (keywords, one-liner description)
# Only include tools that aren't obvious from their names
TOOL_INDEX = {
    "probe": (
        ["api", "signature", "method", "attribute", "inspect", "runtime", "class", "object"],
        "runtime API inspection - see what methods/attrs exist",
    ),
    "research": (
        ["docs", "documentation", "library", "package", "how", "api", "external"],
        "web search for docs/libraries",
    ),
    "xray": (
        ["find", "class", "function", "structure", "ast", "definition", "where"],
        "AST search - find classes/functions by name",
    ),
    "audit": (
        ["security", "vulnerability", "injection", "secrets", "unsafe"],
        "security audit for code",
    ),
    "void": (
        ["stub", "todo", "incomplete", "notimplemented", "missing", "placeholder"],
        "find incomplete/stub code",
    ),
    "think": (
        ["complex", "decompose", "break", "analyze", "stuck", "approach"],
        "structured problem decomposition",
    ),
    "council": (
        ["decision", "tradeoff", "choice", "should", "approach", "design"],
        "multi-perspective analysis",
    ),
    "gaps": (
        ["missing", "incomplete", "coverage", "crud", "error", "handling"],
        "completeness check",
    ),
    "spark": (
        ["remember", "previous", "lesson", "pattern", "protocol", "learned"],
        "associative memory recall",
    ),
    "verify": (
        ["check", "exists", "confirm", "test", "validate", "ensure"],
        "verify file/command/state",
    ),
}


def match_tools(keywords: list[str]) -> list[tuple[str, str, int]]:
    """Match keywords to tools. Returns [(tool, desc, score)]."""
    matches = []
    kw_set = set(keywords)

    for tool, (tool_kws, desc) in TOOL_INDEX.items():
        score = len(kw_set & set(tool_kws))
        if score >= 1:
            matches.append((tool, desc, score))

    matches.sort(key=lambda x: -x[2])
    return matches[:MAX_TOOL_POINTERS]


# =============================================================================
# FILE INDEX (cached, refreshed periodically)
# =============================================================================

# Folder -> keywords (for quick matching without walking tree)
FOLDER_HINTS = {
    "src/": ["source", "code", "main", "app"],
    "lib/": ["library", "util", "helper", "shared"],
    "test/": ["test", "spec", "fixture"],
    "tests/": ["test", "spec", "fixture"],
    ".claude/ops/": ["tool", "script", "ops", "command"],
    ".claude/hooks/": ["hook", "gate", "enforce", "check"],
    ".claude/lib/": ["library", "core", "shared", "state"],
    "api/": ["api", "endpoint", "route", "handler"],
    "auth/": ["auth", "login", "session", "token", "user"],
    "db/": ["database", "model", "schema", "query", "sql"],
    "config/": ["config", "setting", "env", "environment"],
}


class FilePointer(NamedTuple):
    path: str
    hint: str
    score: int


def get_file_index() -> dict:
    """Get or build file index. Cached for speed."""
    import time

    # Try cache first
    if FILE_INDEX_CACHE.exists():
        try:
            cache = json.loads(FILE_INDEX_CACHE.read_text())
            # Validate cache structure
            if isinstance(cache, dict) and isinstance(cache.get("index"), dict):
                # Cache valid for 10 minutes
                if time.time() - cache.get("ts", 0) < 600:
                    return cache["index"]
        except (json.JSONDecodeError, KeyError, TypeError):
            # Corrupted cache - delete and rebuild
            try:
                FILE_INDEX_CACHE.unlink()
            except OSError:
                pass

    # Build index (fast scan, no content reading)
    index = {}

    # Index key files by name keywords
    for pattern in ["**/*.py", "**/*.ts", "**/*.js", "**/*.go", "**/*.rs"]:
        try:
            for f in PROJECT_ROOT.glob(pattern):
                if ".git" in str(f) or "node_modules" in str(f):
                    continue
                rel = str(f.relative_to(PROJECT_ROOT))
                # Extract keywords from path
                path_words = re.findall(r'[a-z]{3,}', rel.lower())
                if path_words:
                    index[rel] = path_words[:5]
        except Exception:
            continue

    # Cache it - track if write fails to avoid repeated attempts
    try:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        FILE_INDEX_CACHE.write_text(json.dumps({"ts": time.time(), "index": index}))
    except (OSError, IOError):
        # Write failed - still return index, just won't be cached
        # On next call, we'll scan again but that's better than crashing
        pass

    return index


def match_files(keywords: list[str]) -> list[FilePointer]:
    """Match keywords to files/folders."""
    matches = []
    kw_set = set(keywords)

    # Check folder hints first (fast)
    for folder, hints in FOLDER_HINTS.items():
        if (PROJECT_ROOT / folder.rstrip("/")).exists():
            score = len(kw_set & set(hints))
            if score >= 1:
                matches.append(FilePointer(folder, ", ".join(hints[:3]), score))

    # Check file index
    file_index = get_file_index()
    for path, path_kws in file_index.items():
        score = len(kw_set & set(path_kws))
        if score >= 1:
            # Use filename as hint
            hint = Path(path).stem
            matches.append(FilePointer(path, hint, score))

    # Sort by score, dedupe folders vs files
    matches.sort(key=lambda x: -x.score)

    # Prefer folders if they cover the same ground
    seen_prefixes = set()
    filtered = []
    for m in matches:
        prefix = m.path.split("/")[0] if "/" in m.path else m.path
        if prefix not in seen_prefixes or m.score >= 2:
            filtered.append(m)
            seen_prefixes.add(prefix)
        if len(filtered) >= MAX_FILE_POINTERS:
            break

    return filtered


# =============================================================================
# LESSON INDEX (line-number pointers, not content)
# =============================================================================

def match_lessons(keywords: list[str]) -> list[tuple[int, str, int]]:
    """Find lesson line numbers matching keywords. Returns [(line_num, preview, score)]."""
    if not LESSONS_FILE.exists():
        return []

    matches = []
    kw_set = set(keywords)

    try:
        lines = LESSONS_FILE.read_text().split('\n')
        for i, line in enumerate(lines, 1):
            if not line.strip() or line.startswith('#'):
                continue

            line_lower = line.lower()
            line_words = set(re.findall(r'[a-z]{3,}', line_lower))
            score = len(kw_set & line_words)

            if score >= MIN_RELEVANCE_SCORE:
                # Create preview (first 40 chars)
                preview = line.strip()[:40]
                if len(line.strip()) > 40:
                    preview += "..."
                matches.append((i, preview, score))
    except Exception:
        return []

    matches.sort(key=lambda x: -x[2])
    return matches[:MAX_LESSON_POINTERS]


# =============================================================================
# FORMAT OUTPUT
# =============================================================================

def format_pointers(
    files: list[FilePointer],
    tools: list[tuple[str, str, int]],
    lessons: list[tuple[int, str, int]],
) -> str:
    """Format pointers for injection. Budget: <100 tokens."""
    if not files and not tools and not lessons:
        return ""

    total_items = len(files) + len(tools) + len(lessons)
    if total_items > MAX_TOTAL_POINTERS:
        # Trim to budget - prioritize tools, then lessons, then files
        while len(files) + len(tools) + len(lessons) > MAX_TOTAL_POINTERS:
            if files:
                files.pop()
            elif lessons and len(lessons) > 1:
                lessons.pop()
            else:
                break

    parts = []

    # Header - minimal
    parts.append("📍 POSSIBLY RELEVANT (investigate if useful):")

    # Files/folders
    if files:
        for fp in files:
            parts.append(f"  • {fp.path}")

    # Tools
    if tools:
        for tool, desc, _ in tools:
            parts.append(f"  • /{tool} - {desc}")

    # Lessons (line pointers only)
    if lessons:
        for line_num, preview, _ in lessons:
            parts.append(f"  • __lessons.md:{line_num} - {preview}")

    return "\n".join(parts)


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

    prompt = input_data.get("user_prompt", "") or input_data.get("prompt", "")

    # Skip short/trivial prompts
    if not prompt or len(prompt) < 15:
        print(json.dumps({}))
        sys.exit(0)

    # Skip meta prompts (commit, status, etc.)
    if re.match(r'^(commit|push|status|help|yes|no|ok|thanks)\b', prompt.lower()):
        print(json.dumps({}))
        sys.exit(0)

    # Extract keywords
    keywords = extract_keywords(prompt)
    if len(keywords) < 2:
        print(json.dumps({}))
        sys.exit(0)

    # Match against indices
    files = match_files(keywords)
    tools = match_tools(keywords)
    lessons = match_lessons(keywords)

    # Only output if we found something meaningful
    total_score = (
        sum(f.score for f in files) +
        sum(t[2] for t in tools) +
        sum(l[2] for l in lessons)
    )

    if total_score < MIN_RELEVANCE_SCORE:
        print(json.dumps({}))
        sys.exit(0)

    # Format and output
    context = format_pointers(files, tools, lessons)

    if context:
        print(json.dumps({"additionalContext": context}))
    else:
        print(json.dumps({}))

    sys.exit(0)


if __name__ == "__main__":
    main()
