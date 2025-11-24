# Git Semantic Grounding: Implementation Plan

## Overview
We're extracting **maximum semantic value** from git commit history to:
1. Ground Claude in **actual execution history** (not aspirational docs)
2. Inject **context at session start** (recent work, hotspots, quality trends)
3. Generate **rich commit messages** (impact analysis, protocol references)
4. Track **system maturity** (protocol evolution, quality adoption)
5. Enable **trauma recall** (avoid repeating past mistakes)

---

## What We've Built (Scratch Directory)

### 1. **Semantic Analysis Engine**
**File**: `scratch/analyze_commit_semantics.py`

**Capabilities**:
- Commit type distribution (feat/fix/chore/docs)
- Scope clustering (system/hooks/lib)
- Temporal patterns (peak hours, peak days)
- Semantic theme extraction (protocol, memory, hook mentions)
- File hotspot detection (high-churn files)
- Feature evolution timeline
- Quality gate adoption tracking
- Impact scoring (files × categories)

**Sample Output**:
```
📊 Analyzing 46 commits

📋 COMMIT TYPE DISTRIBUTION
  feat:     52.2% → Feature-driven development
  chore:    21.7% → High automation overhead
  docs:     10.9% → Documentation discipline

🔥 FILE HOTSPOTS (Last 30 commits)
  25x : .claude/memory/upkeep_log.md → Expected (auto-maintenance)
  23x : session_state.json → ⚠️ High churn, consider stabilizing
  14x : CLAUDE.md → Constitution evolving

🧠 SEMANTIC THEMES
  memory (24x), hook (18x), protocol (15x), audit (9x)
```

---

### 2. **SessionStart Hook: Context Injector**
**File**: `scratch/git_semantic_injector_hook.py`

**Purpose**: Inject historical context at session start

**What It Injects**:
- Recent feature work (last 5 feat commits with timestamps)
- High-churn files (≥5 changes in 7 days)
- Quality gate usage trends (audit/void/drift/verify)
- Dominant themes (protocol, hook, performance)
- Actionable recommendations

**Sample Output**:
```
🧠 GIT SEMANTIC CONTEXT (Last 7 days, 30 commits):

Recent Feature Work:
  • [def891e] (hooks) Update 1 hooks (today)
  • [d13fa6a] (system) Complete parallel execution (today)

⚠️ High-Churn Files (≥5 changes):
  • session_state.json (23x) → Consider stabilizing
  • CLAUDE.md (14x) → Constitution evolving

🛡️ Quality Gate Usage:
  ✅ audit.py: 9 mentions
  ⚠️ drift.py: Not used recently

💡 Recommendations:
  • Run drift_check.py (not seen in recent commits)
  • High file churn detected - consider refactoring
```

**Integration**: Add to `.claude/settings.json`:
```json
{
  "hooks": {
    "SessionStart": [
      ".claude/hooks/git_semantic_injector.py"
    ]
  }
}
```

---

### 3. **Enhanced Commit Message Generator**
**File**: `scratch/enhanced_commit_message.py`

**Purpose**: Generate rich commit bodies with semantic metadata

**Capabilities**:
- Auto-infer commit type/scope from files
- Impact analysis (files changed, LOC delta, categories)
- Protocol cross-reference detection
- Quality gate execution and reporting
- Impact scoring

**Sample Output**:
```
feat(hooks): Add git semantic injection hook

Impact Analysis:
  Files changed: 3 (hooks: 2, memory: 1)
  Lines: +215 -0
  Impact score: 6
  Protocols affected: Synapse Protocol, Epistemological Protocol

Quality Gates:
  ✅ audit.py (0 critical issues)
  ✅ void.py (0 stubs)

Files Changed:
  • .claude/hooks/git_semantic_injector.py
  • .claude/settings.json
  • .claude/memory/lessons.md

🤖 Generated with [Claude Code]
Co-Authored-By: Claude <noreply@anthropic.com>
```

**Usage**:
```bash
# Stage your changes
git add .

# Generate message
python3 scratch/enhanced_commit_message.py "Add git semantic injection"

# Copy output to git commit
```

---

## Integration Roadmap

### Phase 1: Low-Hanging Fruit (Immediate Value)

