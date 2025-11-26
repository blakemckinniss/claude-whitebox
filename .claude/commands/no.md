---
description: 🚫 No - Reject proposal and get alternatives
argument-hint: [reason]
allowed-tools: Bash, Read, Glob, Grep, Task
---

Reject the most recent proposal/suggestion and provide better alternatives.

**Input:** $ARGUMENTS (optional reason for rejection)

**Protocol:**

1. **Acknowledge Rejection**
   - Identify what was just proposed
   - Accept the "no" without pushback
   - If $ARGUMENTS provided, note the specific concern

2. **Understand Why**
   - Too complex?
   - Wrong approach?
   - Doesn't fit project principles?
   - Over-engineered?
   - Too much effort?

3. **Generate Alternatives (2-4)**
   ```
   ## 🚫 Rejected: [original proposal]
   
   **Reason:** [stated or inferred]
   
   ### Alternatives:
   
   1. **[Simpler Option]**
      - What: ...
      - Tradeoff: ...
   
   2. **[Different Approach]**
      - What: ...
      - Tradeoff: ...
   
   3. **[Do Nothing]** (if valid)
      - What: Keep current behavior
      - Tradeoff: ...
   
   Which direction?
   ```

4. **Alternative Quality Rules:**
   - Each must be meaningfully different (not variants of same idea)
   - At least one should be simpler than original
   - Include "do nothing" if the problem isn't urgent
   - Rank by effort (lowest first)

5. **Don't Defend Original**
   - No "but the original approach would..."
   - No re-pitching rejected idea
   - Accept the no, move forward

**Anti-Pattern:** Offering the same proposal with minor tweaks. "No" means find a different path.
