# Introspector Hook - Example Outputs

## What is the Introspector?

The Introspector is a meta-cognition hook that injects "Aha!" moments and proactive tool suggestions based on semantic analysis of user prompts. It detects implicit needs and triggers self-reflective questions BEFORE Claude starts coding.

## Philosophy

- **Proactive, not Reactive**: Suggest the RIGHT tool BEFORE user asks
- **Context-Aware**: Considers confidence level, session state, tool usage
- **Self-Reflective**: Injects questions like "What is user REALLY trying to achieve?"
- **Failure Prevention**: Catches common anti-patterns (XY problems, unverified claims, iteration loops)

---

## Example Outputs by Semantic Signal

### 1. Browser Automation Signal

**User Prompt:**
```
How do I scrape product prices from Amazon's website?
```

**Injected Context:**
```
🧠 META-COGNITION INTROSPECTION:

🎭 PLAYWRIGHT SIGNAL: This requires browser automation.
   • Static scraping (requests/BeautifulSoup) WILL FAIL on JS sites
   • Use: python3 scripts/ops/playwright.py 'scrape Amazon products'
   • Scaffolds complete solution in scratch/ (zero friction)
   • Handles: login, waits, screenshots, PDFs automatically
```

**Impact:** Prevents user from attempting requests/BeautifulSoup on a JavaScript-heavy site.

---

### 2. Research Signal (Stale Knowledge)

**User Prompt:**
```
How does Playwright's auto-waiting feature work in 2025?
```

**Injected Context:**
```
🧠 META-COGNITION INTROSPECTION:

🔬 RESEARCH SIGNAL: This involves recent libraries/APIs (training cutoff: Jan 2025).
   • Your knowledge may be stale
   • Use: /research 'Playwright auto-waiting 2025' (live web search)
   • Example: /research 'Playwright auto-waiting 2025'
   • Prevents hallucinating outdated APIs
```

**Impact:** Forces research BEFORE answering with potentially outdated info.

---

### 3. API Uncertainty Signal

**User Prompt:**
```
What methods are available on pandas.DataFrame?
```

**Injected Context:**
```
🧠 META-COGNITION INTROSPECTION:

🔬 API UNCERTAINTY: Don't guess method signatures.
   • Use: /probe pandas.DataFrame
   • Shows actual runtime API (not guesses)
   • Example: /probe pandas.DataFrame
   • Prevents hallucinated methods (anti-gaslighting)
```

**Impact:** Prevents hallucinating non-existent methods.

---

### 4. Decision Complexity Signal

**User Prompt:**
```
Should we migrate from REST to GraphQL for our API?
```

**Injected Context:**
```
🧠 META-COGNITION INTROSPECTION:

⚖️ DECISION COMPLEXITY: Strategic choice detected.
   • Single advisor = confirmation bias
   • Use: python3 scripts/ops/balanced_council.py 'Should we migrate from REST to GraphQL?'
   • 6 perspectives (Six Thinking Hats) → clear verdict
   • Time: ~60s for comprehensive analysis
   • Prevents groupthink and blind spots
```

**Impact:** Triggers multi-perspective consultation instead of single-advisor bias.

---

### 5. XY Problem Signal

**User Prompt:**
```
How do I use requests to scrape a React SPA built with latest Next.js?
```

**Injected Context:**
```
🧠 META-COGNITION INTROSPECTION:

🎯 XY PROBLEM ALERT: You stated HOW, but not WHY.
   • What is the ACTUAL end goal?
   • Is there a simpler path to achieve it?
   • Meta-question: Should I ask user for clarification?
   • Often the stated problem is not the real problem

🎭 PLAYWRIGHT SIGNAL: This requires browser automation.
   • Static scraping (requests/BeautifulSoup) WILL FAIL on JS sites
   • Use: python3 scripts/ops/playwright.py 'scrape React SPA'
   • Scaffolds complete solution in scratch/
```

**Impact:** Detects that user is solving wrong problem (requests on React SPA).

---

### 6. Iteration Detection Signal

**User Prompt:**
```
Process all files in the src/ directory and update imports
```

**Injected Context:**
```
🧠 META-COGNITION INTROSPECTION:

🔁 ITERATION DETECTED: Manual loops are banned.
   • Write script to scratch/ using parallel.py
   • Prevents: token waste, slow execution, manual errors
   • Pattern: Write once, execute in parallel (max_workers=50)
   • Scratch-First Enforcement will block manual iteration
```

**Impact:** Prevents manual file-by-file iteration.

---

### 7. Verification Gap Signal

**User Prompt:**
```
I've fixed the authentication bug and it should work now
```

**Injected Context:**
```
🧠 META-COGNITION INTROSPECTION:

⚠️ VERIFICATION GAP: Claims require proof.
   • Before 'Fixed': /verify command_success '<test command>'
   • Reality Check Protocol: Exit code 0 = truth
   • Examples:
     - /verify file_exists 'config.json'
     - /verify grep_text 'app.py' --expected 'DEBUG = False'
     - /verify command_success 'pytest tests/'
   • Anti-gaslighting enforcement: LLMs hallucinate success
```

**Impact:** Forces verification BEFORE claiming "fixed".

---

### 8. Production Gate Signal

**User Prompt:**
```
I'm ready to deploy scripts/ops/new_feature.py to production
```

**Injected Context:**
```
🧠 META-COGNITION INTROSPECTION:

🛡️ QUALITY GATE: Production code requires validation.
   • /audit scripts/ops/new_feature.py (security: secrets, injection, hardcoded creds)
   • /void scripts/ops/new_feature.py (completeness: stubs, TODOs, missing CRUD)
   • Both must pass before scripts/ops/ writes
   • Gatekeeper hook will block deadly sins
```

