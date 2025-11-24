# Prompt-Based Hooks Implementation Plan

## Executive Summary

**Goal:** Use LLM-based "prompt" hooks for meta-enforcement of CLAUDE.md rules, replacing simple keyword-matching Python scripts with context-aware semantic evaluation.

**Impact:**
- 5 Python scripts → 9 prompt templates (7 UserPromptSubmit, 2 PreToolUse)
- Semantic understanding vs keyword matching
- +1-2 seconds latency (parallel LLM calls)
- ~500-1000 tokens per prompt hook

**Status:** Design complete, ready for implementation

---

## Architecture

### Two-Layer Defense System

**Layer 1: Command-Based (Fast, Deterministic)** - KEEP
- State tracking (confidence, evidence, command history)
- Hard blocks (tier gates, prerequisite gates)
- Pattern detection (secrets, stubs)
- File operations (git, memory, session management)

**Layer 2: Prompt-Based (Context-Aware, Semantic)** - NEW
- Meta-enforcement of CLAUDE.md rules
- Intent analysis (catch semantic violations)
- Dynamic guidance based on actual context

---

## Phase 1: Simple Advisory Conversions (5 hooks)

### Removing (Python Scripts)
1. `detect_batch.py` - Batch operation keyword matching
2. `check_knowledge.py` - Fast-moving tech detection
3. `sanity_check.py` - Library + code intent detection
4. `force_playwright.py` - UI automation detection
5. `intervention.py` - Bikeshedding/YAGNI/NIH detection

### Adding (Prompt-Based)

#### UserPromptSubmit (7 hooks)

1. **Protocol Enforcer** (Meta-Enforcement)
   - Analyzes user request against CLAUDE.md § Behavioral Protocols
   - Identifies MANDATORY protocol requirements
   - Returns systemMessage with NON-NEGOTIABLE rules
   - Timeout: 30s

2. **Intent Router** (Tool Recommendation)
   - Maps user requests to CLAUDE.md § Tool Registry
   - Recommends best tool/command for the task
   - Provides reasoning for recommendation
   - Timeout: 20s

3. **Batch Detection**
   - Detects batch operations (bulk, mass, "all files")
   - Recommends scripts.lib.parallel
   - Timeout: 15s

4. **Knowledge Freshness**
   - Identifies need for current documentation
   - Recommends /research for new libs/APIs
   - Timeout: 15s

5. **API Guessing Prevention**
   - Detects coding with complex libraries
   - Enforces /research + /probe before coding
   - Timeout: 15s

6. **Browser Automation**
   - Detects UI automation needs
   - Forces Playwright over requests/BS4
   - Timeout: 15s

7. **Bikeshedding Detection**
   - Detects trivial work (config, formatting)
   - Enforces /judge value assessment
   - Timeout: 15s

#### PreToolUse (2 hooks)

1. **Shortcut Detector** (Task delegation)
   - Matcher: `Task`
   - Checks delegation rules (>200 chars needs /think)
   - Prevents lazy delegation
   - Can DENY with permissionDecision
   - Timeout: 25s

2. **Code Intent Validator** (Write/Edit)
   - Matcher: `Write|Edit`
   - Detects documentation spam (CLAUDE.md forbids .md "JUST FOR HUMANS")
   - Detects stub code (pass, TODO, NotImplementedError)
   - Warns on production code without quality gates
   - Can DENY critical violations
   - Timeout: 30s

---

## Keeping Command-Based (27 hooks)

### Critical State (5)
- `confidence_init.py` - Session initialization
- `command_tracker.py` - Prerequisite enforcement
- `evidence_tracker.py` - Confidence calculation
- `detect_confidence_penalty.py` - State penalties
- `detect_confidence_reward.py` - State rewards

### Critical Gates (8)
- `pre_advice.py` - Strategic advice block
- `tier_gate.py` - Tier violations
- `confidence_gate.py` - Confidence violations
- `command_prerequisite_gate.py` - Prerequisite violations
- `risk_gate.py` - Risky operations
- `pre_write_audit.py` - Security/stub detection
- `ban_stubs.py` - Stub prevention
- `block_mcp.py` - Whitebox enforcement

### Complex Logic (9)
- `synapse_fire.py` - Associative memory
- `session_init.py` - Session setup
- `auto_commit_on_complete.py` - Git automation
- `auto_commit_on_end.py` - Git automation
- `auto_remember.py` - Memory extraction
- `session_digest.py` - Digest generation
- `token_tracker.py` - Token estimation
- `debt_tracker.py` - Technical debt
- `pattern_detector.py` - Multi-pattern detection

### Advisory Complex (5) - Defer to Phase 2
- `detect_low_confidence.py`
- `prerequisite_checker.py`
- `anti_sycophant.py`
- `detect_gaslight.py`
- `enforce_workflow.py`

---

## Implementation Steps

### 1. Backup
```bash
cp .claude/settings.json .claude/settings.json.backup
```

### 2. Apply Configuration

