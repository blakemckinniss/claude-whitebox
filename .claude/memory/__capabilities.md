# Capabilities Index

**Generated:** 2025-12-04 21:42

**PURPOSE:** Before proposing new functionality, check if it exists here.

---

## 🔒 Security Gates

- `audit.py` - The Sentinel: Runs static analysis and anti-pattern detection on target files
- `audit_hooks.py` - System Auditor (The Hook Sheriff)
- **content_gate** - Content Gate Hook v4: AST-based semantic security blocking for Write/Edit operat
- `orchestrate.py` - Orchestrate: Claude-powered programmatic tool orchestration
- **repomix_generator** - Repomix Generator Hook: Auto-generate codebase summaries for AI context
- **security_claim_gate** - Security Claim Gate Hook: Require audit for security-sensitive code

## 📋 Workflow Gates

- `coderabbit.py` - CodeRabbit: AI-powered code review and commit workflow
- **commit_gate** - Commit Gate Hook: Block git commit without running upkeep first
- **deferral_gate** - Deferral Gate Hook: Block deferral theater language
- `upkeep.py` - The Janitor: Pre-commit health checks and project maintenance

## ✅ Quality Gates

- **auto_learn** - Auto Learn Hook v3: PostToolUse hook that captures lessons from errors
- **completion_gate** - Completion Gate Hook: Block "fixed/done/complete" claims without verification
- **error_suppression_gate** - Error Suppression Gate: PreToolUse hook blocking work until errors are resolved
- `groq.py` - Groq: Zero-Dependency Groq API Client
- **import_gate** - Import Gate Hook: Verifies imports exist before allowing Write operations
- **integration_gate** - Integration Gate: PreToolUse hook enforcing grep after function edits

## 🎯 Scope Control

- `drift.py` - The Court: Detects stylistic drift by comparing code against reference templates
- `drift_check.py` - The Court: Detects stylistic drift by comparing code against reference templates
- **goal_anchor** - Goal Anchor Hook: Prevents drift from original user intent
- `scope.py` - The Project Manager: Manages the Definition of Done (DoD) for the current task

## 🧠 Reasoning Guards

- **counterfactual_check** - Counterfactual Pre-Check: Force contingency planning BEFORE action
- `think.py` - The Thinker: Decomposes complex problems into atomic steps using Chain of Though
- **thinking_coach** - Thinking Coach Hook v3: Analyzes Claude's thinking blocks for reasoning flaws

## 💉 Context Injectors

- **assumption_ledger** - Assumption Ledger: Surface hidden assumptions before code changes
- **context_injector** - Context Injector Hook v3: UserPromptSubmit hook for smart context injection
- `council.py` - Deliberative Council: Multi-Round Decision Framework with Convergence
- `docs.py` - The Documentation Hunter: Retrieves latest documentation using Context7 REST API
- **intake_protocol** - Intake Protocol Hook - Structured checklist for every user prompt
- **pre_compact** - PreCompact Hook: Fires before compaction
- **project_context** - Project Context Hook v3: Provide git/folder/file awareness
- **prompt_disclaimer** - Static disclaimer injected into every user prompt
- **python_path_injector** - Python Path Enforcer: PreToolUse hook that rejects bare python/pip commands
- **reminder_injector** - Reminder Injector Hook: Dynamic context injection based on trigger patterns
- **resource_pointer** - Resource Pointer Hook: Surface availability, not content
- **ui_verification_gate** - UI Verification Gate Hook: Require browser screenshot after CSS/UI changes

## 🧠 Memory Injectors

- **doc_theater_gate** - Documentation Theater Gate: Blocks creation of standalone documentation files
- **memory_injector** - Memory Injector Hook v3: Auto-surface relevant memories on every prompt
- `remember.py` - The Elephant: Manages persistent project memory (Context, Decisions, Lessons)
- `spark.py` - The Synapse: Scans prompt for keywords and retrieves associated memories and pro

## 🔧 Ops Awareness

