---
description: 🧪 Test Worth - Evaluate if something deserves test coverage
argument-hint: <code/feature>
allowed-tools: Read, Grep, Glob
---

Evaluate whether the target is worth testing or creating tests for.

**Input:** $ARGUMENTS

**Evaluation Criteria:**

| Worth Testing | NOT Worth Testing |
|---------------|-------------------|
| Critical paths (auth, payments, data integrity) | Getters/setters, trivial wrappers |
| Complex logic with edge cases | Glue code, pass-through functions |
| Bug-prone areas (history of issues) | UI layout (unless critical) |
| Public APIs others depend on | Internal helpers used once |
| State machines, parsers | Config/constants |

**Output Format:**
```
🧪 TEST VERDICT: [WORTH IT / SKIP / CONDITIONAL]

Target: [what's being evaluated]
Complexity: [Low/Medium/High]
Failure Impact: [Low/Medium/High]
Change Frequency: [Low/Medium/High]

Decision: [1-2 sentences explaining why]

If WORTH IT:
  → Suggested test type: [unit/integration/e2e]
  → Key cases to cover: [list 2-3]

If SKIP:
  → Better use of time: [alternative]
```

Apply Pareto principle: Test the 20% that catches 80% of bugs.
