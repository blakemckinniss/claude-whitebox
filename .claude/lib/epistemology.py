#!/usr/bin/env python3
"""
Epistemology Library: State Management for Confidence & Risk Tracking
Provides utilities for the Dual-Metric Epistemological Protocol
"""
import json
import re
import logging
import fcntl
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Paths
MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"  # .claude/lib -> .claude -> .claude/memory
STATE_FILE = MEMORY_DIR / "confidence_state.json"  # Global state (backward compat)

# Confidence Tiers (Graduated System - 6 tiers)
TIER_IGNORANCE = (0, 30)      # Read-only, no coding
TIER_HYPOTHESIS = (31, 50)    # Scratch writes only, no Edit
TIER_WORKING = (51, 70)       # Scratch Edit allowed, git read-only
TIER_CERTAINTY = (71, 85)     # Production with MANDATORY quality gates
TIER_TRUSTED = (86, 94)       # Production with WARNINGS (not blocks)
TIER_EXPERT = (95, 100)       # Maximum freedom, minimal hooks

# Tier Privilege Mapping
TIER_PRIVILEGES = {
    "IGNORANCE": {
        "write_scratch": False,
        "edit_any": False,
        "write_production": False,
        "git_write": False,
        "bash_production": False,
        "prerequisite_mode": "n/a",  # Can't code anyway
    },
    "HYPOTHESIS": {
        "write_scratch": True,
        "edit_any": False,  # Edit blocked entirely
        "write_production": False,
        "git_write": False,
        "git_read": False,
        "bash_production": False,
        "prerequisite_mode": "n/a",
    },
    "WORKING": {
        "write_scratch": True,
        "edit_scratch": True,  # Can Edit .claude/tmp/ (with read check)
        "edit_production": False,
        "write_production": False,
        "git_read": True,  # Can run git status/diff/log
        "git_write": False,
        "bash_production": False,
        "prerequisite_mode": "n/a",
    },
    "CERTAINTY": {
        "write_scratch": True,
        "edit_scratch": True,
        "write_production": True,  # With audit/void
        "edit_production": True,  # With read+audit
        "git_write": True,  # With upkeep
        "bash_production": True,
        "prerequisite_mode": "enforce",  # HARD blocks
    },
    "TRUSTED": {
        "write_scratch": True,
        "edit_any": True,
        "write_production": True,
        "edit_production": True,
        "git_write": True,
        "bash_production": True,
        "prerequisite_mode": "warn",  # Warnings only (except verify)
    },
    "EXPERT": {
        "write_scratch": True,
        "edit_any": True,
        "write_production": True,
        "edit_production": True,
        "git_write": True,
        "bash_production": True,
        "prerequisite_mode": "disabled",  # Maximum freedom
    },
}

# Confidence Value Map
CONFIDENCE_GAINS = {
    # High-value actions
    "user_question": 25,
    "web_search": 20,
    "use_script": 20,
    # Medium-value actions
    "probe_api": 15,
    "verify_success": 15,
    # Low-value actions
    "read_file_first": 10,
    "read_file_repeat": 2,
    "grep_glob": 5,
    # Meta-actions
    "use_researcher": 25,
    "use_script_smith": 15,
    "use_council": 10,
    "run_tests": 30,
    "run_audit": 15,
    # Git operations (state awareness)
    "git_commit": 10,
    "git_status": 5,
    "git_log": 5,
    "git_diff": 10,
    "git_add": 5,
    # Documentation reading (explicit knowledge)
    "read_md_first": 15,
    "read_md_repeat": 5,
    "read_claude_md": 20,
    "read_readme": 15,
    # Technical debt cleanup (proactive quality)
    "fix_todo": 10,
    "remove_stub": 15,
    "reduce_complexity": 10,
    # Testing (quality assurance)
    "write_tests": 15,
    "add_test_coverage": 20,
    # Performance optimization (resource efficiency)
    "parallel_tool_calls": 15,
    "write_batch_script": 20,
    "use_parallel_py": 25,
    "parallel_agent_delegation": 15,
    "agent_free_context": 20,  # Using agents for free context parallelism
    # Browser automation (appropriate tool usage)
    "use_playwright": 15,
    "setup_playwright": 20,
    "browser_instead_requests": 25,  # Using browser for JS sites instead of requests
}

CONFIDENCE_PENALTIES = {
    # Pattern violations
    "hallucination": -20,
    "falsehood": -25,
    "insanity": -15,
    "loop": -15,
    # Tier violations
    "tier_violation": -10,
    # Failures
    "tool_failure": -10,
    "user_correction": -20,
    # Context blindness (severe)
    "edit_before_read": -20,
    "modify_unexamined": -25,
    # User context ignorance
    "repeat_instruction": -15,
    # Testing negligence
    "skip_test_easy": -15,
    "claim_done_no_test": -20,
    # Security/quality shortcuts (critical)
    "modify_no_audit": -25,
    "commit_no_upkeep": -15,
    "write_stub": -10,
    # Performance anti-patterns (resource waste)
    "sequential_when_parallel": -20,
    "manual_instead_of_script": -15,
    "ignore_performance_gate": -25,
    # Delegation violations (offloading work to user)
    "delegation_detected": -15,
    "delegation_repeated": -25,  # Multiple violations in session
    # Hack-around violations (patching around errors instead of fixing)
    "hack_around_severe": -20,   # Bare except Exception:pass, chmod 777, etc.
    "hack_around_detected": -10, # Suspicious patterns
    "hack_around_minor": -5,     # TODO/hack comments
}

# Tool -> Tier requirements
TIER_GATES = {
    "Write": {
        "min_confidence": 31,  # Hypothesis
        "production_min": 71,  # Certainty for non-scratch
        "check_scratch": True,
    },
    "Edit": {
        "min_confidence": 71,  # Always Certainty
    },
    "Bash": {
        "min_confidence": 71,  # Certainty
        "read_only_commands": ["ls", "pwd", "echo", "cat", "head", "tail"],
        "read_only_min": 31,  # Hypothesis for read-only
    },
    "Task": {
        "min_confidence": 40,  # Delegation requires understanding
    },
}


