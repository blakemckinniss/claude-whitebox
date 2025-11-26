#!/usr/bin/env python3
"""
Static disclaimer injected into every user prompt.
Outputs plain text to stdout - Claude Code appends this to the prompt.
"""

DISCLAIMER = "⚠️ Least code. Need X? Act, don't ask. Read before edit. Batch calls. Verify before claiming. Now, not later. USE Agents: scout(find), digest(compress), parallel(batch), chore(run+summarize). USE Tools: oracle(reasoning), bdg(chrome devtools), groq(fast LLM), firecrawl(scrape), research(web), void(gaps), xray(AST), audit(security), verify(assertions), think(decompose), council(multi-perspective), spark(memory), scope(DoD), docs(library docs), inventory(system scan). ⚠️"

print(DISCLAIMER.strip())
