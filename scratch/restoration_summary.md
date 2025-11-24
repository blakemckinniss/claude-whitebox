# Settings Restoration Summary

**Date:** 2025-11-22
**Action:** Restored original command-only config (pre-prompt-type experiment)
**Reason:** Catastrophic failure during prompt-type migration

---

## What Was Restored

### Original Stable Config (Command-Only)
**Total Hook Registrations:** 15
**Unique Scripts:** 13
**Prompt Type Hooks:** 0

### Hook Breakdown:

**PreToolUse (3 matchers, 4 hook registrations):**
1. `block_mcp.py` (mcp__.*)
2. `pre_write_audit.py` (Write)
3. `ban_stubs.py` (Write)
4. `trigger_skeptic.py` (Bash|Write|Edit)

**SessionStart (1 matcher, 2 hook registrations):**
1. `cat manifesto.txt`
2. Memory loading (touch + cat active_context + lessons)

**UserPromptSubmit (1 matcher, 9 hook registrations):**
1. `synapse_fire.py`
2. `detect_gaslight.py`
3. `intervention.py`
4. `anti_sycophant.py`
5. `enforce_workflow.py`
6. `check_knowledge.py`
7. `detect_batch.py`
8. `sanity_check.py`
9. `force_playwright.py`

**SessionEnd (1 matcher, 1 hook registration):**
1. `upkeep.py`

---

## What Was Removed

### Deleted Command Hooks (18):
- `command_prerequisite_gate.py`
- `tier_gate.py`
- `risk_gate.py`
- `pre_delegation.py`
- `session_init.py`
- `confidence_init.py`
- `pre_advice.py`
- `intent_classifier.py`
- `command_suggester.py`
- `prerequisite_checker.py`
- `best_practice_enforcer.py`
- `ecosystem_mapper.py`
- `auto_commit_on_complete.py`
- `command_tracker.py`
- `evidence_tracker.py`
- `post_tool_command_suggester.py`
- `pattern_detector.py`
- `token_tracker.py`
- `auto_commit_on_end.py`

### Deleted Prompt Hooks (9):
- Shortcut Detector (Task PreToolUse)
- Code Intent Validator (Write|Edit PreToolUse)
- Protocol Enforcer (UserPromptSubmit)
- Intent Router (UserPromptSubmit)
- Batch Operation Detector (UserPromptSubmit)
- Knowledge Check (UserPromptSubmit)
- API Guessing Prohibitor (UserPromptSubmit)
- Browser Automation Enforcer (UserPromptSubmit)
- Bikeshedding Detector (UserPromptSubmit)

**Total Removed:** 27 hooks (18 command + 9 prompt)

---

## Verification

✅ All 13 hook scripts exist in `.claude/hooks/`
✅ All scripts are executable
✅ JSON syntax valid
✅ Backup created: `settings.json.backup_current_<timestamp>`
✅ Post-mortem documented: `.claude/memory/postmortem_prompt_type_migration.md`

---

## Next Steps (User Decision Required)

### Option 1: Feature Freeze (RECOMMENDED)
- Keep current 13-hook baseline
- No further hook expansion
- Focus on other improvements (SDK, protocols, tooling)

### Option 2: Cautious Re-Introduction
- Add back 2-3 critical hooks ONLY
- Candidates: `command_tracker.py`, `evidence_tracker.py`
- Requirement: Integration testing first

### Option 3: Consolidation Strategy
- Merge 18 deleted command hooks → 3 mega-hooks
- `workflow_gate.py`, `session_manager.py`, `advisor.py`
- Atomic state updates, no race conditions

---

## Critical Lessons

1. **Hook Limit Law:** N ≤ 10 per event type (UserPromptSubmit had 19 → failed)
2. **Integration Testing Mandatory:** No deployment without full-chain testing
3. **Simplicity Over Features:** 13 working hooks > 27 broken hooks
4. **State Management:** Multiple hooks writing to session state = race conditions
5. **Context Budget:** Prompt hooks inject unlimited tokens = CLAUDE.md drowning

---

**Status:** System restored to known stable baseline. Awaiting user direction.
