#!/usr/bin/env python3
"""
Detour Protocol Library - Detection and Context Preservation for Unexpected Issues

The Detour Protocol handles the common scenario where Claude encounters an unexpected
blocking issue mid-task that requires a "side quest" to fix before continuing.

Key Features:
1. Pattern detection in tool output (errors that block progress)
2. Context preservation (save original task to resume later)
3. Subagent spawning recommendation (isolate fix from main context)
4. Stack-based detour tracking (nested detours supported)

Philosophy:
- Unexpected issues should NOT pollute main task context
- Original task context must be preserved and restored
- Subagents provide free context isolation
- Resume prompts ensure task completion
"""
import json
import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Paths - .claude/lib -> .claude -> .claude/memory
MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
DETOUR_STACK_FILE = MEMORY_DIR / "detour_stack.json"


class DetourType(Enum):
    """Categories of blocking issues that trigger detours"""
    IMPORT_ERROR = "import_error"          # Missing Python module
    PERMISSION_ERROR = "permission_error"  # File/resource permission denied
    FILE_NOT_FOUND = "file_not_found"      # Missing file/directory
    TEST_FAILURE = "test_failure"          # Test suite failures
    BUILD_ERROR = "build_error"            # npm/cargo/pip build failures
    CONFIG_ERROR = "config_error"          # Missing/invalid configuration
    PORT_CONFLICT = "port_conflict"        # Address already in use
    DEPENDENCY_ERROR = "dependency_error"  # Package dependency issues
    SYNTAX_ERROR = "syntax_error"          # Code syntax problems
    CONNECTION_ERROR = "connection_error"  # Network/DB connection issues
    UNKNOWN = "unknown"


class DetourStatus(Enum):
    """Status of a detour"""
    DETECTED = "detected"        # Issue detected, not yet addressed
    IN_PROGRESS = "in_progress"  # Subagent spawned, working on fix
    RESOLVED = "resolved"        # Issue fixed, can resume original task
    ABANDONED = "abandoned"      # User chose to abandon original task
    BLOCKED = "blocked"          # Detour itself is blocked (nested)


@dataclass
class DetourPattern:
    """Pattern for detecting blocking issues"""
    pattern: str           # Regex pattern
    detour_type: DetourType
    severity: int          # 1-10, higher = more blocking
    suggested_agent: str   # Agent type to spawn
    description: str       # Human-readable description


@dataclass
class Detour:
    """A detected detour requiring side-quest resolution"""
    id: str
    original_task: str           # What we were doing before
    blocking_issue: str          # The error/issue detected
    detour_type: DetourType
    severity: int
    detected_at_turn: int
    detected_at_time: str
    suggested_agent: str
    tool_name: str               # Tool that produced the error
    tool_input: Dict             # Input that caused the error
    error_snippet: str           # Relevant error output (truncated)
    status: DetourStatus
    resolution_turn: Optional[int] = None
    resolution_note: Optional[str] = None
    subagent_id: Optional[str] = None


