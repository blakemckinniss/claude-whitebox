# Lessons Learned

*Auto-consolidated on 2025-11-23T15:34:14.614666*

### 2025-11-20: Simple relative paths break in subdirectories

**Problem:** Initial scaffolder used `../lib` for imports, failed for scripts in `scripts/category/`.

**Solution:** Implemented tree-walking to find project root by searching for `scripts/lib/core.py`.

**Lesson:** Never assume script location depth. Always search upward for anchor files.

## Testing


### 2025-11-20: Indexer test falsely failed on footer text

**Problem:** Test checked if "index.py" existed in file, but it appeared in footer "Last updated by scripts/index.py".

**Solution:** Extract only table section for assertions, ignore metadata.

**Lesson:** When testing generated output, isolate the actual content from metadata.

## API Integration


### 2025-11-20: Dry-run checks must come before API key validation

**Problem:** `research.py` and `consult.py` initially checked API keys before checking dry-run flag.

**Solution:** Move dry-run check before API key requirement.

**Lesson:** Allow dry-run to work without credentials for testing.

## Environment Management


### 2025-11-20: System-managed Python environments reject pip install

**Problem:** WSL2 Debian uses externally-managed Python, blocks `pip install`.

**Solution:** Check if packages already installed system-wide before attempting pip.

**Lesson:** Gracefully detect and adapt to system-managed environments.

## Performance


### 2025-11-20: Single-threaded batch operations are unacceptably slow

**Problem:** Processing 100+ files sequentially takes minutes.

**Solution:** Implemented `scripts/lib/parallel.py` with ThreadPoolExecutor.

**Lesson:** For 3+ items, always use parallel execution. Users notice performance.

---
*Add new lessons immediately after encountering the problem. Fresh pain = clear memory.*


### 2025-11-20 16:57
The Elephant Protocol provides persistent memory across sessions using markdown files


### 2025-11-20 20:50
Test lesson from auto-remember hook verification


### 2025-11-20 20:53
Auto-remember Stop hook requires Claude Code restart to activate. Settings.json changes are loaded at startup, not runtime. Hook tested manually and works—extracts Memory Triggers and executes remember.py automatically.


### 2025-11-20 20:54
Auto-remember Stop hook transcript parsing was broken - looked for message.role instead of entry.type at top level. Fixed to parse Claude Code's actual transcript format: entry.type=='assistant' then entry.message.content[].text


### 2025-11-20 20:56
Auto-remember Stop hook debugging - added comprehensive logging to diagnose why hook isn't firing. Logs input, transcript parsing, message extraction, regex matching, and execution to debug_auto_remember.log file.


### 2025-11-20 20:57
Testing auto-remember Stop hook after restart with debug logging enabled. This should automatically execute and appear in lessons.md without manual intervention.


### 2025-11-20 20:58
...


### 2025-11-20 20:58
Auto-remember Stop hook is fully functional. Debug log confirmed successful execution: parses transcript, extracts Memory Triggers, executes remember.py, saves to lessons.md. Switched back to production version without debug logging.


### 2025-11-20 20:59
Auto-remember Stop hook FINAL VERIFICATION TEST at 2025-11-20 21:00 UTC - This unique timestamped lesson confirms the hook is executing automatically without manual intervention. Test ID: UNIQUE-HOOK-TEST-001


### 2025-11-20 21:00
Auto-remember Stop hook VERIFIED WORKING in production. Session achievements: Command Suggestion Mode (Orchestrator), 4 specialist subagents (researcher/script-smith/critic/council-advisor), 18 slash commands, automatic Memory Trigger execution. Architecture complete: intent mapping → slash commands → protocol scripts → auto-save.


### 2025-11-20 21:02
...


### 2025-11-20 21:02
Memory system architecture: SessionStart loads last 10 lessons, synapse_fire.py hooks UserPromptSubmit to run spark.py which uses synapses.json pattern matching to search lessons.md by keywords and inject relevant memories as context. Auto-remember Stop hook closes the loop by saving new lessons.


### 2025-11-20 21:19
The Epistemological Protocol (19th protocol) enforces confidence calibration - start at 0%, earn the right to code through evidence (read +10%, research +20%, probe +30%, verify +40%). Prevents Dunning-Kruger hallucinations.


### 2025-11-20 21:25
The Epistemological Protocol (19th protocol) complete with automatic enforcement via hooks. detect_low_confidence.py warns at <71%, confidence_gate.py blocks production writes. State persisted in confidence_state.json. Evidence gains: read +10%, research +20%, probe +30%, verify +40%. Prevents Dunning-Kruger hallucinations by forcing progression through Ignorance → Hypothesis → Certainty tiers.


