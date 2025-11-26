---
description: ⚖️ Optimality Check - Evaluates if X is the best choice for this project
argument-hint: <proposal>
allowed-tools: Bash, Read, Glob, Grep, Task
---

Evaluate whether the proposed approach/tool/pattern is optimal for THIS specific project.

**Input:** $ARGUMENTS

**Analysis Framework:**

1. **Understand the Proposal**
   - What is X? (tool, pattern, architecture, dependency, approach)
   - What problem does X solve?

2. **Project Context Scan**
   - Read CLAUDE.md for project principles
   - Check existing patterns in codebase
   - Identify current tech stack and constraints

3. **Optimality Criteria** (score 1-5 each):
   | Criterion | Question |
   |-----------|----------|
   | **Fit** | Does X align with project principles? |
   | **Simplicity** | Is X the simplest solution that works? |
   | **Maintenance** | Will X create future burden? |
   | **Alternatives** | Are simpler options available? |
   | **Dependency Cost** | Does X violate Dependency Diet? |

4. **Verdict Format:**
   ```
   ## ⚖️ Optimality Assessment: [X]

   **Context:** [What problem X addresses]

   | Criterion | Score | Notes |
   |-----------|-------|-------|
   | Fit | X/5 | ... |
   | Simplicity | X/5 | ... |
   | Maintenance | X/5 | ... |
   | Alternatives | X/5 | ... |
   | Dependency Cost | X/5 | ... |

   **Total:** XX/25

   ### Verdict: [OPTIMAL / ACCEPTABLE / SUBOPTIMAL / AVOID]

   **Reasoning:** [1-2 sentences]

   **If not optimal, consider:** [Alternative approach]
   ```

5. **Threshold Guide:**
   - 20-25: OPTIMAL - Use it
   - 15-19: ACCEPTABLE - Fine, but note tradeoffs
   - 10-14: SUBOPTIMAL - Investigate alternatives first
   - <10: AVOID - Find another way

**Anti-Pattern:** Don't defend X just because user proposed it. Apply the same rigor as "What I'd actually respect" from the Self-Assessment Protocol.
