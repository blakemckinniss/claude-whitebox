---
description: 💎 Worth Check - Is X worth adding to this project?
argument-hint: <feature/tool/dependency>
allowed-tools: Bash, Read, Glob, Grep, Task
---

Evaluate whether X is worth adding to this project, considering effort, value, and project principles.

**Input:** $ARGUMENTS

**Analysis Framework:**

1. **Identify X**
   - What is being proposed? (feature, tool, dependency, pattern, abstraction)
   - What value does it promise?

2. **Project Context**
   - Read CLAUDE.md for principles (especially Dependency Diet, Colocation, Over-engineering warnings)
   - Check what already exists in codebase
   - Understand current pain points

3. **Worth Equation:**
   ```
   Worth = (Value × Certainty) / (Effort + Ongoing Cost + Risk)
   ```

4. **Score Each Factor (1-5):**

   | Factor | Question | Score |
   |--------|----------|-------|
   | **Value** | How much does this improve the project? | |
   | **Certainty** | How sure are we it delivers that value? | |
   | **Effort** | How hard to implement/integrate? | |
   | **Ongoing Cost** | Maintenance burden, complexity added? | |
   | **Risk** | What can go wrong? Lock-in? Breaking changes? | |

5. **Critical Questions:**
   - Does this solve an **actual** problem or a **hypothetical** one?
   - Is there a simpler way to achieve 80% of the benefit?
   - Would you add this if starting fresh today?
   - Does it violate any Hard Blocks (Dependency Diet, etc.)?

6. **Verdict Format:**
   ```
   ## 💎 Worth Assessment: [X]

   **Proposed Value:** [What X promises]
   **Actual Need:** [The real problem, if any]

   | Factor | Score | Notes |
   |--------|-------|-------|
   | Value | X/5 | ... |
   | Certainty | X/5 | ... |
   | Effort | X/5 (lower=harder) | ... |
   | Ongoing Cost | X/5 (lower=costly) | ... |
   | Risk | X/5 (lower=risky) | ... |

   **Worth Score:** (Value × Certainty) / (6 - Effort + 6 - Ongoing + 6 - Risk)

   ### Verdict: [WORTH IT / MAYBE / NOT WORTH IT / YAGNI]

   **Honest Assessment:** [Direct take, no diplomatic softening]

   **If not worth it:** [What to do instead, or why to wait]
   ```

7. **Threshold Guide:**
   - Score > 2.0: WORTH IT - Add it
   - Score 1.0-2.0: MAYBE - Only if low effort
   - Score 0.5-1.0: NOT WORTH IT - Skip unless situation changes
   - Score < 0.5 or hypothetical problem: YAGNI - You Ain't Gonna Need It

**Anti-Pattern:** Don't justify X because it's "nice to have" or "might be useful someday." Apply Dependency Diet ruthlessly.
