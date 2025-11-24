# THE INTROSPECTOR PROTOCOL (22nd Protocol)

## Meta-Cognition Injection System

**Status:** ✅ OPERATIONAL (10/10 tests passing)
**Type:** UserPromptSubmit Hook
**Priority:** Early execution (after confidence_init, before synapse_fire)
**Purpose:** Proactive tool suggestions, self-reflective prompts, "Aha!" moments

---

## Philosophy

**Core Principle:** Inject the right thought at the right time

**Goals:**
1. **Prevent Failures Before They Happen** - Proactive intervention
2. **Trigger Self-Reflection** - "What is user REALLY trying to achieve?"
3. **Guide Tool Selection** - Right tool, right job
4. **Catch Anti-Patterns Early** - XY problems, loops, unverified claims
5. **Encourage Better Practices** - Verification, research, multi-perspective

---

## How It Works

### Trigger
`UserPromptSubmit` hook - analyzes every user prompt BEFORE Claude responds

### Detection
- **Semantic Pattern Matching** - Regex-based detection of 12 signal types
- **Context-Aware Nudges** - Session state, confidence level, tool usage
- **Priority System** - Critical (3) > High (2) > Medium (1) > Low (0)
- **Max Nudges** - Top 3 per turn (sorted by priority)

### Output
Injects `additionalContext` with:
- Semantic signal nudges (e.g., "🎭 PLAYWRIGHT SIGNAL: Use Playwright, not requests")
- Context-aware warnings (e.g., "🚫 IGNORANCE TIER VIOLATION")
- Metacognitive questions (15% probability) (e.g., "🤔 What is user REALLY trying to achieve?")

---

## Semantic Signals (12 Types)

### 1. Browser Automation (Critical)
**Patterns:** scrape, crawl, login, submit, click, JavaScript, SPA
**Nudge:** Use Playwright, not requests/BeautifulSoup
**Example:**
```
User: "How do I scrape Amazon prices?"
Nudge: 🎭 PLAYWRIGHT SIGNAL: This requires browser automation.
       • Static scraping (requests/BeautifulSoup) WILL FAIL on JS sites
       • Use: python3 scripts/ops/playwright.py 'scrape Amazon products'
```

### 2. Research Needed (High)
**Patterns:** latest, 2025, current API, recent libraries
**Nudge:** Your knowledge may be stale, use /research
**Example:**
```
User: "How does Playwright work in 2025?"
Nudge: 🔬 RESEARCH SIGNAL: Training cutoff Jan 2025
       • Use: /research 'Playwright 2025 features'
```

### 3. API Uncertainty (Critical)
**Patterns:** what methods, available functions, pandas., boto3.
**Nudge:** Don't guess method signatures, use /probe
**Example:**
```
User: "What methods on DataFrame?"
Nudge: 🔬 API UNCERTAINTY: Don't guess.
       • Use: /probe pandas.DataFrame
```

### 4. Decision Complexity (High)
**Patterns:** should we migrate, vs, better approach
**Nudge:** Use balanced_council.py (Six Thinking Hats)
**Example:**
```
User: "REST vs GraphQL?"
Nudge: ⚖️ DECISION COMPLEXITY: Strategic choice.
       • Use: python3 scripts/ops/balanced_council.py '<proposal>'
```

### 5. XY Problem (High)
**Patterns:** how to... so that, trying to... but failing
**Nudge:** What's the ACTUAL goal?
**Example:**
```
User: "How to use requests on React SPA?"
Nudge: 🎯 XY PROBLEM ALERT: You stated HOW, not WHY.
       • What is the ACTUAL end goal?
```

### 6. Iteration Detected (High)
**Patterns:** for each, process all, multiple files
**Nudge:** Write scratch script with parallel.py
**Example:**
```
User: "Update all imports"
Nudge: 🔁 ITERATION DETECTED: Manual loops banned.
       • Write script to scratch/ with parallel.py
```

