# Git Semantic Grounding: Recommendations

## Executive Decision

**Install the SessionStart hook immediately.** Here's why:

### Risk Assessment
- **Effort**: 5 minutes (copy file, update settings.json)
- **Risk**: Near-zero (silent fallback on failure, <1s overhead)
- **Reversibility**: 100% (remove from settings.json)
- **Dependencies**: Zero (stdlib only, git already present)

### Value Assessment
- **Immediate**: Context injection at every session start
- **Compounding**: Trauma recall prevents repeated mistakes
- **Strategic**: Foundation for Phase 2 (enhanced commits) and Phase 3 (trauma ledger)

**Verdict**: No-brainer. High value, zero risk, trivial effort.

---

## Installation Instructions

### Step 1: Copy Hook to Production (1 minute)
```bash
cp scratch/git_semantic_injector_hook.py \
   .claude/hooks/git_semantic_injector.py

chmod +x .claude/hooks/git_semantic_injector.py
```

### Step 2: Register Hook in Settings (2 minutes)
Edit `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      ".claude/hooks/startup.py",
      ".claude/hooks/git_semantic_injector.py"  // ADD THIS LINE
    ],
    // ... other hooks
  }
}
```

### Step 3: Test (2 minutes)
```bash
# Test hook manually
python3 .claude/hooks/git_semantic_injector.py

# Expected output: JSON with "additionalContext" field
# Should complete in <1s
```

### Step 4: Validate (Next Session)
Restart Claude Code session. You should see:
```
🧠 GIT SEMANTIC CONTEXT (Last 7 days, N commits):
[Context appears here]
```

---

## Phase 2 Preparation (Optional, Later)

If Phase 1 validation succeeds, prepare for Phase 2:

### 1. Promote Analysis Tool to Production
```bash
cp scratch/analyze_commit_semantics.py scripts/ops/git_analyze.py
chmod +x scripts/ops/git_analyze.py

# Update .claude/skills/tool_index.md
# Add: git_analyze: Semantic analysis of commit history
```

### 2. Create Slash Command (Optional)
```bash
# Create .claude/commands/git-analyze.md
echo 'Run semantic analysis on commit history: `python3 scripts/ops/git_analyze.py`' \
  > .claude/commands/git-analyze.md
```

### 3. Integrate Enhanced Commits (Future Session)
Modify `.claude/hooks/auto_commit_on_complete.py` to use enhanced message generation.

---

## Alternative Approaches Considered

### Option A: Manual Analysis Only
**Pros**: Zero integration risk
**Cons**: Requires manual invocation, no automatic context

**Verdict**: Rejected. Automation is core to Whitebox philosophy.

### Option B: Pre-Commit Hook Only
**Pros**: Enriches commit messages immediately
**Cons**: No session-start context, misses trauma recall value

**Verdict**: Partial solution. Do Phase 1 first, then Phase 2.

### Option C: Full Integration (All Phases at Once)
**Pros**: Maximum value immediately
**Cons**: Higher risk, harder to debug, longer validation cycle

**Verdict**: Too aggressive. Incremental rollout preferred.

### Option D: SessionStart + Enhanced Commits (Phases 1-2)
**Pros**: Balanced risk/reward, incremental validation
**Cons**: Misses trauma ledger (Phase 3)

**Verdict**: **RECOMMENDED**. This is the pragmatic path.

---

## Risk Mitigation

### Failure Mode 1: Hook Crashes
**Symptom**: Session start delayed or fails
**Mitigation**: Hook has try/except wrapper, returns empty context on error
**Recovery**: Remove from settings.json

### Failure Mode 2: Slow Execution
**Symptom**: Session start takes >5s
**Mitigation**: Timeout set to 5s, partial results returned
**Tuning**: Reduce commit limit (currently 30, can lower to 10)

