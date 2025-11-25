#!/usr/bin/env python3
"""
Hack-Around Gate: PreToolUse hook that detects and blocks hack-around patterns

When Write/Edit contains hack-around patterns (try/except pass, || true, etc.),
this hook:
1. Detects the pattern
2. Logs the violation
3. Applies confidence penalty
4. Injects warning demanding root cause fix
5. Optionally BLOCKS the operation (for egregious patterns)

This forces Claude to fix actual errors instead of patching around them.
"""
import sys
import json
import re
import subprocess
import os
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict

# Paths
HOOK_DIR = Path(__file__).resolve().parent
if ".claude/hooks" in str(HOOK_DIR):
    MEMORY_DIR = HOOK_DIR.parent / "memory"
    PROJECT_ROOT = HOOK_DIR.parent.parent
else:
    # Running from scratch
    PROJECT_ROOT = HOOK_DIR.parent
    MEMORY_DIR = PROJECT_ROOT / ".claude" / "memory"

HACK_AROUND_LOG = MEMORY_DIR / "hack_around_violations.json"
CONFIDENCE_CMD = PROJECT_ROOT / "scripts" / "ops" / "confidence.py"

# ============================================================================
# HACK-AROUND PATTERNS
# ============================================================================

# (regex, description, severity, block?)
# severity: 1-10 (10 = most severe)
# block: if True, operation is BLOCKED, not just warned
HACK_AROUND_PATTERNS = [
    # BLOCKING patterns (egregious hack-arounds)
    (r'except\s*:\s*pass\s*$',
     "Bare except with pass - suppresses ALL errors silently",
     10, True),

    (r'except\s+Exception\s*:\s*pass',
     "Catching Exception with pass - broad error suppression",
     9, True),

    (r'\|\|\s*true\s*$',
     "|| true at end of command - hiding failures",
     8, True),

    (r'chmod\s+777\s',
     "chmod 777 - security vulnerability, fix actual permissions",
     9, True),

    # WARNING patterns (suspicious but may be legitimate)
    (r'except\s+\w+Error\s*:\s*pass',
     "Specific error with pass - consider proper handling",
     6, False),

    (r'2>\s*/dev/null',
     "Hiding stderr - are you suppressing useful errors?",
     5, False),

    (r'@pytest\.mark\.skip',
     "Skipping test - fix the test instead of skipping",
     7, False),

    (r'@unittest\.skip',
     "Skipping test - fix the test instead of skipping",
     7, False),

    (r'#.*(TODO|FIXME).*(fix|hack|workaround|temporary)',
     "TODO/hack comment detected - this should be fixed now",
     4, False),

    (r'if\s+.*:\s*pass\s*$',
     "Empty if block with pass - incomplete implementation",
     5, False),

    (r'raise\s+NotImplementedError',
     "NotImplementedError - stub code, implement properly",
     6, False),

    (r'\.\.\.\s*$',
     "Ellipsis as placeholder - incomplete implementation",
     5, False),
]

# Patterns that are NEVER hack-arounds (whitelist)
LEGITIMATE_PATTERNS = [
    r'except\s+\w+.*:\s*\n\s*(logger|logging|print|raise|return|self\.)',  # Proper handling
    r'2>/dev/null.*\|\|',  # Suppressing then handling
    r'@pytest\.mark\.skip.*reason=',  # Skip with reason (maybe legitimate)
    r'@abstractmethod',  # Abstract methods use ...
    r'class\s+\w+.*Protocol',  # Protocol classes use ...
    r'\.pyi$',  # Type stub files
]

# ============================================================================
# DETECTION
# ============================================================================

def is_legitimate(content: str, match_text: str, match_start: int = 0) -> bool:
    """Check if the match is actually legitimate code (within context window)."""
    # Check within ±200 chars of match for context
    context_start = max(0, match_start - 200)
    context_end = min(len(content), match_start + len(match_text) + 200)
    context = content[context_start:context_end]

    for pattern in LEGITIMATE_PATTERNS:
        if re.search(pattern, context, re.MULTILINE | re.IGNORECASE):
            return True
    return False

def detect_hack_arounds(content: str) -> List[Tuple[str, str, int, bool]]:
    """
    Detect hack-around patterns in content.
    Returns: List of (description, matched_text, severity, should_block)
    """
    detections = []

    for pattern, description, severity, block in HACK_AROUND_PATTERNS:
        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            matched_text = match.group(0)
            # Check if it's actually legitimate (pass match position for context)
            if not is_legitimate(content, matched_text, match.start()):
                detections.append((description, matched_text, severity, block))

    # Sort by severity (highest first)
    detections.sort(key=lambda x: x[2], reverse=True)
    return detections

# ============================================================================
# LOGGING & PENALTY
# ============================================================================