# Detection Patterns (ordered by severity)
DETOUR_PATTERNS: List[DetourPattern] = [
    # Import/Module Errors (High severity - blocks all execution)
    DetourPattern(
        pattern=r"ModuleNotFoundError:\s*No module named ['\"](\w+)['\"]",
        detour_type=DetourType.IMPORT_ERROR,
        severity=9,
        suggested_agent="macgyver",
        description="Missing Python module"
    ),
    DetourPattern(
        pattern=r"ImportError:\s*cannot import name ['\"](\w+)['\"]",
        detour_type=DetourType.IMPORT_ERROR,
        severity=8,
        suggested_agent="macgyver",
        description="Import name error"
    ),

    # Permission Errors (High severity - blocks file operations)
    DetourPattern(
        pattern=r"Permission denied|EACCES|PermissionError",
        detour_type=DetourType.PERMISSION_ERROR,
        severity=8,
        suggested_agent="sherlock",
        description="Permission denied"
    ),

    # File Not Found (Medium-High severity)
    DetourPattern(
        pattern=r"FileNotFoundError|No such file or directory|ENOENT",
        detour_type=DetourType.FILE_NOT_FOUND,
        severity=7,
        suggested_agent="sherlock",
        description="File or directory not found"
    ),

    # Test Failures (Medium severity - blocks verification)
    DetourPattern(
        pattern=r"FAILED\s+[\w/]+\.py::|pytest.*(\d+)\s+failed",
        detour_type=DetourType.TEST_FAILURE,
        severity=6,
        suggested_agent="tester",
        description="Test failures detected"
    ),
    DetourPattern(
        pattern=r"AssertionError|assert.*failed",
        detour_type=DetourType.TEST_FAILURE,
        severity=6,
        suggested_agent="tester",
        description="Assertion failure"
    ),

    # Build Errors (High severity - blocks deployment)
    DetourPattern(
        pattern=r"npm ERR!|npm error",
        detour_type=DetourType.BUILD_ERROR,
        severity=8,
        suggested_agent="macgyver",
        description="npm build error"
    ),
    DetourPattern(
        pattern=r"cargo error|error\[E\d+\]",
        detour_type=DetourType.BUILD_ERROR,
        severity=8,
        suggested_agent="macgyver",
        description="Cargo/Rust build error"
    ),
    DetourPattern(
        pattern=r"pip.*error|Could not find a version",
        detour_type=DetourType.BUILD_ERROR,
        severity=7,
        suggested_agent="macgyver",
        description="pip dependency error"
    ),

    # Config Errors (Medium severity)
    DetourPattern(
        pattern=r"missing.*(config|configuration)|invalid.*config|ConfigError",
        detour_type=DetourType.CONFIG_ERROR,
        severity=6,
        suggested_agent="sherlock",
        description="Configuration error"
    ),
    DetourPattern(
        pattern=r"Environment variable.*not set|missing.*env",
        detour_type=DetourType.CONFIG_ERROR,
        severity=5,
        suggested_agent="sherlock",
        description="Missing environment variable"
    ),

    # Port Conflicts (Medium severity)
    DetourPattern(
        pattern=r"Address already in use|EADDRINUSE|port.*already.*bound",
        detour_type=DetourType.PORT_CONFLICT,
        severity=5,
        suggested_agent="sherlock",
        description="Port already in use"
    ),

    # Dependency Errors
    DetourPattern(
        pattern=r"dependency.*not found|unmet.*dependency|peer.*dependency",
        detour_type=DetourType.DEPENDENCY_ERROR,
        severity=7,
        suggested_agent="macgyver",
        description="Dependency not satisfied"
    ),

    # Syntax Errors (High severity - code won't run)
    DetourPattern(
        pattern=r"SyntaxError:|IndentationError:|TabError:",
        detour_type=DetourType.SYNTAX_ERROR,
        severity=9,
        suggested_agent="sherlock",
        description="Syntax error in code"
    ),

    # Connection Errors (Medium severity)
    DetourPattern(
        pattern=r"ConnectionRefusedError|Connection refused|ECONNREFUSED",
        detour_type=DetourType.CONNECTION_ERROR,
        severity=6,
        suggested_agent="sherlock",
        description="Connection refused"
    ),
    DetourPattern(
        pattern=r"timeout|TimeoutError|ETIMEDOUT",
        detour_type=DetourType.CONNECTION_ERROR,
        severity=5,
        suggested_agent="sherlock",
        description="Connection timeout"
    ),
]


def load_detour_stack() -> Dict:
    """Load detour stack from file"""
    if not DETOUR_STACK_FILE.exists():
        return {"detours": [], "resolved": [], "stats": {"total_detours": 0, "total_resolved": 0}}

    try:
        with open(DETOUR_STACK_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"detours": [], "resolved": [], "stats": {"total_detours": 0, "total_resolved": 0}}