- **background_enforcer** - Background Enforcer Hook v3.2: PreToolUse blocker for slow Bash commands
- `bdg.py` - Browser Debugger CLI (bdg): Direct Chrome DevTools Protocol access for AI agents
- `browser.py` - Browser Debugger CLI (bdg): Direct Chrome DevTools Protocol access for AI agents
- `detour.py` - CLI management tool for the Detour Protocol - status tracking, resolution, and t
- `hooks.py` - System Tool - Unified audit and testing for Claude Code hooks
- **loop_detector** - Loop Detector: PreToolUse hook blocking bash loops
- **modularization_gate** - Modularization Gate - Reminds Claude to modularize before creating/editing code
- **ops_awareness** - Ops Awareness Hook v3: Remind Claude to use existing ops scripts
- **ops_nudge** - Ops Tool Nudge Hook: Suggest appropriate .claude/ops/ tools based on prompt patt
- **oracle_gate** - Oracle Gate Hook: Enforce oracle consultation after repeated failures
- `playwright.py` - The Playwright Enforcer: Browser automation setup and verification tool
- **probe_gate** - Probe Gate Hook v3: Suggest probe before using unfamiliar library APIs
- **production_gate** - Production Gate Hook v4: PreToolUse hook enforcing audit+void before .claude/ops
- **recursion_guard** - Recursion Guard: PreToolUse hook blocking catastrophic folder duplication
- **research_gate** - Research Gate Hook: BLOCK writes using unverified external libraries
- **root_pollution_gate** - Root Pollution Gate: PreToolUse hook blocking writes to repository root
- **scratch_enforcer** - Scratch Enforcer Hook v3: Detect repetitive manual work, suggest scripts
- **script_nudge** - Nudge Hook: Suggests writing scripts for complex manual work
- **subagent_stop** - SubagentStop Hook: Fires when Task tool agents finish
- **sunk_cost_detector** - Sunk Cost Detector Hook: Breaks "I've invested too much to quit" loops

## 📊 Trackers

- **info_gain_tracker** - Information Gain Tracker Hook: Detects "spinning" - reads without progress
- **intention_tracker** - Intention Tracker Hook v3.2: UserPromptSubmit hook for pending file/search extra
- **state_updater** - State Updater Hook v3: PostToolUse hook that updates session state
- **velocity_tracker** - Velocity Tracker Hook: Detect spinning vs actual progress

## 🔄 Lifecycle Hooks

- **beads_integration** - Beads Integration Hook: Surface ready work and maintain agent memory
- **epistemic_boundary** - Epistemic Boundary Enforcer: Catches claims not backed by session evidence
- `evidence.py` - Evidence Ledger Viewer - Review evidence gathered during sessions
- **proactive_nudge** - Proactive Nudge Hook: Surfaces actionable suggestions based on session state
- **recommendation_gate** - Recommendation Gate Hook: Blocks "create X" suggestions without verification
- **session_cleanup** - Session Cleanup Hook v3: SessionEnd hook for cleanup and persistence
- **session_init** - Session Init Hook v3: SessionStart hook for initialization
- **stop_cleanup** - Stop Cleanup Hook: Fires when Claude stops responding
- `test_hooks.py` - Test Suite: Comprehensive testing for Claude Code hooks

## 🔍 Verification Tools

- **gap_detector** - Gap Detector Hook v3: PreToolUse hook with directive injection system
- `gaps.py` - The Void Hunter: Scans code for missing functionality, stubs, and logical gaps
- `verify.py` - The Fact-Checker: Validates system state assertions. Returns True/False. Use thi
- `void.py` - The Void Hunter: Scans code for missing functionality, stubs, and logical gaps

## 🌐 Research Tools

- `firecrawl.py` - The Firecrawler: Scrape and crawl websites using Firecrawl API
- `probe.py` - The Probe: Introspects Python modules/objects to reveal the ACTUAL runtime API
- `research.py` - The Researcher: Performs deep web search using Tavily to retrieve up-to-date doc
- **tool_preference** - Preference Hook: PreToolUse intercept for better tool choices

## ⚖️ Decision Tools

- `agents.py` - Oracle Swarm: Massive Parallel External Reasoning
- `oracle.py` - Oracle: Generic OpenRouter LLM Consultation
- `recruiter.py` - Council Recruiter: Selects optimal personas for a given proposal
- `swarm.py` - Oracle Swarm: Massive Parallel External Reasoning

## ⌨️ Slash Commands

