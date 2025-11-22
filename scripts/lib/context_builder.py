#!/usr/bin/env python3
"""
Context Builder for Council Consultations (v2)
==========================================

Enriches council proposals with relevant project context.
Fixes from void analysis:
- Explicit error handling (no silent failures)
- Audit trail (logs enriched context)
- Structured output (dict, not pre-formatted string)
- Configurable limits

Usage:
    from context_builder import build_council_context
    result = build_council_context("Should we migrate to GraphQL?", "session-123")
    if result["success"]:
        enriched = result["formatted"]
    else:
        print(f"Error: {result['error']}")
"""
import os
import re
import json
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime

# Setup logging
logger = logging.getLogger(__name__)


class ContextBuildError(Exception):
    """Raised when context building fails critically"""
    pass


# Configuration (can be overridden)
class ContextConfig:
    """Configuration for context builder"""
    STOP_WORDS = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
        "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "will",
        "with", "we", "should", "can", "could", "would", "this", "what", "when",
        "where", "who", "how", "why", "i", "you", "they", "them", "their", "our"
    }

    # Scoring weights
    SUMMARY_SCORE_WEIGHT = 2
    TOPIC_SCORE_WEIGHT = 3
    ENTITY_SCORE_WEIGHT = 1

    # Limits
    TOP_MEMORIES = 3
    TOP_SESSIONS = 3
    TOP_FILES_READ = 5
    TOP_KEYWORDS = 10
    MIN_SECTION_LENGTH = 20
    MIN_KEYWORD_LENGTH = 3

    # Timeouts
    GIT_TIMEOUT = 5

    # Paths (relative to project root)
    MEMORY_DIR = ".claude/memory"
    LESSONS_FILE = "lessons.md"
    DECISIONS_FILE = "decisions.md"
    DIGESTS_DIR = "session_digests"
    AUDIT_DIR = "context_audit"

    # Project root marker
    ROOT_MARKER = "scripts/lib/core.py"


def find_project_root(start_path: str = None) -> Optional[Path]:
    """
    Find project root by walking up directory tree looking for marker file.

    Returns:
        Path to project root, or None if not found
    """
    if start_path is None:
        start_path = os.path.abspath(__file__)

    current = Path(start_path).resolve()

    # Walk up to root
    while str(current) != "/":
        marker = current / ContextConfig.ROOT_MARKER
        if marker.exists():
            logger.debug(f"Found project root: {current}")
            return current
        current = current.parent

    logger.error(f"Could not find project root (looking for {ContextConfig.ROOT_MARKER})")
    return None


def extract_keywords(text: str, min_length: int = None) -> List[str]:
    """Extract significant keywords from text"""
    if min_length is None:
        min_length = ContextConfig.MIN_KEYWORD_LENGTH

    # Tokenize
    tokens = re.findall(r'\b\w+\b', text.lower())

    # Filter stop words and short tokens
    keywords = [
        t for t in tokens
        if t not in ContextConfig.STOP_WORDS and len(t) >= min_length
    ]

    # Return unique keywords (preserve order)
    seen = set()
    unique = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            unique.append(k)

    return unique


def search_memories(keywords: List[str], project_root: Path) -> Dict[str, List[str]]:
    """
    Search lessons.md and decisions.md for keyword matches.

    Raises:
        FileNotFoundError: If memory directory doesn't exist
        PermissionError: If files can't be read
    """
    memory_dir = project_root / ContextConfig.MEMORY_DIR

    if not memory_dir.exists():
        raise FileNotFoundError(f"Memory directory not found: {memory_dir}")

    results = {"lessons": [], "decisions": []}

    for memory_type in ["lessons", "decisions"]:
        file_path = memory_dir / f"{memory_type}.md"

        if not file_path.exists():
            logger.warning(f"Memory file not found: {file_path}")
            continue

        try:
            content = file_path.read_text()
        except PermissionError as e:
            raise PermissionError(f"Cannot read {file_path}: {e}")
        except UnicodeDecodeError as e:
            logger.error(f"Encoding error in {file_path}: {e}")
            continue

        # Split into sections
        sections = re.split(r'\n\s*\n', content)

        # Score each section by keyword density
        scored_sections = []
        for section in sections:
            if len(section.strip()) < ContextConfig.MIN_SECTION_LENGTH:
                continue

            section_lower = section.lower()
            matches = sum(1 for kw in keywords if kw in section_lower)

            if matches > 0:
                scored_sections.append((matches, section.strip()))

        # Sort by score and take top N
        scored_sections.sort(reverse=True, key=lambda x: x[0])
        top_matches = [s[1] for s in scored_sections[:ContextConfig.TOP_MEMORIES]]

        results[memory_type] = top_matches

    return results


