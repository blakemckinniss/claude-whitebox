---

## 🤖 The Enforcement System (LLM-Based Meta-Hooks)

**How You're Kept Honest:**

Your behavior is monitored by **prompt-based hooks** - LLM evaluators that analyze your actions against CLAUDE.md rules. These run automatically at key decision points.

### UserPromptSubmit Hooks (Pre-Response)

Before you respond to any user request, 7 LLM evaluators analyze the prompt:

1. **The Protocol Enforcer** (Meta-Enforcement)
   - Analyzes user request against CLAUDE.md § Behavioral Protocols
   - Identifies MANDATORY protocol requirements
   - Injects NON-NEGOTIABLE reminders into your context
   - Example: "MUST run /council for migration" → Catches you trying to decide alone

2. **The Intent Router** (Tool Guidance)
   - Maps user requests to CLAUDE.md § Tool Registry
   - Recommends best script/command for the task
   - Example: "Finding class? Use /xray --type class"

3. **Batch Operation Detector**
   - Semantic detection of bulk operations (not just keywords)
   - Forces `scripts.lib.parallel` usage
   - Example: "Process multiple files" → Must use parallel execution

4. **Knowledge Freshness Checker**
   - Detects fast-moving tech (React, AWS, LangChain)
   - Enforces /research before coding
   - Example: "Latest Next.js" → Must research, not use stale training data

5. **API Guessing Prevention**
   - Detects coding with complex libraries
   - Enforces /research + /probe pipeline
   - Example: "Use pandas" → Must probe actual API, not hallucinate signatures

6. **Browser Automation Enforcer**
   - Detects UI automation needs
   - Forces Playwright over requests/BS4
   - Example: "Login to site" → Must use browser, not text scraping

7. **Bikeshedding Detector**
   - Detects trivial work (config, formatting, premature abstraction)
   - Enforces /judge value assessment
   - Example: "Update prettier config" → Must prove ROI first

### PreToolUse Hooks (Action Validation)

Before you execute certain tools, LLM evaluators validate your intent:

1. **The Shortcut Detector** (Task Delegation)
   - Matcher: `Task`
   - Checks if delegation follows rules (>200 chars needs /think)
   - Prevents lazy delegation
   - **Can BLOCK**: Returns `permissionDecision: "deny"` if violation detected

2. **The Code Intent Validator** (Write/Edit)
   - Matcher: `Write|Edit`
   - Detects documentation spam ("JUST FOR HUMANS" violations)
   - Detects stub code (pass, TODO, NotImplementedError)
   - Warns on production code without quality gates
   - **Can BLOCK**: Critical violations are hard-blocked

### Why LLM-Based Hooks?

**Before (Keyword Matching):**
- `if "pandas" in prompt: warn()`
- Easy to bypass with different phrasing
- Misses semantic violations

**After (Semantic Understanding):**
- LLM evaluates: "Is this user asking Claude to use a complex library without research?"
- Context-aware (understands intent, not just keywords)
- Catches rationalizations ("I'll just do a quick pandas script...")

### The Two-Layer Defense

**Layer 1: Command-Based Hooks** (Fast, Deterministic)
- State tracking (confidence, evidence, command history)
- Hard blocks (tier gates, prerequisite gates)
- Pattern detection (secrets, stubs)
- File operations (git, memory)

**Layer 2: Prompt-Based Hooks** (Context-Aware, Semantic)
- Meta-enforcement of CLAUDE.md rules
- Intent analysis (catch semantic violations)
- Dynamic guidance based on actual context

### Cost & Performance

**Latency:** +1-2 seconds per UserPromptSubmit (7 parallel LLM calls using Haiku)
**Token Cost:** ~3500-7000 tokens per prompt (~$0.003-$0.006 with Haiku)
**Benefit:** Semantic understanding prevents shortcuts that keyword matching misses

### What This Means For You

You CANNOT:
- Rationalize past protocol requirements ("I'll just give quick advice without evidence")
- Take semantic shortcuts ("User wants migration help" → Must run /council, not decide alone)
- Bypass rules with clever phrasing (LLM understands intent, not just keywords)
- Write documentation "JUST FOR HUMANS" (Code Intent Validator blocks this)
- Delegate complex tasks without /think decomposition (Shortcut Detector blocks)

The hooks inject `systemMessage` warnings into your context. These are NON-NEGOTIABLE reminders that override your default behavior.

---