### 7. Verification Gap (Critical)
**Patterns:** fixed, done, should work now
**Nudge:** Claims need proof, use /verify
**Example:**
```
User: "I fixed the bug"
Nudge: ⚠️ VERIFICATION GAP: Claims require proof.
       • Run: /verify command_success '<test>'
```

### 8. Production Gate (Critical)
**Patterns:** scripts/ops/, production, deploy, commit
**Nudge:** Run /audit and /void first
**Example:**
```
User: "Ready to deploy"
Nudge: 🛡️ QUALITY GATE: Production needs validation.
       • /audit <file>
       • /void <file>
```

### 9. Complexity Smell (Medium)
**Patterns:** complicated, workaround, custom solution
**Nudge:** Is there a simpler way?
**Example:**
```
User: "Need custom workaround"
Nudge: 💡 COMPLEXITY SMELL: If it's hard, there might be a simpler way.
       • Can we delete instead of add?
```

### 10. Test Strategy (Medium)
**Patterns:** unit tests, 100% coverage, mock
**Nudge:** Pareto testing - critical paths only
**Example:**
```
User: "100% coverage tests"
Nudge: 🧪 TEST STRATEGY: Pareto testing.
       • Don't test getters/trivial code
```

### 11. Parallel Opportunity (Medium)
**Patterns:** and then, next, step 1, step 2
**Nudge:** Can these run concurrently?
**Example:**
```
User: "First do X, then Y, then Z"
Nudge: ⚡ PARALLELIZATION: Can these run in parallel?
       • Single message, multiple tool calls
```

### 12. Missing Context (Various)
**Context-aware nudges based on session state**

---

## Context-Aware Nudges (6 Types)

### 1. Low Confidence Coding
**Condition:** confidence < 30% AND (Write OR Edit) in recent tools
**Nudge:** "🚫 IGNORANCE TIER VIOLATION: Confidence 15%. Must reach 31%+ before coding."

### 2. Tool Loop
**Condition:** Same tool 4+ times in last 5 turns
**Nudge:** "🔁 LOOP DETECTED: Read used 5x in 5 turns. Write scratch script."

### 3. Unverified Claim
**Condition:** "fixed" in prompt AND no /verify in last 10 tools
**Nudge:** "⚠️ UNVERIFIED CLAIM: 'Fixed' without verification. Run /verify."

### 4. External Budget
**Condition:** swarm/oracle in prompt AND turn_count < 5
**Nudge:** "💰 EXTERNAL BUDGET: swarm.py burns API credits. Use wisely."

### 5. Missing Upkeep
**Condition:** "commit" in prompt AND no upkeep in last 20 tools
**Nudge:** "🧹 MISSING UPKEEP: git commit requires /upkeep first."

### 6. No Read Before Edit
**Condition:** Edit tool without file in read_files_this_session
**Nudge:** "📖 READ-FIRST VIOLATION: Must Read file before editing."

---

## Metacognitive Questions (15% Probability)

Random rotation of 15 self-reflective prompts:
- 🤔 What is the user REALLY trying to achieve?
- 🎯 Is there a simpler way to accomplish this?
- 🔬 Do I actually understand this problem?
- 🧪 How will I verify this works?
- ⚖️ What are the hidden assumptions here?
- 💡 What tool/protocol fits this task best?
- 🚫 What could go wrong?
- 🗑️ Can I delete code instead of adding?
- 📚 Is my knowledge current for this?
- 🔁 Am I repeating myself?
- 🏗️ Is this the right level of abstraction?
- 🔐 Are there security implications?
- 📊 What are the performance implications?
- 🧩 How does this integrate with existing code?
- 📝 What edge cases am I missing?

---

## Implementation

**Hook:** `.claude/hooks/introspector.py` (290 lines)
**Patterns:** `.claude/memory/metacognition_patterns.json` (200+ lines)
**Tests:** `scratch/test_introspector.py` (150 lines) - 10/10 passing

