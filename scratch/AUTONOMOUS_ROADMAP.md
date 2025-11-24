# Autonomous Systems Roadmap

## Vision: Zero Human Loop Execution

**Goal:** Human provides strategic intent, AI executes completely autonomously.

---

## ✅ What Already Exists

### Partial Automation
- `auto_commit_on_complete.py` - Suggests commits (doesn't execute)
- Agent auto-invocation (macgyver, sherlock, tester)
- Hook-based enforcement (batching, background)
- Quality gates (audit, void, verify)

### Foundation Ready
- Orchestrator framework (scratch/orchestrator.py)
- Event-based architecture
- Audit trail logging
- Configuration system

---

## 🎯 Four Autonomous Systems to Build

### 1. The Guardian (Auto-Test Loop)
**Status:** 🔴 Not Started
**Priority:** P0 (Critical)
**Effort:** 2-3 hours

**What it does:**
- Detects code changes (PostToolUse:Write/Edit)
- Automatically runs relevant tests
- Enters auto-fix loop if failures (max 3 attempts)
- Escalates to user after 3 failures
- Records results for Committer

**Files to create:**
- `.claude/hooks/auto_guardian.py` (PostToolUse hook)
- `scripts/lib/test_runner.py` (test execution logic)
- `.claude/memory/test_mappings.json` (file → test mapping)

**Integration:**
- Orchestrator triggers on code_change event
- Quality gate: tests_passing
- Blocks Committer until passing

---

### 2. The Committer (Auto-Commit Flow)
**Status:** 🟡 Partial (suggest only)
**Priority:** P0 (Critical)
**Effort:** 2-3 hours

**What it does:**
- Waits for all quality gates (Guardian + audit + void)
- Analyzes git status + diff
- Generates context-aware commit message
- Executes commit (in dry-run initially)
- Optionally pushes (if auto_push=true)

**Files to create:**
- `.claude/hooks/auto_committer.py` (orchestrated)
- `scripts/lib/commit_generator.py` (message generation)
- Upgrade existing: `auto_commit_on_complete.py`

**Integration:**
- Orchestrator triggers after quality gates pass
- Uses Guardian results
- Records commit hash in state

---

### 3. The Documentarian (Auto-Docs Sync)
**Status:** 🔴 Not Started
**Priority:** P1 (High)
**Effort:** 1-2 hours

**What it does:**
- Watches scripts/ops/ and .claude/hooks/
- Detects new/modified/removed tools
- Updates CLAUDE.md automatically
- Syncs CLI Shortcuts section
- Updates protocol sections

**Files to create:**
- `.claude/hooks/auto_documentarian.py` (PostToolUse hook)
- `scripts/lib/doc_sync.py` (CLAUDE.md parser/updater)

**Integration:**
- Triggered by code changes to watched paths
- Runs in parallel with Guardian
- Included in same commit as code

---

### 4. The Janitor (Auto-Cleanup)
**Status:** 🔴 Not Started
**Priority:** P2 (Medium)
**Effort:** 1-2 hours

**What it does:**
- Runs on SessionEnd or every 50 turns
- Archives old scratch files (>7 days)
- Removes duplicate scripts
- Cleans unused imports
- Deletes dead hooks

**Files to create:**
- `.claude/hooks/auto_janitor.py` (SessionEnd hook)
- `scripts/lib/cleanup_engine.py` (cleanup logic)
- `.claude/memory/janitor_config.json` (rules)

**Integration:**
- Orchestrator triggers on session_end
- Runs after Guardian + Committer
- Logs all actions (reversible)

---

## 📅 Implementation Timeline

### Week 1: Foundation
- [x] Design zero human loop strategy
- [x] Implement Orchestrator
- [ ] Create automation_config.json
- [ ] Test orchestrator event flow

### Week 2: Guardian + Committer (Critical Path)
- [ ] Implement Guardian (auto-test)
- [ ] Implement test_runner.py
- [ ] Test Guardian with 10 code changes
- [ ] Implement Committer (dry-run)
- [ ] Test commit generation
- [ ] Validate quality gates work

### Week 3: Documentarian + Janitor
- [ ] Implement Documentarian
- [ ] Test doc sync on 5 tools
- [ ] Implement Janitor
- [ ] Test cleanup rules

### Week 4: Integration + Live Testing
- [ ] Wire all 4 systems to Orchestrator
- [ ] Enable dry-run mode for all
- [ ] Monitor 1 week (20+ sessions)
- [ ] Tune thresholds
- [ ] Enable full automation (not dry-run)

---

## 🔧 Quick Start: Minimum Viable Automation

**Goal:** Get value TODAY with minimal work

### Phase 0: Auto-Test Only (1 hour)

Build just the Guardian in simplest form:

```python
# .claude/hooks/simple_guardian.py

# On Write/Edit to scripts/ops/:
if file.startswith("scripts/ops/"):
    # Run tests
    result = subprocess.run(["pytest", "tests/"], capture_output=True)

    if result.returncode != 0:
        # Tests failed
        print(f"⚠️ Tests failed after code change")
        print(result.stdout.decode())

        # Inject: "Please fix test failures before continuing"
```

**Impact:** Immediate feedback on broken tests, no manual test runs.

---

## 📊 Success Metrics

### Quantitative (After 1 Month)
- **Human interventions:** <5 per session (from 20+)
- **Auto-commits:** 80%+ of changes
- **Test failures caught:** 95%+ before commit
- **Doc sync:** 100% accuracy
- **Time savings:** 20+ minutes per feature

### Qualitative
- User never types "run tests"
- User never types "git commit"
- User never types "update docs"
- User trusts autonomous systems
- User focuses on strategy, not tactics

---

## 🛡️ Safety First

### Fail-Safe Mechanisms
1. **Dry-run default:** All systems start in preview-only mode
2. **Max attempts:** Guardian stops after 3 failures, escalates
3. **Audit trail:** Every action logged with rollback command
4. **Manual override:** MANUAL_MODE=true disables all
5. **Gradual rollout:** One system at a time, validate before next

### Escalation Triggers
- Guardian: 3 failed fix attempts → user
- Committer: Breaking changes detected → user approval
- Documentarian: Ambiguous change → user review
- Janitor: >100 files to delete → user confirmation

---

## 🎓 Learning System

### Adaptive Thresholds
**Current:** Fixed (3 attempts, 7 days, 50 turns)
**Future:** Learn from user patterns

Example:
```
User always ignores cleanup suggestions for scratch/prototypes/
→ Janitor learns: exclude scratch/prototypes/ from cleanup
```

### Confidence Scoring
**Current:** Binary (pass/fail)
**Future:** Probabilistic confidence

Example:
```
Guardian: 95% confident these tests validate the change
Committer: 80% confident this commit message is accurate
```

If confidence <80%, ask user before executing.

---

## 🚀 Vision: 6 Months Out

### Full Autonomous Development

**User says:** "Build a tool to analyze API response times"

**AI executes (zero prompts):**
```
Turn 1: Planning
  - /think "API response time analyzer"
  - Write scratch/api_timing_plan.md

Turn 2: Implementation
  - Write scripts/ops/api_timing.py
  - [Guardian: Auto-create tests]
  - [Guardian: Run tests → ✅ pass]

Turn 3: Documentation
  - [Documentarian: Add to CLAUDE.md]
  - [Documentarian: Create examples]

Turn 4: Quality Gates
  - [Committer: Run /upkeep → ✅]
  - [Committer: Run /audit → ✅]
  - [Committer: Run /void → ✅]

Turn 5: Commit
  - [Committer: Execute commit]
  - git add scripts/ops/api_timing.py tests/ CLAUDE.md
  - git commit -m "feat: Add API response time analyzer

    - Collects timing metrics from API calls
    - Supports statistical analysis (p50, p95, p99)
    - Exports to JSON/CSV formats
    - Full test coverage (10/10 passing)

    🤖 Generated with Claude Code
    Co-Authored-By: Claude <noreply@anthropic.com>"

Turn 6: Report
  - "Feature complete. Committed abc123."
  - "Tests: 10/10 passing"
  - "Documentation: Synced"
  - "Ready to use: python3 scripts/ops/api_timing.py"

Total: 6 turns, 0 human interventions, <5 minutes
```

---

## 💡 Key Insights

### 1. Autonomous ≠ Aggressive
- Don't auto-commit every change
- Wait for quality gates
- Escalate on ambiguity

### 2. Trust Through Transparency
- Audit trail shows all actions
- User can review/revert anytime
- Dry-run builds confidence

### 3. Gradual Adoption
- Start with Guardian (immediate value)
- Add Committer once trust built
- Add Documentarian + Janitor later

### 4. Human for Strategy, AI for Execution
- Human: "Build X"
- AI: Plans, codes, tests, docs, commits
- Human: Reviews outcome (not process)

---

## 🔗 Related Systems

### Already Built
- Native Tool Batching (parallelizes I/O)
- Background Execution (parallelizes Bash)
- Epistemological Protocol (confidence tracking)
- Quality Gates (audit, void, verify)

### Synergies
- Guardian uses Background Execution (tests in background)
- Committer uses Quality Gates (audit + void)
- Orchestrator uses Epistemology (confidence-based escalation)
- All use Batching (parallel operations)

---

## 📝 Next Immediate Action

**Option A: Build Guardian Now (1 hour)**
Get immediate value from auto-testing

**Option B: Create Config File (15 min)**
Set up automation_config.json for future systems

**Option C: Test Orchestrator (30 min)**
Validate event flow works before building systems

**Recommendation:** Option A (Guardian) for immediate impact

---

*This roadmap transforms Claude from assistant to autonomous engineer.*
*Human provides vision, AI handles execution end-to-end.*
