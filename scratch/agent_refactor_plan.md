# Agent Refactor Plan: From Vestige to Value

## The Core Problem

**Agents exist but aren't used because:**
1. No automatic invocation (LLM forgets)
2. Scripts provide same functionality (easier to call directly)
3. No exclusive capabilities (agents = glorified script wrappers)
4. Unclear triggers ("use proactively" is too vague)

## Solution: Three-Tier Agent Strategy

### Tier 1: AUTO-INVOKED Agents (Context Firewall)
**Problem:** Large outputs pollute main context
**Solution:** PostToolUse hook auto-spawns agent when output >threshold

**KEEP: researcher**
- **Auto-trigger:** Bash output >1000 chars from research.py/probe.py/xray.py
- **Unique capability:** Auto-compression (500 lines → 50 words summary)
- **Hook:** `auto_researcher.py` (PostToolUse)
- **Value:** Prevents context pollution automatically

```python
# .claude/hooks/auto_researcher.py (PostToolUse)
if tool_name == "Bash":
    if "research.py" in command or "probe.py" in command:
        output_size = len(result.get('output', ''))
        if output_size > 1000:
            # Auto-spawn researcher agent to compress
            return {
                "suggestion": "Output is large ({}chars). Auto-spawning researcher agent for compression...".format(output_size)
            }
```

### Tier 2: TOOL-SCOPED Agents (Capability Restriction)
**Problem:** Main assistant has too much power, causes errors
**Solution:** Hard-block main assistant, force delegation to scoped agent

**KEEP: sherlock (read-only debugger)**
- **Auto-trigger:** Detect gaslighting loop (user says "still broken" after "fixed" claim)
- **Unique capability:** CANNOT modify code (only Read, Bash, Glob, Grep)
- **Hook:** `detect_gaslight.py` (already exists) + hard block Write/Edit
- **Value:** Prevents modification loops during debugging

**KEEP: script-smith (write-only coder)**
- **Auto-trigger:** User asks to "write" or "create" script
- **Unique capability:** ONLY agent that can Write to scripts/ directory
- **Hook:** `block_main_write.py` (PreToolUse) - block main assistant Write to scripts/
- **Value:** Forces quality gates (audit/void/drift) automatically

```python
# .claude/hooks/block_main_write.py (PreToolUse)
if tool_name == "Write":
    file_path = params.get('file_path', '')
    if file_path.startswith('scripts/'):
        return {
            "allow": False,
            "message": "Production code must go through script-smith agent (quality gates required). Spawning script-smith..."
        }
```

### Tier 3: MINDSET Agents (Behavioral Framing)
**Problem:** Main assistant has bad habits (install instead of improvise)
**Solution:** Agent system prompt enforces mindset

**KEEP: macgyver (Living off the Land)**
- **Auto-trigger:** Tool failure or "pip install" detected
- **Unique capability:** Enforces "no install" constraint
- **Hook:** `detect_install.py` (PreToolUse) - block pip/npm/cargo install
- **Value:** Forces creative problem-solving

```python
# .claude/hooks/detect_install.py (PreToolUse)
if tool_name == "Bash":
    if re.search(r'(pip|npm|cargo|apt-get|brew)\s+install', command):
        return {
            "allow": False,
            "message": "Installing dependencies is banned. Spawning macgyver agent for improvisation..."
        }
```

### Tier 4: DELETE (No Unique Value)
**DELETE: council-advisor**
- Why: Just calls `council.py` - main assistant can do this
- Replacement: Main assistant runs `council.py` directly

**DELETE: critic**
- Why: Just calls `critic.py` + `skeptic.py` - main assistant can do this
- Replacement: Main assistant runs scripts directly

**DELETE: runner**
- Why: No unique value over main assistant Bash tool
- Replacement: Main assistant runs Bash directly

## Implementation Plan

### Phase 1: Add Auto-Invocation Hooks (Make Agents Automatic)
1. Create `auto_researcher.py` (PostToolUse) - auto-spawn on large outputs
2. Create `block_main_write.py` (PreToolUse) - force script-smith for scripts/
3. Create `detect_install.py` (PreToolUse) - force macgyver on install attempts
4. Update `detect_gaslight.py` - force sherlock on gaslighting loops