def find_related_sessions(keywords: List[str], project_root: Path, current_session: str) -> List[Dict]:
    """
    Find session digests with similar topics.

    Returns:
        List of related session dicts, or empty list if directory doesn't exist
    """
    digests_dir = project_root / ContextConfig.MEMORY_DIR / ContextConfig.DIGESTS_DIR

    if not digests_dir.exists():
        logger.warning(f"Session digests directory not found: {digests_dir}")
        return []

    scored_sessions = []
    corrupted_files = []

    for digest_file in digests_dir.glob("*.json"):
        # Skip current session and temp files
        if str(digest_file.stem) == current_session or digest_file.stem.startswith("tmp."):
            continue

        try:
            with open(digest_file) as f:
                digest = json.load(f)
        except json.JSONDecodeError as e:
            corrupted_files.append(str(digest_file))
            logger.warning(f"Corrupted session digest: {digest_file} ({e})")
            continue
        except Exception as e:
            logger.error(f"Error reading {digest_file}: {e}")
            continue

        # Calculate relevance score
        score = 0

        summary = digest.get("summary", "").lower()
        score += sum(ContextConfig.SUMMARY_SCORE_WEIGHT for kw in keywords if kw in summary)

        topic = digest.get("current_topic", "").lower()
        score += sum(ContextConfig.TOPIC_SCORE_WEIGHT for kw in keywords if kw in topic)

        entities = [e.lower() for e in digest.get("active_entities", [])]
        score += sum(ContextConfig.ENTITY_SCORE_WEIGHT for kw in keywords if any(kw in e for e in entities))

        if score > 0:
            scored_sessions.append((score, digest))

    if corrupted_files:
        logger.warning(f"Found {len(corrupted_files)} corrupted session files: {corrupted_files}")

    # Sort by score and return top N
    scored_sessions.sort(reverse=True, key=lambda x: x[0])
    return [s[1] for s in scored_sessions[:ContextConfig.TOP_SESSIONS]]


def get_session_state(session_id: str, project_root: Path) -> Dict:
    """
    Load current session state.

    Returns:
        Dict with session state, or default values if file not found

    Raises:
        PermissionError: If state file exists but can't be read
    """
    state_file = project_root / ContextConfig.MEMORY_DIR / f"session_{session_id}_state.json"

    default_state = {
        "confidence": 0,
        "risk": 0,
        "tier": "IGNORANCE",
        "evidence_count": 0,
        "files_read": [],
        "tools_used": []
    }

    if not state_file.exists():
        logger.debug(f"Session state file not found: {state_file}")
        return default_state

    try:
        with open(state_file) as f:
            state = json.load(f)
    except PermissionError as e:
        raise PermissionError(f"Cannot read session state: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Corrupted session state file: {e}")
        return default_state

    # Extract relevant fields
    confidence = state.get("confidence", 0)
    tier = state.get("tier", "IGNORANCE")
    risk = state.get("risk", 0)

    # Extract evidence stats
    evidence = state.get("evidence_ledger", [])
    evidence_count = len(evidence)

    # Get unique files read
    files_read = list(set(
        e.get("file_path", "")
        for e in evidence
        if e.get("tool") == "Read" and e.get("file_path")
    ))[:ContextConfig.TOP_FILES_READ]

    # Get unique tools used
    tools_used = list(set(
        e.get("tool", "")
        for e in evidence
        if e.get("tool")
    ))

    return {
        "confidence": confidence,
        "risk": risk,
        "tier": tier,
        "evidence_count": evidence_count,
        "files_read": files_read,
        "tools_used": tools_used
    }


