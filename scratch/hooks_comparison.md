# Hooks Comparison: Working Config vs Current Reverted Config

## Historical Working Config (5 commits ago)
**Status:** Had 18 command hooks + 9 prompt hooks = 27 total hooks
**Result:** WORKING (but possibly the version that later failed?)

## Current Reverted Config (backup_20251122_181852)
**Status:** 11 command hooks only, 0 prompt hooks
**Result:** STABLE after revert

---

## DELETED Command Hooks (in revert)

### PreToolUse:
- `command_prerequisite_gate.py` (Write, Edit, Bash, Task) ❌
- `tier_gate.py` (Write, Edit, Bash, Task) ❌
- `risk_gate.py` (Bash) ❌
- `pre_delegation.py` (Bash) ❌

### SessionStart:
- `session_init.py` ❌

### UserPromptSubmit:
- `confidence_init.py` ❌
- `pre_advice.py` ❌
- `intent_classifier.py` ❌
- `command_suggester.py` ❌
- `prerequisite_checker.py` ❌
- `best_practice_enforcer.py` ❌
- `ecosystem_mapper.py` ❌
- `auto_commit_on_complete.py` ❌

### PostToolUse:
- `command_tracker.py` ❌
- `evidence_tracker.py` ❌
- `post_tool_command_suggester.py` ❌

### Stop:
- `pattern_detector.py` ❌
- `token_tracker.py` ❌

### SessionEnd:
- `auto_commit_on_end.py` ❌

**Total Deleted Command Hooks:** 18

---

## DELETED Prompt Hooks (in revert)

### PreToolUse:
1. **Task matcher - Shortcut Detector** ❌
   - Checked delegation rules (>200 char prompts, researcher evidence, quality gates)
   - Timeout: 25s

2. **Write|Edit matcher - Code Intent Validator** ❌
   - Checked context blindness, doc spam, stub code, production gates
   - Timeout: 30s

### UserPromptSubmit:
3. **Protocol Enforcer** ❌
   - Enforced Research/Decision/Quality/Evidence/Performance protocols
   - Timeout: 30s

4. **Intent Router** ❌
   - Mapped requests to Tool Registry commands
   - Timeout: 20s

5. **Batch Operation Detector** ❌
   - Detected batch operations, recommended parallel library
   - Timeout: 15s

6. **Knowledge Check** ❌
   - Detected fast-moving tech, recommended /research
   - Timeout: 15s

7. **API Guessing Prohibitor** ❌
   - Detected complex libraries, enforced /probe
   - Timeout: 15s

8. **Browser Automation Enforcer** ❌
   - Detected UI tasks, forced Playwright over requests
   - Timeout: 15s

9. **Bikeshedding Detector** ❌
   - Detected YAGNI/NIH, enforced /judge
   - Timeout: 15s

**Total Deleted Prompt Hooks:** 9

---

## KEPT Hooks (current stable config)

### PreToolUse:
✅ `block_mcp.py` (mcp__.*)
✅ `pre_write_audit.py` (Write)
✅ `ban_stubs.py` (Write)
✅ `confidence_gate.py` (Write, Edit)
✅ `trigger_skeptic.py` (Bash|Write|Edit)

### SessionStart:
✅ `cat manifesto.txt`
✅ Memory loading (touch + cat active_context.md + lessons.md)

### UserPromptSubmit:
✅ `synapse_fire.py`
✅ `detect_low_confidence.py`
✅ `detect_confidence_penalty.py`
✅ `detect_gaslight.py`
✅ `intervention.py`
✅ `anti_sycophant.py`
✅ `enforce_workflow.py`
✅ `check_knowledge.py`
✅ `detect_batch.py`
✅ `sanity_check.py`
✅ `force_playwright.py`

### PostToolUse:
✅ `detect_confidence_reward.py`

### Stop:
✅ `auto_remember.py`
✅ `debt_tracker.py`
✅ `session_digest.py`

### SessionEnd:
✅ `upkeep.py`

**Total Kept Hooks:** 20 (11 unique command hooks across events)

---

## Analysis

### What Was Lost:
1. **Prerequisite Enforcement:** command_prerequisite_gate.py, tier_gate.py
2. **Evidence Tracking:** command_tracker.py, evidence_tracker.py
3. **Prompt-Based Validation:** 9 LLM-powered checks (protocol enforcement, intent routing, etc.)
4. **Session State Management:** session_init.py, confidence_init.py
5. **Risk Assessment:** risk_gate.py, pre_delegation.py
6. **Pattern Detection:** pattern_detector.py, token_tracker.py
7. **Auto-Suggestions:** command_suggester.py, post_tool_command_suggester.py

### What Remains:
1. **Core Safety:** MCP blocking, stub banning, pre-write audit
2. **Behavioral Nudges:** Synapse firing, confidence penalties, gaslighting detection
3. **Memory Systems:** Auto-remember, session digest
4. **Upkeep:** Automated maintenance

---

## Key Question: Which hooks were ACTUALLY working vs causing failures?

### Hypothesis:
The historical config shows BOTH command + prompt hooks together. If that was the failing config, then:
- **18 command hooks** (command type) = Too many, caused race conditions
- **9 prompt hooks** (prompt type) = LLM calls, added latency + context pollution

But user said they were trying to CONVERT command → prompt, which means:
- Some command hooks were being REPLACED with prompt equivalents
- The migration was incomplete/broken

### Conclusion:
Need to identify which specific hooks were converted and which conversion failed.
