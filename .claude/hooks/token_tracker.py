#!/usr/bin/env python3
"""
Token Tracker Hook: Updates token usage tracking at session stop
Triggers on: Stop
Purpose: Prevent false confidence from limited/stale context
"""
import sys
import json
from pathlib import Path

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import (
    load_session_state,
    save_session_state,
    estimate_tokens,
    get_token_percentage,
)

# Load input
try:
    input_data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

session_id = input_data.get("sessionId", "unknown")
transcript_path = input_data.get("transcriptPath")

if not transcript_path or not Path(transcript_path).exists():
    sys.exit(0)

# Load session state
state = load_session_state(session_id)
if not state:
    sys.exit(0)

# Estimate tokens from transcript
tokens = estimate_tokens(transcript_path)
token_pct = get_token_percentage(tokens)

# Update state
state["tokens_estimated"] = tokens
state["context_window_percent"] = round(token_pct, 1)

# Save state
save_session_state(session_id, state)

# Check for critical threshold: tokens ≥ 30% AND confidence < 50%
confidence = state.get("confidence", 0)

if token_pct >= 30 and confidence < 50:
    # Output warning about context staleness
    warning = f"""⚠️  TOKEN THRESHOLD WARNING

Context Usage: {token_pct:.1f}% ({tokens:,} tokens / 200,000)
Current Confidence: {confidence}%

CONCERN: High token usage with low confidence suggests limited or stale context.
False confidence may arise from repeated shallow interactions rather than deep evidence.

RECOMMENDED ACTION: Convene council for context synthesis and validation.

Command:
  python3 scripts/ops/balanced_council.py "Synthesize current context and validate confidence level - {token_pct:.0f}% tokens used with {confidence}% confidence"
"""
    print(warning, file=sys.stderr)

sys.exit(0)
