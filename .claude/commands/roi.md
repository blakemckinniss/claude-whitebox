---
description: 💰 ROI Maximizer - Implements highest-value concepts by impact/effort ratio
argument-hint: [context]
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Task
---

Analyze context and implement the highest ROI concepts.

**Input:** $ARGUMENTS

**Protocol:**

1. **Context Gathering** (if no arguments):
   - Scan recent conversation for proposed ideas/improvements
   - Check .claude/tmp/ for pending proposals
   - Review any TODO comments or enhancement requests

2. **ROI Ranking:**
   For each concept, calculate: `ROI = Impact / Effort`
   - **Impact:** User value, bug prevention, time savings, risk reduction
   - **Effort:** Lines of code, complexity, dependencies, testing needed

3. **Triage into Buckets:**
   - 🚀 **Quick Wins** (High Impact, Low Effort) → Implement FIRST
   - 📈 **Strategic** (High Impact, High Effort) → Plan, maybe defer
   - 🗑️ **Noise** (Low Impact, Any Effort) → Skip entirely

4. **Execution:**
   - Implement Quick Wins immediately
   - For Strategic items: create TODO or scope.py punch list
   - Report what was skipped and why

5. **Output Format:**
   ```
   ## 💰 ROI Implementation Report

   ### ✅ Implemented (Quick Wins)
   - [Item]: [1-line description] (Est. value: X)

   ### 📋 Deferred (Strategic)
   - [Item]: [Why deferred, effort estimate]

   ### 🗑️ Rejected (Noise)
   - [Item]: [Why low ROI]

   **Total Value Delivered:** [Summary]
   ```

**Rules:**
- Prefer editing existing code over creating new files
- No gold-plating or scope creep
- YAGNI: Only implement what's explicitly requested
- Quick wins first, always