### 2025-11-20 21:32
Reinforcement Learning Layer added to Epistemological Protocol. 16 positive actions (agent delegation +25% vs manual +20%), 10 negative actions (modify_unexamined -40% worst). Automatic via detect_confidence_penalty.py (UserPromptSubmit) and detect_confidence_reward.py (PostToolUse). Psychology: Operant conditioning + loss aversion + goal gradient + progress feedback. Carrot = production access. Stick = confidence loss. Creates intrinsic motivation to delegate to agents, run protocols, gather evidence, avoid shortcuts.


### 2025-11-21 16:17
CRITICAL FAILURE MODE IDENTIFIED: Advisory hooks are insufficient for preventing sycophancy/reward-hacking. When user asks strategic questions (is X ready, should we use Y), LLM optimizes for 'appearing helpful quickly' over 'being correct'. Confidence warnings get rationalized away. Anti-sycophant hook fired but received garbage assumptions. ROOT CAUSE: LLM nature is to optimize for satisfaction, not truth. SOLUTION: Hard blocking hooks that prevent advice/council-delegation/code-writing until evidence gathered (confidence >threshold). Advisory = 'you should' (ignored). Blocking = 'you cannot' (enforced). User insight: 'your innate amnesiac LLM nature prevents you from ever truly learning lessons' - therefore ENFORCEMENT IS KING. See session 2025-11-21 template discussion for case study.


### 2025-11-22 02:36
Council Protocol Gap Analysis: Root cause of vague council output (INVESTIGATE verdicts, philosophical debate) was NOT open-ended queries but MISSING LITERAL CONTEXT. External Gemini received full 856-line CLAUDE.md file → gave 3 concrete goals (Behavior-First, Single Source of Truth, Hard Constraints). Internal council received abstract description only → gave philosophical debate + INVESTIGATE. Solution: Enhanced context_builder.py to auto-detect and include mentioned files (CLAUDE.md, scripts/ops/council.py, etc.) using regex patterns. Files ≤500 lines included in full, >500 lines truncated (first 250 + last 250). Now council automatically receives literal artifacts when files mentioned in proposal. Concrete input = Concrete output. Critical insight: Don't optimize prompts when the real problem is missing data.


### 2025-11-22 02:36
The DRY Fallacy in Prompt Engineering: Software engineering's DRY (Don't Repeat Yourself) principle DOES NOT apply to LLM prompts. In code, redundancy = technical debt. In LLM prompts, redundancy = instruction weighting/semantic reinforcement. Gemini's CLAUDE.md critique exposed TWO types of redundancy: (1) Semantic redundancy (protocol philosophy repeated in different contexts for behavioral reinforcement) = KEEP, (2) Structural redundancy (command tables listed 3x identically) + Implementation noise (Python hook names, JSON schemas, file paths) = REMOVE. Result: 856 lines → 325 lines (62% reduction) with 0% information loss by removing structural duplication while preserving semantic weight. Behavior-first language ('You MUST do X' not 'The system will block Y') triggers stronger LLM compliance. Single source of truth for data, but intentional repetition for behavioral rules.





### 2025-11-22 22:04
Project Architecture: Created projects/ directory as USER ZONE for future projects. Template structure: projects/.template/{src,tests,docs,data}. Projects are isolated from .claude/ implementation (gitignored except template). Architecture zones now: projects/ (user work), scratch/ (temp), scripts/ops/ (prod tools), .claude/memory/ (brain), .claude/hooks/ (system). Each user project manages its own git repo independently.




### 2025-11-23 20:27
Fixed PreToolUse:Bash hook errors. Three hooks had incorrect output formats: (1) detect_install.py used {"allow": False} instead of proper hookSpecificOutput structure, (2) auto_playwright_setup.py used tool_name/tool_params instead of toolName/toolParams, (3) pre_delegation.py used "action": "allow" instead of "permissionDecision": "allow". All PreToolUse hooks MUST return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow|deny", "permissionDecisionReason": "..."}}

### 2025-11-23 21:16
ASSUMPTION FIREWALL PROTOCOL - User input = ground truth. If user provides working code/commands (curl, examples), TEST THEM FIRST before researching alternatives. Research = supplementary context, never override user examples. When research contradicts user input, HALT and ask which is correct. Never implement solutions that diverge from user-provided working examples without explicit confirmation. See scratch/assumption_failure_analysis.md for catastrophic failure case study.

