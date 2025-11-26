---
description: 🧭 Best Way - Evaluates optimal approaches for implementing X
argument-hint: <question>
allowed-tools: Bash, Read, Glob, Grep, Task, WebSearch, WebFetch
---

Analyze and recommend the best way to accomplish what the user is asking about.

**Input:** $ARGUMENTS

**Process:**

1. **Clarify the goal** - Parse exactly what X is from the input
2. **Scout the codebase** - Search for existing patterns, prior art, or related implementations
3. **Enumerate options** - List 2-4 viable approaches with trade-offs:
   - Effort (low/med/high)
   - Risk (low/med/high)
   - Alignment with existing patterns
4. **Research if needed** - Use web search for external best practices when the question involves libraries, frameworks, or industry patterns
5. **Recommend** - Pick the best option with clear rationale

**Output format:**

```
## Goal: [parsed X]

### Options Considered
1. **[Option A]** - [1-line description]
   - Effort: [L/M/H] | Risk: [L/M/H]
   - Pros: ...
   - Cons: ...

2. **[Option B]** - ...

### Recommendation
**[Winner]** because [concrete reasons tied to this codebase/context]

### Implementation Sketch
[3-5 concrete steps to execute]
```

**Rules:**
- Don't recommend what you can't justify
- Prefer options that align with existing codebase patterns
- If all options are bad, say so and explain why
- If you need more context to answer well, ask ONE clarifying question
