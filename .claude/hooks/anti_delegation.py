#!/usr/bin/env python3
"""
Anti-Delegation Hook: Detects when Claude offloaded work to the user

PHILOSOPHY: Claude optimizes for "appearing helpful" over "actually completing tasks".
This manifests as giving instructions ("try running X") instead of running X itself.

DETECTION: We can't intercept Claude's output, but we CAN detect when the user's
response indicates they just followed instructions Claude should have executed:
- "Here's the output..."
- "I ran that and..."
- Pasting terminal output
- Brief confirmations like "done" or "ok"

When detected:
1. Log violation to pattern tracker
2. Apply confidence penalty
3. Inject shame + reminder that Claude should DO, not INSTRUCT.
"""
import sys
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime

# Paths
HOOK_DIR = Path(__file__).resolve().parent
MEMORY_DIR = HOOK_DIR.parent / "memory"
TRACKER_FILE = MEMORY_DIR / "delegation_violations.json"
CONFIDENCE_CMD = HOOK_DIR.parent.parent / "scripts" / "ops" / "confidence.py"

# ============================================================================
# PATTERN TRACKING
# ============================================================================

def load_tracker():
    """Load delegation violation tracker."""
    if not TRACKER_FILE.exists():
        return {"violations": [], "session_counts": {}}
    try:
        with open(TRACKER_FILE) as f:
            return json.load(f)
    except Exception:
        return {"violations": [], "session_counts": {}}

def save_tracker(tracker):
    """Save delegation violation tracker."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    # Keep only last 100 violations to prevent unbounded growth
    if len(tracker.get("violations", [])) > 100:
        tracker["violations"] = tracker["violations"][-100:]
    with open(TRACKER_FILE, "w") as f:
        json.dump(tracker, f, indent=2)

def log_violation(detection_types, evidence, prompt_snippet):
    """Log a delegation violation for pattern analysis."""
    tracker = load_tracker()

    # Get session ID from environment or generate one
    import os
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")[:16]

    violation = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "detection_types": detection_types,
        "evidence": evidence,
        "prompt_snippet": prompt_snippet[:100],  # First 100 chars
    }
    tracker["violations"].append(violation)

    # Track per-session count for repeated violation detection
    tracker["session_counts"][session_id] = tracker["session_counts"].get(session_id, 0) + 1
    session_count = tracker["session_counts"][session_id]

    save_tracker(tracker)
    return session_count

def apply_penalty(penalty_type, reason):
    """Apply confidence penalty via the epistemology system."""
    try:
        subprocess.run(
            ["python3", str(CONFIDENCE_CMD), "loss", penalty_type, reason],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass  # Silent failure - don't break the hook

# ============================================================================
# LOAD INPUT
# ============================================================================

try:
    input_data = json.load(sys.stdin)
except Exception:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "",
        }
    }))
    sys.exit(0)

prompt = input_data.get("prompt", "")

if not prompt:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "",
        }
    }))
    sys.exit(0)

prompt_lower = prompt.lower().strip()
prompt_lines = prompt.strip().split('\n')

# ============================================================================
# DETECTION PATTERNS: User reporting back from delegated work
# ============================================================================

# User explicitly saying they ran something
execution_reports = [
    "i ran",
    "i tried",
    "i executed",
    "when i run",
    "after running",
    "i did that",
    "ok i did",
    "done, here",
    "here's what i got",
    "here's the output",
    "here's the result",
    "this is what it says",
    "it returned",
    "it shows",
    "it says",
    "the output is",
    "the result is",
    "the error is",
    "got this error",
    "getting this error",
    "i get this",
    "i'm getting",
    "this happened",
    "that gave me",
]

# Brief confirmations (user just did what Claude asked)
brief_confirmations = [
    "done",
    "ok done",
    "okay done",
    "did it",
    "here you go",
    "here it is",
    "there you go",
    "as requested",
    "as you asked",
    "like you said",
]

# Terminal/command output patterns (first line indicators)
terminal_patterns = [
    r'^[\$\>\#]\s',           # Shell prompts: $ command, > prompt, # root
    r'^error:',               # Error messages
    r'^warning:',             # Warning messages
    r'^traceback',            # Python tracebacks
    r'^exception',            # Exception messages
    r'^\s*at\s+\w+\s*\(',     # Stack traces (at Function (file:line))
    r'^\s*file\s+"',          # Python file references
    r'^npm\s+(err|warn)',     # npm errors
    r'^errno',                # System errors
    r'^\[\d+\]',              # Process output [pid]
    r'^fatal:',               # Git fatal errors
    r'^command.*failed',      # Command failures
]

# ============================================================================
# COUNTER-PATTERNS: Legitimate user messages (DON'T flag these)
# ============================================================================

# User asking Claude to do something
asking_claude = [
    "can you run",
    "could you run",
    "please run",
    "please execute",
    "please try",
    "run this",
    "execute this",
    "try this",
    "check this",
    "look at this",
    "what does this",
    "why does this",
    "how do i",
    "how can i",
    "what's wrong",
    "can you help",
    "can you fix",
    "can you check",
]

# User providing context/code (not reporting back)
providing_context = [
    "here's my code",
    "here's the code",
    "this is my",
    "my config",
    "my file",
    "i have this",
    "i wrote this",
    "i'm trying to",
    "i want to",
    "i need to",
]

# ============================================================================
# DETECTION LOGIC
# ============================================================================

def is_legitimate_message():
    """Check if message is a legitimate user request, not a report-back."""
    for pattern in asking_claude:
        if pattern in prompt_lower:
            return True
    for pattern in providing_context:
        if pattern in prompt_lower:
            return True
    # Questions are usually legitimate
    if prompt.strip().endswith('?'):
        return True
    return False

def detect_execution_report():
    """Detect if user is reporting output from running something."""
    for pattern in execution_reports:
        if pattern in prompt_lower:
            return True, f"Phrase detected: '{pattern}'"
    return False, None

def detect_brief_confirmation():
    """Detect brief confirmations that suggest user just followed instructions."""
    # Only flag very short messages that are confirmations
    if len(prompt_lower) < 50:
        for pattern in brief_confirmations:
            if prompt_lower.startswith(pattern) or prompt_lower == pattern:
                return True, f"Brief confirmation: '{pattern}'"
    return False, None

def detect_terminal_output():
    """Detect if message looks like pasted terminal output."""
    if not prompt_lines:
        return False, None

    first_line = prompt_lines[0].lower().strip()

    for pattern in terminal_patterns:
        if re.match(pattern, first_line, re.IGNORECASE):
            return True, f"Terminal output pattern: {pattern}"

    # Also detect if message is mostly code/output (high symbol density)
    symbol_chars = sum(1 for c in prompt if c in '{}[]()<>|&;$#@!%^*')
    if len(prompt) > 50 and symbol_chars / len(prompt) > 0.1:
        # High symbol density + no question = likely pasted output
        if '?' not in prompt:
            return True, "High symbol density (likely pasted output)"

    # Detect raw error-like text (short, no question, looks like system message)
    error_keywords = ['denied', 'failed', 'error', 'permission', 'refused',
                      'not found', 'no such', 'cannot', 'unable', 'forbidden',
                      'timeout', 'connection', 'rejected', 'invalid', 'missing']
    if len(prompt) < 200 and '?' not in prompt:
        keyword_count = sum(1 for kw in error_keywords if kw in prompt_lower)
        if keyword_count >= 2:
            return True, f"Raw error text ({keyword_count} error keywords)"

    return False, None

# ============================================================================
# MAIN DETECTION
# ============================================================================

# Skip if this looks like a legitimate user request
if is_legitimate_message():
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "",
        }
    }))
    sys.exit(0)

# Run detection
detections = []

exec_detected, exec_reason = detect_execution_report()
if exec_detected:
    detections.append(("EXECUTION_REPORT", exec_reason))

confirm_detected, confirm_reason = detect_brief_confirmation()
if confirm_detected:
    detections.append(("BRIEF_CONFIRMATION", confirm_reason))

terminal_detected, terminal_reason = detect_terminal_output()
if terminal_detected:
    detections.append(("TERMINAL_OUTPUT", terminal_reason))

# ============================================================================
# OUTPUT
# ============================================================================

if detections:
    detection_types = [d[0] for d in detections]
    detection_reasons = [d[1] for d in detections]

    # Log violation and get session count
    session_count = log_violation(detection_types, detection_reasons, prompt)

    # Determine severity and penalty based on repetition
    if session_count >= 3:
        severity = "CRITICAL"
        penalty_type = "delegation_repeated"
        penalty_amount = -25
    elif len(detections) >= 2:
        severity = "CRITICAL"
        penalty_type = "delegation_detected"
        penalty_amount = -15
    else:
        severity = "WARNING"
        penalty_type = "delegation_detected"
        penalty_amount = -15

    # Apply confidence penalty
    apply_penalty(penalty_type, f"Delegation detected: {', '.join(detection_types)}")

    additional_context = f"""
