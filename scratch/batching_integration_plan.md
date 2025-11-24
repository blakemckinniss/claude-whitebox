# Native Tool Batching Enforcement Strategy

## Problem Statement

Claude Code frequently executes tools sequentially when parallel execution would be:
1. **Faster** (10x+ for I/O-bound operations)
2. **More token-efficient** (no context pollution from intermediate responses)
3. **More deterministic** (atomic operation vs multi-turn state management)

## Current State

### What Works ✅
- `detect_sequential_agents.py` - Blocks sequential agent delegation
- `detect_batch.py` - Warns about batch operations in user prompts
- `parallel.py` library - Provides batching utilities for scripts
- `meta_cognition_performance.py` - Reminds about parallel patterns

### What's Missing ❌
- **No enforcement for native tool batching** (Read, Grep, Glob, WebFetch)
- Sequential Read calls are common and inefficient
- No automatic detection of batchable tool patterns
- No context-aware suggestions

## Enforcement Architecture

### Three-Layer Strategy

#### Layer 1: Detection Hook (PreToolUse)
**File:** `.claude/hooks/native_batching_enforcer.py`

**Purpose:** Detect and block sequential tool usage patterns

**Enforcement Rules:**
1. **Read Tool** - HARD BLOCK if >1 Read in same turn (unless dependency exists)
2. **Grep Tool** - SOFT WARNING if >2 Grep in same turn
3. **Glob Tool** - SOFT WARNING if >2 Glob in same turn
4. **WebFetch/WebSearch** - HARD BLOCK if >1 in same turn
5. **Write/Edit** - No enforcement (dependency chains are common)

**Bypass Mechanism:**
- User can say "SEQUENTIAL" in prompt to disable check for that turn
- Legitimate use cases: path depends on previous read, conditional logic

#### Layer 2: Pattern Analysis (UserPromptSubmit)
**File:** `.claude/hooks/batching_analyzer.py`

**Purpose:** Analyze user intent and inject batching guidance

**Detection Patterns:**
- "read these files" + file list → Suggest parallel Read
- "search for X, Y, Z" → Suggest parallel Grep
- "fetch docs from A, B, C" → Suggest parallel WebFetch
- "check 10 files" → Suggest parallel.py script

**Output:** Inject context reminder before Claude starts executing

#### Layer 3: Telemetry & Learning (PostToolUse)
**File:** `.claude/hooks/batching_telemetry.py`

**Purpose:** Track batching compliance and report efficiency gains

**Metrics:**
- Sequential vs Parallel ratio per session
- Average tools per response message
- Estimated time savings from parallel execution
- Pattern violations per session

**Dashboard:** `.claude/memory/batching_metrics.json`

## Integration Steps

### Step 1: Install Detection Hook
```bash
# Add to settings.json PreToolUse section
{
  "matcher": "(Read|Grep|Glob|WebFetch|WebSearch)",
  "hooks": [
    {
      "type": "command",
      "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/native_batching_enforcer.py"
    }
  ]
}
```

### Step 2: Install Analysis Hook
```bash
# Add to settings.json UserPromptSubmit section
{
  "type": "command",
  "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/batching_analyzer.py"
}
```

### Step 3: Install Telemetry Hook
```bash
# Add to settings.json PostToolUse section
{
  "type": "command",
  "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/batching_telemetry.py"
}
```

### Step 4: Update CLAUDE.md
Add batching rules to Hard Blocks section:
```markdown
11. **Native Tool Batching:** When executing 2+ Read/Grep/Glob/WebFetch operations,
    you MUST use parallel invocation (single message, multiple tool calls).
    Sequential calls will be BLOCKED unless "SEQUENTIAL" keyword present.
```

## Smart Batching Logic

### When to Batch (Parallel)
✅ Independent file reads
✅ Multiple search patterns across same/different files
✅ Multiple web fetches for documentation
✅ Exploratory code analysis (read 5 related files)
✅ Validation checks (verify 10 files exist)

