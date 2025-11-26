#!/usr/bin/env python3
"""
Static disclaimer injected into every user prompt.
Outputs plain text to stdout - Claude Code appends this to the prompt.
"""

DISCLAIMER = "⚠️ Least code. Need X? Act, don't ask. Read before edit. Batch calls. Verify before claiming. Use scripts/ops/*.py as your extended toolset. ⚠️"

print(DISCLAIMER.strip())