#### 1.1 Install SessionStart Hook
```bash
# Copy to hooks directory
cp scratch/git_semantic_injector_hook.py .claude/hooks/git_semantic_injector.py
chmod +x .claude/hooks/git_semantic_injector.py

# Register in settings.json
# Add to "SessionStart" array
```

**Value**: Every session starts with historical context

#### 1.2 Promote Analysis Tool
```bash
# Move to ops directory
cp scratch/analyze_commit_semantics.py scripts/ops/git_analyze.py
chmod +x scripts/ops/git_analyze.py

# Add to tool index
# Update upkeep.py to include it
```

**Usage**:
```bash
python3 scripts/ops/git_analyze.py
# Or: /git-analyze (slash command)
```

**Value**: On-demand semantic analysis

---

### Phase 2: Enhanced Auto-Commit (High Impact)

#### 2.1 Modify `auto_commit_on_complete.py`
Integrate `enhanced_commit_message.py` logic into auto-commit hook:

```python
# In auto_commit_on_complete.py, replace generate_commit_message()
from enhanced_commit_message import generate_enhanced_message

def generate_commit_message(files):
    """Generate rich commit message"""
    # Infer description from file categories
    description = infer_description_from_files(files)
    return generate_enhanced_message(description)
```

**Value**: Every auto-commit includes semantic metadata

#### 2.2 Add Commit Body Templates
Create `.claude/templates/commit_body.md` with:
- Impact analysis template
- Protocol reference checklist
- Quality gate results format
- Cross-reference links

---

### Phase 3: Trauma Ledger (Strategic)

#### 3.1 Create Commit Trauma Database
**File**: `.claude/memory/commit_trauma.jsonl`

**Schema**:
```jsonl
{"hash":"abc123","subject":"fix: Revert parallel hooks","lesson":"Race conditions in shared state","severity":"critical","date":"2025-11-22","affected_files":["session_state.json"]}
```

#### 3.2 Auto-Populate from `git log`
Parse commit history for:
- `fix:` commits → Extract what broke
- `revert:` commits → What was reverted and why
- Commits with "broken", "failed", "regression" in message

#### 3.3 Integrate with Synapse Protocol
**File**: `.claude/hooks/synapse_fire.py`

Add trauma recall:
```python
# When user mentions keywords in commit trauma
# Inject warning:
"""
⚠️ TRAUMA RECALL: abc123 (2 days ago)
"Parallel hooks caused race conditions"
Affected: session_state.json
Recommendation: Use sequential dispatch with parallel internals
"""
```

---

### Phase 4: Semantic Diff Tools

#### 4.1 `git_semantic_diff.py`
Compare semantic state across commit ranges:

```bash
python3 scripts/ops/git_semantic_diff.py HEAD~10..HEAD

# Output:
# Semantic Changes (Last 10 commits):
# - Hook count: 15 → 18 (+3)
# - Protocol count: 17 → 19 (+2)
# - Quality gate usage: audit 60% → 85%
# - File hotspots: 3 new high-churn files
```

#### 4.2 `git_protocol_timeline.py`
Visualize protocol maturity over time:

```bash
python3 scripts/ops/git_protocol_timeline.py

# Output:
# Protocol Evolution:
# 2025-11-20: Oracle Protocol (a799f2f)
# 2025-11-20: Research Protocol (6a80606)
# 2025-11-20: Epistemology Protocol (f33efe0)
# ...
# 2025-11-22: Git Semantic Protocol (CURRENT)
```

---

## Recommended Priorities

### Immediate (This Session)
1. ✅ Create semantic analysis engine (DONE)
2. ✅ Create SessionStart hook (DONE)
3. ✅ Create enhanced commit generator (DONE)
4. **Install SessionStart hook** (5 minutes)
5. **Test with next session restart** (validation)

### Next Session
6. Promote `git_analyze.py` to scripts/ops/
7. Create slash command `/git-analyze`
8. Modify `auto_commit_on_complete.py` to use enhanced messages

### Strategic (Next Week)
9. Build commit trauma ledger
10. Integrate trauma recall with Synapse Protocol
11. Create `git_semantic_diff.py` tool
12. Create `git_protocol_timeline.py` tool

---

## Success Metrics

### Before (Baseline)
- ❌ No historical context at session start
- ❌ Generic auto-commit messages
- ❌ Claude repeats past mistakes
- ❌ File hotspots invisible
- ❌ Protocol evolution not tracked