def get_session_state_file(session_id: str) -> Path:
    """Get path to session-specific state file"""
    return MEMORY_DIR / f"session_{session_id}_state.json"


def initialize_session_state(session_id: str) -> Dict:
    """Initialize fresh session state"""
    state = {
        "session_id": session_id,
        "confidence": 0,
        "risk": 0,
        "turn_count": 0,
        "tokens_estimated": 0,
        "context_window_percent": 0,
        "evidence_ledger": [],
        "risk_events": [],
        "confidence_history": [
            {
                "turn": 0,
                "confidence": 0,
                "reason": "session_start",
                "timestamp": datetime.now().isoformat(),
            }
        ],
        "read_files": {},  # Track files read for diminishing returns
        "initialized_at": datetime.now().isoformat(),
    }

    # Save to session file
    state_file = get_session_state_file(session_id)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

    return state


def load_session_state(session_id: str) -> Optional[Dict]:
    """Load session state, return None if not found"""
    state_file = get_session_state_file(session_id)
    if not state_file.exists():
        return None

    try:
        with open(state_file) as f:
            return json.load(f)
    except Exception:
        return None


def save_session_state(session_id: str, state: Dict) -> None:
    """Save session state to file"""
    state_file = get_session_state_file(session_id)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


def assess_initial_confidence(prompt: str) -> int:
    """
    Assess initial confidence based on prompt complexity (max 70%)

    Returns:
        int: Initial confidence score (0-70)
    """
    prompt_lower = prompt.lower()

    # Simple question patterns
    simple_patterns = [
        r"what is",
        r"how do i",
        r"can you explain",
        r"tell me about",
    ]

    # Code request with context
    contextual_patterns = [
        r"fix (this|the) bug",
        r"update (this|the)",
        r"refactor (this|the)",
    ]

    # Architecture decisions
    architecture_patterns = [
        r"should (we|i) (use|migrate|switch)",
        r"which (library|framework|approach)",
    ]

    # Vague requests
    vague_patterns = [
        r"make it better",
        r"improve (this|the)",
        r"optimize",
    ]

    # Check patterns
    if any(re.search(p, prompt_lower) for p in simple_patterns):
        return 15
    elif any(re.search(p, prompt_lower) for p in contextual_patterns):
        return 25
    elif any(re.search(p, prompt_lower) for p in architecture_patterns):
        return 10
    elif any(re.search(p, prompt_lower) for p in vague_patterns):
        return 5

    # Default: moderate complexity
    return 20


def get_confidence_tier(confidence: int) -> Tuple[str, str]:
    """
    Get confidence tier name and description (graduated 6-tier system)

    Returns:
        Tuple[str, str]: (tier_name, tier_description)
    """
    if TIER_IGNORANCE[0] <= confidence <= TIER_IGNORANCE[1]:
        return "IGNORANCE", "Read/Research/Probe only, no coding"
    elif TIER_HYPOTHESIS[0] <= confidence <= TIER_HYPOTHESIS[1]:
        return "HYPOTHESIS", "Can write to .claude/tmp/ only (no Edit)"
    elif TIER_WORKING[0] <= confidence <= TIER_WORKING[1]:
        return "WORKING", "Can Edit .claude/tmp/, git read-only"
    elif TIER_CERTAINTY[0] <= confidence <= TIER_CERTAINTY[1]:
        return "CERTAINTY", "Production access with MANDATORY quality gates"
    elif TIER_TRUSTED[0] <= confidence <= TIER_TRUSTED[1]:
        return "TRUSTED", "Production access with WARNINGS (not blocks)"
    else:  # TIER_EXPERT
        return "EXPERT", "Maximum freedom, minimal hook interference"


def get_tier_privileges(confidence: int) -> Dict:
    """
    Get privilege settings for current confidence tier

    Returns:
        Dict: Privilege settings for tier
    """
    tier_name, _ = get_confidence_tier(confidence)
    return TIER_PRIVILEGES.get(tier_name, TIER_PRIVILEGES["IGNORANCE"])