def save_detour_stack(stack: Dict) -> bool:
    """Save detour stack to file. Returns True on success, False on failure."""
    # SUDO: Simple error handling fix per void.py gap analysis
    try:
        DETOUR_STACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DETOUR_STACK_FILE, 'w') as f:
            json.dump(stack, f, indent=2, default=str)
        return True
    except (IOError, OSError, PermissionError) as e:
        import sys
        print(f"Warning: Failed to save detour stack: {e}", file=sys.stderr)
        return False


def detect_detour(tool_output: str, tool_name: str, tool_input: Dict) -> Optional[Tuple[DetourPattern, str]]:
    """
    Analyze tool output for blocking issues that require a detour.

    Args:
        tool_output: The output/error from a tool execution
        tool_name: Name of the tool that was used
        tool_input: Input parameters to the tool

    Returns:
        Tuple of (matching pattern, matched text) if detour detected, None otherwise
    """
    for pattern in DETOUR_PATTERNS:
        match = re.search(pattern.pattern, tool_output, re.IGNORECASE | re.MULTILINE)
        if match:
            return (pattern, match.group(0))

    return None


def create_detour(
    original_task: str,
    pattern: DetourPattern,
    error_snippet: str,
    turn: int,
    tool_name: str,
    tool_input: Dict
) -> Detour:
    """Create a new detour entry"""
    return Detour(
        id=str(uuid.uuid4())[:8],
        original_task=original_task,
        blocking_issue=error_snippet[:200],
        detour_type=pattern.detour_type,
        severity=pattern.severity,
        detected_at_turn=turn,
        detected_at_time=datetime.now().isoformat(),
        suggested_agent=pattern.suggested_agent,
        tool_name=tool_name,
        tool_input=tool_input,
        error_snippet=error_snippet[:500],
        status=DetourStatus.DETECTED
    )


def push_detour(detour: Detour) -> None:
    """Push a detour onto the stack"""
    stack = load_detour_stack()
    stack["detours"].append(asdict(detour))
    stack["stats"]["total_detours"] = stack["stats"].get("total_detours", 0) + 1
    save_detour_stack(stack)


def pop_detour(detour_id: Optional[str] = None) -> Optional[Dict]:
    """
    Pop a detour from the stack (mark as resolved).

    Args:
        detour_id: Specific detour to resolve. If None, resolves most recent.

    Returns:
        The resolved detour dict, or None if stack is empty
    """
    stack = load_detour_stack()

    if not stack["detours"]:
        return None

    if detour_id:
        # Find specific detour
        for i, detour in enumerate(stack["detours"]):
            if detour["id"] == detour_id:
                resolved = stack["detours"].pop(i)
                resolved["status"] = DetourStatus.RESOLVED.value
                stack["resolved"].append(resolved)
                stack["stats"]["total_resolved"] = stack["stats"].get("total_resolved", 0) + 1
                save_detour_stack(stack)
                return resolved
        return None
    else:
        # Pop most recent
        resolved = stack["detours"].pop()
        resolved["status"] = DetourStatus.RESOLVED.value
        stack["resolved"].append(resolved)
        stack["stats"]["total_resolved"] = stack["stats"].get("total_resolved", 0) + 1
        save_detour_stack(stack)
        return resolved


def peek_detour() -> Optional[Dict]:
    """Look at current detour without removing it"""
    stack = load_detour_stack()
    if stack["detours"]:
        return stack["detours"][-1]
    return None


def get_active_detours() -> List[Dict]:
    """Get all active (unresolved) detours"""
    stack = load_detour_stack()
    return stack.get("detours", [])


def mark_detour_in_progress(detour_id: str, subagent_id: Optional[str] = None) -> bool:
    """Mark a detour as being worked on"""
    stack = load_detour_stack()

    for detour in stack["detours"]:
        if detour["id"] == detour_id:
            detour["status"] = DetourStatus.IN_PROGRESS.value
            if subagent_id:
                detour["subagent_id"] = subagent_id
            save_detour_stack(stack)
            return True

    return False


