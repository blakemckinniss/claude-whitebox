---
description: 🔧 Implement - Research + optimal setup of X for this project
argument-hint: <tool/feature/pattern>
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Task, WebSearch, WebFetch
---

Research best practices, then implement an optimal setup of X tailored to this project.

**Input:** $ARGUMENTS

**Protocol:**

1. **Understand X**
   - What is being requested? (tool, library, pattern, feature)
   - What's the minimal viable version?

2. **Research Phase** (BEFORE implementing)
   - Use `research` or web search to find:
     - Current best practices for X
     - Common pitfalls to avoid
     - Minimal vs full setup tradeoffs
     - Alternatives that might be simpler
   - Summarize findings briefly:
     ```
     ### 📚 Research Summary: [X]
     - **Best practice:** ...
     - **Common pitfall:** ...
     - **Recommended approach:** ...
     ```

3. **Project Context Check**
   - Read CLAUDE.md for principles
   - Scan existing patterns in codebase
   - Check for conflicts with Hard Blocks (especially Dependency Diet)
   - Reconcile research findings with project constraints

4. **Design Optimal Setup**
   - Simplest configuration that works
   - Follows existing project conventions
   - Incorporates research insights
   - No over-engineering or "nice-to-have" extras
   - Prefer stdlib/builtins when possible

5. **Execute Implementation**
   - Create necessary files
   - Install dependencies (only if stdlib failed twice)
   - Configure with sensible defaults
   - Wire into existing code if needed

6. **Verify**
   - Run basic smoke test
   - Confirm it works
   - No dangling TODOs

7. **Report**
   ```
   ## 🔧 Implemented: [X]

   **Research informed:** [key insight applied]

   **Setup:**
   - [file/config created]
   - [dependency added, if any]
   - [integration point]

   **Usage:**
   ```
   [minimal example]
   ```

   **Verification:** ✅ [what was tested]
   ```

**Quality Gates:**
- Don't add config options that won't be used
- Don't create abstraction layers for one use case
- Don't add error handling for impossible scenarios
- Delete example/boilerplate code after adapting

**Anti-Pattern:** 
- Installing the "full" setup with all features when minimal suffices
- Blindly copying tutorials without understanding project fit
- Skipping research and implementing based on stale knowledge
