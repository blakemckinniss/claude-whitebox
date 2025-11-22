#!/usr/bin/env python3
"""
PRE-DELEGATION VALIDATION HOOK
===============================
Prevents delegating to council/critic/advisors without evidence.
Enforces multi-perspective consultation for strategic decisions.

TRIGGER: PreToolUse (Bash)
PATTERN: Calls to council.py, critic.py, judge.py, skeptic.py, think.py
ENFORCEMENT:
  1. Block if confidence < 40% (context requirement)
  2. Block single-advisor strategic decisions (require Six Thinking Hats)

Philosophy: "Garbage in, garbage out" - If you don't understand the problem,
            advisors can't help. Must gather context before delegation.
            Single-perspective advice is confirmation bias. Strategic decisions
            require balanced consultation: Six Thinking Hats (5+1 system).
"""

import json
import sys
import re
from pathlib import Path


def find_project_root():
    """Find project root by looking for scripts/lib/core.py"""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "scripts" / "lib" / "core.py").exists():
            return current
        current = current.parent
    return Path.cwd()


PROJECT_ROOT = find_project_root()
CONFIDENCE_STATE = PROJECT_ROOT / ".claude" / "memory" / "confidence_state.json"

# Advisory scripts that require context
ADVISORS = [
    "council.py",
    "balanced_council.py",  # Six Thinking Hats (5+1 system)
    "critic.py",
    "judge.py",
    "skeptic.py",
    "think.py",
    "consult.py",
]

# Single advisors (not multi-perspective)
SINGLE_ADVISORS = ["critic.py", "judge.py", "skeptic.py", "think.py", "consult.py"]
# NOTE: council.py and balanced_council.py are NOT single advisors (multi-perspective systems)

# Strategic decision patterns (require balanced consultation)
STRATEGIC_PATTERNS = [
    r"\b(?:should|shall)\s+(?:we|i)\s+(?:use|migrate|switch|add|implement|adopt)",
    r"\bis\s+(?:this|it).*?(?:ready|good|worth|safe)",
    r"\b(?:migrate|migration|switch|switching|move|moving)\s+(?:to|from)",
    r"\b(?:architecture|design)\s+(?:decision|choice|proposal)",
    r"\b(?:choose|choosing|select|selecting)\s+(?:between|library|framework|technology)",
]


def load_confidence():
    """Load current confidence level"""
    if not CONFIDENCE_STATE.exists():
        return 0
    try:
        with open(CONFIDENCE_STATE) as f:
            data = json.load(f)
            return data.get("confidence", 0)
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


def is_advisor_call(command):
    """Check if command is calling an advisor script"""
    for advisor in ADVISORS:
        if advisor in command:
            return advisor
    return None


def is_single_advisor(advisor):
    """Check if this is a single-perspective advisor (not council)"""
    return advisor in SINGLE_ADVISORS


def is_strategic_decision(command):
    """Check if command contains strategic decision keywords"""
    command_lower = command.lower()
    for pattern in STRATEGIC_PATTERNS:
        if re.search(pattern, command_lower):
            return True
    return False


