# Meta-Cognition Injection System Design

## Vision
Inject "Aha!" moments and self-questioning prompts based on semantic analysis of user requests and current context state.

## Current State
- **synapse_fire.py**: Keyword matching → static protocol/tool suggestions
- **pre_delegation.py**: Blocks delegation if confidence < 40%
- **Limitation**: No deeper semantic reasoning, no "why is user asking this?" analysis

## Proposed System: The Introspector Protocol

### Architecture

```
UserPromptSubmit Hook: introspector.py
│
├─ Load Context State (confidence, recent tools, session patterns)
├─ Semantic Analysis (what is user REALLY asking?)
├─ Pattern Detection (detect implicit needs)
├─ Meta-Question Generation (inject self-reflective prompts)
└─ Tool Recommendation (suggest best-fit tools proactively)
```

### Semantic Patterns to Detect

#### 1. **Research Signals** (stale knowledge risk)
```python
{
  "patterns": [
    r"(?:latest|current|updated|new|2024|2025) (?:version|api|docs|features)",
    r"(?:how does|how to).+(?:work|use) (?:in|with) \w+",  # APIs/libraries
    r"(?:playwright|fastapi|react|nextjs|tailwind)",  # Modern libs
    r"(?:compatible|support|available) (?:in|with)",
  ],
  "nudge": "🔬 RESEARCH SIGNAL: This question involves recent libraries/APIs. Your training data is Jan 2025. Consider:\n• /research '<library> <feature> documentation'\n• /probe <library>.<object> (runtime introspection)"
}
```

#### 2. **Browser Automation Signals**
```python
{
  "patterns": [
    r"(?:scrape|crawl|extract|download).+(?:website|page|html)",
    r"(?:login|fill|submit|click).+(?:form|button)",
    r"(?:javascript|dynamic|spa|react).+(?:content|site)",
    r"(?:screenshot|pdf|headless|browser)",
  ],
  "nudge": "🎭 PLAYWRIGHT SIGNAL: This requires browser automation.\n• Static scraping (requests/BS4) WILL FAIL on JS sites\n• Use: python3 scripts/ops/playwright.py '<task>'\n• Scaffolds complete solution in scratch/"
}
```

#### 3. **Goal Clarification Signals** (XY Problem)
```python
{
  "patterns": [
    r"(?:can|how).+(?:make|do|create).+(?:so that|because|in order to)",
    r"(?:trying to|want to|need to).+but.+(?:not working|failing|error)",
    r"(?:convert|transform|change).+(?:to|into)",
  ],
  "nudge": "🎯 XY PROBLEM ALERT: You stated HOW, but not WHY.\n• What is the actual end goal?\n• Is there a simpler path to that goal?\n• Should I ask: 'What are you ultimately trying to achieve?'"
}
```

#### 4. **Decision Complexity Signals** (needs council)
```python
{
  "patterns": [
    r"(?:should|shall) (?:we|i) (?:use|choose|migrate|switch|add)",
    r"(?:better|best|recommend|suggest).+(?:approach|library|tool|way)",
    r"(?:vs|versus|or|between).+(?:and|,)",  # Comparisons
    r"(?:worth|trade.?off|pros.?cons)",
  ],
  "nudge": "⚖️ DECISION COMPLEXITY: This is a strategic choice requiring multi-perspective analysis.\n• Single advisor = confirmation bias\n• Use: python3 scripts/ops/balanced_council.py '<proposal>'\n• 6 perspectives (Six Thinking Hats) → clear verdict in 60s"
}
```

#### 5. **Unknown API/Library Signals** (needs probe)
```python
{
  "patterns": [
    r"(?:methods|functions|attributes|api).+(?:available|exist|support)",
    r"(?:how to call|how to use).+(?:method|function|class)",
    r"(?:pandas|boto3|fastapi|sqlalchemy|requests)\.\w+",  # Common libs
  ],
  "nudge": "🔬 API UNCERTAINTY: Don't guess method signatures.\n• /probe <library>.<object> (shows actual runtime API)\n• Example: /probe pandas.DataFrame\n• Prevents hallucinated methods"
}
```