def get_git_status(project_root: Path) -> Dict[str, str]:
    """
    Get current git branch and uncommitted changes summary.

    Returns:
        Dict with 'branch', 'changes', 'error' keys
        - If git unavailable/fails, 'error' key will be present
    """
    result = {"branch": None, "changes": None, "error": None}

    try:
        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=ContextConfig.GIT_TIMEOUT
        )

        if branch_result.returncode == 0:
            result["branch"] = branch_result.stdout.strip()
        else:
            # Not a git repo or git error
            result["error"] = f"Git branch check failed: {branch_result.stderr.strip()}"
            logger.warning(result["error"])
            return result

        # Get uncommitted changes summary
        status_result = subprocess.run(
            ["git", "status", "--short"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=ContextConfig.GIT_TIMEOUT
        )

        if status_result.returncode == 0:
            lines = status_result.stdout.strip().split("\n")
            modified = len([l for l in lines if l.startswith(" M") or l.startswith("M ")])
            added = len([l for l in lines if l.startswith("A ") or l.startswith("??")])
            deleted = len([l for l in lines if l.startswith(" D") or l.startswith("D ")])

            result["changes"] = f"{modified} modified, {added} added, {deleted} deleted"
        else:
            result["error"] = f"Git status check failed: {status_result.stderr.strip()}"
            logger.warning(result["error"])

        return result

    except FileNotFoundError:
        result["error"] = "Git binary not found in PATH"
        logger.error(result["error"])
        return result
    except subprocess.TimeoutExpired:
        result["error"] = f"Git command timed out after {ContextConfig.GIT_TIMEOUT}s"
        logger.error(result["error"])
        return result
    except Exception as e:
        result["error"] = f"Git command failed: {e}"
        logger.error(result["error"])
        return result


def save_context_audit(session_id: str, proposal: str, context_data: Dict, project_root: Path):
    """
    Save audit trail of enriched context.

    Creates: .claude/memory/context_audit/<session_id>_<timestamp>.json
    """
    audit_dir = project_root / ContextConfig.MEMORY_DIR / ContextConfig.AUDIT_DIR
    audit_dir.mkdir(exist_ok=True, parents=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_file = audit_dir / f"{session_id}_{timestamp}.json"

    audit_data = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "proposal": proposal,
        "context": context_data
    }

    try:
        with open(audit_file, "w") as f:
            json.dump(audit_data, f, indent=2)
        logger.info(f"Context audit saved: {audit_file}")
    except Exception as e:
        logger.error(f"Failed to save context audit: {e}")


def format_context(proposal: str, context_data: Dict, project_root: Path) -> str:
    """Format enriched context as string for council consumption"""
    parts = []

    # Section 1: Original Proposal
    parts.append("PROPOSAL:")
    parts.append(proposal)
    parts.append("")

    # Section 2: Project Context
    parts.append("PROJECT CONTEXT:")
    repo_name = project_root.name if project_root else "unknown"
    parts.append(f"- Repository: {repo_name}")

    git = context_data.get("git_status", {})
    if git.get("error"):
        parts.append(f"- Git: {git['error']}")
    else:
        parts.append(f"- Current Branch: {git.get('branch', 'unknown')}")
        parts.append(f"- Working Tree: {git.get('changes', 'unknown')}")
    parts.append("")

    # Section 3: Session State
    session = context_data.get("session_state", {})
    parts.append("SESSION STATE:")
    parts.append(f"- Confidence: {session.get('confidence', 0)}% ({session.get('tier', 'UNKNOWN')} tier)")
    parts.append(f"- Risk: {session.get('risk', 0)}%")
    parts.append(f"- Evidence Gathered: {session.get('evidence_count', 0)} items")

    if session.get('files_read'):
        files_str = ", ".join(session['files_read'])
        parts.append(f"- Files Examined: {files_str}")

    if session.get('tools_used'):
        tools_str = ", ".join(session['tools_used'])
        parts.append(f"- Tools Used: {tools_str}")
    parts.append("")

    # Section 4: Relevant Memories
    memories = context_data.get("memories", {})
    if memories.get('lessons') or memories.get('decisions'):
        parts.append("RELEVANT MEMORIES:")

        if memories.get('lessons'):
            parts.append("\nLessons:")
            for lesson in memories['lessons']:
                preview = lesson if len(lesson) < 200 else lesson[:200] + "..."
                parts.append(f"  - {preview}")

        if memories.get('decisions'):
            parts.append("\nDecisions:")
            for decision in memories['decisions']:
                preview = decision if len(decision) < 200 else decision[:200] + "..."
                parts.append(f"  - {preview}")
        parts.append("")

    # Section 5: Related Sessions
    sessions = context_data.get("related_sessions", [])
    if sessions:
        parts.append("RELATED PAST SESSIONS:")
        for session in sessions:
            summary = session.get("summary", "No summary")
            topic = session.get("current_topic", "Unknown topic")
            parts.append(f"  - Topic: {topic}")
            parts.append(f"    Summary: {summary}")
        parts.append("")

    # Section 6: Keywords
    keywords = context_data.get("keywords", [])
    if keywords:
        keywords_str = ", ".join(keywords[:ContextConfig.TOP_KEYWORDS])
        parts.append(f"KEYWORDS EXTRACTED: {keywords_str}")
        parts.append("")

    return "\n".join(parts)


def build_council_context(
    proposal: str,
    session_id: str = "unknown",
    project_root: Path = None,
    save_audit: bool = True
) -> Dict:
    """
    Build enriched context for council consultation.

    Args:
        proposal: The original proposal text
        session_id: Current session ID
        project_root: Project root directory (auto-detected if None)
        save_audit: Whether to save audit trail

    Returns:
        Dict with:
            - success: bool
            - formatted: str (enriched context, if success=True)
            - raw_data: dict (structured context data, if success=True)
            - error: str (error message, if success=False)
            - warnings: list of warning messages
    """
    warnings = []

    # Find project root
    if project_root is None:
        project_root = find_project_root()
        if project_root is None:
            return {
                "success": False,
                "error": f"Could not find project root (looking for {ContextConfig.ROOT_MARKER})",
                "warnings": []
            }

    try:
        # Extract keywords
        keywords = extract_keywords(proposal)
        if not keywords:
            warnings.append("No keywords extracted from proposal")

        # Gather context from multiple sources
        try:
            session_state = get_session_state(session_id, project_root)
        except PermissionError as e:
            return {"success": False, "error": str(e), "warnings": warnings}

        try:
            memories = search_memories(keywords, project_root)
        except FileNotFoundError as e:
            warnings.append(f"Memory directory not found: {e}")
            memories = {"lessons": [], "decisions": []}
        except PermissionError as e:
            return {"success": False, "error": str(e), "warnings": warnings}

        related_sessions = find_related_sessions(keywords, project_root, session_id)
        git_status = get_git_status(project_root)

        if git_status.get("error"):
            warnings.append(git_status["error"])

        # Build context data structure
        context_data = {
            "keywords": keywords,
            "session_state": session_state,
            "memories": memories,
            "related_sessions": related_sessions,
            "git_status": git_status
        }

        # Format as string
        formatted = format_context(proposal, context_data, project_root)

        # Save audit trail
        if save_audit:
            try:
                save_context_audit(session_id, proposal, context_data, project_root)
            except Exception as e:
                warnings.append(f"Failed to save audit trail: {e}")

        return {
            "success": True,
            "formatted": formatted,
            "raw_data": context_data,
            "warnings": warnings
        }

    except Exception as e:
        logger.exception("Unexpected error building context")
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "warnings": warnings
        }


