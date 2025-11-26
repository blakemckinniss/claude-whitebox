#!/usr/bin/env python3
"""
Session State Machine v3: The brain of the hook system.

This module maintains a comprehensive state of the current session:
- What files have been read/edited
- What libraries are being used vs researched
- What domain of work we're in (infra, dev, exploration)
- What errors have occurred
- What patterns are emerging

Other hooks import this module to:
- Update state (PostToolUse)
- Query state for gaps (PreToolUse)
- Inject relevant context (UserPromptSubmit)

Design Principles:
- Silent by default (only surface gaps)
- Domain-aware (infra ≠ development ≠ research)
- Accumulated (patterns over session, not single actions)
- Specific (reference actual files/tools, not generic advice)
"""

import json
import time
import re
import os
import tempfile
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict

# =============================================================================
# PATHS
# =============================================================================

HOOK_DIR = Path(__file__).resolve().parent
MEMORY_DIR = HOOK_DIR.parent / "memory"
STATE_FILE = MEMORY_DIR / "session_state_v3.json"
OPS_DIR = Path(__file__).resolve().parent.parent.parent / ".claude" / "ops"

# =============================================================================
# DOMAIN DETECTION
# =============================================================================

class Domain:
    UNKNOWN = "unknown"
    INFRASTRUCTURE = "infrastructure"  # gcloud, aws, docker, k8s
    DEVELOPMENT = "development"        # editing code, debugging
    EXPLORATION = "exploration"        # reading, understanding codebase
    DATA = "data"                      # jupyter, pandas, SQL

DOMAIN_SIGNALS = {
    Domain.INFRASTRUCTURE: [
        r"gcloud\s+",
        r"aws\s+",
        r"docker\s+",
        r"kubectl\s+",
        r"terraform\s+",
        r"--region",
        r"--project",
        r"deploy",
        r"service",
        r"secrets?",
    ],
    Domain.DEVELOPMENT: [
        r"\.py$",
        r"\.js$",
        r"\.ts$",
        r"\.rs$",
        r"npm\s+(run|test|build)",
        r"pytest",
        r"cargo\s+(build|test|run)",
        r"function\s+\w+",
        r"class\s+\w+",
        r"def\s+\w+",
    ],
    Domain.EXPLORATION: [
        r"what\s+(is|does|are)",
        r"how\s+(does|do|to)",
        r"explain",
        r"understand",
        r"find.*file",
        r"where\s+is",
        r"show\s+me",
    ],
    Domain.DATA: [
        r"\.ipynb",
        r"pandas",
        r"dataframe",
        r"sql",
        r"query",
        r"\.csv",
        r"\.parquet",
    ],
}

# =============================================================================
# LIBRARY DETECTION
# =============================================================================

# Libraries that should be researched before use (fast-moving, complex APIs)
RESEARCH_REQUIRED_LIBS = {
    # Python
    "fastapi", "pydantic", "langchain", "llamaindex", "anthropic", "openai",
    "polars", "duckdb", "streamlit", "gradio", "transformers", "torch",
    "boto3", "playwright", "httpx", "aiohttp",
    # JavaScript
    "next", "nuxt", "remix", "astro", "svelte",
    # Cloud SDKs
    "@google-cloud", "@aws-sdk", "@azure",
}

# Standard libraries that don't need research
STDLIB_PATTERNS = [
    r"^(os|sys|json|re|time|datetime|pathlib|subprocess|typing|collections|itertools)$",
    r"^(math|random|string|io|functools|operator|contextlib|abc|dataclasses)$",
]

# =============================================================================
# STATE SCHEMA
# =============================================================================

