---
description: 🔬 Improvement Analyzer - Identifies concrete ways to make things better
argument-hint: [target]
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Task
---

**IMPROVEMENT ANALYSIS MODE**

Target: $ARGUMENTS

## Protocol

1. **Identify the Subject**
   - If argument provided, focus on that specific file/feature/system
   - If no argument, analyze the most recent work or conversation topic
   - If ambiguous, scan `git diff` for recent changes

2. **Apply Improvement Lenses**

   **🎯 Simplicity Lens**
   - What can be deleted without losing value?
   - What abstraction is premature?
   - What complexity exists "just in case"?

   **⚡ Performance Lens**
   - What's the hot path? Is it optimal?
   - Any O(n²) hiding in loops?
   - Unnecessary I/O or network calls?

   **🛡️ Robustness Lens**
   - What assumptions will break first?
   - Where's the missing error handling that matters?
   - What edge case will bite hardest?

   **📖 Clarity Lens**
   - Would you understand this in 6 months?
   - Is the naming honest about what things do?
   - Is the structure discoverable?

   **🔧 Maintainability Lens**
   - What will be painful to change?
   - What's coupled that shouldn't be?
   - Where's the test coverage actually needed?

3. **Output Format**

   ```
   ## 🔬 Improvement Analysis: [target]

   ### Quick Wins (< 5 min each)
   - [ ] [specific action]
   - [ ] [specific action]

   ### Medium Effort (worth doing)
   - [ ] [specific action + why]

   ### Consider Later
   - [ ] [idea + tradeoff]

   ### Leave Alone
   - [thing that seems improvable but isn't worth touching + why]
   ```

4. **Rules**
   - Be specific. "Improve error handling" is useless. "Add timeout to fetch in line 47" is useful.
   - Acknowledge tradeoffs. Every improvement has a cost.
   - Don't suggest improvements you wouldn't actually make.
   - If it's already good, say so. Not everything needs fixing.