### Failure Mode 3: False Positives
**Symptom**: Hook warns about non-issues (e.g., "drift not used" when it's intentional)
**Mitigation**: Thresholds are tunable (currently ≥5 changes = hotspot)
**Recovery**: Adjust thresholds in hook code

### Failure Mode 4: Git Unavailable
**Symptom**: Hook fails in non-git directory
**Mitigation**: Subprocess calls have timeout, silent fallback
**Recovery**: Automatic (empty context returned)

---

## Performance Tuning

### If Hook is Too Slow (>2s)
**Option 1**: Reduce commit limit
```python
# In git_semantic_injector.py, line 15
commits = get_recent_commits(days=7, limit=30)
# Change to: limit=10
```

**Option 2**: Reduce analysis scope
```python
# Skip file hotspot analysis (most expensive)
# Comment out: hotspots = analyze_file_hotspots(commits)
```

**Option 3**: Cache results (aggressive)
```python
# Store results in .claude/memory/git_semantic_cache.json
# Regenerate every N commits (e.g., 5)
```

### If Hook Output is Too Verbose
**Option 1**: Reduce feature count
```python
# In extract_feature_work(), line 73
return features[:5]  # Change to: features[:3]
```

**Option 2**: Skip recommendations section
```python
# Comment out lines 100-107 (Recommendations section)
```

---

## Monitoring & Validation

### After Installation, Monitor:

#### 1. Session Start Time
- **Baseline**: Current session start time (typically <2s)
- **Target**: +1s overhead maximum
- **Red flag**: >3s total

#### 2. Context Quality
- **Check**: Are features recent? (≤7 days)
- **Check**: Are hotspots real? (≥5 changes is meaningful)
- **Check**: Are recommendations actionable?

#### 3. False Positives
- **Check**: Does it warn about drift when drift is fine?
- **Check**: Does it flag expected high-churn files (like upkeep_log.md)?
- **Action**: Tune thresholds or add ignore list

#### 4. User Perception
- **Ask**: Does context feel valuable or noisy?
- **Ask**: Did it prevent a repeated mistake?
- **Ask**: Did it surface a hotspot you didn't know about?

---

## Success Stories to Watch For

### Story 1: Trauma Recall
**Scenario**: User requests feature previously attempted and reverted
**Expected**: Hook shows recent revert in "Recent Feature Work"
**Value**: Claude says "We tried this before and reverted it. Here's why..."

### Story 2: Hotspot Detection
**Scenario**: File with 15+ changes in 7 days appears in warning
**Expected**: Hook flags it in "High-Churn Files"
**Value**: Triggers refactoring discussion before crisis

### Story 3: Quality Gate Reminder
**Scenario**: drift.py hasn't been run in 30 commits
**Expected**: Hook shows "⚠️ drift.py: Not used recently"
**Value**: Triggers periodic quality check

### Story 4: Theme Awareness
**Scenario**: Recent commits focus on "memory" and "protocol"
**Expected**: Hook shows themes in "Dominant Themes"
**Value**: Claude understands current architectural focus

---

## Long-Term Vision

### Phase 3: Trauma Ledger (Month 2)
Once Phase 1 is validated, build commit trauma database:

**Use Cases**:
- User: "Implement parallel hooks"
- Claude: "⚠️ TRAUMA: def456 (reverted due to race conditions)"

**Implementation**:
```bash
# Parse git log for fix/revert commits
git log --grep="fix:" --grep="revert:" --format="%H|%s|%b" \
  > .claude/memory/commit_trauma_raw.txt

# Process with NLP to extract lessons
python3 scripts/ops/build_trauma_ledger.py
```

### Phase 4: Semantic Diff (Month 3)
Compare semantic state across ranges:

```bash
python3 scripts/ops/git_semantic_diff.py HEAD~20..HEAD

# Output:
# Protocol count: 15 → 18 (+3)
# Hook count: 12 → 15 (+3)
# Quality gate usage: 60% → 85% (+25%)
```

**Use Case**: Quantify system maturity over time

### Phase 5: Protocol Timeline (Month 4)
Visualize protocol evolution:

```bash
python3 scripts/ops/git_protocol_timeline.py

# Output: ASCII timeline of protocol additions
# 2025-11-20: Oracle, Research, Epistemology
# 2025-11-22: Synapse, Judge, Critic
# 2025-11-23: Git Semantic (YOU ARE HERE)
```

**Use Case**: Celebrate milestones, track velocity

---

## Decision Matrix

| Factor | Weight | SessionStart Hook | Manual Tool Only | Full Integration |
|--------|--------|-------------------|------------------|------------------|
| **Effort** | 0.2 | 9/10 (5 min) | 10/10 (0 min) | 3/10 (2 hours) |
| **Risk** | 0.3 | 9/10 (near-zero) | 10/10 (zero) | 6/10 (moderate) |
| **Value** | 0.4 | 8/10 (high) | 4/10 (low) | 10/10 (maximum) |
| **Reversibility** | 0.1 | 10/10 (instant) | 10/10 (N/A) | 7/10 (moderate) |
| **TOTAL** | | **8.7/10** | 6.8/10 | 7.0/10 |

**Winner**: SessionStart Hook (Phase 1)

---

## Final Recommendation

**Install the SessionStart hook now.**

```bash
# 30-second install:
cp scratch/git_semantic_injector_hook.py .claude/hooks/git_semantic_injector.py
chmod +x .claude/hooks/git_semantic_injector.py

# Edit .claude/settings.json, add to SessionStart array

# Test:
python3 .claude/hooks/git_semantic_injector.py

# Restart session to validate
```

**Then**:
- Use for 3-5 sessions
- Observe context quality
- Tune thresholds if needed
- Proceed to Phase 2 if successful

**Why now?**
- Zero risk, high value
- Foundation for trauma recall (strategic value)
- Aligns with auto-commit system (synergistic)
- Demonstrates Whitebox philosophy (code is truth)

**Why not?**
- [No valid reasons identified]

---

## Appendix: Tunable Parameters

```python
# In git_semantic_injector_hook.py

# Line 15: How far back to look
commits = get_recent_commits(days=7, limit=30)
# Tune: days=3 (faster), days=14 (more context)
# Tune: limit=10 (faster), limit=50 (more complete)

# Line 41: Hotspot threshold
high_churn = [f for f, count in hotspots if count >= 5]
# Tune: count >= 3 (more sensitive), count >= 10 (less noisy)

# Line 73: Feature count
return features[:5]
# Tune: features[:3] (less verbose), features[:10] (more complete)
```

**Recommendation**: Start with defaults, tune after 5 sessions if needed.