**Option A: Manual Merge**
1. Open `.claude/settings.json`
2. Remove UserPromptSubmit hooks for:
   - `detect_batch.py`
   - `check_knowledge.py`
   - `sanity_check.py`
   - `force_playwright.py`
   - `intervention.py`

3. Add prompt-based hooks from `scratch/settings_snippet.json`:
   - Merge UserPromptSubmit hooks
   - Add new PreToolUse hooks (Task, Write|Edit)

**Option B: Automated Script** (TODO)
```bash
python3 scratch/apply_prompt_hooks.py
```

### 3. Testing

**Latency Test:**
```bash
# Time UserPromptSubmit with 7 prompt hooks
time echo "write a script to process all files" | claude-code --test-hooks
```

**Token Usage Test:**
```bash
# Monitor token consumption
claude-code --debug | grep "prompt hook"
```

**Effectiveness Test:**
```bash
# Test each hook trigger
echo "migrate to new framework" → Should trigger bikeshedding
echo "use pandas" → Should trigger API guessing prevention
echo "process all files" → Should trigger batch detection
```

### 4. Iteration

Monitor hook output quality:
- Are systemMessages clear and actionable?
- Are false positives acceptable?
- Does semantic understanding beat keyword matching?

Refine prompts in `scratch/prompt_templates.json` based on results.

---

## Cost Analysis

### Latency
- **Before:** ~50-100ms (Python script execution)
- **After:** ~1-2 seconds (7 parallel LLM calls)
- **Impact:** UserPromptSubmit lifecycle slower but acceptable

### Token Cost
- **Per UserPromptSubmit:** ~3500-7000 tokens (7 hooks × 500-1000 tokens each)
- **Per session (10 prompts):** ~35,000-70,000 tokens
- **Cost (Haiku @ $0.80/MTok):** ~$0.028-$0.056 per session
- **Impact:** Negligible for individual use, monitor for production

### Maintenance
- **Before:** 5 Python scripts × avg 60 lines = 300 lines of code
- **After:** 9 prompt templates × avg 15 lines = 135 lines of JSON
- **Benefit:** 55% reduction, easier to modify prompts vs Python logic

---

## Risks & Mitigations

### Risk 1: LLM Hallucination
**Problem:** Prompt hook itself hallucinates, gives wrong guidance  
**Mitigation:** Keep critical gates as command-based (hard blocks are deterministic)

### Risk 2: Latency Creep
**Problem:** 7 LLM calls add 1-2 seconds delay  
**Mitigation:** 
- Use fast model (Haiku)
- Parallel execution
- Cache results for identical prompts (future enhancement)

### Risk 3: Token Cost Escalation
**Problem:** Tokens accumulate quickly  
**Mitigation:**
- Monitor usage with token_tracker.py
- Reduce prompt verbosity after testing
- Consider cost caps for production

### Risk 4: Non-Deterministic Behavior
**Problem:** Same prompt may get different guidance  
**Mitigation:**
- Test prompts extensively
- Use clear, structured output formats
- Fall back to "approve" by default (safe default)

---

## Success Metrics

### Effectiveness
- **Semantic Catch Rate:** % of semantic violations caught vs keyword-only
- **False Positive Rate:** % of unnecessary warnings
- **User Override Rate:** % of times user ignores systemMessage

### Performance
- **P50 Latency:** Median UserPromptSubmit latency
- **P99 Latency:** 99th percentile latency
- **Timeout Rate:** % of prompt hooks that timeout

### Cost
- **Tokens Per Session:** Average tokens consumed
- **Cost Per Session:** USD spent on prompt hooks
- **ROI:** Maintenance time saved vs token cost

---

## Future Enhancements

### Phase 2: Advisory Complex Conversions
Convert remaining advisory hooks to prompt-based:
- `anti_sycophant.py` → Prompt-based opinion detection
- `detect_gaslight.py` → Prompt-based frustration detection
- `intent_classifier.py` → Already have Intent Router
- `command_suggester.py` → Enhanced Intent Router

### Phase 3: Prompt Optimization
- Reduce prompt verbosity (fewer tokens)
- A/B test prompt variations
- Cache prompt hook results for identical inputs

### Phase 4: Hybrid Intelligence
- Combine command-based fast path + prompt-based fallback
- Command scripts pre-filter, prompts handle edge cases
- Best of both worlds: speed + semantic understanding

---

## Files Generated

1. **scratch/hook_audit.py** - Categorizes all 40 hooks
2. **scratch/hook_categorization.json** - Full categorization data
3. **scratch/prompt_templates.json** - Prompt template library
4. **scratch/convert_to_prompt_hooks.py** - Configuration generator
5. **scratch/prompt_hooks_config.json** - Full migration plan
6. **scratch/settings_snippet.json** - Ready-to-use settings fragment
7. **scratch/PROMPT_HOOKS_IMPLEMENTATION.md** - This document

---

## Decision Point

**Recommendation:** Proceed with Phase 1 implementation.

**Why:**
- Low risk (keeping all critical gates as command-based)
- High value (semantic understanding > keyword matching)
- Reversible (backup exists, easy rollback)
- Testable (can A/B test vs current implementation)

**Next Action:** User approval to apply configuration changes.
