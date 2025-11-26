---
description: 🔧 Usefulness Amplifier - Makes X more practical, actionable, and valuable
argument-hint: <target>
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Task
---

Analyze the target and make it MORE USEFUL. This is about pragmatic improvements, not cosmetic changes.

**Target:** $ARGUMENTS

## Process

1. **Identify the target** - What is X? (file, feature, tool, concept, output)
2. **Assess current utility** - How useful is it now? What's the friction?
3. **Find the gaps** - What would make someone actually USE this more?
4. **Implement improvements** - Don't just suggest. DO.

## Usefulness Criteria (prioritize these)

| Factor | Question |
|--------|----------|
| **Actionable** | Can you act on it immediately? |
| **Accessible** | Is it easy to find/invoke/understand? |
| **Valuable** | Does it save time, reduce errors, or unlock capability? |
| **Friction-free** | Are there unnecessary steps or cognitive load? |
| **Discoverable** | Will people know it exists and what it does? |

## Actions by Target Type

**If file/code:**
- Add missing functionality that's obviously needed
- Remove dead/confusing parts
- Add helpful defaults
- Make error messages actionable

**If tool/command:**
- Add missing flags that users would want
- Improve help text
- Add examples
- Make output more parseable/useful

**If output/response:**
- Make it more concise
- Add structure (headers, bullets)
- Include next steps
- Remove fluff

**If concept/plan:**
- Make it concrete
- Add implementation steps
- Identify blockers
- Provide alternatives

## Output

After improvements, report:
```
🔧 Made X more useful:
- [What was improved]
- [Impact: what's now possible/easier]
```

Do NOT suggest. Implement. If the target is unclear, ask for clarification before proceeding.