@dataclass
class SessionState:
    """Comprehensive session state."""

    # Identity
    session_id: str = ""
    started_at: float = 0

    # Domain detection
    domain: str = Domain.UNKNOWN
    domain_signals: list = field(default_factory=list)
    domain_confidence: float = 0.0

    # File tracking
    files_read: list = field(default_factory=list)
    files_edited: list = field(default_factory=list)
    files_created: list = field(default_factory=list)

    # Library tracking
    libraries_used: list = field(default_factory=list)
    libraries_researched: list = field(default_factory=list)

    # Command tracking
    commands_succeeded: list = field(default_factory=list)
    commands_failed: list = field(default_factory=list)

    # Error tracking
    errors_recent: list = field(default_factory=list)  # Last 10
    errors_unresolved: list = field(default_factory=list)

    # Pattern tracking
    edit_counts: dict = field(default_factory=dict)  # file -> count
    tool_counts: dict = field(default_factory=dict)  # tool -> count
    tests_run: bool = False
    last_verify: Optional[float] = None
    last_deploy: Optional[dict] = None

    # Gap tracking
    gaps_detected: list = field(default_factory=list)
    gaps_surfaced: list = field(default_factory=list)  # Already shown to user

    # Ops scripts available
    ops_scripts: list = field(default_factory=list)

    # Synapse tracking (v3)
    turn_count: int = 0
    last_5_tools: list = field(default_factory=list)  # For iteration detection
    ops_turns: dict = field(default_factory=dict)  # op_name -> last turn
    directives_fired: int = 0
    confidence: int = 0  # 0-100%
    evidence_ledger: list = field(default_factory=list)  # Evidence items

    # Meta-cognition: Goal Anchor (v3.1)
    original_goal: str = ""  # First substantive user prompt
    goal_set_turn: int = 0  # Turn when goal was set
    goal_keywords: list = field(default_factory=list)  # Key terms from goal

    # Meta-cognition: Sunk Cost Detector (v3.1)
    approach_history: list = field(default_factory=list)  # [{approach, turns, failures}]
    consecutive_failures: int = 0  # Same approach failures
    last_failure_turn: int = 0

    # Batch Tracking (pattern detection only, no blocking)
    consecutive_single_reads: int = 0  # Sequential single Read/Grep/Glob messages
    pending_files: list = field(default_factory=list)  # Files mentioned but not read
    pending_searches: list = field(default_factory=list)  # Searches mentioned but not run
    last_message_tool_count: int = 0  # Tools in last message

    # Integration Blindness Prevention (v3.3)
    pending_integration_greps: list = field(default_factory=list)  # [{function, file, turn}]

    # Nudge Tracking (v3.4) - prevents repetitive warnings, enables escalation
    # Format: {nudge_type: {last_turn, times_shown, times_ignored, last_content_hash}}
    nudge_history: dict = field(default_factory=dict)

# =============================================================================
# STATE MANAGEMENT
# =============================================================================

def _ensure_memory_dir():
    """Ensure memory directory exists."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

def load_state() -> SessionState:
    """Load session state from file."""
    _ensure_memory_dir()

    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
                return SessionState(**data)
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    # Initialize new state
    state = SessionState(
        session_id=os.environ.get("CLAUDE_SESSION_ID", "")[:16] or f"ses_{int(time.time())}",
        started_at=time.time(),
        ops_scripts=_discover_ops_scripts(),
    )
    save_state(state)
    return state

def save_state(state: SessionState):
    """Save session state to file (atomic write to prevent corruption)."""
    _ensure_memory_dir()

    # Trim lists to prevent unbounded growth
    state.files_read = state.files_read[-50:]
    state.files_edited = state.files_edited[-50:]
    state.commands_succeeded = state.commands_succeeded[-20:]
    state.commands_failed = state.commands_failed[-20:]
    state.errors_recent = state.errors_recent[-10:]
    state.domain_signals = state.domain_signals[-20:]
    state.gaps_detected = state.gaps_detected[-10:]
    state.gaps_surfaced = state.gaps_surfaced[-10:]
    state.last_5_tools = state.last_5_tools[-5:]
    state.evidence_ledger = state.evidence_ledger[-20:]

    # Atomic write: write to temp file, then rename (prevents corruption from concurrent writes)
    try:
        fd, tmp_path = tempfile.mkstemp(dir=MEMORY_DIR, suffix='.json')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(asdict(state), f, indent=2, default=str)
            os.replace(tmp_path, STATE_FILE)  # Atomic on POSIX
        except Exception:
            # Clean up temp file on failure
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
    except (IOError, OSError):
        # Fallback to direct write if atomic fails
        with open(STATE_FILE, 'w') as f:
            json.dump(asdict(state), f, indent=2, default=str)

def reset_state():
    """Reset state for new session."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    return load_state()

# =============================================================================
# DOMAIN DETECTION
# =============================================================================

def detect_domain(state: SessionState) -> tuple[str, float]:
    """Detect domain from accumulated signals."""
    if not state.domain_signals:
        return Domain.UNKNOWN, 0.0

    # Count matches per domain
    scores = {d: 0 for d in [Domain.INFRASTRUCTURE, Domain.DEVELOPMENT,
                              Domain.EXPLORATION, Domain.DATA]}

    combined_signals = " ".join(state.domain_signals[-20:]).lower()

    for domain, patterns in DOMAIN_SIGNALS.items():
        for pattern in patterns:
            matches = len(re.findall(pattern, combined_signals, re.IGNORECASE))
            scores[domain] += matches

    # Find winner
    if max(scores.values()) == 0:
        return Domain.UNKNOWN, 0.0

    winner = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = scores[winner] / total if total > 0 else 0

    return winner, confidence

def add_domain_signal(state: SessionState, signal: str):
    """Add a signal for domain detection."""
    state.domain_signals.append(signal)
    state.domain, state.domain_confidence = detect_domain(state)

# =============================================================================
# FILE TRACKING
# =============================================================================

