---
description: 🔧 Fix Console Errors - Diagnose and fix browser console errors
argument-hint: <error_description>
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Task, WebFetch
---

Fix browser console errors based on the provided description.

**Input:** $ARGUMENTS

**Protocol:**

1. **Parse the error(s):**
   - Extract error type (TypeError, ReferenceError, network, CORS, etc.)
   - Identify file/line if provided
   - Note any stack trace hints

2. **Locate the source:**
   - Use `xray` or `grep` to find the offending code
   - If error mentions a specific file/component, read it first
   - For network errors, check API routes and fetch calls

3. **Diagnose:**
   - Common patterns:
     - `Cannot read property X of undefined` → null check needed
     - `X is not a function` → wrong import or missing method
     - `Failed to fetch` → CORS, wrong URL, or server down
     - `Uncaught SyntaxError` → malformed JSON or JS
   - Read surrounding context to understand expected behavior

4. **Fix:**
   - Apply minimal targeted fix
   - Prefer defensive coding only at boundaries
   - Don't over-engineer (no try/catch spam)

5. **Verify:**
   - If browser MCP available: `browser page screenshot` or `browser eval` to confirm
   - Otherwise: state what to check manually

**Output format:**
```
🔍 Error: [parsed error summary]
📁 Location: [file:line]
🔧 Fix: [what was changed]
✅ Verify: [how to confirm it's fixed]
```
