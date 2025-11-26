---
description: 💡 HAR - Have Any Recommendations for improving X?
argument-hint: <target>
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Task, WebSearch
---

Analyze the specified target and provide concrete improvement recommendations.

**Target:** $ARGUMENTS

**Process:**

1. **Identify the target:**
   - If file path → read and analyze that file
   - If directory → scan structure and key files
   - If concept/feature → search codebase for relevant code
   - If empty → analyze recent conversation context or ask for clarification

2. **Analyze for improvements across these dimensions:**
   - **Correctness:** Bugs, edge cases, logic errors
   - **Performance:** Inefficiencies, unnecessary work, better algorithms
   - **Readability:** Unclear naming, complex logic, missing context
   - **Maintainability:** Tight coupling, code duplication, fragile patterns
   - **Robustness:** Error handling gaps, missing validation, failure modes

3. **Output format:**

```
## Recommendations for [target]

### 🔴 Critical (fix now)
- [issue]: [concrete fix]

### 🟡 Important (worth doing)
- [issue]: [concrete fix]

### 🟢 Nice-to-have (if time permits)
- [issue]: [concrete fix]

### 💭 Observations
- [notable patterns, both good and concerning]
```

4. **Rules:**
   - Be specific: "rename `x` to `userCount`" not "improve naming"
   - Be actionable: every recommendation should be implementable
   - Be honest: if it's fine, say so. Don't manufacture issues
   - Prioritize: critical issues first, bikeshedding last
   - Skip empty sections

5. **Follow-up:** Ask if user wants any recommendations implemented.