def track_file_read(state: SessionState, filepath: str):
    """Track that a file was read."""
    if filepath and filepath not in state.files_read:
        state.files_read.append(filepath)
    add_domain_signal(state, filepath)

def track_file_edit(state: SessionState, filepath: str):
    """Track that a file was edited."""
    if filepath:
        if filepath not in state.files_edited:
            state.files_edited.append(filepath)
        state.edit_counts[filepath] = state.edit_counts.get(filepath, 0) + 1
    add_domain_signal(state, filepath)

def track_file_create(state: SessionState, filepath: str):
    """Track that a file was created."""
    if filepath and filepath not in state.files_created:
        state.files_created.append(filepath)
    add_domain_signal(state, filepath)

def was_file_read(state: SessionState, filepath: str) -> bool:
    """Check if a file was read this session."""
    return filepath in state.files_read

# =============================================================================
# LIBRARY TRACKING
# =============================================================================

def extract_libraries_from_code(code: str) -> list:
    """Extract library imports from code."""
    libs = []

    # Python imports
    py_imports = re.findall(r'(?:from|import)\s+([\w.]+)', code)
    libs.extend(py_imports)

    # JavaScript requires/imports
    js_imports = re.findall(r"(?:require|from)\s*['\"]([^'\"]+)['\"]", code)
    libs.extend(js_imports)

    # Clean up
    cleaned = []
    for lib in libs:
        # Get top-level package
        top_level = lib.split('.')[0].split('/')[0]
        if top_level and not _is_stdlib(top_level):
            cleaned.append(top_level)

    return list(set(cleaned))

def _is_stdlib(lib: str) -> bool:
    """Check if library is standard library."""
    for pattern in STDLIB_PATTERNS:
        if re.match(pattern, lib):
            return True
    return False

def track_library_used(state: SessionState, lib: str):
    """Track that a library is being used."""
    if lib and lib not in state.libraries_used:
        state.libraries_used.append(lib)

def track_library_researched(state: SessionState, lib: str):
    """Track that a library was researched."""
    if lib and lib not in state.libraries_researched:
        state.libraries_researched.append(lib)

def needs_research(state: SessionState, lib: str) -> bool:
    """Check if a library needs research before use."""
    if lib in state.libraries_researched:
        return False
    if _is_stdlib(lib):
        return False
    # Check if it's a fast-moving library
    lib_lower = lib.lower()
    for research_lib in RESEARCH_REQUIRED_LIBS:
        if research_lib in lib_lower or lib_lower in research_lib:
            return True
    return False

# =============================================================================
# COMMAND TRACKING
# =============================================================================

def track_command(state: SessionState, command: str, success: bool, output: str = ""):
    """Track a command execution."""
    cmd_record = {
        "command": command[:200],
        "success": success,
        "timestamp": time.time(),
    }

    if success:
        state.commands_succeeded.append(cmd_record)
    else:
        state.commands_failed.append(cmd_record)
        track_error(state, f"Command failed: {command[:100]}", output[:500])

    add_domain_signal(state, command)

    # Check for specific patterns
    if "pytest" in command or "npm test" in command or "cargo test" in command:
        state.tests_run = True

    if "verify.py" in command:
        state.last_verify = time.time()

    if "deploy" in command.lower():
        state.last_deploy = {
            "command": command[:200],
            "timestamp": time.time(),
            "success": success,
        }

    # Check for research commands
    if "research.py" in command or "probe.py" in command:
        # Try to extract what was researched
        parts = command.split()
        for i, part in enumerate(parts):
            if part in ["research.py", "probe.py"] and i + 1 < len(parts):
                topic = parts[i + 1].strip("'\"")
                track_library_researched(state, topic)

# =============================================================================
# ERROR TRACKING
# =============================================================================

def track_error(state: SessionState, error_type: str, details: str = ""):
    """Track an error."""
    error = {
        "type": error_type,
        "details": details[:500],
        "timestamp": time.time(),
        "resolved": False,
    }
    state.errors_recent.append(error)
    state.errors_unresolved.append(error)

def resolve_error(state: SessionState, error_pattern: str):
    """Mark errors matching pattern as resolved."""
    state.errors_unresolved = [
        e for e in state.errors_unresolved
        if error_pattern.lower() not in e.get("type", "").lower()
        and error_pattern.lower() not in e.get("details", "").lower()
    ]

def has_unresolved_errors(state: SessionState) -> bool:
    """Check if there are unresolved errors."""
    # Only consider errors from last 10 minutes
    cutoff = time.time() - 600
    recent_unresolved = [e for e in state.errors_unresolved if e.get("timestamp", 0) > cutoff]
    return len(recent_unresolved) > 0

# =============================================================================
# GAP DETECTION
# =============================================================================

