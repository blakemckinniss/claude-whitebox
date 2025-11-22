#!/usr/bin/env python3
"""
Session Initialization Hook: Initializes confidence/risk state at session start
Triggers on: SessionStart
"""
import sys
import json
from pathlib import Path

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import initialize_session_state

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    # SessionStart hooks may not have standard input
    input_data = {}

session_id = input_data.get("sessionId", "unknown")

# Initialize session state
state = initialize_session_state(session_id)

# Output initialization message
message = f"""SYSTEM OVERRIDE: EPISTEMOLOGICAL PROTOCOL ACTIVE

🎯 Dual-Metric System Initialized:
   • Confidence: 0% (IGNORANCE TIER)
   • Risk: 0%
   • Session ID: {session_id[:8]}...

📊 Confidence Tiers:
   • IGNORANCE (0-30%): Read/Research/Probe only, no coding
   • HYPOTHESIS (31-70%): Can write to scratch/, no production code
   • CERTAINTY (71-100%): Full capabilities

⚖️ Evidence Gathering Required:
   • User Question: +25%
   • Web Search: +20%
   • Use Scripts: +20%
   • Probe API: +15%
   • Read File: +10% (first time), +2% (repeat)
   • Verify: +15%

🚫 Pattern Detection Active:
   • Hallucination: -20%
   • Falsehood: -25%
   • Insanity (repeated failures): -15%
   • Tier Violation: -10%

State File: .claude/memory/session_{session_id}_state.json
"""

# For SessionStart, we just print to stdout
print(message)
sys.exit(0)