### Phase 2: Delete Redundant Agents
1. Delete `council-advisor.md`
2. Delete `critic.md`
3. Delete `runner.md`
4. Update CLAUDE.md references
5. Update epistemology.py reward bonuses

### Phase 3: Strengthen Remaining Agents
1. Update `researcher.md`:
   - Add "AUTO-INVOKED on large outputs >1000 chars"
   - Clarify compression capability

2. Update `sherlock.md`:
   - Add "AUTO-INVOKED on gaslighting detection"
   - Emphasize read-only tool scoping

3. Update `script-smith.md`:
   - Add "AUTO-INVOKED for scripts/ writes"
   - Emphasize quality gate enforcement

4. Update `macgyver.md`:
   - Add "AUTO-INVOKED on install attempts"
   - Emphasize no-install constraint

### Phase 4: Update Documentation
1. CLAUDE.md - Update agent list (7 → 4)
2. CLAUDE.md - Add "Auto-Invocation" section
3. CLAUDE.md - Add decision tree: "Agent vs Script"
4. Hook documentation - Document new auto-hooks

## Expected Outcomes

**Before Refactor:**
- 7 agents defined, rarely used
- Main assistant calls scripts directly
- No forcing function for agent usage
- Context pollution from large outputs

**After Refactor:**
- 4 agents, automatically invoked
- Auto-researcher prevents context pollution
- Script-smith enforces quality gates
- Sherlock prevents gaslighting loops
- MacGyver enforces improvisation mindset

**Key Metric:** Agent invocation frequency
- Before: ~0 per session (manual only)
- After: ~5-10 per session (automatic triggers)

## Decision Tree (Post-Refactor)

```
User action → Check triggers → Auto-invoke agent?

┌─ Large output (>1000 chars)
│  └─ Auto-spawn: researcher
│
┌─ Write to scripts/*
│  └─ Hard block → Force: script-smith
│
┌─ "Still broken" after "Fixed" claim
│  └─ Auto-spawn: sherlock
│
┌─ "pip install" detected
│  └─ Hard block → Force: macgyver
│
└─ All other cases
   └─ Main assistant (runs scripts directly)
```

## Validation Criteria

**An agent is worth keeping if it provides ONE of:**
1. ✅ Context isolation (researcher)
2. ✅ Tool scoping (sherlock read-only, script-smith write-only)
3. ✅ Mindset enforcement (macgyver no-install)
4. ✅ Automatic invocation trigger

**Delete if:**
- ❌ Just wraps a script with no added value
- ❌ No automatic trigger (requires manual invocation)
- ❌ No unique capability (main assistant can do same thing)

## Files to Modify

### Create:
- `.claude/hooks/auto_researcher.py` (PostToolUse)
- `.claude/hooks/block_main_write.py` (PreToolUse)
- `.claude/hooks/detect_install.py` (PreToolUse)

### Delete:
- `.claude/agents/council-advisor.md`
- `.claude/agents/critic.md`
- `.claude/agents/runner.md`

### Update:
- `.claude/agents/researcher.md` (add auto-invoke description)
- `.claude/agents/sherlock.md` (add auto-invoke description)
- `.claude/agents/script-smith.md` (add auto-invoke description)
- `.claude/agents/macgyver.md` (add auto-invoke description)
- `CLAUDE.md` (update agent list, add auto-invocation section)
- `scripts/lib/epistemology.py` (remove deleted agent bonuses)
- `.claude/settings.json` (register new hooks)

## Risk Assessment

**Low Risk:**
- Deleting council-advisor/critic/runner (main assistant can run scripts)
- Adding auto-hooks (can be disabled if problematic)

**Medium Risk:**
- Blocking main assistant Write to scripts/ (might be too restrictive?)
- Blocking pip install (might frustrate user?)

**Mitigation:**
- Add `--force` flag to bypass hooks if needed
- Make auto-invocation optional (config flag)
- Monitor first week for false positives

## Next Steps

1. User approval for this plan
2. Implement Phase 1 (auto-hooks)
3. Test auto-invocation with scratch scripts
4. Execute Phase 2 (delete redundant agents)
5. Execute Phase 3 (strengthen remaining agents)
6. Execute Phase 4 (update docs)
7. Monitor usage for 1 week
8. Iterate based on actual invocation frequency
