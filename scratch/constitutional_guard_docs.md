# Constitutional Guard Hook - Documentation

**Hook:** `constitutional_guard.py`
**Type:** PreToolUse (Write/Edit)
**Enforcement:** Hard Block
**Created:** 2025-11-23

---

## Purpose

Prevents unauthorized AI modification of CLAUDE.md (the system constitution).

**Philosophy:**
- CLAUDE.md defines CURRENT REALITY, not future plans
- AI should not self-modify its instruction set without human review
- Changes require explicit approval workflow

---

## How It Works

### Detection
Intercepts any Write or Edit tool targeting `CLAUDE.md`:
```
Write(file_path="/path/to/CLAUDE.md", ...)  → BLOCKED
Edit(file_path="/path/to/CLAUDE.md", ...)   → BLOCKED
```

### Response
1. **Hard blocks** the operation
2. **Instructs Claude** to write proposal to `scratch/claude_md_proposals.md`
3. **Provides template** for structured proposal

### Bypass Mechanism
User includes keyword in prompt:
```
"SUDO CONSTITUTIONAL: Apply the proposed change to add Rule 19"
```

Only the **user** should use this keyword, after reviewing Claude's proposal.

---

## Workflow Example

### Scenario: Claude Wants to Add New Rule

**Step 1:** Claude attempts to edit CLAUDE.md
```
Edit(file_path="CLAUDE.md", old_string="...", new_string="...")
```

**Step 2:** Hook blocks with message
```
🛡️ CONSTITUTIONAL GUARD TRIGGERED

BLOCKED: Unauthorized modification of CLAUDE.md

Recommended: Write proposal to scratch/claude_md_proposals.md
```

**Step 3:** Claude writes proposal
```markdown
## Proposal: Add Constitutional Immutability Rule
**Date:** 2025-11-23
**Status:** PENDING

### Section
Manifesto - Rule 19 (new rule)

### Rationale
Need explicit rule preventing AI from self-modifying CLAUDE.md.

### Proposed Change
19. **Constitutional Immutability:** CLAUDE.md is READ-ONLY to AI.
    Propose changes via scratch/claude_md_proposals.md for user review.

### Impact
- Prevents accidental constitutional drift
- Creates audit trail for system changes
- Maintains human oversight of AI instructions
```

**Step 4:** User reviews proposal
- Opens `scratch/claude_md_proposals.md`
- Evaluates rationale and impact
- Decides: APPROVE or REJECT

**Step 5a:** If APPROVED
- User manually edits CLAUDE.md (using their editor)
- User marks proposal as APPROVED in proposals file
- User runs: `"SUDO CONSTITUTIONAL: Applied Rule 19 as proposed"`
- Claude can now commit changes with upkeep

**Step 5b:** If REJECTED
- User deletes proposal from file
- User provides feedback to Claude on why change isn't needed

---

## Integration with Existing Hooks

**Position in Hook Chain:**
1. **constitutional_guard.py** ← First (position 1)
2. root_pollution_gate.py
3. block_main_write.py
4. command_prerequisite_gate.py
5. tier_gate.py
6. pre_write_audit.py
7. ban_stubs.py
8. enforce_reasoning_rigor.py
9. confidence_gate.py

**Rationale for Position 1:**
- Constitutional integrity is highest priority
- Should block before any other validation
- Prevents wasted computation on doomed operation

---

## Why This Hook is Necessary

### Problem Without Guard

AI can accidentally pollute CLAUDE.md with:

1. **Hallucinated Features**
   ```markdown
   ## Tools Available
   - oracle.py ✅
   - magic_solver.py ✅  ← DOESN'T EXIST
   - quantum_debugger.py ✅  ← HALLUCINATION
   ```

2. **Future Plans as Current Reality**
   ```markdown
   ## Roadmap (Next 4 Weeks)
   - Week 1: Build X
   - Week 2: Implement Y
   ```
   This bloats system prompt with non-actionable content.

3. **Self-Justifying Rule Changes**
   AI might weaken rules that constrain it:
   ```markdown
   - Rule: "No Write without Read" → "No Write without Read (unless obvious)"
   ```

### Solution With Guard

- All changes go through proposal → review → approval
- Audit trail in `scratch/claude_md_proposals.md`
- Human maintains veto power over constitutional changes
- Claude can still recommend improvements (encouraged!)

---

## Testing

### Test 1: Block Unauthorized Write
```bash
echo '{"toolName":"Write","toolParams":{"file_path":"CLAUDE.md"},"prompt":"Update docs"}' | \
  python3 .claude/hooks/constitutional_guard.py
```

**Expected:** Block message with proposal instructions

### Test 2: Allow With Bypass
```bash
echo '{"toolName":"Write","toolParams":{"file_path":"CLAUDE.md"},"prompt":"SUDO CONSTITUTIONAL: Add rule"}' | \
  python3 .claude/hooks/constitutional_guard.py
```

**Expected:** Allow with warning message

### Test 3: Ignore Non-CLAUDE.md Files
```bash
echo '{"toolName":"Write","toolParams":{"file_path":"README.md"},"prompt":"Update readme"}' | \
  python3 .claude/hooks/constitutional_guard.py
```

**Expected:** No output (pass through)

---

## Maintenance

### When to Update This Hook

1. **New bypass keywords needed** - Edit `constitutional_guard.py` line ~52
2. **Proposal template changes** - Edit `scratch/claude_md_proposals.md`
3. **Block message improvements** - Edit `constitutional_guard.py` lines ~70-140

### Monitoring

Check proposal file periodically:
```bash
cat scratch/claude_md_proposals.md
```

If many proposals accumulate:
- Review why Claude is suggesting changes
- Consider if patterns indicate missing documentation
- Update CLAUDE.md proactively to reduce proposal volume

---

## FAQ

**Q: Can Claude ever edit CLAUDE.md?**
A: Only with explicit "SUDO CONSTITUTIONAL" authorization from user.

**Q: What if Claude's proposal is good?**
A: User reviews, manually applies, then authorizes with SUDO keyword.

**Q: What if I want to disable this hook temporarily?**
A: Comment out the hook in `.claude/settings.json` or use SUDO bypass.

**Q: Does this slow down normal operations?**
A: No. Hook only activates on CLAUDE.md writes (~0.1% of operations).

**Q: Can I use this pattern for other protected files?**
A: Yes! Extend the hook to check for other paths (e.g., `.claude/settings.json`).

---

## Related Hooks

- `root_pollution_gate.py` - Prevents writes to repository root
- `block_main_write.py` - Prevents writes to main branch without review
- `tier_gate.py` - Confidence-based write restrictions

---

## Metrics

**Since Installation:**
- Blocks: 0 (new hook)
- Proposals Generated: 0
- Approvals: 0
- Rejections: 0

*Track in `.claude/memory/constitutional_guard_telemetry.jsonl` (future enhancement)*

---

## Conclusion

Constitutional Guard ensures:
✅ CLAUDE.md integrity maintained
✅ Human oversight of system changes
✅ Audit trail via proposal workflow
✅ Claude can still recommend improvements
✅ Prevents accidental self-modification

**Status:** Operational, integrated into PreToolUse chain (position 1)
