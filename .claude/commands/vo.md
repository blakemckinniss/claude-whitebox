---
description: 🔍 Gap Oracle - Runs gaps.py + oracle analysis on changes
argument-hint: [file_or_dir]
allowed-tools: Bash, Read, Glob, Grep
---

Run gaps.py completeness check combined with Oracle gap analysis.

**Input:** $ARGUMENTS

**Protocol:**

1. **Identify Target:**
   - If argument provided: use that file/directory
   - Otherwise: detect recent changes via `git diff --name-only HEAD~1` or `git status`

2. **Run Gap Hunter:**
   ```bash
   python3 $CLAUDE_PROJECT_DIR/.claude/ops/gaps.py <target>
   ```
   This detects:
   - Stubs (TODO, FIXME, pass, ..., NotImplementedError)
   - CRUD asymmetry (create without delete)
   - Missing error handling
   - Config hardcoding
   - Silent operations

3. **Oracle Deep Analysis** (if gaps finds issues):
   ```bash
   python3 $CLAUDE_PROJECT_DIR/.claude/ops/oracle.py --persona critic "Analyze these completeness gaps: <gaps_output>"
   ```

4. **Output Format:**
   ```
   ## 🔍 Gap Oracle Report

   ### Phase 1: Stub Hunt
   [gaps.py output - stubs found]

   ### Phase 2: Gap Analysis
   [gaps.py output - logical gaps]

   ### Phase 3: Oracle Verdict
   [oracle analysis of most critical gaps]

   ### 🎯 Action Items
   1. [Highest priority fix]
   2. [Second priority]
   ...
   ```

**Rules:**
- Run gaps.py first (fast, local)
- Only invoke oracle if gaps found (saves API credits)
- Prioritize action items by risk level
- Focus on ecosystem completeness, not style
