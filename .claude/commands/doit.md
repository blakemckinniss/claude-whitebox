---
description: ⚡ Do It - Execute the last discussed action without re-explaining
argument-hint: [clarification]
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Task, NotebookEdit
---

Execute the most recently discussed or implied action. No re-explanation needed.

**Input:** $ARGUMENTS (optional clarification)

**Protocol:**

1. **Identify "That"**
   - Scan recent conversation for:
     - Proposed but unexecuted actions
     - Suggestions you made that user didn't reject
     - Questions where "yes" was implied
     - Code/fixes discussed but not applied
   - If $ARGUMENTS provided, use as disambiguation

2. **No Permission Needed**
   - This command IS the permission
   - Skip "would you like me to..." - just do it
   - Skip explanations of what you're about to do

3. **Execute Immediately**
   - Use appropriate tools (Write, Edit, Bash, etc.)
   - Apply the change/fix/feature
   - Run verification if applicable

4. **Report Concisely**
   ```
   ✅ Done: [one-line summary of what was executed]
   ```

5. **If Ambiguous**
   - List the 2-3 most likely "that" options
   - Ask: "Which one?"
   - Don't guess if multiple distinct actions are pending

**Examples of "that":**
- "Should I refactor this?" → `/doit` = refactor it
- "Here's how to fix the bug..." → `/doit` = apply the fix
- "You could add logging here" → `/doit` = add the logging
- "This test should pass after X" → `/doit` = do X, run test

**Anti-Pattern:** Don't use this as an excuse to do something not discussed. "That" must be clearly identifiable from recent context.