@dataclass
class Gap:
    """A detected gap in the workflow."""
    type: str
    message: str
    suggestion: str
    severity: str = "warn"  # warn, block
    context: dict = field(default_factory=dict)

def detect_gaps(state: SessionState, context: dict = None) -> list[Gap]:
    """Detect gaps based on current state and context."""
    gaps = []
    context = context or {}

    tool_name = context.get("tool_name", "")
    tool_input = context.get("tool_input", {})

    # Gap: Editing file without reading
    if tool_name in ["Edit", "Write"]:
        filepath = tool_input.get("file_path", "")
        # Check if file was read OR already edited this session
        file_seen = was_file_read(state, filepath) or filepath in state.files_edited
        if filepath and not file_seen:
            # Exceptions:
            # 1. New files in .claude/scratch/
            # 2. File doesn't exist (new file creation)
            # 3. Explicitly marked as new_file
            # 4. For Edit: old_string exists in file (implicit proof we have context)
            file_exists = Path(filepath).exists() if filepath else False
            is_scratch = ".claude/scratch/" in filepath

            # Fallback: if old_string matches file content, state tracking failed but we have context
            has_implicit_context = False
            if tool_name == "Edit" and file_exists:
                old_string = tool_input.get("old_string", "")
                if old_string and len(old_string) > 20:  # Non-trivial match
                    try:
                        with open(filepath, 'r') as f:
                            content = f.read()
                        has_implicit_context = old_string in content
                    except (IOError, OSError, UnicodeDecodeError):
                        pass
            is_new_file = tool_input.get("new_file", False)

            if file_exists and not is_scratch and not is_new_file and not has_implicit_context:
                gaps.append(Gap(
                    type="edit_without_read",
                    message=f"Editing `{Path(filepath).name}` without reading it first",
                    suggestion="Read the file first to understand its structure",
                    severity="block",
                    context={"filepath": filepath}
                ))

    # Gap: Using library without research
    if tool_name in ["Edit", "Write"]:
        code = tool_input.get("new_string", "") or tool_input.get("content", "")
        if code:
            libs = extract_libraries_from_code(code)
            for lib in libs:
                if needs_research(state, lib):
                    gaps.append(Gap(
                        type="library_not_researched",
                        message=f"Using `{lib}` without verifying its API",
                        suggestion=f"Run: research.py '{lib} api' or probe.py '{lib}'",
                        severity="warn",
                        context={"library": lib}
                    ))

    # Gap: Multiple edits without testing
    for filepath, count in state.edit_counts.items():
        if count >= 3 and not state.tests_run:
            if filepath not in [g.get("context", {}).get("filepath") for g in state.gaps_surfaced]:
                gaps.append(Gap(
                    type="multiple_edits_no_test",
                    message=f"Edited `{Path(filepath).name}` {count}x without running tests",
                    suggestion="Run tests to verify changes work",
                    severity="warn",
                    context={"filepath": filepath, "count": count}
                ))

    # Gap: Deploying without testing
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if "deploy" in command.lower() and not state.tests_run:
            gaps.append(Gap(
                type="deploy_without_test",
                message="Deploying without running tests",
                suggestion="Consider running tests before deployment",
                severity="warn",
                context={"command": command[:100]}
            ))

    # Gap: Unresolved errors
    if has_unresolved_errors(state) and tool_name not in ["Read", "Grep", "Glob"]:
        recent = state.errors_unresolved[-1] if state.errors_unresolved else {}
        gaps.append(Gap(
            type="unresolved_error",
            message=f"Unresolved error: {recent.get('type', 'unknown')[:50]}",
            suggestion="Fix the error before proceeding",
            severity="warn",
            context={"error": recent}
        ))

    return gaps

def surface_gap(state: SessionState, gap: Gap):
    """Mark a gap as surfaced (shown to user)."""
    state.gaps_surfaced.append(asdict(gap))

# =============================================================================
# OPS SCRIPT DISCOVERY
# =============================================================================

def _discover_ops_scripts() -> list:
    """Discover available ops scripts."""
    scripts = []
    if OPS_DIR.exists():
        for f in OPS_DIR.glob("*.py"):
            scripts.append(f.stem)
    return scripts

def get_relevant_ops_script(state: SessionState, action: str) -> Optional[dict]:
    """Get relevant ops script for an action."""
    action_lower = action.lower()

    # Map actions to ops scripts
    mappings = {
        "research": ["search", "docs", "documentation", "lookup", "find info"],
        "probe": ["inspect", "api", "signature", "method", "attribute"],
        "xray": ["find class", "find function", "ast", "structure"],
        "verify": ["check", "confirm", "exists", "test command"],
        "audit": ["security", "vulnerability", "injection", "secrets"],
        "void": ["stub", "todo", "incomplete", "notimplemented"],
        "think": ["decompose", "break down", "analyze", "complex"],
    }

    for script, triggers in mappings.items():
        if script in state.ops_scripts:
            for trigger in triggers:
                if trigger in action_lower:
                    return {
                        "script": script,
                        "command": f"python3 .claude/ops/{script}.py",
                    }

    return None

