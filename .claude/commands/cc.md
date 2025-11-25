---
description: 🏭 Command Creator - Creates new slash commands from description
argument-hint: <name> "<description/instructions>"
allowed-tools: Bash, Write
---

Create a new slash command based on the user's request.

**Input:** `$ARGUMENTS`

**Task:**
1. Parse the first word as the command name (e.g., `roi`)
2. Parse the remaining text as the command's purpose/instructions
3. Create the file `.claude/commands/<name>.md` with this structure:

```markdown
---
description: 🎯 <short description for /help>
argument-hint: [args]
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Task
---

<The full instructions/prompt that will execute when the command is invoked>

Use $ARGUMENTS to access any arguments passed to the command.
```

**Rules:**
- Pick an appropriate emoji for the description
- The description should be concise (for /help display)
- The body should contain the full instructions/prompt
- If the user wants a script-executing command, use exclamation prefix for bash
- After creating, confirm with the created path and description

**Example:**
Input: `roi "implement the highest ROI concepts listed"`
Output file `.claude/commands/roi.md`:
```markdown
---
description: 💰 ROI Implementer - Prioritizes and implements high-value concepts
argument-hint: [context]
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Task
---

Analyze the current context and implement the highest ROI concepts.

1. If $ARGUMENTS provided, use as context
2. Otherwise, scan recent conversation for proposed ideas
3. Rank by: Impact / Effort ratio
4. Implement top items, starting with quick wins
5. Report what was implemented and estimated value delivered
```
