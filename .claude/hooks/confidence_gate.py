#!/usr/bin/env python3
"""
Confidence Gate Hook: Blocks Write/Edit to production files at <71% confidence
Allows scratch/ writes at any level (experimentation)
Supports SUDO bypass via transcript check
"""
import sys
import json
from pathlib import Path


def validate_file_path(file_path: str) -> bool:
    """
    Validate file path to prevent path traversal attacks.
    Per official docs: "Block path traversal - Check for .. in file paths"
    """
    if not file_path:
        return True

    # Normalize path to resolve any . or .. components
    normalized = str(Path(file_path).resolve())

    # Check for path traversal attempts
    if '..' in file_path:
        return False

    return True


# Load confidence state
MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
STATE_FILE = MEMORY_DIR / "confidence_state.json"


def load_confidence():
    """Load current confidence level"""
    if not STATE_FILE.exists():
        return 0
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
            return data.get("current_confidence", 0)
    except (FileNotFoundError, PermissionError):
        # File issues - return 0
        return 0
    except json.JSONDecodeError as e:
        # Corrupt confidence file - log and return 0
        print(f"Warning: Corrupt confidence file - {e}", file=sys.stderr)
        return 0
    except Exception as e:
        # Unexpected error - log and return 0
        print(f"Error loading confidence: {type(e).__name__} - {e}", file=sys.stderr)
        return 0


# Load input
try:
    input_data = json.load(sys.stdin)
except Exception:
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
        )
    )
    sys.exit(0)

tool_name = input_data.get("tool_name", "")
tool_params = input_data.get("tool_input", {})

# Only intercept Write/Edit/Delete operations
if tool_name not in ["Write", "Edit", "Delete"]:
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
        )
    )
    sys.exit(0)

# Get file path
file_path = tool_params.get("file_path", "")
if not file_path:
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
        )
    )
    sys.exit(0)

# Delete operations ALWAYS require CERTAINTY tier (no scratch exception)
if tool_name == "Delete":
    confidence = load_confidence()
    
    # Check for SUDO bypass via transcript
    transcript_path = input_data.get("transcript_path", "")
    sudo_found = False
    if transcript_path:
        try:
            import os
            if os.path.exists(transcript_path):
                with open(transcript_path, 'r') as tf:
                    transcript = tf.read()
                    last_chunk = transcript[-5000:] if len(transcript) > 5000 else transcript
                    sudo_found = "SUDO" in last_chunk
        except Exception:
            pass
    
    if sudo_found:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "additionalContext": f"⚠️ SUDO BYPASS: Delete operation allowed ({confidence}% confidence)\nTarget: {file_path}",
                    }
                }
            )
        )
        sys.exit(0)
    
    if confidence < 71:
        additional_context = f"""🚨 DELETE OPERATION BLOCKED

Current Confidence: {confidence}% (INSUFFICIENT)
Target File: {file_path}

⛔ DELETE OPERATIONS ALWAYS REQUIRE 71%+ CONFIDENCE

Deleting files is irreversible and more dangerous than editing.
There is NO scratch exception for delete operations.

REQUIRED: Reach CERTAINTY tier (71%+) before deleting any files.

Current tier: {"IGNORANCE (0-30%)" if confidence < 31 else "HYPOTHESIS (31-70%)"}

To boost confidence:
  1. Read relevant files (+10% each)
  2. Research context if needed (+20%)
  3. Verify what you're deleting (+15%)

**Deletion requires absolute certainty. No exceptions.**
"""
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": additional_context,
                    }
                }
            )
        )
        sys.exit(0)

# Allow scratch/ writes at any confidence (experimentation)
# (Does NOT apply to Delete - handled above)
if "/scratch/" in file_path or file_path.startswith("scratch/"):
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
        )
    )
    sys.exit(0)

# Check confidence for production files
confidence = load_confidence()

# Check for SUDO bypass via transcript (more reliable than session state)
# The transcript contains the conversation including user's current message
transcript_path = input_data.get("transcript_path", "")
prompt = ""
if transcript_path:
    try:
        import os
        if os.path.exists(transcript_path):
            with open(transcript_path, 'r') as tf:
                transcript = tf.read()
                # Look for SUDO in the last portion of transcript (most recent messages)
                last_chunk = transcript[-5000:] if len(transcript) > 5000 else transcript
                if "SUDO" in last_chunk:
                    prompt = "SUDO"  # Flag that SUDO was found
    except Exception:
        pass

if "SUDO" in prompt:
    # SUDO bypass - allow with warning
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": f"⚠️ SUDO BYPASS: Confidence gate bypassed ({confidence}% < 71%)\nTarget: {file_path}",
                }
            }
        )
    )
    sys.exit(0)

if confidence < 71:
    additional_context = f"""
🚨 CONFIDENCE GATE: PRODUCTION WRITE BLOCKED

Current Confidence: {confidence}% (INSUFFICIENT)
Target File: {file_path}

⛔ PRODUCTION CODE MODIFICATION REQUIRES 71%+ CONFIDENCE

You are attempting to modify production code without runtime verification.

CURRENT TIER: {"IGNORANCE (0-30%)" if confidence < 31 else "HYPOTHESIS (31-70%)"}

REQUIRED EVIDENCE FOR 71%+:
  1. Read relevant code files (+10% each)
  2. Research documentation (/research, +20%)
  3. Inspect runtime APIs (/probe, +30%)
  4. Verify system state (/verify, +40%)

ALLOWED RIGHT NOW:
  ✅ Write to scratch/ (experimentation allowed)
  ✅ Gather evidence using investigation tools
  ✅ Test hypotheses in throwaway code

FORBIDDEN:
  ❌ Modify scripts/ at <71%
  ❌ Edit production files at <71%
  ❌ Commit unverified changes

NEXT STEPS:
  1. python3 scripts/ops/confidence.py status (check current state)
  2. Gather evidence to reach 71%
  3. Retry this operation after threshold met

**Earn the right to code. Evidence > Intuition.**
"""
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": additional_context,
                }
            }
        )
    )
    sys.exit(0)

# Confidence sufficient, allow operation
print(
    json.dumps(
        {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
    )
)
sys.exit(0)
