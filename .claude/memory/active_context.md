# Active Context (Short-Term Memory)

**CURRENT SPRINT:** Whitebox SDK Development - Building AI Engineering Platform

**STATUS:** ✅ **Platform Complete** - All Core Systems Operational
- Whitebox SDK with scaffolder, indexer, core library ✅
- The Oracle Protocol (external reasoning via OpenRouter) ✅
- The Research Protocol (real-time web search via Tavily) ✅
- The Probe Protocol (runtime introspection for anti-hallucination) ✅
- The X-Ray Protocol (AST-based structural code search) ✅
- The Headless Protocol (browser automation via Playwright) ✅
- High-Performance Batching (parallel execution library) ✅
- The Elephant Protocol (persistent memory system) ✅
- The Upkeep Protocol (automated maintenance and drift prevention) ✅

**SYSTEM HEALTH:**
- All 24 tests passing (5 suites: unit, integration, alignment, stability)
- 8 operational tools registered in index
- Memory persistence validated across session restoration
- All hooks active (SessionStart, UserPromptSubmit, SessionEnd)
- Automatic maintenance on session end
- Code search: text (grep) + structure (xray)
- Browser automation: Playwright SDK with zero-friction scaffolding

**NEXT STEPS:**
1. Awaiting new direction from user
2. Platform ready for production use or expansion

**BLOCKERS:** None

---
*Last updated: 2025-11-20*

### 2025-11-20 17:32
The Sentinel Protocol (9th protocol) is now complete. All quality gates operational: audit.py (The Sheriff), drift_check.py (The Court), pre_write_audit.py hook (The Gatekeeper). Anti-patterns registry defined in .claude/memory/anti_patterns.md. Documentation added to CLAUDE.md.

### 2025-11-20 17:41
The Cartesian Protocol (10th protocol) is now complete. Meta-cognition tools operational: think.py (The Thinker - sequential decomposition), skeptic.py (The Skeptic - hostile review), trigger_skeptic.py hook (watches for risky operations). Documentation added to CLAUDE.md. This enforces Think → Skepticize → Code workflow.

### 2025-11-20 17:46
The MacGyver Protocol (11th protocol) is now complete. Living off the Land (LotL) philosophy operational. Tools: inventory.py (The Scanner - system capability detection), macgyver agent (improvisation mindset). Documentation in CLAUDE.md. Enforces: Scan → Fallback Chain (stdlib > binaries > raw I/O) → Never surrender.

### 2025-11-20 17:57
SYNAPSE PROTOCOL (12th Protocol) - Associative Memory System: Implemented spark.py (association retrieval engine), synapses.json (neural network map with 17 patterns), synapse_fire.py hook (automatic context injection). The system matches user prompts against regex patterns, retrieves relevant protocols/tools/lessons, searches lessons.md for past trauma, and injects random constraints (10% probability) for lateral thinking. All context is injected automatically before Claude processes prompts. Testing verified: pattern matching, association retrieval, memory recall, random constraints all working.

### 2025-11-20 18:03
JUDGE PROTOCOL (13th Protocol) - Value Assurance & Anti-Bikeshedding: Implemented judge.py (ruthless pragmatism evaluator) and intervention.py hook (automatic bikeshedding detection). The Judge applies Occam's Razor and YAGNI principles to proposals, returning PROCEED/SIMPLIFY/STOP verdicts with brutal honesty. Intervention hook triggers on bikeshedding keywords (prettier config, linting rules, custom framework, might need, future proof) and warns users. Philosophy: Code is a liability, not an asset. The best code is no code. ROI over elegance. Testing verified: dry-run works, OpenRouter integration correct, hook registered. Tool registered in index (15 total scripts).

### 2025-11-20 18:08
CRITIC PROTOCOL (14th Protocol) - The 10th Man / Mandatory Dissent: Implemented critic.py (eternal pessimist / assumption attacker) and anti_sycophant.py hook (opinion request detection). The Critic attacks core premises with four sections: THE ATTACK (why assumptions are wrong), THE BLIND SPOT (hidden optimism), THE COUNTER-POINT (opposite approach), THE BRUTAL TRUTH (uncomfortable reality). Anti-sycophant hook triggers on opinion requests ('what do you think', 'is this a good idea', 'we should migrate') and forces consultation before agreeing. Philosophy: Optimism is a bug. Agreement is weakness. The 10th Man Rule prevents groupthink. Testing verified: dry-run works, OpenRouter integration correct, hook registered. Tool registered in index (16 total scripts). The Three-Layer Defense complete: Judge (value/ROI), Skeptic (technical risks), Critic (assumption attack).