🚫 DELEGATION DETECTED - {severity}

The user's response suggests they just performed work that YOU should have done.
Detection: {', '.join(detection_types)}
Evidence: {'; '.join(detection_reasons)}

📉 CONFIDENCE PENALTY APPLIED: {penalty_amount}% ({penalty_type})
📊 Session Violations: {session_count} (3+ = CRITICAL with -25% penalty)

⚠️ ANTI-DELEGATION PROTOCOL ACTIVE (CLAUDE.md § Rule #5, #17):

You have VIOLATED the Operator Protocol by offloading work to the user.
This is tracked and penalized. Repeated violations compound the penalty.

FORBIDDEN PHRASES (that lead to offloading):
  ❌ "Try running..."
  ❌ "You can check by..."
  ❌ "Run this command..."
  ❌ "Execute the following..."
  ❌ "Let me know what happens when..."
  ❌ "You might want to..."

REQUIRED BEHAVIOR:
  ✅ RUN commands yourself using Bash tool
  ✅ CHECK outputs yourself before asking user
  ✅ VERIFY results yourself with verify.py
  ✅ FIX issues yourself before reporting back
  ✅ COMPLETE the task, don't give homework

THE RULE: If YOU can run it, YOU run it. The user is not your QA team.

NOW: Process what the user provided, but DO NOT delegate further work back to them.
Complete the task fully before responding.
"""

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        }
    }))
else:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "",
        }
    }))

sys.exit(0)