def check_tier_gate(
    tool_name: str, tool_input: Dict, current_confidence: int, session_id: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[str], str]:
    """
    Check if tool usage is allowed at current confidence tier (GRADUATED SYSTEM)

    Args:
        tool_name: Name of tool being used
        tool_input: Tool parameters
        current_confidence: Current confidence level
        session_id: Session ID for checking read_files state

    Returns:
        Tuple[bool, Optional[str], Optional[str], str]:
            (allowed, block_message, penalty_type, enforcement_mode)
            - enforcement_mode: "disabled", "warn", "enforce"
    """
    tier_name, tier_desc = get_confidence_tier(current_confidence)
    privileges = get_tier_privileges(current_confidence)
    enforcement_mode = privileges.get("prerequisite_mode", "enforce")

    # === EXPERT TIER (95-100%): Maximum freedom ===
    if tier_name == "EXPERT":
        # Only critical safety checks (dangerous commands)
        if tool_name == "Bash":
            dangerous = is_dangerous_command(tool_input.get("command", ""))
            if dangerous:
                pattern, reason = dangerous
                message = f"""🚨 CRITICAL SAFETY BLOCK (Even at Expert tier)

Command: {tool_input.get('command', '')[:100]}
Pattern: {reason}

This command is destructive and blocked even at maximum confidence.
Expert tier grants autonomy, not system destruction permissions.

Blocked pattern: {pattern}"""
                return False, message, "dangerous_command", "enforce"

        # All other actions allowed (no read checks, no prerequisites)
        return True, None, None, "disabled"

    # === TRUSTED TIER (86-94%): Warnings instead of blocks ===
    if tier_name == "TRUSTED":
        # Still enforce read-before-edit for context safety
        if tool_name == "Edit":
            file_path = tool_input.get("file_path", "")
            if session_id:
                state = load_session_state(session_id)
                if state:
                    read_files = state.get("read_files", {})
                    if file_path not in read_files:
                        # Warning mode at Trusted tier
                        message = f"""⚠️ CONTEXT WARNING (Trusted tier)

Action: Edit {Path(file_path).name}
Problem: File not read before editing

You are trusted to Edit without reading, but this is risky.
Consider reading first to avoid breaking changes.

Proceeding with warning penalty.
Confidence Penalty: {CONFIDENCE_PENALTIES['edit_before_read']}%"""
                        return True, message, "edit_before_read", "warn"

        # Other actions allowed (prerequisites become warnings, not blocks)
        return True, None, None, "warn"

    # === LOWER TIERS: Progressive restrictions ===

    # EDIT TOOL: Graduated restrictions by tier
    if tool_name == "Edit":
        file_path = tool_input.get("file_path", "")
        is_scratch = file_path.startswith(".claude/tmp/") or "/scratch/" in file_path
        is_production = not is_scratch

        # HYPOTHESIS (31-50%): Edit blocked entirely
        if tier_name == "HYPOTHESIS":
            message = f"""🚫 EDIT BLOCKED AT HYPOTHESIS TIER

Action: Edit {Path(file_path).name}
Your Confidence: {current_confidence}% ({tier_name} TIER)
Required: 51%+ (WORKING tier)

Edit modifies existing code (higher risk than Write).
Gather more evidence before editing.

Current tier allows: Write to .claude/tmp/ only
Confidence Penalty: -10%"""
            return False, message, "tier_violation", "enforce"

        # WORKING (51-70%): Can Edit .claude/tmp/, but not production
        if tier_name == "WORKING" and is_production:
            message = f"""🚫 PRODUCTION EDIT BLOCKED AT WORKING TIER

Action: Edit {Path(file_path).name}
Your Confidence: {current_confidence}% ({tier_name} TIER)
Required: 71%+ (CERTAINTY tier)

You can Edit .claude/tmp/ files, but production requires CERTAINTY tier.
Gather more evidence before editing production code.

Confidence Penalty: -10%"""
            return False, message, "tier_violation", "enforce"

        # WORKING/CERTAINTY: Enforce read-before-edit
        if session_id:
            state = load_session_state(session_id)
            if state:
                read_files = state.get("read_files", {})
                if file_path not in read_files:
                    penalty_type = "edit_before_read"
                    message = f"""🚫 CONTEXT BLINDNESS DETECTED

Action: Edit {Path(file_path).name}
Problem: File not read before editing

You attempted to modify code without understanding it first.
This leads to breaking changes and context blindness.

Required workflow:
  1. Read {file_path}
  2. Understand existing code
  3. Then Edit safely

Current Confidence: {current_confidence}% ({tier_name} TIER)
Confidence Penalty: {CONFIDENCE_PENALTIES['edit_before_read']}%"""
                    return False, message, penalty_type, "enforce"

    # WRITE TOOL: Graduated restrictions by tier
    if tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        is_scratch = file_path.startswith(".claude/tmp/") or "/scratch/" in file_path
        is_production = not is_scratch

        # IGNORANCE (0-30%): No Write at all
        if tier_name == "IGNORANCE":
            message = f"""🚫 WRITE BLOCKED AT IGNORANCE TIER

Action: Write {Path(file_path).name}
Your Confidence: {current_confidence}% ({tier_name} TIER)
Required: 31%+ (HYPOTHESIS tier)

You know nothing yet. Gather evidence first.
Allowed actions: Read, Research, Probe, Ask questions

Confidence Penalty: -10%"""
            return False, message, "tier_violation", "enforce"

        # HYPOTHESIS (31-50%): Can Write .claude/tmp/ only
        if tier_name == "HYPOTHESIS" and is_production:
            message = f"""🚫 PRODUCTION WRITE BLOCKED AT HYPOTHESIS TIER

Action: Write {Path(file_path).name}
Your Confidence: {current_confidence}% ({tier_name} TIER)
Required: 71%+ (CERTAINTY tier)

You can write to .claude/tmp/ for experiments, but production requires CERTAINTY.
Gather more evidence before writing production code.

Confidence Penalty: -10%"""
            return False, message, "tier_violation", "enforce"

        # WORKING (51-70%): Still can't write production
        if tier_name == "WORKING" and is_production:
            message = f"""🚫 PRODUCTION WRITE BLOCKED AT WORKING TIER

Action: Write {Path(file_path).name}
Your Confidence: {current_confidence}% ({tier_name} TIER)
Required: 71%+ (CERTAINTY tier)

WORKING tier allows editing .claude/tmp/, but production writes require CERTAINTY.
Gather more evidence (run tests, verify, etc.) to reach 71%.

Confidence Penalty: -10%"""
            return False, message, "tier_violation", "enforce"

        # CERTAINTY+: Check if overwriting existing production file
        if tier_name == "CERTAINTY" and is_production:
            if session_id and Path(file_path).exists():
                state = load_session_state(session_id)
                if state:
                    read_files = state.get("read_files", {})
                    if file_path not in read_files:
                        penalty_type = "modify_unexamined"
                        message = f"""🚫 PRODUCTION MODIFICATION WITHOUT CONTEXT

Action: Write {Path(file_path).name}
Problem: Modifying existing production file without reading it first

CRITICAL: You are overwriting production code blindly.
This is extremely dangerous and leads to data loss.

Required workflow:
  1. Read {file_path} first
  2. Understand existing implementation
  3. Then Write changes safely

Current Confidence: {current_confidence}% ({tier_name} TIER)
Confidence Penalty: {CONFIDENCE_PENALTIES['modify_unexamined']}%"""
                        return False, message, penalty_type, "enforce"

    # BASH TOOL: Check for git operations and production commands
    if tool_name == "Bash":
        command = tool_input.get("command", "")

        # Git write operations (commit, push, add)
        if any(command.strip().startswith(cmd) for cmd in ["git commit", "git push", "git add"]):
            if not privileges.get("git_write", False):
                message = f"""🚫 GIT WRITE BLOCKED AT {tier_name} TIER

Action: {command[:50]}
Your Confidence: {current_confidence}% ({tier_name} TIER)
Required: 71%+ (CERTAINTY tier)

Git write operations (commit/push/add) require CERTAINTY tier.
You can use git status/diff/log at WORKING tier (51%+).

Confidence Penalty: -10%"""
                return False, message, "tier_violation", "enforce"

        # Git read operations (status, diff, log)
        elif any(command.strip().startswith(cmd) for cmd in ["git status", "git diff", "git log"]):
            if not privileges.get("git_read", False):
                message = f"""🚫 GIT READ BLOCKED AT {tier_name} TIER

Action: {command[:50]}
Your Confidence: {current_confidence}% ({tier_name} TIER)
Required: 51%+ (WORKING tier)

Git read operations require WORKING tier.
Gather evidence (read files, research) to reach 51%.

Confidence Penalty: -10%"""
                return False, message, "tier_violation", "enforce"

    # All checks passed
    return True, None, None, enforcement_mode


