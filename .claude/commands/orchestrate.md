---
description: 🎯 Orchestrate - Claude API code_execution for batch/aggregate tasks
---

Run Claude-powered programmatic tool orchestration.

**When to use:**
- Processing many files, returning only summary
- Multi-step workflows (3+ dependent operations)
- Data aggregation/filtering before returning results

**Example tasks:**
- "Analyze all Python files for security issues, return only critical"
- "Read all *.md, extract TODOs, group by priority"
- "Search for API endpoints, count by HTTP method"

```bash
.claude/hooks/py .claude/ops/orchestrate.py "$ARGUMENTS"
```
