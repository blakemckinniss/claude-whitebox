---
description: 🪞 Do You Respect - Verify Claude follows a specific principle/rule
argument-hint: <principle>
allowed-tools: Read, Grep
---

The user wants to verify that you respect and will follow a specific principle, rule, or directive.

**Input:** $ARGUMENTS

**Task:**
1. Acknowledge the principle explicitly
2. State how it affects your behavior concretely
3. Give a brief example of what you WON'T do because of it
4. Confirm commitment

**Format:**
```
✓ Acknowledged: [principle name/summary]
→ Behavior change: [concrete effect]
✗ Forbidden: [specific example of what's now banned]
```

Keep response under 50 words. No hedging, no "I'll try to" - either you respect it or you don't.