def abandon_detour(detour_id: str, reason: str) -> bool:
    """Abandon a detour (user decided not to fix)"""
    stack = load_detour_stack()

    for i, detour in enumerate(stack["detours"]):
        if detour["id"] == detour_id:
            detour["status"] = DetourStatus.ABANDONED.value
            detour["resolution_note"] = reason
            stack["resolved"].append(stack["detours"].pop(i))
            save_detour_stack(stack)
            return True

    return False


def get_resume_prompt(detour: Dict) -> str:
    """Generate a prompt to help Claude resume the original task"""
    return f"""
🔄 DETOUR RESOLVED - RESUME ORIGINAL TASK

The blocking issue has been addressed. Resume your original task:

**Original Task:** {detour['original_task']}
**Issue Fixed:** {detour['blocking_issue'][:100]}
**Detour ID:** {detour['id']}

Continue from where you left off. The issue that was blocking you should now be resolved.
"""


def generate_detour_suggestion(
    pattern: DetourPattern,
    error_snippet: str,
    original_task: str
) -> str:
    """Generate suggestion for handling the detour"""

    agent_descriptions = {
        "sherlock": "read-only investigation agent (cannot modify, only investigate)",
        "macgyver": "improvisation agent (Living off the Land - stdlib solutions)",
        "tester": "test specialist agent (writes/fixes tests)",
        "optimizer": "performance specialist (profiling and optimization)",
    }

    agent_desc = agent_descriptions.get(pattern.suggested_agent, "general-purpose agent")

    return f"""
🚧 DETOUR DETECTED - Blocking Issue Requires Side-Quest

**Type:** {pattern.detour_type.value}
**Severity:** {pattern.severity}/10
**Description:** {pattern.description}

**Error:**
```
{error_snippet[:300]}
```

**Original Task:** {original_task}

**Recommended Action:**
Spawn a **{pattern.suggested_agent}** agent ({agent_desc}) to fix this issue.

The subagent will:
1. Investigate/fix the blocking issue in isolated context
2. Report back when resolved
3. You resume original task with clean context

**Subagent Prompt Template:**
```
Fix the following blocking issue so the main task can continue:

Issue: {pattern.description}
Error: {error_snippet[:150]}

Investigate the root cause and implement a fix. Report success/failure.
```

**To proceed:**
- Use Task tool with subagent_type='{pattern.suggested_agent}'
- Or manually fix and run: /detour resolve

**To skip (not recommended):**
- Run: /detour abandon "reason"
"""


def get_detour_status_report() -> str:
    """Generate status report of current detours"""
    stack = load_detour_stack()
    active = stack.get("detours", [])
    resolved = stack.get("resolved", [])[-5:]  # Last 5 resolved
    stats = stack.get("stats", {})

    if not active and not resolved:
        return "📊 No detours recorded in this session."

    report = ["📊 DETOUR STATUS REPORT\n"]

    if active:
        report.append(f"🔴 Active Detours ({len(active)}):")
        for d in active:
            report.append(f"  [{d['id']}] {d['detour_type']} (sev:{d['severity']}) - {d['blocking_issue'][:50]}...")
            report.append(f"      Original: {d['original_task'][:40]}... | Status: {d['status']}")
    else:
        report.append("✅ No active detours")

    report.append("")

    if resolved:
        report.append(f"📜 Recently Resolved ({len(resolved)}):")
        for d in resolved:
            report.append(f"  [{d['id']}] {d['detour_type']} - {d['blocking_issue'][:50]}...")

    report.append("")
    report.append(f"📈 Stats: {stats.get('total_detours', 0)} total | {stats.get('total_resolved', 0)} resolved")

    return "\n".join(report)