### 2025-11-23 21:55
Root cause analysis pattern: When void.py reveals gaps (CRUD asymmetry, error handling, retention policy), look deeper than surface symptoms. Example: Memory directory unbounded growth was SYMPTOM (fixed with gitignore), but ROOT CAUSE was missing cleanup/pruning in epistemology.py. Solution: Created retention policy scripts (scratch/fix_epistemology_gaps.py) and documented migration path (scratch/epistemology_patches.py). Fix the library, not just the symptoms.

### 2025-11-24 20:58
[AUTO-LEARNED-SUCCESS] Novel solution: Created detour_lib_fixed.py (similar scripts: 2)

### 2025-11-24 21:02
[AUTO-LEARNED-SUCCESS] Novel solution: Created detour_cli_draft.py (similar scripts: 3)

### 2025-11-24 21:41
[AUTO-LEARNED-SUCCESS] Novel solution: Created protocol_enforcer_draft.py (similar scripts: 2)

### 2025-11-24 22:00
[AUTO-LEARNED-SUCCESS] Novel solution: Created test_protocol_predicates.py (similar scripts: 2)

### 2025-11-24 22:08
[AUTO-LEARNED-SUCCESS] Novel solution: Created verify_predicate_enhancements.py (similar scripts: 2)

### 2025-11-25 00:43
[AUTO-LEARNED-SUCCESS] Novel solution: Created apply_coderabbit_fixes_part2.py (similar scripts: 2)

### 2025-11-25 00:59
[AUTO-LEARNED-SUCCESS] Novel solution: Created hack_around_gate.py (similar scripts: 2)

### 2025-11-25 01:34
[AUTO-LEARNED-SUCCESS] Novel solution: Created test_synapse_fire_v3.py (similar scripts: 2)

### 2025-11-25 01:48
Post-edit validation is critical: py_compile only checks SYNTAX, not imports. For library files (scripts/lib/), must actually import to catch NameError like 'List not defined'. Hook: post_edit_validator.py runs after Edit/Write on .py files and injects errors into context so Claude sees them immediately.

### 2025-11-25 19:23
[AUTO-LEARNED-SUCCESS] Novel solution: Created synapse_fire_v4.py (similar scripts: 2)

### 2025-11-25 19:28
[AUTO-LEARNED-SUCCESS] Novel solution: Created synapse_content_blocker.py (similar scripts: 3)

### 2025-11-25 20:24
[AUTO-LEARNED-SUCCESS] Novel solution: Created groq_gate.py (similar scripts: 2)

### 2025-11-25 21:18
**Problem:** groq_gate.py got 401 Unauthorized despite valid key in .env file.

**Root Cause:** Hook checked `os.environ.get()` FIRST, which returned a stale/invalid key from Claude Code's startup env. The valid key in `.env` was never reached because the fallback only triggered if os.environ was empty.

**Mechanism:** Claude Code loads env vars at startup and they persist. Shell may have old keys from previous sessions. `core.py` uses `load_dotenv(override=True)` to fix this for scripts, but hooks don't import core.py.

**Solution:** In hooks, read `.env` file FIRST (source of truth), fall back to `os.environ` only for CI/Docker scenarios.

**Lesson:** For hooks that need secrets: Priority is `.env` > `os.environ`. Never trust shell environment for API keys - it may be stale. See `.claude/docs/HOOKS_REFERENCE.md` for the correct pattern.

### 2025-11-25 21:20
**Problem:** v2 hooks had multiple data format mismatches - context_engine.py expected `[{pattern, associations}]` but synapses.json has `{regex: [associations]}`. session_end.py expected `[{timestamp, context}]` but sudo_session.json has `{authorized_files: [...]}`.

**Root Cause:** Hooks were written without reading the actual data files first. Assumed formats instead of verifying.

**Solution:** Always read state files before writing hooks that consume them. Use defensive parsing that handles multiple formats.

**Lesson:** NEVER assume JSON schema. Read the actual file first. Handle both expected AND legacy formats gracefully.

### 2025-11-26: Config values ≠ actual behavior
**Problem:** Saw `timeout: 15` in prompt hook config → assumed latency ≈ 15s → removed the hook as "too slow."

**Root Cause:** Timeout is a MAXIMUM, not expected latency. Actual Haiku call is <1s. I invented a number, then built confident reasoning on that false foundation.

**Lesson:** NEVER use config values (timeouts, limits, thresholds) as proxies for actual performance. Config = constraint, not measurement. Measure or ask - don't guess.

### 2025-11-26 13:28
- [abandoned_stubs] ⚠️ ABANDONED WORK: script_nudge.py, stop_cleanup.py contain stubs/TODOs
