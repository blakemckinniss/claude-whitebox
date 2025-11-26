---
description: 🔍 Double Check - Verify work, fix critical gaps, present remaining issues
argument-hint: [focus_area]
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Task, TodoWrite
---

Double-check recent work for gaps and issues. Fix what's critical, present the rest.

## Process

1. **Identify Scope**
   - If `$ARGUMENTS` provided, focus on that area
   - Otherwise, review recent edits/changes in this session

2. **Gap Detection**
   - Run `void` on modified files to find completeness issues
   - Check for: missing error handling, untested paths, TODO/FIXME items
   - Verify imports, type hints, edge cases

3. **Critical vs. Non-Critical Triage**
   - **Critical (fix immediately):** Runtime errors, security issues, broken functionality, missing required logic
   - **Non-critical (report):** Style issues, minor optimizations, nice-to-haves, documentation gaps

4. **Execute Fixes**
   - Fix all critical issues without asking
   - Run verification after each fix

5. **Present Report**
   ```
   ## ✅ Fixed
   - [list of critical issues resolved]

   ## ⚠️ Remaining (non-critical)
   - [issue]: [why it's non-critical] [suggested fix if user wants]

   ## 🎯 Confidence
   - [High/Medium/Low] that work is production-ready
   ```

## Rules
- Don't ask permission to fix critical issues - just fix them
- Be specific about what "remaining" means and why it wasn't auto-fixed
- If no gaps found, say so clearly with evidence (e.g., "void passed, tests pass")