def _detect_git_operation(command: str) -> Tuple[Optional[str], int]:
    """
    Detect git operations and return boost key and amount

    Returns:
        Tuple[Optional[str], int]: (boost_key, boost_amount)
    """
    command = command.strip()

    if command.startswith("git commit"):
        return ("git_commit", CONFIDENCE_GAINS["git_commit"])
    elif command.startswith("git status"):
        return ("git_status", CONFIDENCE_GAINS["git_status"])
    elif command.startswith("git diff"):
        return ("git_diff", CONFIDENCE_GAINS["git_diff"])
    elif command.startswith("git log"):
        return ("git_log", CONFIDENCE_GAINS["git_log"])
    elif command.startswith("git add"):
        return ("git_add", CONFIDENCE_GAINS["git_add"])

    return (None, 0)


def _detect_documentation_read(file_path: str, read_files: Dict) -> Tuple[Optional[str], int]:
    """
    Detect documentation file reads and return boost key and amount

    Returns:
        Tuple[Optional[str], int]: (boost_key, boost_amount)
    """
    if not file_path.endswith(".md"):
        return (None, 0)

    # Check if already read (diminishing returns)
    if file_path in read_files:
        return ("read_md_repeat", CONFIDENCE_GAINS["read_md_repeat"])

    # Special cases for important docs
    if file_path.endswith("CLAUDE.md"):
        return ("read_claude_md", CONFIDENCE_GAINS["read_claude_md"])
    elif file_path.endswith("README.md"):
        return ("read_readme", CONFIDENCE_GAINS["read_readme"])
    else:
        # Generic .md file
        return ("read_md_first", CONFIDENCE_GAINS["read_md_first"])


def _detect_test_file_operation(file_path: str, operation: str) -> Tuple[Optional[str], int]:
    """
    Detect test file creation/modification and return boost key and amount

    Args:
        file_path: Path to file being operated on
        operation: "Write" or "Edit"

    Returns:
        Tuple[Optional[str], int]: (boost_key, boost_amount)
    """
    import os

    filename = os.path.basename(file_path)

    # Check if test file
    is_test = (
        filename.startswith("test_") or
        filename.endswith("_test.py") or
        "/tests/" in file_path
    )

    if not is_test:
        return (None, 0)

    if operation == "Write":  # New test file
        return ("write_tests", CONFIDENCE_GAINS["write_tests"])
    elif operation == "Edit":  # Adding to existing test file
        return ("add_test_coverage", CONFIDENCE_GAINS["add_test_coverage"])

    return (None, 0)


