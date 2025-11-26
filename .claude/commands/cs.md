---
description: 🤔 Can/Should - Quick feasibility and advisability check for X
argument-hint: <question>
allowed-tools: Bash, Read, Glob, Grep, Task, WebSearch, WebFetch
---

Evaluate whether we CAN and/or SHOULD do X.

**Input:** $ARGUMENTS

**Framework:**

## 1. CAN we? (Feasibility)
- **Technical:** Do we have the tools, APIs, dependencies?
- **Knowledge:** Do we know how, or can we figure it out quickly?
- **Constraints:** Time, tokens, complexity - is it tractable?

## 2. SHOULD we? (Advisability)
- **Value:** What problem does this solve? Who benefits?
- **Cost:** What's the effort, risk, maintenance burden?
- **Alternatives:** Is there a simpler way to achieve the same goal?
- **Timing:** Is now the right time, or is this premature?

## 3. Verdict

Provide ONE of:
- **YES** - Do it. [brief reason]
- **NO** - Don't. [brief reason]
- **MAYBE** - Depends on [specific clarification needed]
- **NOT YET** - Valid idea, wrong time. [what needs to happen first]

## 4. If YES, Next Action

State the concrete first step. Don't just recommend - if trivial, execute it.

---

**Rules:**
- Be direct. This is a decision accelerator, not a pros/cons essay.
- Default to NO for complexity theater, premature abstraction, or "nice to have"
- Default to YES for quick wins, obvious improvements, removing friction
- If uncertain, state what you'd need to verify and how