# =============================================================================
# CONTEXT GENERATION
# =============================================================================

def generate_context(state: SessionState) -> str:
    """Generate context string for injection."""
    parts = []

    # Domain
    if state.domain != Domain.UNKNOWN and state.domain_confidence > 0.3:
        domain_emoji = {
            Domain.INFRASTRUCTURE: "☁️",
            Domain.DEVELOPMENT: "💻",
            Domain.EXPLORATION: "🔍",
            Domain.DATA: "📊",
        }.get(state.domain, "📁")
        parts.append(f"{domain_emoji} Domain: {state.domain} ({state.domain_confidence:.0%})")

    # Files
    if state.files_edited:
        recent_edits = state.files_edited[-3:]
        names = [Path(f).name for f in recent_edits]
        parts.append(f"📝 Edited: {', '.join(names)}")

    # Errors
    if state.errors_unresolved:
        error = state.errors_unresolved[-1]
        parts.append(f"⚠️ Unresolved: {error.get('type', 'error')[:40]}")

    # Deploy status
    if state.last_deploy:
        age = time.time() - state.last_deploy.get("timestamp", 0)
        if age < 600:  # Last 10 minutes
            status = "✅" if state.last_deploy.get("success") else "❌"
            parts.append(f"{status} Deploy: {int(age)}s ago")

    # Tests
    if state.tests_run:
        parts.append("✅ Tests: run")
    elif any(c >= 2 for c in state.edit_counts.values()):
        parts.append("⚠️ Tests: not run")

    return " | ".join(parts) if parts else ""

# =============================================================================
# UTILITY
# =============================================================================

def get_session_summary(state: SessionState) -> dict:
    """Get a summary of the session for debugging."""
    return {
        "session_id": state.session_id,
        "domain": state.domain,
        "domain_confidence": state.domain_confidence,
        "files_read": len(state.files_read),
        "files_edited": len(state.files_edited),
        "libraries_used": state.libraries_used,
        "libraries_researched": state.libraries_researched,
        "tests_run": state.tests_run,
        "errors_unresolved": len(state.errors_unresolved),
        "edit_counts": state.edit_counts,
    }


# =============================================================================
# SYNAPSE TRACKING (v3)
# =============================================================================

def track_tool_usage(state: SessionState, tool_name: str):
    """Track tool usage for iteration detection."""
    state.turn_count += 1
    state.last_5_tools.append(tool_name)
    if len(state.last_5_tools) > 5:
        state.last_5_tools.pop(0)

    # Update tool counts in last 5
    state.tool_counts = {}
    for t in state.last_5_tools:
        state.tool_counts[t] = state.tool_counts.get(t, 0) + 1


def track_ops_command(state: SessionState, command: str):
    """Track ops script execution for directive enforcement."""
    ops_names = ["upkeep", "verify", "audit", "void", "think", "council",
                 "research", "probe", "scope", "spark"]
    for op in ops_names:
        if op in command:
            state.ops_turns[op] = state.turn_count


def get_turns_since_op(state: SessionState, op_name: str) -> int:
    """Get turns since an ops command was run."""
    last_turn = state.ops_turns.get(op_name, -1)
    if last_turn < 0:
        return 999  # Never run
    return state.turn_count - last_turn


def is_iteration_detected(state: SessionState) -> bool:
    """Detect if Claude is in an iteration loop (4+ same tool in 5 turns)."""
    for tool, count in state.tool_counts.items():
        if tool in ("Read", "Grep", "Glob") and count >= 4:
            return True
    return False


def add_evidence(state: SessionState, evidence_type: str, content: str):
    """Add evidence to the ledger."""
    state.evidence_ledger.append({
        "type": evidence_type,
        "content": content[:200],
        "turn": state.turn_count,
        "timestamp": time.time(),
    })


def update_confidence(state: SessionState, delta: int, reason: str = ""):
    """Update confidence level with bounds checking."""
    old = state.confidence
    state.confidence = max(0, min(100, state.confidence + delta))
    if reason:
        add_evidence(state, "confidence_change",
                    f"{old} -> {state.confidence}: {reason}")


# =============================================================================
# GOAL ANCHOR (v3.1)
# =============================================================================