# Test harness
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    if len(sys.argv) < 2:
        print("Usage: python3 context_builder_v2.py '<proposal>' [session_id]")
        sys.exit(1)

    proposal = sys.argv[1]
    session_id = sys.argv[2] if len(sys.argv) > 2 else "test-session"

    result = build_council_context(proposal, session_id)

    print("=" * 70)
    if result["success"]:
        print("✅ ENRICHED CONTEXT FOR COUNCIL")
        print("=" * 70)
        print(result["formatted"])
        print("=" * 70)

        if result["warnings"]:
            print("\n⚠️  WARNINGS:")
            for warning in result["warnings"]:
                print(f"  - {warning}")

        print(f"\n📊 Context Stats:")
        raw = result["raw_data"]
        print(f"  - Keywords: {len(raw['keywords'])}")
        print(f"  - Lessons: {len(raw['memories']['lessons'])}")
        print(f"  - Decisions: {len(raw['memories']['decisions'])}")
        print(f"  - Related Sessions: {len(raw['related_sessions'])}")
    else:
        print("❌ CONTEXT BUILD FAILED")
        print("=" * 70)
        print(f"Error: {result['error']}")
        if result["warnings"]:
            print("\nWarnings:")
            for warning in result["warnings"]:
                print(f"  - {warning}")
        sys.exit(1)