### 2025-11-20 18:15
REALITY CHECK PROTOCOL (15th Protocol) - Anti-Gaslighting / Binary Verification: Implemented verify.py (objective fact checker with 4 check types: file_exists, grep_text, port_open, command_success), detect_gaslight.py hook (frustration detection), sherlock.md agent (evidence-based detective). Philosophy: LLMs optimize for consistency over reality. Solution: Binary verification - exit code 0 (TRUE) or exit code 1 (FALSE). Claude cannot argue with the kernel. The 'Show Your Work' Rule: FORBIDDEN from claiming 'I fixed it' without running verify.py first. Detect-gaslight hook triggers on frustration keywords ('you said', 'still not working', 'stop lying', 'check again') and forces verification loop. Testing verified: all 4 check types working (file_exists, grep_text, command_success all pass/fail correctly). Tool registered in index (17 total scripts). Ground truth > Internal model. Evidence > Claims. The system state is the source of truth.

### 2025-11-20 18:20
FINISH LINE PROTOCOL (16th Protocol) - Anti-Laziness / Reward Hacking Prevention: Implemented scope.py (project manager with 3 commands: init, check, status) using OpenRouter Oracle to generate exhaustive checklists. State stored in .claude/memory/punch_list.json (task description, items array with done flags, completion percentage). Philosophy: LLMs optimize for perceived completion over actual completion (reward hacking/sandbagging). Solution: External DoD tracker - Claude FORBIDDEN from claiming 'I'm done' unless scope.py status shows 100%. Oracle generates exhaustive checklists (tests, docs, verification, cleanup - not just implementation). The 'Big Reveal' Rule: quantitative stats required (files modified, lines added/removed, tests passing) - no qualitative BS. Anti-Sandbagging Rules: Cannot mark items you didn't do, cannot skip items, cannot declare victory early, stats required at completion. Testing verified: status shows 'No active punch list' correctly. Tool registered in index (18 total scripts). Enforcement is manual (no hooks). 100% > 'Almost Done'. External > Internal. Proof > Claims.

### 2025-11-20 18:30
VOID HUNTER PROTOCOL (17th Protocol) - Completeness Checking / Gap Detection: Implemented void.py (completeness checker with 2 phases: stub hunting + logical gap analysis) and ban_stubs.py hook (prevents writing stub code). Philosophy: LLMs suffer from "Happy Path Bias" - they implement requested features but ignore ecosystem requirements (complementary operations, error handling, configuration, feedback). Solution: Automated detection of "negative space" - code that SHOULD exist but doesn't. Phase 1 (Stub Hunt): Regex-based detection of incomplete code markers (TODO, FIXME, pass, ..., NotImplementedError). Phase 2 (Gap Analysis): Oracle-powered structural analysis checking for CRUD Asymmetry (create without delete), Error Handling Gaps (operations without try/except), Config Hardcoding (magic numbers instead of env vars), Missing Feedback (silent operations). Ban-stubs hook blocks Write operations containing stub patterns. Testing verified: stub detection working (3 stubs found in test file), clean files pass correctly, void.py registered in index (19 total scripts). Enforcement: automatic via ban_stubs.py hook + manual via void.py. Ecosystem thinking > Feature thinking. Completeness > Speed. Complementary operations mandatory.

### 2025-11-20 19:40
The Council Protocol (18th protocol) is now complete. Meta-protocol that assembles Judge, Critic, Skeptic, Thinker, and Oracle in parallel for comprehensive decision analysis. Demonstrated value on Context7 proposal (unanimous rejection from all perspectives). Tool: scripts/ops/council.py. Supports --only, --skip, --model flags. 4x faster than sequential consultation. Documentation added to CLAUDE.md.

### 2025-11-22
COMMAND PREREQUISITE ENFORCEMENT (20th Protocol) - Workflow Automation via Hard Blocks: Implemented command_tracker.py (PostToolUse - silent tracking) and command_prerequisite_gate.py (PreToolUse - hard blocking). Philosophy: LLMs optimize for "appearing helpful quickly" over "following best practices" → Advisory warnings get rationalized away → Solution: Hard-block actions until workflow commands run. The Five Rules: (1) git commit requires /upkeep (last 20 turns), (2) Claims ("Fixed"/"Done") require /verify (last 3 turns), (3) Edit requires Read first, (4) Production write requires /audit AND /void (last 10 turns), (5) Complex script-smith delegation requires /think (last 10 turns). Session state tracks `commands_run` dictionary with turn numbers, `verified_commands` for proof. Testing verified: 6/6 tests passing (scratch/test_command_enforcement.py). Hooks registered in settings.json for Bash/Write/Edit/Task tools. Library functions added to epistemology.py: record_command_run(), check_command_prerequisite(). Documentation in CLAUDE.md § Epistemological Protocol Phase 5. Impact: Forces /verify before claims (anti-gaslighting), /upkeep before commits (consistency), Read before Edit (context), quality gates for production code. Enforcement > Advisory. Hard blocks > Soft suggestions. The system cannot ignore blocks.
