#!/usr/bin/env python3
"""
Static disclaimer injected into every user prompt.
Outputs plain text to stdout - Claude Code appends this to the prompt.
"""

DISCLAIMER = "⚠️ IMPORTANT: IF UNSURE ASK USER for clarification. Provide next steps. Read before edit. Prefer batch or parallel calls when it would speed things up. Verify before claiming. Available agents: scout(find), digest(compress), parallel(batch), chore(run+summarize)." \

print(DISCLAIMER.strip())
