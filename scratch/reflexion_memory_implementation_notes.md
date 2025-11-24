# Reflexion Memory Implementation Notes

## Implementation Complete

### Components Created

1. **detect_failure_auto_learn.py** (.claude/hooks/)
   - PostToolUse hook
   - Detects: verify.py failures, bash errors, Edit rejections, agent failures
   - Action: Auto-adds to lessons.md with [AUTO-LEARNED-FAILURE] tag

2. **detect_success_auto_learn.py** (.claude/hooks/)
   - PostToolUse hook
   - Detects: verify success after 2+ failures, novel scratch scripts, successful agent delegations
   - Action: Auto-adds to lessons.md with [AUTO-LEARNED-SUCCESS] tag
   - Tracks state in session_unknown_state.json

3. **consolidate_lessons.py** (scripts/ops/)
   - Merges duplicate auto-learned patterns
   - Removes tags from single entries (promotes to permanent)
   - Merges duplicates with count: "(occurred N times)"
   - Integrated into upkeep.py (runs before commits)

4. **Updated upkeep.py**
   - Added consolidate_lessons() function
   - Integrated into main workflow (step 5 of 6)

5. **Updated settings.json**
   - Registered both hooks in PostToolUse section

6. **Updated council_engine.py**
   - Replaced grep with ripgrep (rg) for faster code search
   - Uses --glob instead of --include patterns

## Activation

**IMPORTANT:** Hooks require Claude Code restart to activate.

Settings.json changes are loaded at startup, not runtime. The new PostToolUse hooks will start firing after restart.

## Testing

Manual testing requires restart. Created test_reflexion_memory.py but it won't work until hooks are active (subprocess calls don't trigger Claude Code hooks).

After restart, test by:
1. Running verify.py with failure → Check lessons.md for [AUTO-LEARNED-FAILURE]
2. Fail verify 2x, then succeed → Check for [AUTO-LEARNED-SUCCESS]
3. Run upkeep.py → Check consolidation output

## Expected Behavior

### Failure Detection
```bash
# This bash command fails
python3 scripts/ops/verify.py file_exists /nonexistent.txt

# Hook detects exit code 1 + "verify.py" in command
# Auto-adds to lessons.md:
### 2025-11-22 21:30
[AUTO-LEARNED-FAILURE] Verification failed: file_exists check for '/nonexistent.txt' returned false
```

### Success Detection
```bash
# Fail twice
python3 scripts/ops/verify.py file_exists /tmp/test.txt  # Fail 1
python3 scripts/ops/verify.py file_exists /tmp/test.txt  # Fail 2

# Succeed once
touch /tmp/test.txt
python3 scripts/ops/verify.py file_exists /tmp/test.txt  # Success!

# Hook detects: exit code 0 + 2 previous failures in session state
# Auto-adds:
### 2025-11-22 21:31
[AUTO-LEARNED-SUCCESS] Verify success after 2 failures: file_exists /tmp/test.txt
```

### Consolidation
```bash
# Before upkeep.py:
### 2025-11-22 21:30
[AUTO-LEARNED-FAILURE] Verification failed: file_exists check for 'foo.txt'
### 2025-11-22 21:31
[AUTO-LEARNED-FAILURE] Verification failed: file_exists check for 'foo.txt'
### 2025-11-22 21:32
[AUTO-LEARNED-FAILURE] Verification failed: file_exists check for 'foo.txt'

# After consolidate_lessons.py:
### 2025-11-22 21:30
Verification failed: file_exists check for 'foo.txt' (occurred 3 times)
```

## ROI Metrics (Target)

After 7 days of operation:
- **30% reduction** in repeated errors (same failure pattern within 7 days)
- **50% increase** in lessons.md entries (from ~3/month to ~5/month)
- **Zero manual** `remember.py add` commands needed
- **Auto-consolidation** prevents lessons.md bloat

## Integration Points

1. **PostToolUse hooks** → Continuous learning during session
2. **upkeep.py** → Consolidation before commits
3. **synapse_fire.py** → Recalls auto-learned lessons via spark.py
4. **session state** → Tracks failure counts for success detection

## Known Limitations

1. Only works for tool invocations via Claude Code (not subprocess calls)
2. Session state resets between sessions (failure counts don't persist)
3. Consolidation is regex-based (may miss complex patterns)
4. Large error outputs (>200 chars) are excluded to avoid noise

## Future Enhancements (Deferred)

1. Persistent failure tracking across sessions (SQLite?)
2. ML-based pattern detection (instead of regex)
3. Confidence boost for applying auto-learned lessons
4. Auto-suggest fixes based on similar past failures

## File Locations

- Hooks: `.claude/hooks/detect_*_auto_learn.py`
- Script: `scripts/ops/consolidate_lessons.py`
- State: `.claude/memory/session_unknown_state.json`
- Output: `.claude/memory/lessons.md`
- Integration: `scripts/ops/upkeep.py`
- Config: `.claude/settings.json`

## Comparison to Claude-Flow

Claude-Flow: Reflexion memory with neural pattern recognition, SQLite persistence
Our approach: File-based with regex patterns, git-trackable

**Advantages:**
- Simple (no DB dependency)
- Transparent (markdown = readable)
- Git-trackable (version control for lessons)
- Low overhead (no embedding computation)

**Trade-offs:**
- No semantic similarity matching
- Session state doesn't persist across restarts
- Consolidation is regex-based (not ML)

**Verdict:** Perfect for whitebox philosophy. Can upgrade to SQLite later if file-based becomes bottleneck.