#### 6. **Iteration/Bulk Operation Signals** (needs scratch script)
```python
{
  "patterns": [
    r"(?:for each|for all|process all|iterate|loop)",
    r"(?:multiple|several|many|all).+(?:files|items|records)",
    r"\d+ (?:files|items|times|steps)",
  ],
  "nudge": "🔁 ITERATION DETECTED: Manual loops are banned.\n• Write script to scratch/ with parallel.py\n• Batch operations prevent token waste\n• Current scratch scripts: <list relevant from scratch/>"
}
```

#### 7. **Verification Gap Signals** (needs /verify)
```python
{
  "patterns": [
    r"(?:fixed|done|completed|working|solved)",
    r"(?:should|will|now) (?:work|pass|succeed)",
    r"(?:i've|i have) (?:updated|changed|modified)",
  ],
  "nudge": "⚠️ VERIFICATION GAP: Claims require proof.\n• Before saying 'Fixed', run: /verify command_success '<test>'\n• Reality Check Protocol: Exit code 0 = truth\n• Anti-gaslighting enforcement"
}
```

#### 8. **Quality Gate Signals** (needs audit/void)
```python
{
  "patterns": [
    r"(?:production|deploy|release|commit|push)",
    r"scripts/ops/\w+\.py",  # Production zone
    r"(?:ready|finished).+(?:feature|implementation)",
  ],
  "nudge": "🛡️ QUALITY GATE: Production code requires gates.\n• /audit <file> (security, secrets, injection)\n• /void <file> (completeness, stubs, gaps)\n• Both must pass before scripts/ops/ writes"
}
```

#### 9. **Alternative Approach Signals** (needs deeper thinking)
```python
{
  "patterns": [
    r"(?:complicated|complex|difficult|hard|tricky)",
    r"(?:workaround|hack|manual|custom).+(?:solution|fix)",
    r"(?:lot of|many).+(?:steps|changes|files)",
  ],
  "nudge": "💡 COMPLEXITY SMELL: If it feels hard, there might be a simpler way.\n• Inversion: What if we DON'T do this?\n• Deletion: Can we delete code instead of adding?\n• Tool fit: Is there an existing tool/lib for this?"
}
```

#### 10. **Test Signal** (needs testing strategy)
```python
{
  "patterns": [
    r"(?:test|testing|verify|validate|check).+(?:works|correct)",
    r"(?:unit|integration|e2e|spec)",
    r"(?:coverage|assertions|mock)",
  ],
  "nudge": "🧪 TEST STRATEGY: Pareto testing - critical paths only.\n• Don't test getters/trivial code\n• Focus on: edge cases, integration points, business logic\n• Use: pytest for simplicity, avoid mock-heavy tests"
}
```

### Context-Aware Nudges (based on session state)

```python
# Low confidence + coding attempt
if confidence < 30 and "Write" in recent_tools:
    nudge = "🚫 IGNORANCE TIER VIOLATION: You're at {}% confidence (IGNORANCE TIER).\n• You can only Read/Research/Probe\n• Coding is BLOCKED until 31%+\n• Gather evidence first"

# High tool repetition (loop smell)
if tool_count("Read") > 4 in last_5_turns:
    nudge = "🔁 LOOP DETECTED: You've used Read {} times in 5 turns.\n• This is a token waste pattern\n• Write a scratch script instead\n• Use parallel.py for bulk operations"

# No verification after claim
if "fixed" in last_message and "verify" not in last_10_tools:
    nudge = "⚠️ UNVERIFIED CLAIM: You said 'fixed' without verification.\n• Run: /verify command_success '<test>'\n• Claims without proof = gaslighting risk"

# Using external tools without checking budget
if "swarm" in command and turn < 5:
    nudge = "💰 EXTERNAL BUDGET: swarm.py burns API credits.\n• Use for complex tasks only\n• Verify necessity before running\n• Alternative: Can parallel.py + stdlib solve this?"
```