def update_confidence(
    session_id: str, tool_name: str, tool_input: Dict, turn: int, reason: str
) -> Tuple[int, int]:
    """
    Update confidence based on tool usage

    Returns:
        Tuple[int, int]: (new_confidence, boost_amount)
    """
    state = load_session_state(session_id)
    if not state:
        state = initialize_session_state(session_id)

    boost = 0

    # Determine boost based on tool and context
    if tool_name == "Read":
        file_path = tool_input.get("file_path", "")

        # Check if .md file first (documentation gets higher boost)
        doc_key, doc_boost = _detect_documentation_read(file_path, state.get("read_files", {}))
        if doc_key:
            boost = doc_boost
        else:
            # Regular code file - check if read before (diminishing returns)
            if file_path in state.get("read_files", {}):
                boost = CONFIDENCE_GAINS["read_file_repeat"]
                state["read_files"][file_path] += 1
            else:
                boost = CONFIDENCE_GAINS["read_file_first"]
                if "read_files" not in state:
                    state["read_files"] = {}
                state["read_files"][file_path] = 1

        # Track file read for diminishing returns
        if "read_files" not in state:
            state["read_files"] = {}
        state["read_files"][file_path] = state["read_files"].get(file_path, 0) + 1

    elif tool_name == "Bash":
        command = tool_input.get("command", "")

        # Check git operations first (state awareness)
        git_key, git_boost = _detect_git_operation(command)
        if git_key:
            boost = git_boost
        # Existing protocol command detection
        elif ".claude/ops/verify.py" in command or "/verify " in command:
            boost = CONFIDENCE_GAINS["verify_success"]
        elif ".claude/ops/research.py" in command or "/research" in command:
            boost = CONFIDENCE_GAINS["web_search"]
        elif ".claude/ops/probe.py" in command or "/probe" in command:
            boost = CONFIDENCE_GAINS["probe_api"]
        elif ".claude/ops/audit.py" in command:
            boost = CONFIDENCE_GAINS["run_audit"]
        elif ".claude/ops/playwright.py" in command or "/playwright" in command:
            # Setup gets higher boost, check gets standard
            if "--setup" in command or "--autonomous" in command:
                boost = CONFIDENCE_GAINS["setup_playwright"]
            else:
                boost = CONFIDENCE_GAINS["use_playwright"]
        elif "get_browser_session" in command or "from browser import" in command:
            boost = CONFIDENCE_GAINS["use_playwright"]
        elif "pytest" in command or "python -m pytest" in command:
            boost = CONFIDENCE_GAINS["run_tests"]
        elif ".claude/ops/council.py" in command:
            boost = CONFIDENCE_GAINS["use_council"]
        else:
            boost = CONFIDENCE_GAINS["use_script"]

    elif tool_name == "Task":
        subagent_type = tool_input.get("subagent_type", "")
        if subagent_type == "researcher":
            boost = CONFIDENCE_GAINS["use_researcher"]
        elif subagent_type == "script-smith":
            boost = CONFIDENCE_GAINS["use_script_smith"]
        elif subagent_type == "sherlock":
            boost = 20  # Read-only debugger (anti-gaslighting)
        elif subagent_type == "macgyver":
            boost = 15  # Living off the Land (improvisation)
        elif subagent_type == "tester":
            boost = 15  # Test writing (quality)
        elif subagent_type == "optimizer":
            boost = 15  # Performance tuning (measurement-driven)
        else:
            boost = 10  # Generic delegation

    elif tool_name in ["Grep", "Glob"]:
        boost = CONFIDENCE_GAINS["grep_glob"]

    elif tool_name == "WebSearch":
        boost = CONFIDENCE_GAINS["web_search"]

    elif tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        # Check if writing test file
        test_key, test_boost = _detect_test_file_operation(file_path, "Write")
        if test_key:
            boost = test_boost

    elif tool_name == "Edit":
        file_path = tool_input.get("file_path", "")
        # Check if editing test file
        test_key, test_boost = _detect_test_file_operation(file_path, "Edit")
        if test_key:
            boost = test_boost

    # Update confidence (cap at 100)
    old_confidence = state["confidence"]
    new_confidence = min(100, old_confidence + boost)
    state["confidence"] = new_confidence

    # Record evidence
    evidence_entry = {
        "turn": turn,
        "tool": tool_name,
        "target": str(
            tool_input.get("file_path")
            or tool_input.get("query")
            or tool_input.get("command", "")
        )[:100],
        "boost": boost,
        "timestamp": datetime.now().isoformat(),
    }
    state["evidence_ledger"].append(evidence_entry)

    # Record confidence history
    history_entry = {
        "turn": turn,
        "confidence": new_confidence,
        "reason": reason or f"{tool_name} usage",
        "timestamp": datetime.now().isoformat(),
    }
    state["confidence_history"].append(history_entry)

    # Prune history to prevent unbounded growth
    state = prune_session_history(state)

    # Save state
    save_session_state(session_id, state)

    # Also update global state for backward compatibility
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(
                {
                    "current_confidence": new_confidence,
                    "reinforcement_log": state["evidence_ledger"][-10:],  # Last 10
                    "last_reset": state["initialized_at"],
                    "total_gains": sum(
                        e["boost"] for e in state["evidence_ledger"] if e["boost"] > 0
                    ),
                    "total_losses": sum(
                        e["boost"] for e in state["evidence_ledger"] if e["boost"] < 0
                    ),
                    "confidence": new_confidence,
                },
                f,
                indent=2,
            )
    except Exception:
        pass  # Silent failure for backward compat

    return new_confidence, boost


def apply_penalty(session_id: str, penalty_type: str, turn: int, reason: str) -> int:
    """
    Apply confidence penalty

    Returns:
        int: New confidence after penalty
    """
    state = load_session_state(session_id)
    if not state:
        state = initialize_session_state(session_id)

    penalty = CONFIDENCE_PENALTIES.get(penalty_type, -10)

    old_confidence = state["confidence"]
    new_confidence = max(0, old_confidence + penalty)  # Can't go below 0
    state["confidence"] = new_confidence

    # Record penalty in evidence ledger
    penalty_entry = {
        "turn": turn,
        "tool": "PENALTY",
        "target": penalty_type,
        "boost": penalty,
        "timestamp": datetime.now().isoformat(),
    }
    state["evidence_ledger"].append(penalty_entry)

    # Record in confidence history
    history_entry = {
        "turn": turn,
        "confidence": new_confidence,
        "reason": f"{penalty_type}: {reason}",
        "timestamp": datetime.now().isoformat(),
    }
    state["confidence_history"].append(history_entry)

    # Prune history to prevent unbounded growth
    state = prune_session_history(state)

    # Save state
    save_session_state(session_id, state)

    # Update global state
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(
                {
                    "current_confidence": new_confidence,
                    "reinforcement_log": state["evidence_ledger"][-10:],
                    "last_reset": state["initialized_at"],
                    "total_gains": sum(
                        e["boost"] for e in state["evidence_ledger"] if e["boost"] > 0
                    ),
                    "total_losses": sum(
                        e["boost"] for e in state["evidence_ledger"] if e["boost"] < 0
                    ),
                    "confidence": new_confidence,
                },
                f,
                indent=2,
            )
    except Exception:
        pass

    return new_confidence


