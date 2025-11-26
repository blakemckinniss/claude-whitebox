---
description: 🛠️ Implementation Brainstorm - Explores options for implementing X in Y
argument-hint: <feature> in <system>
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Task
---

**IMPLEMENTATION OPTIONS ANALYSIS**

Query: $ARGUMENTS

## Protocol

1. **Parse the Request**
   - Extract the FEATURE (what to implement)
   - Extract the SYSTEM (where to implement it)
   - If unclear, ask for clarification before proceeding

2. **Understand the System**
   - Locate relevant code (`Glob`, `Grep`, `xray`)
   - Identify existing patterns and conventions
   - Map dependencies and integration points
   - Note constraints (language, framework, architecture)

3. **Generate Options**
   Present 2-4 distinct approaches:

   ```
   ## Option A: [Name]
   **Approach:** [1-2 sentence summary]
   **Fits because:** [why this matches the system]
   **Effort:** [Low/Medium/High]
   **Risk:** [what could go wrong]
   **Changes:** [files/modules affected]

   ## Option B: [Name]
   ...
   ```

4. **Recommendation**
   ```
   ## 🎯 Recommendation
   **Go with:** Option [X]
   **Because:** [honest reasoning, not just "it's simpler"]
   **Start with:** [first concrete step]
   ```

5. **Anti-Patterns to Avoid**
   - Don't propose options you wouldn't actually choose
   - Don't pad with obviously bad options to make one look good
   - Don't ignore existing patterns in the codebase
   - Don't propose architecture astronautics for simple features

6. **Output Ends With**
   ```
   Ready to implement? Say which option (or describe a hybrid).
   ```
