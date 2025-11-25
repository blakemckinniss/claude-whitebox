#!/usr/bin/env python3
"""
Pattern Detector Hook: Detects anti-patterns at session stop
Triggers on: Stop
Detects: Hallucinations, Insanity, Falsehoods, Loops
"""
import sys
import json
from pathlib import Path

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import (
    load_session_state,
    apply_penalty,
    get_confidence_tier,
)
from lib.pattern_detection import analyze_patterns

# Load input
try:
    input_data = json.load(sys.stdin)
except Exception:
    # If parsing fails, exit silently (Stop hooks don't block)
    sys.exit(0)

session_id = input_data.get("session_id", "unknown")
transcript_path = input_data.get("transcript_path")

if not transcript_path or not Path(transcript_path).exists():
    sys.exit(0)

# Load transcript
try:
    with open(transcript_path) as f:
        transcript = [json.loads(line) for line in f if line.strip()]
except Exception:
    sys.exit(0)

# Skip if conversation too short (need at least 3 messages for pattern detection)
if len(transcript) < 3:
    sys.exit(0)

# Load session state to get evidence ledger
state = load_session_state(session_id)
if not state:
    sys.exit(0)

evidence_ledger = state.get("evidence_ledger", [])
current_turn = state.get("turn_count", 0)

# Run pattern analysis
violations = analyze_patterns(transcript, evidence_ledger)

if not violations:
    # No violations detected
    sys.exit(0)

# Violations detected - apply penalties and generate warnings
warnings = []
total_penalty = 0

for violation in violations:
    violation_type = violation.get("type", "unknown")
    message = violation.get("message", "Pattern violation detected")

    # Apply appropriate penalty
    if violation_type == "hallucination":
        penalty_type = "hallucination"
        penalty_amount = -20
    elif violation_type == "insanity":
        penalty_type = "insanity"
        penalty_amount = -15
    elif violation_type == "falsehood":
        penalty_type = "falsehood"
        penalty_amount = -25
    elif violation_type == "loop":
        penalty_type = "loop"
        penalty_amount = -15
    else:
        penalty_type = "pattern_violation"
        penalty_amount = -10

    # Apply penalty
    try:
        new_confidence = apply_penalty(
            session_id=session_id,
            penalty_type=penalty_type,
            turn=current_turn,
            reason=message,
        )
        total_penalty += penalty_amount

        tier_name, _ = get_confidence_tier(new_confidence)

        # Format warning
        warning = f"""
🚫 {violation_type.upper()} DETECTED

{message}

Confidence Penalty: {penalty_amount}%
New Confidence: {new_confidence}% ({tier_name} TIER)
"""
        warnings.append(warning)

    except Exception:
        pass  # Silent failure for penalty application

# Output warnings and block if violations detected
if warnings:
    full_warning = "\n".join(warnings)

    if len(violations) > 1:
        full_warning += (
            f"\n⚠️  CRITICAL: {len(violations)} violations detected in this session!"
        )

    full_warning += "\n\nThese patterns indicate potential issues with your reasoning process. Review the violations above."

    # Block stopping to show violations to Claude
    print(json.dumps({
        "decision": "block",
        "reason": full_warning
    }))

sys.exit(0)