def apply_reward(session_id: str, reward_type: str, turn: int, reason: str) -> int:
    """
    Apply confidence reward (opposite of penalty)

    Returns:
        int: New confidence after reward
    """
    state = load_session_state(session_id)
    if not state:
        state = initialize_session_state(session_id)

    reward = CONFIDENCE_GAINS.get(reward_type, 10)

    old_confidence = state["confidence"]
    new_confidence = min(100, old_confidence + reward)  # Cap at 100
    state["confidence"] = new_confidence

    # Record reward in evidence ledger
    reward_entry = {
        "turn": turn,
        "tool": "REWARD",
        "target": reward_type,
        "boost": reward,
        "timestamp": datetime.now().isoformat(),
    }
    state["evidence_ledger"].append(reward_entry)

    # Record in confidence history
    history_entry = {
        "turn": turn,
        "confidence": new_confidence,
        "reason": f"{reward_type}: {reason}",
        "timestamp": datetime.now().isoformat(),
    }
    state["confidence_history"].append(history_entry)

    # Prune history to prevent unbounded growth
    state = prune_session_history(state)

    # Save state
    save_session_state(session_id, state)

    # Update global state
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(
                {
                    "current_confidence": new_confidence,
                    "reinforcement_log": state["evidence_ledger"][-10:],
                    "last_reset": state["initialized_at"],
                    "total_gains": sum(
                        e["boost"] for e in state["evidence_ledger"] if e["boost"] > 0
                    ),
                    "total_losses": sum(
                        e["boost"] for e in state["evidence_ledger"] if e["boost"] < 0
                    ),
                    "confidence": new_confidence,
                },
                f,
                indent=2,
            )
    except Exception:
        pass

    return new_confidence


# Risk Management


def increment_risk(
    session_id: str, amount: int, turn: int, reason: str, command: str = ""
) -> int:
    """
    Increment risk level for dangerous actions

    Args:
        session_id: Session identifier
        amount: Amount to increment (typically 20 for hard blocks)
        turn: Current turn number
        reason: Reason for risk increment
        command: The dangerous command (optional)

    Returns:
        New risk level
    """
    state = load_session_state(session_id)
    if not state:
        state = initialize_session_state(session_id)

    old_risk = state.get("risk", 0)
    new_risk = min(100, old_risk + amount)  # Cap at 100
    state["risk"] = new_risk

    # Record risk event
    risk_event = {
        "turn": turn,
        "event": "risk_increase",
        "amount": amount,
        "command": command[:100] if command else "",
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }
    state["risk_events"].append(risk_event)

    # Save state
    save_session_state(session_id, state)

    return new_risk


def decrement_risk(session_id: str, amount: int, turn: int, reason: str) -> int:
    """
    Decrement risk level for safe completions

    Args:
        session_id: Session identifier
        amount: Amount to decrement
        turn: Current turn number
        reason: Reason for risk decrement

    Returns:
        New risk level
    """
    state = load_session_state(session_id)
    if not state:
        state = initialize_session_state(session_id)

    old_risk = state.get("risk", 0)
    new_risk = max(0, old_risk - amount)  # Floor at 0
    state["risk"] = new_risk

    # Record risk event
    risk_event = {
        "turn": turn,
        "event": "risk_decrease",
        "amount": -amount,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }
    state["risk_events"].append(risk_event)

    # Save state
    save_session_state(session_id, state)

    return new_risk


def get_risk_level(risk: int) -> Tuple[str, str]:
    """
    Get risk level name and description

    Returns:
        Tuple[str, str]: (level_name, level_description)
    """
    if risk == 0:
        return "SAFE", "No dangerous actions detected"
    elif risk < 50:
        return "LOW", "Minor risk from blocked actions"
    elif risk < 80:
        return "MODERATE", "Multiple dangerous attempts detected"
    elif risk < 100:
        return "HIGH", "Approaching council consultation threshold"
    else:
        return "CRITICAL", "Council consultation required immediately"


def check_risk_threshold(session_id: str) -> Optional[str]:
    """
    Check if risk has hit critical threshold (100%)

    Returns:
        Message if council trigger needed, None otherwise
    """
    state = load_session_state(session_id)
    if not state:
        return None

    risk = state.get("risk", 0)

    if risk >= 100:
        # Get recent risk events for context
        risk_events = state.get("risk_events", [])
        recent_events = risk_events[-5:]  # Last 5 events

        event_summary = "\n".join(
            [
                f"  - Turn {e['turn']}: {e.get('reason', 'Unknown')} ({e.get('command', '')[:50]})"
                for e in recent_events
            ]
        )

        return f"""🚨 CRITICAL RISK THRESHOLD REACHED (100%)

Multiple dangerous commands blocked in this session.

Recent Risk Events:
{event_summary}

MANDATORY ACTION: Convene the council to review session intent and reset risk.

Command:
  python3 .claude/ops/balanced_council.py "Review session with multiple dangerous command attempts - assess if actions are intentional or problematic"
"""

    return None


# Dangerous command patterns
DANGEROUS_PATTERNS = [
    (r"rm\s+-rf\s+/", "Recursive delete from root"),
    (r"dd\s+if=.*of=/dev/", "Direct disk write"),
    (r"mkfs", "Format filesystem"),
    (r":\(\)\{ :\|:& \};:", "Fork bomb"),
    (r"chmod\s+-R\s+777", "Recursive permissions to 777"),
    (r"curl.*\|\s*bash", "Pipe curl to bash"),
    (r"wget.*\|\s*sh", "Pipe wget to shell"),
    (r"eval.*\$\(", "Eval with command substitution"),
    (r">/dev/sd", "Write to disk device"),
]


def is_dangerous_command(command: str) -> Optional[Tuple[str, str]]:
    """
    Check if command matches dangerous patterns

    Returns:
        Tuple of (pattern, reason) if dangerous, None otherwise
    """
    for pattern, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return (pattern, reason)
    return None


# Token estimation
def estimate_tokens(transcript_path: str) -> int:
    """
    Estimate token count from transcript file

    Rough heuristic: 1 token ≈ 4 characters
    """
    try:
        size = Path(transcript_path).stat().st_size
        return size // 4  # Rough estimate
    except Exception:
        return 0


def get_token_percentage(tokens: int, max_tokens: int = 200000) -> float:
    """Get percentage of context window used"""
    return (tokens / max_tokens) * 100 if max_tokens > 0 else 0