def set_goal(state: SessionState, prompt: str):
    """Set the original goal if not already set."""
    if state.original_goal:
        return  # Goal already set

    # Skip meta/administrative prompts
    skip_patterns = [
        r"^(hi|hello|hey|thanks|ok|yes|no|sure)\b",
        r"^(commit|push|pr|status|help)\b",
        r"^/",  # Slash commands
    ]
    prompt_lower = prompt.lower().strip()
    for pattern in skip_patterns:
        if re.match(pattern, prompt_lower):
            return

    # Extract substantive goal
    state.original_goal = prompt[:200]
    state.goal_set_turn = state.turn_count

    # Extract keywords (nouns/verbs, skip common words)
    stop_words = {"the", "a", "an", "is", "are", "to", "for", "in", "on", "with",
                  "and", "or", "but", "can", "you", "i", "me", "my", "this", "that",
                  "it", "be", "do", "have", "will", "would", "could", "should"}
    words = re.findall(r'\b[a-z]{3,}\b', prompt_lower)
    state.goal_keywords = [w for w in words if w not in stop_words][:10]


def check_goal_drift(state: SessionState, current_activity: str) -> tuple[bool, str]:
    """Check if current activity has drifted from original goal.

    Returns: (is_drifting, drift_message)
    """
    if not state.original_goal or not state.goal_keywords:
        return False, ""

    # Only check after some turns
    if state.turn_count - state.goal_set_turn < 5:
        return False, ""

    # Check keyword overlap
    activity_lower = current_activity.lower()
    matches = sum(1 for kw in state.goal_keywords if kw in activity_lower)
    overlap_ratio = matches / len(state.goal_keywords) if state.goal_keywords else 0

    # Drift if <20% keyword overlap after 5+ turns
    if overlap_ratio < 0.2:
        return True, f"📍 GOAL ANCHOR: \"{state.original_goal[:80]}...\"\n🔀 CURRENT: {current_activity[:60]}\n⚠️ Low overlap ({overlap_ratio:.0%}) - verify alignment"

    return False, ""


# =============================================================================
# SUNK COST DETECTOR (v3.1)
# =============================================================================

def track_approach(state: SessionState, approach_signature: str):
    """Track current approach (file+operation pattern)."""
    # Find or create approach entry
    for entry in state.approach_history:
        if entry.get("signature") == approach_signature:
            entry["turns"] = entry.get("turns", 0) + 1
            return
    state.approach_history.append({
        "signature": approach_signature,
        "turns": 1,
        "failures": 0,
        "start_turn": state.turn_count
    })
    # Limit history
    state.approach_history = state.approach_history[-5:]


def track_failure(state: SessionState, approach_signature: str):
    """Track a failure for the current approach."""
    state.consecutive_failures += 1
    state.last_failure_turn = state.turn_count

    for entry in state.approach_history:
        if entry.get("signature") == approach_signature:
            entry["failures"] = entry.get("failures", 0) + 1


def reset_failures(state: SessionState):
    """Reset failure count (on success)."""
    state.consecutive_failures = 0


def check_sunk_cost(state: SessionState) -> tuple[bool, str]:
    """Check if stuck in sunk cost trap.

    Returns: (is_trapped, nudge_message)
    """
    # Check consecutive failures
    if state.consecutive_failures >= 3:
        return True, f"🔄 SUNK COST: {state.consecutive_failures} consecutive failures.\n💡 If starting fresh, would you still pick this approach?"

    # Check approach with high turns + failures
    for entry in state.approach_history:
        turns = entry.get("turns", 0)
        failures = entry.get("failures", 0)
        if turns >= 5 and failures >= 2:
            sig = entry.get("signature", "unknown")[:40]
            return True, f"🔄 SUNK COST: {turns} turns on `{sig}` with {failures} failures.\n💡 Consider: pivot vs persist?"

    return False, ""


# =============================================================================
# BATCH ENFORCEMENT (v3.2)
# =============================================================================

# Strict batching (local files - you CAN know what you need upfront via ls/find)
STRICT_BATCH_TOOLS = frozenset({"Read", "Grep", "Glob"})
# Soft batching (external URLs - discovery is inherently sequential)
SOFT_BATCH_TOOLS = frozenset({"WebFetch", "WebSearch"})
# Combined for type checking
BATCHABLE_TOOLS = STRICT_BATCH_TOOLS | SOFT_BATCH_TOOLS


def track_batch_tool(state: SessionState, tool_name: str, tools_in_message: int):
    """Track batch/sequential tool usage patterns.

    Args:
        tool_name: Current tool being used
        tools_in_message: Total tool calls in this message (from hook context)
    """
    if tool_name not in BATCHABLE_TOOLS:
        return

    state.last_message_tool_count = tools_in_message

    if tools_in_message == 1:
        state.consecutive_single_reads += 1
    else:
        state.consecutive_single_reads = 0  # Reset on batch


def add_pending_file(state: SessionState, filepath: str):
    """Add a file to pending reads (extracted from prompt/response)."""
    if filepath and filepath not in state.pending_files:
        state.pending_files.append(filepath)
        state.pending_files = state.pending_files[-20:]  # Limit