### When NOT to Batch (Sequential OK)
❌ Path of file2 depends on content of file1
❌ Conditional reads (if A exists, read B, else read C)
❌ Iterative refinement (grep for X, analyze results, grep for Y)
❌ Token budget constraint (reading 100 files would exceed context)

### Context-Aware Batching

**Smart Limits:**
- Max 10 Read calls per batch (context limit)
- Max 5 WebFetch calls per batch (API rate limits)
- Max 20 Grep calls per batch (result readability)

**Progressive Enhancement:**
```python
# Phase 1: If user asks "read files A, B, C"
# → Batch all 3 reads in one message

# Phase 2: If user asks "analyze entire src/ directory"
# → Use Task agent with Explore subagent (separate context)
# → Don't batch 100 reads in main context

# Phase 3: If user asks "validate 1000 files"
# → Write scratch script with parallel.py
# → Don't use native tools at all
```

## Expected Impact

### Performance Gains
- **Sequential Read (3 files):** 3 turns × 2s = 6 seconds
- **Parallel Read (3 files):** 1 turn × 2s = 2 seconds
- **Speedup:** 3x faster

### Token Efficiency
- **Sequential:** Full response after each read (200 tokens × 3 = 600 tokens wasted)
- **Parallel:** Single response after all reads (200 tokens)
- **Savings:** 400 tokens per batch

### User Experience
- Fewer back-and-forth turns
- Faster responses
- More deterministic behavior
- Less "thinking out loud" between reads

## Rollout Plan

### Phase 1: Soft Launch (This Session)
- Install detection hook with warnings only (no blocking)
- Collect telemetry for 5 sessions
- Tune thresholds and bypass logic

### Phase 2: Hard Enforcement (Next Sprint)
- Enable hard blocks for Read/WebFetch
- Keep soft warnings for Grep/Glob
- Monitor false positive rate

### Phase 3: Auto-Optimization (Future)
- Hook automatically rewrites sequential tool calls to parallel
- "Did you mean to batch these reads?" with auto-fix
- Machine learning to detect legitimate sequential patterns

## Success Metrics

### Quantitative
- 80%+ of multi-file operations use parallel invocation
- Average tools per message increases from 1.2 to 2.5
- Session turn count decreases by 20%

### Qualitative
- No user complaints about over-aggressive blocking
- Claude develops "muscle memory" for parallel patterns
- Natural language prompts consistently trigger batching

## Open Questions

1. **Should we auto-rewrite?** Instead of blocking, should hook rewrite sequential calls to parallel?
   - Pro: Zero user friction, immediate compliance
   - Con: Might hide legitimate sequential intent

2. **Confidence penalty?** Should sequential tool use decrease confidence score?
   - Pro: Reinforces correct behavior
   - Con: Might be too punitive for edge cases

3. **Cross-tool batching?** Should we suggest batching different tools together?
   - Example: Read file + Grep for pattern in same message
   - Pro: Even better performance
   - Con: More complex coordination

4. **Token budget awareness?** Should hook prevent batching if context limit would be exceeded?
   - Pro: Prevents context overflow
   - Con: Requires parsing file sizes before read

## Related Protocols

- **Performance Protocol** (§ CLAUDE.md): Batch processing rules
- **Epistemological Protocol** (§ CLAUDE.md): Evidence gathering efficiency
- **Parallel Execution** (scripts/lib/parallel.py): Script-level batching
- **Agent Delegation** (detect_sequential_agents.py): Multi-agent batching

## Next Steps

1. ✅ Create `native_batching_enforcer.py` hook
2. ⏳ Create `batching_analyzer.py` hook (pattern detection)
3. ⏳ Create `batching_telemetry.py` hook (metrics)
4. ⏳ Update `.claude/settings.json` with all 3 hooks
5. ⏳ Update `CLAUDE.md` with batching rules
6. ⏳ Test with 5 real-world scenarios
7. ⏳ Tune thresholds based on telemetry
8. ⏳ Add to next sprint documentation