### After (Target)
- ✅ Rich context injection at every session start
- ✅ Semantic commit messages with impact analysis
- ✅ Trauma recall prevents repeated failures
- ✅ File churn warnings trigger refactoring
- ✅ Protocol maturity tracked quantitatively

---

## Example: Full Workflow Demo

### **Before Enhancement**
```
User: "Make hooks run in parallel"

Claude: [Implements parallel hooks]
         [Causes race condition in session_state.json]
         [User reports bug]
         [Claude fixes]
         [Auto-commit: "chore: Update 3 files"]
```

### **After Enhancement**
```
Session starts:

🧠 GIT SEMANTIC CONTEXT:
⚠️ High-Churn Files:
  • session_state.json (23x) → Consider stabilizing

User: "Make hooks run in parallel"

Claude: I notice session_state.json has 23 changes in 7 days
         (high churn signal). Before implementing parallel hooks,
         let me check if we've attempted this before...

         [Checks commit history]
         [Finds: "fix: Revert parallel hooks" commit]

         ⚠️ TRAUMA RECALL: def456 (2 days ago)
         We previously reverted parallel hooks due to race conditions
         in session_state.json.

         Proposed approach:
         1. Sequential dispatch (no races)
         2. Parallel operations WITHIN each hook
         3. Add state locking mechanism

         This avoids the def456 failure mode. Proceed?

User: "Yes"

[Claude implements safe version]
[Auto-commit with rich message:]

feat(hooks): Add safe parallel hook execution

Impact Analysis:
  Files changed: 4 (hooks: 2, lib: 1, tests: 1)
  Lines: +180 -0
  Impact score: 8
  Protocols affected: None

Quality Gates:
  ✅ audit.py (0 issues)
  ✅ void.py (0 stubs)
  ✅ verify.py (tests pass)

Related Commits:
  def456 - Previous parallel attempt (reverted)
  Lesson: Avoid shared state races

Decision Rationale:
  Sequential dispatch + parallel internals avoids
  def456 race condition while maintaining performance.

🤖 Generated with [Claude Code]
```

---

## Technical Notes

### Performance
- SessionStart hook: <1s overhead (30 commits analyzed)
- Commit message generation: <3s (includes audit + void)
- Semantic analysis: <5s for 100 commits

### Dependencies
- Zero new dependencies (stdlib only)
- Git 2.0+ required (for --format flags)
- Python 3.7+ (subprocess, json, re)

### Failure Modes
- If git fails: Silent fallback (empty context)
- If analysis times out: Partial results returned
- If quality gates fail: Warning in commit message (not blocking)

### Storage
- No persistent storage needed (git is the database)
- Optional: `.claude/memory/commit_trauma.jsonl` (JSONL, append-only)
- Analysis results: Ephemeral (regenerated on demand)

---

## Philosophical Alignment

This approach embodies Whitebox principles:

1. **Code is Truth**: Git commits = executed decisions, not aspirational docs
2. **Self-Documenting Systems**: Commit history auto-generates context
3. **Evidence-Based**: Semantic analysis replaces manual documentation
4. **Anti-Bloat**: Zero new dependencies, leverage existing git infrastructure
5. **Automation First**: Hooks inject context automatically
6. **Ground in Reality**: Trauma recall prevents hallucinated "improvements"

Git commit logs are the **highest-fidelity signal** of codebase evolution. By treating them as a **semantic database**, we achieve:

- **Temporal awareness** (what happened when)
- **Causal reasoning** (commit dependency chains)
- **Pattern recognition** (hotspots, themes, quality trends)
- **Trauma avoidance** (don't repeat mistakes)
- **Maturity tracking** (protocol evolution over time)

This is **context injection without token bloat**: 200 lines of hook code → infinite historical context.

---

## Next Steps

**Recommended Action**: Install SessionStart hook now

```bash
# 1. Copy hook to production
cp scratch/git_semantic_injector_hook.py .claude/hooks/git_semantic_injector.py
chmod +x .claude/hooks/git_semantic_injector.py

# 2. Update settings.json
# Add to "SessionStart" hook array

# 3. Restart session to test

# 4. Observe context injection at next session start
```

**Expected Result**: Next session starts with:
```
🧠 GIT SEMANTIC CONTEXT (Last 7 days, N commits):
[Rich historical context appears here]
```

Then proceed with Phase 2 (enhanced auto-commit) in next session.