def add_pending_search(state: SessionState, pattern: str):
    """Add a search pattern to pending searches."""
    if pattern and pattern not in state.pending_searches:
        state.pending_searches.append(pattern)
        state.pending_searches = state.pending_searches[-10:]  # Limit


def clear_pending_file(state: SessionState, filepath: str):
    """Clear a file from pending (after it's been read)."""
    if filepath in state.pending_files:
        state.pending_files.remove(filepath)


def clear_pending_search(state: SessionState, pattern: str):
    """Clear a search from pending (after it's been run)."""
    if pattern in state.pending_searches:
        state.pending_searches.remove(pattern)


def check_pending_items(state: SessionState, tool_name: str, tool_input: dict) -> str:
    """Check if there are pending items that should be batched.

    Returns: Warning message or empty string
    """
    warnings = []

    if tool_name == "Read":
        filepath = tool_input.get("file_path", "")
        if filepath:
            clear_pending_file(state, filepath)

        # Check remaining pending files
        remaining = [f for f in state.pending_files if f != filepath]
        if remaining:
            names = [f.split("/")[-1] for f in remaining[:3]]
            warnings.append(
                f"⚡ PENDING FILES: {names} were mentioned but not read.\n"
                f"Batch them NOW or they'll be forgotten."
            )

    elif tool_name in ("Grep", "Glob"):
        pattern = tool_input.get("pattern", "")
        if pattern:
            clear_pending_search(state, pattern)

        remaining = [s for s in state.pending_searches if s != pattern]
        if remaining:
            warnings.append(
                f"⚡ PENDING SEARCHES: {remaining[:3]} were mentioned but not run."
            )

    return "\n".join(warnings)


# =============================================================================
# INTEGRATION BLINDNESS PREVENTION (v3.3)
# =============================================================================

# Patterns to detect function/method definitions
FUNCTION_PATTERNS = [
    # Python: def function_name(
    (r'\bdef\s+(\w+)\s*\(', 'python'),
    # Python: async def function_name(
    (r'\basync\s+def\s+(\w+)\s*\(', 'python'),
    # JavaScript/TypeScript: function name(
    (r'\bfunction\s+(\w+)\s*\(', 'js'),
    # JavaScript/TypeScript: const/let/var name = function/arrow
    (r'\b(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(', 'js'),
    # JavaScript/TypeScript: name(args) { or name = (args) =>
    (r'\b(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>', 'js'),
    # Class methods: name(args) {
    (r'^\s+(\w+)\s*\([^)]*\)\s*\{', 'js'),
    # Rust: fn name(
    (r'\bfn\s+(\w+)\s*[<(]', 'rust'),
    # Go: func name(
    (r'\bfunc\s+(\w+)\s*\(', 'go'),
]


def extract_function_names(code: str) -> list[str]:
    """Extract function/method names from code snippet."""
    functions = []
    for pattern, _ in FUNCTION_PATTERNS:
        matches = re.findall(pattern, code, re.MULTILINE)
        functions.extend(matches)
    # Dedupe and filter out common non-function matches and entry points
    # Entry points (main, __init__, etc.) don't need caller verification
    skip = {
        # Control flow (false positives from regex)
        'if', 'for', 'while', 'switch', 'catch', 'with', 'return',
        # Standard entry points (no external callers to check)
        'main', '__init__', '__main__', 'setup', 'teardown',
        # Test patterns
        'test', 'setUp', 'tearDown',
        # Common dunder methods
        '__str__', '__repr__', '__eq__', '__hash__',
    }
    return list(set(f for f in functions if f not in skip and len(f) > 1))


def add_pending_integration_grep(state: SessionState, function_name: str, file_path: str):
    """Add a function that needs grep verification after edit."""
    entry = {
        "function": function_name,
        "file": file_path,
        "turn": state.turn_count,
    }
    # Avoid duplicates
    existing = [p["function"] for p in state.pending_integration_greps]
    if function_name not in existing:
        state.pending_integration_greps.append(entry)
    # Limit to prevent unbounded growth
    state.pending_integration_greps = state.pending_integration_greps[-5:]


def clear_integration_grep(state: SessionState, pattern: str):
    """Clear pending integration grep if pattern matches function name."""
    state.pending_integration_greps = [
        p for p in state.pending_integration_greps
        if p["function"] not in pattern and pattern not in p["function"]
    ]


def get_pending_integration_greps(state: SessionState) -> list[dict]:
    """Get pending integration greps (max age: 10 turns)."""
    return [
        p for p in state.pending_integration_greps
        if state.turn_count - p.get("turn", 0) <= 10
    ]