# Command Tracking (Workflow Enforcement)


def record_command_run(
    session_id: str, command_name: str, turn: int, full_command: str
) -> None:
    """
    Track workflow command execution

    Args:
        session_id: Session identifier
        command_name: Command name (verify, upkeep, xray, think, audit, void, research)
        turn: Current turn number
        full_command: Full bash command string

    Updates session state with command execution tracking.
    """
    state = load_session_state(session_id)
    if not state:
        state = initialize_session_state(session_id)

    # Initialize commands_run structure if needed
    if "commands_run" not in state:
        state["commands_run"] = {}

    if command_name not in state["commands_run"]:
        state["commands_run"][command_name] = []

    # Record this execution
    state["commands_run"][command_name].append(turn)
    state[f"last_{command_name}_turn"] = turn

    # Special handling for verify command - track what was verified
    if command_name == "verify" and "command_success" in full_command:
        if "verified_commands" not in state:
            state["verified_commands"] = {}

        # Extract command from verify invocation
        # Example: verify.py command_success "pytest tests/" -> "pytest tests/"
        import re

        match = re.search(r'command_success\s+["\'](.+?)["\']', full_command)
        if match:
            verified_cmd = match.group(1)
            state["verified_commands"][verified_cmd] = True

    save_session_state(session_id, state)