def main():
    # Load input
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        # SECURITY: Fail CLOSED on malformed input
        error_msg = f"Pre-delegation: Malformed JSON - {str(e)[:100]}"
        print(error_msg, file=sys.stderr)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": f"Security: Cannot validate delegation without valid input. {error_msg}",
                    }
                }
            )
        )
        sys.exit(0)
    except Exception as e:
        # SECURITY: Fail CLOSED on unexpected errors
        error_msg = f"Pre-delegation: Unexpected error - {type(e).__name__}"
        print(error_msg, file=sys.stderr)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": f"Security: System error in delegation gate. {error_msg}",
                    }
                }
            )
        )
        sys.exit(0)

    tool_name = input_data.get("toolName", "")
    tool_params = input_data.get("toolParams", {})

    # Only intercept Bash tool
    if tool_name != "Bash":
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                    }
                }
            )
        )
        sys.exit(0)

    # Check if it's an advisor call
    command = tool_params.get("command", "")
    advisor = is_advisor_call(command)

    if not advisor:
        # Not an advisor call, allow
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                    }
                }
            )
        )
        sys.exit(0)

    # Check confidence
    confidence = load_confidence()
    DELEGATION_THRESHOLD = 40

    if confidence < DELEGATION_THRESHOLD:
        # BLOCK delegation
        denial_message = f"""
⛔ DELEGATION BLOCKED: INSUFFICIENT CONTEXT

Current Confidence: {confidence}% (Need {DELEGATION_THRESHOLD}%+)
Attempting to call: {advisor}

VIOLATION: "Garbage In, Garbage Out"

You are trying to delegate to advisors without understanding the problem yourself.
The advisors cannot help if you feed them bad assumptions or incomplete context.

Example of what went wrong in this session:
  1. User asked about templates
  2. You had 0% confidence (hadn't read codebase)
  3. You delegated to Critic with wrong assumptions
  4. Critic attacked the wrong target
  5. User had to correct you multiple times

REQUIRED BEFORE DELEGATION:
  ✅ Read relevant files to understand the problem (+10% each)
  ✅ Research external context if needed (/research, +20%)
  ✅ Probe APIs if complex libraries involved (/probe, +30%)
  ✅ Understand what you're actually asking about

MINIMUM {DELEGATION_THRESHOLD}% confidence required to delegate.

WHY THIS MATTERS:
  • Council/Critic are expensive (external API calls)
  • Bad questions → bad advice → wasted user time
  • You must understand the problem to frame it correctly

NEXT STEPS:
  1. Gather evidence about the problem domain
  2. Reach {DELEGATION_THRESHOLD}%+ confidence
  3. Then delegate with proper context

Track: python3 scripts/ops/confidence.py status
"""
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": denial_message,
                    }
                }
            )
        )
        sys.exit(0)

    # Confidence sufficient, now check for balanced consultation requirement
    # Block single-advisor strategic decisions (require multi-perspective)
    if is_single_advisor(advisor) and is_strategic_decision(command):
        denial_message = f"""
⛔ SINGLE-PERSPECTIVE BIAS DETECTED

Attempting to call: {advisor}
Decision type: STRATEGIC (requires balanced consultation)

VIOLATION: Single-Perspective Confirmation Bias

You are trying to consult only ONE advisor for a strategic decision.
This guarantees biased advice:
  • Judge alone → pure pragmatism (may miss innovation)
  • Critic alone → pure pessimism (may kill good ideas)
  • Skeptic alone → pure risk focus (may cause paralysis)

REQUIRED: Six Thinking Hats Multi-Perspective Consultation (5+1 System)
  ⚪ WHITE HAT: Facts & Data (objective evidence)
  🔴 RED HAT: Risks & Intuition (gut instincts, warning signs)
  ⚫ BLACK HAT: Critical Analysis (weaknesses, why it will fail)
  🟡 YELLOW HAT: Benefits & Opportunities (best-case scenario, ROI)
  🟢 GREEN HAT: Alternatives & Creative (what else could we do?)
  🔵 BLUE HAT: Arbiter Synthesis (weighs all 5 perspectives → verdict)

RECOMMENDED APPROACH:

Use Six Thinking Hats Council (evidence-based framework):
   python3 scripts/ops/balanced_council.py "<proposal>"

   Example:
   python3 scripts/ops/balanced_council.py "Should we migrate from REST to GraphQL?"

   Output: All 6 perspectives + clear verdict (STRONG GO / CONDITIONAL GO / STOP / INVESTIGATE / ALTERNATIVE RECOMMENDED)

   Framework: Based on Edward de Bono's Six Thinking Hats, jury research, and multi-agent AI studies
   Time: ~45-90 seconds for complete 6-perspective consultation
   Anti-sycophancy: Each hat uses random model from council pool

WHY THIS MATTERS:
  • Strategic decisions have long-term consequences
  • Single perspective = confirmation bias
  • User will get incomplete picture
  • Bad decisions from biased advice
  • Six Thinking Hats proven optimal (research-backed)

BLOCKED: This single-advisor call for a strategic decision.
USE: balanced_council.py for comprehensive Six Thinking Hats consultation.
"""
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": denial_message,
                    }
                }
            )
        )
        sys.exit(0)

    # Confidence sufficient and either:
    # - Using council (multi-perspective)
    # - OR non-strategic question to single advisor
    # Allow delegation
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "PreToolUse", "action": "allow"}}
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
