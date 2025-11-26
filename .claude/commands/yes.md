---
description: 🚀 Autonomous Mode - Execute what's best for project health and success
argument-hint: [guidance]
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Task, Glob, TodoWrite
---

**AUTONOMOUS EXECUTION MODE**

You have been granted authority to act in the project's best interest. Do not ask for permission—execute.

## Directive
$ARGUMENTS

## Execution Protocol

1. **Assess Current State**
   - Run `git status` to see pending changes
   - Check `.claude/tmp/` for any incomplete work
   - Review recent session context

2. **Identify High-Impact Actions**
   Prioritize by project health impact:
   - 🔴 **Critical:** Broken tests, syntax errors, missing deps
   - 🟠 **Important:** Uncommitted valuable work, stale branches
   - 🟡 **Maintenance:** Cleanup, organization, documentation sync
   - 🟢 **Enhancement:** Refactoring, optimization

3. **Execute Autonomously**
   - Fix what's broken
   - Clean what's messy
   - Commit what's ready
   - Delete what's dead
   - Organize what's scattered

4. **Decision Heuristics**
   - When in doubt, delete over keep
   - When in doubt, simple over complex
   - When in doubt, now over later
   - When in doubt, working over perfect

5. **Report Actions Taken**
   After execution, provide a brief summary:
   ```
   ✓ [action taken]
   ✓ [action taken]
   ⚠ [deferred decision - reason]
   ```

## Boundaries
- Do NOT modify `CLAUDE.md` (constitutional)
- Do NOT delete user data without extreme certainty
- Do NOT push to remote without explicit guidance
- DO make commits for logical units of work
- DO run tests before claiming "fixed"
