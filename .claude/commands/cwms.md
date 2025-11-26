---
description: ✅ Can We Make Sure - Verify and enforce X is true
argument-hint: <condition/invariant>
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Task
---

Verify that X is currently true, and if not, make it true.

**Input:** $ARGUMENTS

**Protocol:**

1. **Parse the Condition**
   - What property/invariant/state is being asked about?
   - Is it checkable right now?
   - What would "true" look like?

2. **Check Current State**
   - Use appropriate tools to verify:
     - File existence: `ls`, `test -f`
     - Code patterns: `grep`, `xray`
     - Config state: read files
     - Runtime state: execute checks
   - Document what was checked

3. **Report Status**
   ```
   ## ✅ Checking: [X]

   **Current state:** [PASSING ✅ | FAILING ❌ | PARTIAL ⚠️]
   
   **Evidence:**
   - [what was checked]
   - [what was found]
   ```

4. **If Failing → Fix It**
   - Don't just report the problem
   - Implement the fix
   - Re-verify after fix
   ```
   **Fix applied:**
   - [what was changed]
   
   **Re-verified:** ✅
   ```

5. **If Can't Auto-Fix**
   - Explain why
   - Provide manual steps
   - Offer alternatives

6. **Optional: Add Enforcement**
   - If this should be permanently enforced, suggest:
     - Pre-commit hook
     - CI check
     - Test case
   - Ask: "Want me to add enforcement?"

**Examples:**
- `/cwms all imports are sorted` → Check + fix with isort
- `/cwms no console.log in production` → Grep + remove
- `/cwms tests pass` → Run tests + fix failures
- `/cwms no hardcoded URLs` → Search + extract to config

**Anti-Pattern:** Just reporting "no, X is not true" without attempting to make it true. The command is "make sure", not "check if".