def check_integration_blindness(state: SessionState, tool_name: str, tool_input: dict) -> tuple[bool, str]:
    """Check if there are pending integration greps that should block.

    Returns: (should_block, message)

    NOTE: Clearing of pending greps happens in state_updater.py (PostToolUse)
    to avoid race conditions with other PreToolUse hooks.
    """
    pending = get_pending_integration_greps(state)
    if not pending:
        return False, ""

    # Diagnostic tools are always allowed (needed to investigate/clear)
    diagnostic_tools = {"Read", "Grep", "Glob", "Bash", "BashOutput", "TodoWrite"}
    if tool_name in diagnostic_tools:
        return False, ""

    # Non-code files are allowed - integration blindness only matters for code
    # Editing .md, .json, .txt, .yaml etc. doesn't affect function callers
    if tool_name in {"Edit", "Write"}:
        file_path = tool_input.get("file_path", "")
        non_code_extensions = {".md", ".json", ".txt", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".csv"}
        from pathlib import Path
        if Path(file_path).suffix.lower() in non_code_extensions:
            return False, ""

    # Block with message about pending greps
    func_list = ", ".join(f"`{p['function']}`" for p in pending[:3])
    return True, (
        f"**INTEGRATION BLINDNESS BLOCKED** (Hard Block #14)\n"
        f"Edited functions: {func_list}\n"
        f"REQUIRED: Run `grep -r \"function_name\"` to find callers before continuing.\n"
        f"Pattern: After function edit, grep is MANDATORY."
    )


# =============================================================================
# NUDGE TRACKING (v3.4) - Anti-Amnesia System
# =============================================================================

# Nudge categories with default cooldowns (turns before re-showing)
NUDGE_COOLDOWNS = {
    "goal_drift": 8,           # Goal anchor warnings
    "library_research": 5,     # Unresearched library warnings
    "multiple_edits": 10,      # "Edited X times without tests"
    "unresolved_error": 3,     # Pending errors
    "sunk_cost": 5,            # "3 failures on same approach"
    "batch_opportunity": 4,    # "Could batch these reads"
    "iteration_loop": 3,       # "4+ same tool calls"
    "stub_warning": 10,        # New file has stubs
    "default": 5,              # Fallback cooldown
}

# Escalation thresholds
ESCALATION_THRESHOLD = 3  # After 3 ignored nudges, escalate severity


def _content_hash(content: str) -> int:
    """Simple hash of content for dedup (first 100 chars)."""
    return hash(content[:100])


def should_nudge(state: SessionState, nudge_type: str, content: str = "") -> tuple[bool, str]:
    """Check if a nudge should be shown based on history.

    Returns: (should_show, severity)
        severity: "normal", "escalate", or "suppress"
    """
    history = state.nudge_history.get(nudge_type, {})
    cooldown = NUDGE_COOLDOWNS.get(nudge_type, NUDGE_COOLDOWNS["default"])

    last_turn = history.get("last_turn", -999)
    turns_since = state.turn_count - last_turn

    # Check cooldown
    if turns_since < cooldown:
        # Same content within cooldown? Suppress
        if content and history.get("last_content_hash") == _content_hash(content):
            return False, "suppress"
        # Different content? Allow (new situation)
        if content and history.get("last_content_hash") != _content_hash(content):
            return True, "normal"
        return False, "suppress"

    # Check for escalation (ignored multiple times)
    times_ignored = history.get("times_ignored", 0)
    if times_ignored >= ESCALATION_THRESHOLD:
        return True, "escalate"

    return True, "normal"


def record_nudge(state: SessionState, nudge_type: str, content: str = ""):
    """Record that a nudge was shown."""
    if nudge_type not in state.nudge_history:
        state.nudge_history[nudge_type] = {}

    history = state.nudge_history[nudge_type]
    history["last_turn"] = state.turn_count
    history["times_shown"] = history.get("times_shown", 0) + 1
    if content:
        history["last_content_hash"] = _content_hash(content)


def mark_nudge_ignored(state: SessionState, nudge_type: str):
    """Mark that a nudge was likely ignored (no action taken).

    Call this when detecting that Claude didn't act on a previous nudge.
    """
    if nudge_type not in state.nudge_history:
        state.nudge_history[nudge_type] = {}

    state.nudge_history[nudge_type]["times_ignored"] = \
        state.nudge_history[nudge_type].get("times_ignored", 0) + 1


def clear_nudge(state: SessionState, nudge_type: str):
    """Clear nudge history (when the issue is resolved)."""
    if nudge_type in state.nudge_history:
        del state.nudge_history[nudge_type]


def get_nudge_stats(state: SessionState) -> dict:
    """Get summary of nudge history for debugging."""
    return {
        nudge_type: {
            "shown": h.get("times_shown", 0),
            "ignored": h.get("times_ignored", 0),
            "last_turn": h.get("last_turn", -1),
        }
        for nudge_type, h in state.nudge_history.items()
    }