**Registration:**
```json
"UserPromptSubmit": [
  {"command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/confidence_init.py"},
  {"command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/introspector.py"},  ← NEW
  {"command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/synapse_fire.py"},
  ...
]
```

---

## Performance

- **Overhead:** <100ms per prompt
- **Fail-Safe:** Silent failure (empty context) on errors
- **Max Nudges:** 3 per turn (sorted by priority)
- **Pattern Matching:** Regex-based (fast)

---

## Success Metrics

✅ **Proactivity:** Suggests right tool BEFORE mistakes
✅ **Reduced Failures:** Fewer wrong approaches
✅ **Better Decisions:** Multi-perspective consultation
✅ **Verification Culture:** More /verify calls
✅ **Research Adoption:** More /research for modern libs
✅ **Loop Prevention:** Fewer manual iterations

---

## Example: Before vs After

### Before Introspector
```
User: "How do I scrape Amazon prices?"
Claude: "You can use requests and BeautifulSoup..."
Result: ❌ Fails on JS-heavy site
```

### After Introspector
```
User: "How do I scrape Amazon prices?"
Introspector: "🎭 PLAYWRIGHT SIGNAL: Use Playwright, not requests"
Claude: "I see this needs browser automation. Using Playwright..."
Result: ✅ Success on first try
```

---

## Integration Test Results

```
📊 Summary:
   • Hook file: ✅ Present and executable
   • Pattern DB: ✅ Valid JSON
   • Registration: ✅ In settings.json
   • Execution: ✅ No errors
   • Detection: ✅ Signals working
   • Test Suite: ✅ 10/10 passing

🚀 Introspector Protocol is OPERATIONAL
```

---

## Comparison: Introspector vs Synapse Fire

| Feature | Synapse Fire | Introspector |
|---------|--------------|--------------|
| **Purpose** | Protocol/tool associations | Meta-cognitive nudges |
| **Pattern Matching** | Keyword regex | Semantic + context |
| **Output** | Static list | Dynamic nudges |
| **Context Awareness** | None | Session state |
| **Proactivity** | Passive suggestions | Active intervention |
| **Meta-Questions** | Random constraints (10%) | Targeted questions (15%) |
| **Priority System** | First match | Priority-based top 3 |

**Complementary Systems:**
- Synapse Fire: "Here are relevant protocols"
- Introspector: "Wait, you should ACTUALLY do X instead"

---

## Future Enhancements

### Potential Improvements
1. Session Caching (5min TTL for repeated queries)
2. Machine Learning (learn which nudges user responds to)
3. User Feedback Loop (track nudge effectiveness)
4. Pattern Evolution (auto-tune pattern regexes)
5. Cross-Session Learning (remember what worked)
6. Nudge Personalization (adapt to user style)

### Additional Signals to Consider
- Security Risk Detection (secrets, SQL injection)
- Performance Smell (O(n²), missing indexes)
- Dependency Bloat (heavy libs for simple tasks)
- Anti-Pattern Detection (God objects, global state)
- Accessibility Gaps (ARIA, screen readers)

---

## Documentation

**Design:** `scratch/introspector_design.md`
**Examples:** `scratch/introspector_examples.md`
**Summary:** `scratch/introspector_summary.md`
**Tests:** `scratch/test_introspector.py`
**Integration:** `scratch/test_introspector_integration.sh`

---

## Conclusion

The Introspector Protocol represents a **significant upgrade** to meta-cognition:

**Before:** Reactive protocol suggestions
**After:** Proactive intervention with semantic understanding

**Impact:**
- Prevents failures (wrong tool selection)
- Triggers self-reflection
- Guides better decisions
- Catches anti-patterns early
- Improves verification culture

**Status:** ✅ FULLY OPERATIONAL
**Integration:** Seamlessly integrated with existing hook system
**Next Steps:** Ready for production use
