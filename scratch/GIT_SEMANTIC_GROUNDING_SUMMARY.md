# Git Semantic Grounding: Executive Summary

## Problem Statement
Claude Code has no **temporal awareness** of codebase evolution. Each session starts with zero historical context, leading to:
- Repeated mistakes from previous sessions
- No awareness of file hotspots or churn patterns
- Generic commit messages lacking semantic value
- Inability to track system maturity over time

## Solution
Treat **git commit history as a semantic database** for context injection and grounding.

---

## Key Insight
Git commits are **executed decisions**, not aspirational documentation. They contain:
- **What changed** (file paths, LOC delta)
- **When it changed** (timestamps, temporal patterns)
- **Why it changed** (commit messages, conventional types)
- **How it relates** (parent commits, dependency chains)

This is **the highest-fidelity signal** of codebase evolution.

---

## What We Built (3 Tools)

### 1. **Semantic Analysis Engine**
**File**: `scratch/analyze_commit_semantics.py` (219 lines)

**Analyzes**:
- Commit type distribution (feat/fix/chore/docs)
- Scope clustering (system/hooks/lib)
- Temporal patterns (peak hours/days)
- File hotspots (high-churn files)
- Semantic themes (protocol, memory, hook mentions)
- Feature evolution timeline
- Quality gate adoption
- Impact scoring

**Output**: 10-section analysis covering 100 commits in <5s

---

### 2. **SessionStart Hook: Context Injector**
**File**: `scratch/git_semantic_injector_hook.py` (195 lines)

**Injects at session start**:
- Recent feature work (last 5 feat commits)
- High-churn files (≥5 changes in 7 days)
- Quality gate usage trends
- Dominant themes
- Actionable recommendations

**Overhead**: <1s per session

**Sample Output**:
```
🧠 GIT SEMANTIC CONTEXT (Last 7 days, 30 commits):

Recent Feature Work:
  • [d13fa6a] (system) Complete parallel execution (today)

⚠️ High-Churn Files (≥5 changes):
  • session_state.json (23x) → Consider stabilizing

🛡️ Quality Gate Usage:
  ✅ audit.py: 9 mentions
  ⚠️ drift.py: Not used recently

💡 Recommendations:
  • Run drift_check.py (not seen in recent commits)
  • High file churn detected - consider refactoring
```

---

### 3. **Enhanced Commit Message Generator**
**File**: `scratch/enhanced_commit_message.py` (251 lines)

**Generates**:
- Auto-inferred commit type/scope
- Impact analysis (files, LOC, categories)
- Protocol cross-references
- Quality gate results (audit, void)
- Impact scoring

**Sample Output**:
```
feat(hooks): Add git semantic injection hook

Impact Analysis:
  Files changed: 3 (hooks: 2, memory: 1)
  Lines: +215 -0
  Impact score: 6
  Protocols affected: Synapse Protocol

Quality Gates:
  ✅ audit.py (0 critical issues)
  ✅ void.py (0 stubs)

Files Changed:
  • .claude/hooks/git_semantic_injector.py
  • .claude/settings.json

🤖 Generated with [Claude Code]
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Semantic Dimensions Extracted

### 1. **Commit Type Distribution** → Codebase Health
```
feat:  52.2% → Feature-driven
chore: 21.7% → High automation overhead
fix:    6.5% → Low bug density (quality gates working)
```

### 2. **File Hotspots** → Technical Debt Signals
```
session_state.json (23x) → High churn, needs stabilization
upkeep_log.md (25x) → Expected (auto-maintenance)
CLAUDE.md (14x) → Constitution actively evolving
```

### 3. **Temporal Patterns** → Work Rhythm
```
Peak hours: 20:00, 16:00, 19:00 → Late-night deep work
Peak days: Thursday, Saturday → Weekend experimentation
```

### 4. **Semantic Themes** → Cognitive Focus
```
memory (24x), hook (18x), protocol (15x), audit (9x)
```

### 5. **Quality Gate Adoption** → Process Maturity
```
audit: 9 mentions → High adoption
void: 5 mentions → Moderate adoption
drift: 0 mentions → Under-utilized
```

### 6. **Feature Evolution** → Protocol Timeline
```
2025-11-20: 10 protocols added (scaffolding phase)
2025-11-22: Epistemology refinement (3 commits)
2025-11-23: Hook system stabilization
```

### 7. **Impact Scoring** → Commit Significance
```
Impact = file_count × (1 + category_count)