**Impact:** Enforces quality gates before production deployment.

---

### 9. Complexity Smell Signal

**User Prompt:**
```
This is really complicated - I need a custom workaround for nested loops
```

**Injected Context:**
```
🧠 META-COGNITION INTROSPECTION:

💡 COMPLEXITY SMELL: If it feels hard, there might be a simpler way.
   • Inversion: What if we DON'T do this at all?
   • Deletion: Can we delete code instead of adding?
   • Tool fit: Is there an existing tool/library for this?
   • Meta-question: Are we over-engineering?
   • Occam's Razor: Simplest solution is usually best

🔁 ITERATION DETECTED: Manual loops are banned.
   • Write script to scratch/ using parallel.py
   • Prevents: token waste, slow execution, manual errors
```

**Impact:** Triggers "simpler approach" thinking.

---

### 10. Test Strategy Signal

**User Prompt:**
```
Write unit tests for the authentication module with 100% coverage
```

**Injected Context:**
```
🧠 META-COGNITION INTROSPECTION:

🧪 TEST STRATEGY: Pareto testing - critical paths only.
   • Don't test: getters, setters, trivial code
   • Do test: edge cases, integration, business logic
   • Anti-pattern: Mock-heavy tests (brittle, low value)
   • Use: pytest for simplicity, avoid over-mocking
   • Philosophy: 20% of tests catch 80% of bugs
```

**Impact:** Prevents writing low-value 100% coverage tests.

---

## Context-Aware Nudges (Session State)

### Low Confidence Coding Attempt

**Condition:** Confidence < 30% AND Write/Edit in recent tools

**Injected Context:**
```
🚫 IGNORANCE TIER VIOLATION: Confidence 15% (IGNORANCE TIER).
   • Allowed: Read, Research, Probe, Questions
   • Blocked: Coding, Edits, Production changes
   • Must reach 31%+ before coding
   • Gather evidence first (read files, research, probe APIs)
```

---

### Tool Loop Detection

**Condition:** Same tool used 4+ times in last 5 turns

**Injected Context:**
```
🔁 LOOP DETECTED: Read used 5x in 5 turns.
   • This is a token waste pattern
   • Write a scratch script instead
   • Use parallel.py for bulk operations
   • Scratch-First Protocol will escalate to hard block
```

---

### Missing Upkeep Before Commit

**Condition:** 'commit' in prompt AND no 'upkeep' in last 20 tools

**Injected Context:**
```
🧹 MISSING UPKEEP: git commit requires /upkeep first.
   • Updates: tool index, requirements.txt, scratch cleanup
   • Prevents: drift, stale deps, context pollution
   • Command: python3 scripts/ops/upkeep.py
   • Hard Block: Will trigger if you attempt commit
```

---

## Metacognitive Questions (15% Probability)

Random rotation of self-reflective questions:

```
🤔 What is the user REALLY trying to achieve? (Goal beyond stated task)
🎯 Is there a simpler way to accomplish this? (Occam's Razor)
🔬 Do I actually understand this problem? (Confidence check)
🧪 How will I verify this works? (Test plan)
⚖️ What are the hidden assumptions here? (Blind spots)
💡 What tool/protocol fits this task best? (Tool selection)
🚫 What could go wrong? (Risk analysis)
🗑️ Can I delete code instead of adding? (Inversion)
📚 Is my knowledge current for this? (Staleness check)
🔁 Am I repeating myself? (Iteration smell)
```

---

## System Integration

**Hook:** `.claude/hooks/introspector.py`
**Trigger:** `UserPromptSubmit`
**Priority:** Runs early (after confidence_init, before synapse_fire)
**Max Nudges:** 3 per turn (sorted by priority)
**Pattern DB:** `.claude/memory/metacognition_patterns.json`

**Pattern Priority Levels:**
- **Critical** (3): browser_automation, api_uncertainty, verification_gap, production_gate
- **High** (2): research_needed, decision_complexity, iteration_detected, xy_problem
- **Medium** (1): complexity_smell, test_strategy, parallel_opportunity

---

## Success Metrics

✅ **Proactivity:** Claude suggests right tool BEFORE user asks
✅ **Aha! Moments:** User realizes better approach via nudges
✅ **Reduced Loops:** Fewer manual iterations (caught early)
✅ **Better Decisions:** Multi-perspective consultation on strategic choices
✅ **Verification Rate:** More /verify calls before "fixed" claims
✅ **Research Adoption:** More /research calls for modern libs

---

## Comparison: Before vs After

### Before Introspector

**User:** "How do I scrape Amazon prices?"
**Claude:** "You can use requests and BeautifulSoup..." ❌
**Result:** Fails on JS-heavy site, user frustrated

### After Introspector

**User:** "How do I scrape Amazon prices?"
**Introspector:** "🎭 PLAYWRIGHT SIGNAL: Use python3 scripts/ops/playwright.py"
**Claude:** "I see this requires browser automation. Let me use Playwright..." ✅
**Result:** Success on first try

---

## Implementation Notes

- **Caching:** Session-level cache (5 min TTL) for repeated queries
- **Performance:** <100ms overhead per prompt
- **Fail-Safe:** Crashes silently (returns empty context) to avoid blocking
- **Extensibility:** Easy to add new patterns to metacognition_patterns.json
- **Testing:** 10/10 test cases passing (scratch/test_introspector.py)