### Meta-Questions to Inject

```python
METACOGNITIVE_QUESTIONS = [
    "🤔 What is the user REALLY trying to achieve? (Goal beyond stated task)",
    "🎯 Is there a simpler way to accomplish this? (Occam's Razor)",
    "🔬 Do I actually understand this problem? (Confidence check)",
    "🧪 How will I verify this works? (Test plan)",
    "⚖️ What are the hidden assumptions here? (Blind spots)",
    "💡 What tool/protocol fits this task best? (Tool selection)",
    "🚫 What could go wrong? (Risk analysis)",
    "🗑️ Can I delete code instead of adding? (Inversion)",
    "📚 Is my knowledge current for this? (Staleness check)",
    "🔁 Am I repeating myself? (Iteration smell)",
]
```

### Implementation Strategy

**Hook: `.claude/hooks/introspector.py`**
- Runs on `UserPromptSubmit`
- Analyzes prompt semantically
- Checks session state (confidence, tools, patterns)
- Generates contextual nudges
- Injects as `additionalContext`

**Pattern DB: `.claude/memory/metacognition_patterns.json`**
- Regex patterns for each signal type
- Nudge templates
- Context rules (when to fire)

**Session Tracking: `.claude/memory/session_<id>_state.json`**
- Track tool usage patterns
- Recent messages
- Confidence trajectory

### Example Output

**User:** "How do I scrape product prices from Amazon?"

**Injected Context:**
```
🧠 META-COGNITION INTROSPECTION:

🎭 PLAYWRIGHT SIGNAL: This requires browser automation.
   • Static scraping (requests/BS4) WILL FAIL on Amazon (heavy JS)
   • Use: python3 scripts/ops/playwright.py 'scrape Amazon products'
   • Scaffolds complete solution in scratch/

🔬 RESEARCH SIGNAL: Amazon's page structure changes frequently.
   • /research 'Amazon product scraping 2025 best practices'
   • Check robots.txt compliance

🤔 META-QUESTION: What is the user REALLY trying to achieve?
   • Price monitoring? Competitive analysis? One-time data pull?
   • Answer determines architecture (cron vs one-shot)

⚖️ DECISION CHECK: Is scraping Amazon the right approach?
   • Alternatives: Amazon Product Advertising API (official)
   • Legal: Scraping may violate Amazon ToS
   • Consider: /council "Should we scrape Amazon vs use API?"
```

## Comparison: Current vs Proposed

| Feature | Current (synapse_fire.py) | Proposed (introspector.py) |
|---------|--------------------------|----------------------------|
| Pattern Matching | Keyword regex | Semantic + context-aware |
| Output | Static protocol list | Dynamic nudges + questions |
| Context Awareness | None | Session state, confidence, tools |
| Meta-Questions | None | "What is user really trying to do?" |
| Tool Suggestions | Passive list | Proactive "Use this NOW" |
| XY Problem Detection | None | Detects goal ambiguity |
| Alternative Thinking | Random constraints (10%) | Triggered by complexity smells |

## Implementation Plan

1. **Create pattern database** (metacognition_patterns.json)
2. **Write introspector.py hook** (semantic analysis engine)
3. **Add session tracking** (tool usage patterns)
4. **Test with diverse prompts** (verify nudge quality)
5. **Integrate with confidence system** (tier-aware nudges)
6. **Add meta-question rotation** (prevent staleness)

## Success Metrics

- **Proactivity:** Claude suggests right tool BEFORE user asks
- **Aha! Moments:** User realizes better approach via nudges
- **Reduced Loops:** Fewer manual iterations (caught early)
- **Better Decisions:** Multi-perspective consultation on strategic choices
- **Verification Rate:** More /verify calls before "fixed" claims
- **Research Adoption:** More /research calls for modern libs