d13fa6a: 32 files, 8 categories = 288 (architectural change)
09cce9b: 16 files, 5 categories = 96 (major feature)
```

---

## Integration Roadmap

### Phase 1: Immediate (This Session) ✅
1. ✅ Create semantic analysis engine
2. ✅ Create SessionStart hook
3. ✅ Create enhanced commit generator
4. **NEXT: Install SessionStart hook** (5 minutes)

### Phase 2: Auto-Commit Enhancement (Next Session)
5. Integrate enhanced messages into auto-commit
6. Add commit body templates
7. Promote git_analyze.py to scripts/ops/

### Phase 3: Trauma Ledger (Strategic)
8. Create `.claude/memory/commit_trauma.jsonl`
9. Parse git history for fix/revert commits
10. Integrate trauma recall with Synapse Protocol

### Phase 4: Advanced Tools
11. `git_semantic_diff.py` - Compare semantic state across ranges
12. `git_protocol_timeline.py` - Visualize protocol maturity
13. `git_dependency_graph.py` - Commit relationship visualization

---

## Value Proposition

### Before (Baseline)
- ❌ No historical context at session start
- ❌ Generic auto-commit messages ("chore: Update 3 files")
- ❌ Claude repeats past mistakes (no trauma recall)
- ❌ File hotspots invisible until crisis
- ❌ Protocol evolution not tracked

### After (Target)
- ✅ Rich context injection every session start
- ✅ Semantic commit messages with impact analysis
- ✅ Trauma recall prevents repeated failures
- ✅ File churn warnings trigger proactive refactoring
- ✅ Protocol maturity tracked quantitatively

---

## Technical Specifications

### Dependencies
- **Zero new dependencies** (stdlib only: subprocess, json, re, collections)
- Git 2.0+ required
- Python 3.7+

### Performance
- SessionStart hook: <1s (analyzes 30 commits)
- Commit message generation: <3s (includes audit + void)
- Full semantic analysis: <5s (100 commits)

### Failure Modes
- Git unavailable: Silent fallback (empty context)
- Timeout: Partial results returned
- Quality gates fail: Warning in message (not blocking)

### Storage
- **No persistent storage needed** (git is the database)
- Optional: `.claude/memory/commit_trauma.jsonl` (append-only JSONL)
- Analysis results: Ephemeral (regenerated on-demand)

---

## Philosophical Alignment

This approach embodies Whitebox principles:

1. **Code is Truth**: Git commits = executed decisions, not aspirational docs
2. **Self-Documenting Systems**: Commit history auto-generates context
3. **Evidence-Based**: Semantic analysis > manual documentation
4. **Anti-Bloat**: Zero dependencies, leverage existing git
5. **Automation First**: Hooks inject context automatically
6. **Ground in Reality**: Trauma recall prevents hallucinated improvements

---

## Example: Full Workflow

### **User**: "Make hooks run in parallel"

### **Without Git Semantic Grounding**:
```
Claude: [Implements parallel hooks]
         [Causes race condition]
         [Bug reported]
         [Claude fixes]
         [Generic commit: "chore: Update 3 files"]
```

### **With Git Semantic Grounding**:
```
Session starts:
🧠 GIT SEMANTIC CONTEXT:
⚠️ High-Churn Files:
  • session_state.json (23x)

Claude: I notice session_state.json has 23 changes in 7 days.
         Let me check if we've attempted parallel hooks before...

         ⚠️ TRAUMA RECALL: def456 (2 days ago)
         "fix: Revert parallel hooks" - race conditions in session_state.json

         Proposed safe approach:
         1. Sequential dispatch (no races)
         2. Parallel operations WITHIN each hook
         3. Add state locking

         This avoids the def456 failure mode.

[Implements safe version]
[Auto-commit with rich message:]

feat(hooks): Add safe parallel hook execution

Impact Analysis:
  Files changed: 4 (hooks: 2, lib: 1, tests: 1)
  Impact score: 8
  Related commits: def456 (previous parallel attempt)

Quality Gates:
  ✅ audit.py (0 issues)
  ✅ void.py (0 stubs)

Decision Rationale:
  Sequential dispatch + parallel internals avoids def456 race condition.
```

---

## ROI Calculation

### Development Time
- **Build**: 2 hours (3 tools × 200 LOC each)
- **Integration**: 30 minutes (install hooks, test)
- **Total**: 2.5 hours

### Value Generated
- **Context injection**: Saves 10+ minutes per session (explaining history)
- **Trauma recall**: Prevents 1-2 hours per repeated mistake
- **Rich commits**: +5 minutes understanding per commit × 100 commits = 500 minutes
- **File hotspot warnings**: Prevents 4+ hours of technical debt crisis

**Total Value**: 15+ hours saved in first month

**ROI**: 6x return on investment

---

## Immediate Action

**Install SessionStart hook now**:

```bash
# 1. Copy hook to production
cp scratch/git_semantic_injector_hook.py \
   .claude/hooks/git_semantic_injector.py

chmod +x .claude/hooks/git_semantic_injector.py

# 2. Update .claude/settings.json
# Add to "SessionStart" hook array:
{
  "hooks": {
    "SessionStart": [
      ".claude/hooks/git_semantic_injector.py"
    ]
  }
}

# 3. Test by restarting session
# Expected: Rich context appears at session start
```

---

## Files Created

### Scratch Directory (Prototypes)
- `scratch/analyze_commit_semantics.py` (219 lines)
- `scratch/git_semantic_injector_hook.py` (195 lines)
- `scratch/enhanced_commit_message.py` (251 lines)
- `scratch/git_semantic_grounding_strategy.md` (586 lines)
- `scratch/git_semantic_implementation_plan.md` (512 lines)
- `scratch/GIT_SEMANTIC_GROUNDING_SUMMARY.md` (THIS FILE)

**Total**: 1,763 lines of implementation + documentation

---

## Success Criteria

### Phase 1 Complete When:
- ✅ SessionStart hook fires and injects context
- ✅ Context includes recent features, hotspots, quality trends
- ✅ Hook completes in <1s
- ✅ No false positives in recommendations

### Phase 2 Complete When:
- ✅ Auto-commit uses enhanced messages
- ✅ Commit bodies include impact analysis
- ✅ Protocol cross-references detected automatically
- ✅ Quality gates results embedded in commits

### Phase 3 Complete When:
- ✅ Commit trauma ledger populated
- ✅ Synapse Protocol triggers trauma recall
- ✅ Claude avoids repeating documented failures
- ✅ User observes reduced rework cycles

---

## Conclusion

Git commit history is **the truth** about codebase evolution. By extracting semantic value from commits, we:

1. **Ground Claude in reality** (actual execution history)
2. **Provide temporal awareness** (what happened when)
3. **Enable trauma recall** (avoid past mistakes)
4. **Track system maturity** (protocol evolution)
5. **Generate rich documentation** (self-documenting commits)

This is **context injection at scale**: 600 lines of code → infinite historical awareness.

**Next Step**: Install SessionStart hook and validate context injection.
