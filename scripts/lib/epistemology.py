#!/usr/bin/env python3
"""
Epistemology Library: State Management for Confidence & Risk Tracking
Provides utilities for the Dual-Metric Epistemological Protocol
"""
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple

# Paths
MEMORY_DIR = Path(__file__).resolve().parent.parent.parent / ".claude" / "memory"
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
        "edit_scratch": True,  # Can Edit scratch/ (with read check)
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
    except:
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
        return "HYPOTHESIS", "Can write to scratch/ only (no Edit)"
    elif TIER_WORKING[0] <= confidence <= TIER_WORKING[1]:
        return "WORKING", "Can Edit scratch/, git read-only"
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
        is_scratch = file_path.startswith("scratch/") or "/scratch/" in file_path
        is_production = not is_scratch

        # HYPOTHESIS (31-50%): Edit blocked entirely
        if tier_name == "HYPOTHESIS":
            message = f"""🚫 EDIT BLOCKED AT HYPOTHESIS TIER

Action: Edit {Path(file_path).name}
Your Confidence: {current_confidence}% ({tier_name} TIER)
Required: 51%+ (WORKING tier)

Edit modifies existing code (higher risk than Write).
Gather more evidence before editing.

Current tier allows: Write to scratch/ only
Confidence Penalty: -10%"""
            return False, message, "tier_violation", "enforce"

        # WORKING (51-70%): Can Edit scratch/, but not production
        if tier_name == "WORKING" and is_production:
            message = f"""🚫 PRODUCTION EDIT BLOCKED AT WORKING TIER

Action: Edit {Path(file_path).name}
Your Confidence: {current_confidence}% ({tier_name} TIER)
Required: 71%+ (CERTAINTY tier)

You can Edit scratch/ files, but production requires CERTAINTY tier.
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
        is_scratch = file_path.startswith("scratch/") or "/scratch/" in file_path
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

        # HYPOTHESIS (31-50%): Can Write scratch/ only
        if tier_name == "HYPOTHESIS" and is_production:
            message = f"""🚫 PRODUCTION WRITE BLOCKED AT HYPOTHESIS TIER

Action: Write {Path(file_path).name}
Your Confidence: {current_confidence}% ({tier_name} TIER)
Required: 71%+ (CERTAINTY tier)

You can write to scratch/ for experiments, but production requires CERTAINTY.
Gather more evidence before writing production code.

Confidence Penalty: -10%"""
            return False, message, "tier_violation", "enforce"

        # WORKING (51-70%): Still can't write production
        if tier_name == "WORKING" and is_production:
            message = f"""🚫 PRODUCTION WRITE BLOCKED AT WORKING TIER

Action: Write {Path(file_path).name}
Your Confidence: {current_confidence}% ({tier_name} TIER)
Required: 71%+ (CERTAINTY tier)

WORKING tier allows editing scratch/, but production writes require CERTAINTY.
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
        elif "scripts/ops/verify.py" in command or "/verify " in command:
            boost = CONFIDENCE_GAINS["verify_success"]
        elif "scripts/ops/research.py" in command or "/research" in command:
            boost = CONFIDENCE_GAINS["web_search"]
        elif "scripts/ops/probe.py" in command or "/probe" in command:
            boost = CONFIDENCE_GAINS["probe_api"]
        elif "scripts/ops/audit.py" in command:
            boost = CONFIDENCE_GAINS["run_audit"]
        elif "pytest" in command or "python -m pytest" in command:
            boost = CONFIDENCE_GAINS["run_tests"]
        elif "scripts/ops/council.py" in command:
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
    except:
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
    except:
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
    except:
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
  python3 scripts/ops/balanced_council.py "Review session with multiple dangerous command attempts - assess if actions are intentional or problematic"
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
    except:
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