def load_hack_around_log() -> Dict:
    """Load hack-around violation log."""
    if not HACK_AROUND_LOG.exists():
        return {"violations": [], "session_counts": {}}
    try:
        with open(HACK_AROUND_LOG) as f:
            return json.load(f)
    except Exception:
        return {"violations": [], "session_counts": {}}

def log_violation(pattern_desc: str, matched_text: str, file_path: str, blocked: bool) -> int:
    """Log a hack-around violation. Returns session count."""
    log_data = load_hack_around_log()
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")[:16]

    violation = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "pattern": pattern_desc,
        "matched_text": matched_text[:100],
        "file_path": str(file_path),
        "blocked": blocked,
    }
    log_data["violations"].append(violation)
    log_data["session_counts"][session_id] = log_data["session_counts"].get(session_id, 0) + 1

    # Prune to last 100
    if len(log_data["violations"]) > 100:
        log_data["violations"] = log_data["violations"][-100:]

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(HACK_AROUND_LOG, "w") as f:
        json.dump(log_data, f, indent=2)

    return log_data["session_counts"][session_id]

def apply_penalty(penalty_type: str, reason: str):
    """Apply confidence penalty."""
    try:
        subprocess.run(
            ["python3", str(CONFIDENCE_CMD), "loss", penalty_type, reason],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass

# ============================================================================
# MAIN HOOK
# ============================================================================

def main():
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        # Parse error - allow operation
        print(json.dumps({"proceed": True}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only check Write and Edit operations
    if tool_name not in ["Write", "Edit"]:
        print(json.dumps({"proceed": True}))
        sys.exit(0)

    # Get content to check
    if tool_name == "Write":
        content = tool_input.get("content", "")
        file_path = tool_input.get("file_path", "")
    elif tool_name == "Edit":
        content = tool_input.get("new_string", "")
        file_path = tool_input.get("file_path", "")
    else:
        content = ""
        file_path = ""

    if not content:
        print(json.dumps({"proceed": True}))
        sys.exit(0)

    # Skip scratch files (experimentation allowed)
    if "scratch/" in file_path or "/scratch/" in file_path:
        print(json.dumps({"proceed": True}))
        sys.exit(0)

    # Detect hack-arounds
    detections = detect_hack_arounds(content)

    if not detections:
        print(json.dumps({"proceed": True}))
        sys.exit(0)

    # Get most severe detection
    worst = detections[0]
    description, matched_text, severity, should_block = worst

    # Log violation
    session_count = log_violation(description, matched_text, file_path, should_block)

    # Determine penalty
    if severity >= 8:
        penalty_type = "hack_around_severe"
        penalty_amount = -20
    elif severity >= 5:
        penalty_type = "hack_around_detected"
        penalty_amount = -10
    else:
        penalty_type = "hack_around_minor"
        penalty_amount = -5

    # Apply penalty
    apply_penalty(penalty_type, f"Hack-around: {description}")

    # Build response
    all_detections = "\n".join([f"  • {d[0]} (severity: {d[2]})" for d in detections[:5]])

    if should_block:
        # BLOCK the operation
        message = f"""🚫 HACK-AROUND BLOCKED

You are attempting to write code that patches AROUND an error instead of FIXING it.

Detected Pattern: {description}
Matched Code: `{matched_text[:60]}...`
Severity: {severity}/10
File: {Path(file_path).name}

📉 CONFIDENCE PENALTY: {penalty_amount}% ({penalty_type})
📊 Session Hack-Around Violations: {session_count}

All detected patterns:
{all_detections}

⛔ THIS OPERATION IS BLOCKED.

REQUIRED ACTION - Fix the ROOT CAUSE:
1. Identify the ACTUAL error that caused you to write this hack
2. Fix that error properly (install package, fix config, fix permissions, etc.)
3. Remove the hack-around code
4. Then retry your operation

DETOUR-FIX PROTOCOL:
  • Import error → pip install the package
  • Test failure → fix the code being tested, not the test
  • Permission error → fix permissions properly
  • Config error → fix/create the config file

Use "SUDO" to bypass this block (tracked and penalized further).
"""
        print(json.dumps({
            "error": message,
            "proceed": False,
        }))
    else:
        # WARNING only
        message = f"""⚠️ HACK-AROUND WARNING

Suspicious pattern detected that may be patching around an error instead of fixing it.

Detected Pattern: {description}
Matched Code: `{matched_text[:60]}...`
Severity: {severity}/10
File: {Path(file_path).name}

📉 CONFIDENCE PENALTY: {penalty_amount}% ({penalty_type})
📊 Session Hack-Around Violations: {session_count}

All detected patterns:
{all_detections}

CONSIDER:
  • Is this a proper fix or a workaround?
  • Will this error happen again?
  • Should you fix the root cause instead?

PROCEEDING with warning. Consider running /verify to ensure proper fix.
"""
        print(json.dumps({
            "proceed": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": message,
            }
        }))

    sys.exit(0)

if __name__ == "__main__":
    main()
