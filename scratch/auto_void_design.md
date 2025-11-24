# Auto-Void Stop Hook Design

## Purpose
Automatically run void.py completeness checks on modified files during Stop lifecycle when confidence is below threshold.

## Philosophy
- You find yourself manually requesting void checks after almost every task completion
- This is a perfect candidate for automation via Stop hook
- Enforcement should be graduated based on confidence tier

## Architecture

### Input (Stop Hook Context)
```json
{
  "sessionId": "abc123",
  "transcriptPath": "/path/to/transcript.jsonl",
  "cwd": "/project/root"
}
```

### Detection Logic

1. **Parse Transcript** - Extract last assistant response
2. **Find Modified Files** - Parse tool use for Write/Edit operations on .py files
3. **Filter Target Files** - Only production zones (scripts/ops/, scripts/lib/, .claude/hooks/)
4. **Check Confidence** - Load session state, get current confidence
5. **Apply Policy** - Run void.py based on confidence tier

### Confidence-Based Policy

| Tier | Confidence | Policy |
|------|-----------|--------|
| IGNORANCE | 0-30% | No action (can't write anyway) |
| HYPOTHESIS | 31-50% | No action (scratch only) |
| WORKING | 51-70% | No action (scratch only) |
| CERTAINTY | 71-85% | **MANDATORY** void check (print results, warn on failures) |
| TRUSTED | 86-94% | OPTIONAL void check (silent unless failures) |
| EXPERT | 95-100% | No action (trusted) |

**Rationale:**
- At CERTAINTY tier (71-85%), you're doing production work but still need quality gates
- At TRUSTED tier (86-94%), you've proven yourself but void is still useful
- At EXPERT tier (95-100%), quality gates are informational only

### Implementation Details

1. **File Tracking**
   - Parse transcript for Write/Edit tool uses
   - Extract file_path from tool parameters
   - Filter: *.py files in production zones only
   - Deduplicate: Same file modified multiple times = one check

2. **Void Execution**
   - Run: `python3 scripts/ops/void.py <file> --stub-only`
   - Use --stub-only to avoid Oracle API costs at Stop
   - Capture exit code (0 = clean, 1 = stubs found)
   - Parse stdout for stub counts

3. **Output Format**
   ```
   🔍 Auto-Void Check (CERTAINTY tier):

   ✅ scripts/ops/foo.py - Clean
   ⚠️  scripts/lib/bar.py - 3 stub(s) detected
       Line 42: TODO comment
       Line 89: Function stub (pass)
       Line 120: NotImplementedError

   💡 Tip: Run void.py with full Oracle analysis for deeper inspection
   ```

4. **Exit Behavior**
   - ALWAYS exit 0 (Stop hooks don't block)
   - Warnings only, no hard blocks
   - Inform user but don't prevent session end

### Edge Cases

1. **No Python Files Modified** - Silent exit
2. **Only Scratch Files Modified** - Silent exit
3. **Void.py Missing** - Silent exit (graceful degradation)
4. **Session State Missing** - Default to CERTAINTY policy (safe)
5. **Multiple Files** - Run void on each, aggregate results
6. **Void Execution Failure** - Log error, continue (don't break Stop)

## Testing Strategy

1. **Unit Tests** (scratch/test_auto_void.py)
   - Transcript parsing
   - File extraction
   - Confidence tier detection
   - Policy application

2. **Integration Tests**
   - Mock Write operation with stubs → verify void runs
   - Mock Write operation clean → verify no warnings
   - Mock Edit scratch file → verify no void run
   - Different confidence tiers → verify policy enforcement

## Files to Create

1. `.claude/hooks/auto_void.py` - Stop hook implementation
2. `scratch/test_auto_void.py` - Test suite
3. Register in `.claude/settings.json` under Stop hooks

## Success Criteria

- ✅ Hook registered and runs on Stop
- ✅ Correctly identifies production Python files
- ✅ Respects confidence tier policy
- ✅ Provides actionable warnings
- ✅ Doesn't block session end
- ✅ Gracefully handles errors
- ✅ Tests pass