- `/audit` - description: 🛡️ The Sheriff - Code quality audit (security, complexity, style)
- `/audit-hooks` - description: 🔍 The Hook Sheriff - Audit hooks against official Claude Code spec
- `/bestway` - description: 🧭 Best Way - Evaluates optimal approaches for implementing X
- `/better` - description: 🔬 Improvement Analyzer - Identifies concrete ways to make things be
- `/cc` - description: 🏭 Command Creator - Creates new slash commands from description
- `/commit` - description: 📦 Smart Commit - Stage, commit all changes, offer push
- `/confidence` - description: 📉 Confidence Tracker - Check epistemological protocol state (status
- `/consult` - description: 🔮 The Oracle - High-level reasoning via OpenRouter
- `/council` - description: 🏛️ The Council - Parallel multi-perspective analysis (Judge, Critic
- `/cr` - description: 🐰 CodeRabbit - Run AI code review on uncommitted changes
- `/critic` - description: 🥊 The Critic - The 10th Man, attacks assumptions and exposes blind 
- `/cs` - description: 🤔 Can/Should - Quick feasibility and advisability check for X
- `/cwms` - description: ✅ Can We Make Sure - Verify and enforce X is true
- `/dc` - description: 🔍 Double Check - Verify work, fix critical gaps, present remaining 
- `/doit` - description: ⚡ Do It - Execute the last discussed action without re-explaining
- `/drift` - description: ⚖️ The Court - Checks project consistency and style drift
- `/dyr` - description: 🪞 Do You Respect - Verify Claude follows a specific principle/rule
- `/evidence` - description: 📚 Evidence Ledger - Review evidence gathered (review, session <id>)
- `/f` - description: 🔧 Fix Console Errors - Diagnose and fix browser console errors
- `/fix` - description: 🔧 The Fixer - Fix all issues, fill gaps, and verify work
- `/gaps` - description: 🔍 Gap Hunter - Completeness check (finds stubs, missing CRUD, error
- `/har` - description: 💡 HAR - Have Any Recommendations for improving X?
- `/imp` - description: 🔧 Implement - Research + optimal setup of X for this project
- `/inventory` - description: 🖇️ MacGyver Scan - Scans for available binaries and system tools
- `/judge` - description: ⚖️ The Judge - Value assurance, ROI, YAGNI, anti-bikeshedding
- `/no` - description: 🚫 No - Reject proposal and get alternatives
- `/opt` - description: ⚖️ Optimality Check - Evaluates if X is the best choice for this pr
- `/orchestrate` - description: 🎯 Orchestrate - Claude API code_execution for batch/aggregate tasks
- `/probe` - description: 🔬 The Probe - Runtime introspection (inspect object APIs before cod
- `/remember` - description: 🐘 The Elephant - Persistent memory (add lessons|decisions|context, 
- `/research` - description: 🌐 The Researcher - Live web search via Tavily API
- `/roi` - description: 💰 ROI Maximizer - Implements highest-value concepts by impact/effor
- `/scope` - description: 🏁 The Finish Line - Manage DoD with checkpoints (init, check, statu
- `/skeptic` - description: 🔍 The Skeptic - Hostile review, finds ways things will fail
- `/spark` - description: ⚡ Synapse Fire - Retrieve associative memories for a topic
- `/test` - description: 🧪 Test Worth - Evaluate if something deserves test coverage
- `/think` - description: 🧠 The Thinker - Decomposes complex problems into sequential steps
- `/upkeep` - description: 🧹 The Janitor - Project upkeep (sync requirements, tool index, chec
- `/useful` - description: 🔧 Usefulness Amplifier - Makes X more practical, actionable, and va
- `/verify` - description: 🤥 Reality Check - Verifies system state (file_exists, grep_text, po
- `/vo` - description: 🔍 Gap Oracle - Runs gaps.py + oracle analysis on changes
- `/void` - description: 🕳️ The Void Hunter - Completeness check (finds stubs, missing CRUD,
- `/wcwd` - description: 🛠️ Implementation Brainstorm - Explores options for implementing X 
- `/worth` - description: 💎 Worth Check - Is X worth adding to this project?
- `/xray` - description: 🔬 X-Ray - AST-based structural code search (--type class|function|i
- `/yes` - description: 🚀 Autonomous Mode - Execute what's best for project health and succ

## 📦 Other

- `inventory.py` - The Scanner: Detects available system binaries, languages, and network capabilit
- `timekeeper.py` - The Timekeeper: Assesses proposal complexity and sets dynamic deliberation limit
- `xray.py` - The X-Ray: Performs AST-based structural search on Python code (Classes, Functio

---

## Before Creating New Functionality

1. **Search this index** for similar capabilities
2. **Read the existing implementation** if found
3. **Justify why existing is insufficient** before creating new
4. **Consider extending** existing over creating new

**Anti-pattern:** Creating `new_security_gate.py` when `content_gate.py` already handles security.