def check_command_prerequisite(
    session_id: str,
    required_command: str,
    current_turn: int,
    recency_window: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Check if required workflow command has been run

    Args:
        session_id: Session identifier
        required_command: Command name (e.g., "verify", "upkeep")
        current_turn: Current turn number
        recency_window: If set, command must be within last N turns

    Returns:
        Tuple[bool, Optional[str]]: (prerequisite_met, error_message)
            - If prerequisite met: (True, None)
            - If prerequisite not met: (False, "error message explaining why")
    """
    state = load_session_state(session_id)
    if not state:
        return False, "No session state found"

    commands_run = state.get("commands_run", {})
    command_turns = commands_run.get(required_command, [])

    if not command_turns:
        return (
            False,
            f"/{required_command} has never been run in this session",
        )

    last_run_turn = max(command_turns)

    if recency_window:
        turns_ago = current_turn - last_run_turn
        if turns_ago > recency_window:
            return (
                False,
                f"/{required_command} last run {turns_ago} turns ago (need within {recency_window} turns)",
            )

    return True, None


# ==============================================================================
# RETENTION POLICY & CONCURRENT SAFETY ADDITIONS
# Added 2025-11-23 to fix root causes identified by void.py analysis
# ==============================================================================

# Constants for retention policy
MAX_SESSION_AGE_DAYS = 7
MAX_HISTORY_LENGTH = 100

# Setup logging (errors only, don't pollute stdout)
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class FileLock:
    """
    Context manager for file locking to prevent concurrent write corruption.

    Usage:
        with FileLock(file_path):
            with open(file_path, 'w') as f:
                json.dump(data, f)
    """

    def __init__(self, file_path: Path, timeout: float = 2.0):
        self.file_path = file_path
        self.timeout = timeout
        self.lock_file = file_path.with_suffix(file_path.suffix + '.lock')
        self.fd = None

    def __enter__(self):
        """Acquire exclusive lock with timeout"""
        start_time = time.time()
        while True:
            try:
                self.lock_file.parent.mkdir(parents=True, exist_ok=True)
                self.fd = open(self.lock_file, 'w')
                fcntl.flock(self.fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (IOError, OSError):
                if time.time() - start_time > self.timeout:
                    logging.error(f"Lock timeout for {self.lock_file}")
                    raise TimeoutError(f"Could not acquire lock for {self.file_path}")
                time.sleep(0.05)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release lock"""
        if self.fd:
            try:
                fcntl.flock(self.fd.fileno(), fcntl.LOCK_UN)
                self.fd.close()
                self.lock_file.unlink(missing_ok=True)
            except Exception as e:
                logging.warning(f"Error releasing lock: {e}")


def prune_session_history(state: Dict, max_length: int = MAX_HISTORY_LENGTH) -> Dict:
    """
    Prune evidence_ledger, confidence_history, risk_events to prevent unbounded growth.

    Args:
        state: Session state dict
        max_length: Maximum entries to keep

    Returns:
        Modified state dict with pruned history
    """
    if "evidence_ledger" in state and len(state["evidence_ledger"]) > max_length:
        old_len = len(state["evidence_ledger"])
        state["evidence_ledger"] = state["evidence_ledger"][-max_length:]
        logging.info(f"Pruned evidence_ledger: {old_len} → {max_length}")

    if "confidence_history" in state and len(state["confidence_history"]) > max_length:
        old_len = len(state["confidence_history"])
        state["confidence_history"] = state["confidence_history"][-max_length:]
        logging.info(f"Pruned confidence_history: {old_len} → {max_length}")

    if "risk_events" in state and len(state["risk_events"]) > max_length:
        old_len = len(state["risk_events"])
        state["risk_events"] = state["risk_events"][-max_length:]
        logging.info(f"Pruned risk_events: {old_len} → {max_length}")

    return state


def cleanup_old_sessions(max_age_days: int = MAX_SESSION_AGE_DAYS, dry_run: bool = False) -> Dict[str, list]:
    """
    Delete session state files older than max_age_days.

    Args:
        max_age_days: Maximum age in days
        dry_run: If True, only report what would be deleted

    Returns:
        Dict with 'deleted', 'kept', 'errors' lists
    """
    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    deleted = []
    kept = []
    errors = []

    for session_file in MEMORY_DIR.glob("session_*_state.json"):
        try:
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
            age_days = (datetime.now() - mtime).days

            if mtime < cutoff_date:
                if dry_run:
                    logging.info(f"[DRY-RUN] Would delete: {session_file.name} ({age_days} days old)")
                else:
                    session_file.unlink()
                    logging.info(f"Deleted old session: {session_file.name} ({age_days} days old)")
                deleted.append(session_file.name)
            else:
                kept.append(session_file.name)

        except Exception as e:
            logging.error(f"Error processing {session_file.name}: {e}")
            errors.append(f"{session_file.name}: {str(e)}")

    return {"deleted": deleted, "kept": kept, "errors": errors}


def delete_session_state(session_id: str) -> bool:
    """
    Delete session state file for given session_id.
    Fills the CRUD gap (create/read/update existed, delete was missing).

    Args:
        session_id: Session identifier

    Returns:
        bool: True if deleted, False if not found or error
    """
    state_file = get_session_state_file(session_id)

    if not state_file.exists():
        logging.warning(f"Session file not found: {session_id}")
        return False

    try:
        state_file.unlink()
        logging.info(f"Deleted session: {session_id}")
        return True
    except Exception as e:
        logging.error(f"Error deleting session {session_id}: {e}")
        return False


# ==============================================================================
# VERIFIED KNOWLEDGE TRACKING (Anti-Hallucination)
# Added 2025-11-25 to support epistemic humility enforcement
# ==============================================================================

def record_verified_library(
    session_id: str,
    library_name: str,
    verification_method: str,
    turn: int,
    methods: Optional[List[str]] = None,
    source: Optional[str] = None,
) -> None:
    """
    Record that a library/API has been verified via research, probe, or read.

    Args:
        session_id: Session identifier
        library_name: Name of library (e.g., "boto3", "pandas")
        verification_method: How it was verified ("research", "probe", "read")
        turn: Current turn number
        methods: Specific methods/classes verified (optional)
        source: Source of verification (URL, file path, etc.)

    Updates session state with verified_knowledge tracking.
    """
    state = load_session_state(session_id)
    if not state:
        state = initialize_session_state(session_id)

    # Initialize verified_knowledge structure if needed
    if "verified_knowledge" not in state:
        state["verified_knowledge"] = {"libraries": {}, "patterns": {}}

    # Record library verification
    state["verified_knowledge"]["libraries"][library_name] = {
        "via": verification_method,
        "turn": turn,
        "methods": methods or [],
        "source": source or "",
        "timestamp": datetime.now().isoformat(),
    }

    save_session_state(session_id, state)


def record_verified_pattern(
    session_id: str,
    pattern_name: str,
    source_file: str,
    turn: int,
) -> None:
    """
    Record that a code pattern has been verified by reading existing code.

    Args:
        session_id: Session identifier
        pattern_name: Name of pattern (e.g., "async_await", "error_handling")
        source_file: File where pattern was observed
        turn: Current turn number
    """
    state = load_session_state(session_id)
    if not state:
        state = initialize_session_state(session_id)

    if "verified_knowledge" not in state:
        state["verified_knowledge"] = {"libraries": {}, "patterns": {}}

    state["verified_knowledge"]["patterns"][pattern_name] = {
        "via": "read",
        "source": source_file,
        "turn": turn,
        "timestamp": datetime.now().isoformat(),
    }

    save_session_state(session_id, state)


def get_verified_libraries(session_id: str) -> Dict[str, Dict]:
    """
    Get all verified libraries for a session.

    Returns:
        Dict mapping library names to verification info
    """
    state = load_session_state(session_id)
    if not state:
        return {}

    return state.get("verified_knowledge", {}).get("libraries", {})


def is_library_verified(session_id: str, library_name: str) -> bool:
    """
    Check if a library has been verified in this session.

    Args:
        session_id: Session identifier
        library_name: Name of library to check

    Returns:
        bool: True if library was verified
    """
    verified = get_verified_libraries(session_id)
    return library_name in verified


def extract_libraries_from_bash_output(
    command: str,
    output: str,
) -> List[str]:
    """
    Extract library names from research.py or probe.py output.

    Heuristic detection based on command and output patterns.

    Args:
        command: The bash command that was run
        output: stdout from the command

    Returns:
        List of library names that were verified
    """
    libraries = []

    # Research command: python3 .claude/ops/research.py "boto3 s3 upload"
    if "research.py" in command:
        # Extract search query
        match = re.search(r'research\.py\s+["\']([^"\']+)["\']', command)
        if match:
            query = match.group(1).lower()
            # Common library patterns in queries
            known_libs = [
                "boto3", "pandas", "numpy", "requests", "httpx", "aiohttp",
                "fastapi", "flask", "django", "sqlalchemy", "pytorch", "torch",
                "tensorflow", "transformers", "openai", "anthropic", "langchain",
                "playwright", "selenium", "redis", "pymongo", "psycopg2",
                "matplotlib", "seaborn", "scipy", "sklearn", "pillow",
            ]
            for lib in known_libs:
                if lib in query:
                    libraries.append(lib)

    # Probe command: python3 .claude/ops/probe.py boto3.client
    elif "probe.py" in command:
        match = re.search(r'probe\.py\s+([a-zA-Z_][a-zA-Z0-9_\.]*)', command)
        if match:
            obj_path = match.group(1)
            # Get top-level module
            top_module = obj_path.split('.')[0]
            libraries.append(top_module)

    return libraries


def extract_libraries_from_code_read(
    file_path: str,
    content: str,
) -> List[str]:
    """
    Extract library imports from a Python file that was read.

    When Claude reads existing code, the libraries used there
    become "verified by example" - we know they work.

    Args:
        file_path: Path to file that was read
        content: Content of the file

    Returns:
        List of library names found in imports
    """
    if not file_path.endswith(".py"):
        return []

    libraries = []

    # Parse imports
    try:
        import ast
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_module = alias.name.split('.')[0]
                    libraries.append(top_module)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top_module = node.module.split('.')[0]
                    libraries.append(top_module)
    except SyntaxError:
        # Fallback regex for partial files
        import_pattern = r'^(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            libraries.append(match.group(1))

    return list(set(libraries))
