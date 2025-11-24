# Auto-Void Protocol - Quick Reference

## What It Does
Automatically runs void.py completeness checks on production Python files when you pause/end a session.

## When It Triggers
**Stop lifecycle** (when Claude pauses waiting for your response or session ends)

## What Gets Checked
Production Python files you modified in the current session:
- ✅ `scripts/ops/*.py`
- ✅ `scripts/lib/*.py`
- ✅ `.claude/hooks/*.py`
- ❌ `scratch/*.py` (excluded)
- ❌ `projects/**/*.py` (excluded)

## Enforcement Policy

### At CERTAINTY Tier (71-85% confidence)
- **Always shows results** for all checked files
- Reports both clean and dirty files
- Shows stub counts with line numbers

### At TRUSTED Tier (86-94% confidence)
- **Silent unless issues found**
- Only shows files with stubs
- No output if all clean

### Other Tiers
- **No action** (IGNORANCE, HYPOTHESIS, WORKING, EXPERT)

## What It Detects
Incomplete code patterns:
- `# TODO:` comments
- `# FIXME:` comments
- Function stubs: `def foo(): pass`
- `raise NotImplementedError`
- Ellipsis stubs: `...`

## Example Output
```
🔍 Auto-Void Check (CERTAINTY tier, 75% confidence):

   ✅ scripts/ops/foo.py - Clean
   ⚠️  scripts/lib/bar.py - 3 stub(s) detected
       Line 42: TODO comment
       Line 89: Function stub (pass)
       Line 120: NotImplementedError

💡 Tip: Run void.py with full Oracle analysis for deeper inspection
```

## Manual Override
To run full void analysis manually:
```bash
python3 scripts/ops/void.py <file>
```

## Disable Temporarily
The hook runs automatically. To disable:
1. Comment out in `.claude/settings.json` Stop hooks
2. Or: Reach EXPERT tier (95-100% confidence) where it auto-disables

## Cost
**Zero** - Uses `--stub-only` mode (no Oracle API calls)

## Performance Impact
**Minimal** - Only runs once per Stop, not every turn

## Key Benefits
1. ✅ Catches incomplete implementations automatically
2. ✅ No manual void requests needed
3. ✅ Confidence-based enforcement (graduated trust)
4. ✅ Non-blocking (warnings only)
5. ✅ Zero cost (no API usage)

## Common Scenarios

### Scenario 1: Building New Feature
- You write `scripts/ops/new_tool.py`
- Leave some TODOs for later
- Session pauses (Stop)
- Auto-void runs, shows: "2 stub(s) detected"
- You see reminder to complete before commit

### Scenario 2: Quick Fix
- You edit `scripts/lib/core.py`
- Complete implementation, no stubs
- Session pauses
- Auto-void runs, shows: "Clean ✅"
- Silent confirmation, no noise

### Scenario 3: High Confidence Work
- You're at TRUSTED tier (90%)
- Write clean code in `scripts/ops/tool.py`
- Session pauses
- Auto-void checks but stays silent (clean)
- No interruption to your flow

## Troubleshooting

### "Hook didn't run"
- Check confidence tier (only runs at CERTAINTY/TRUSTED)
- Check if you modified production Python files
- Verify hook is registered in settings.json

### "False positives"
- Some patterns are intentional (template files, etc.)
- Run at TRUSTED tier for silent mode
- Or manually disable for special cases

### "Want full analysis"
Run manually with Oracle:
```bash
python3 scripts/ops/void.py <file>
```

## Related Tools
- **Manual void:** `python3 scripts/ops/void.py <file>`
- **Audit (security):** `python3 scripts/ops/audit.py <file>`
- **Drift (style):** `python3 scripts/ops/drift_check.py`
- **Verify (facts):** `/verify command_success "<cmd>"`

## Philosophy
"If you're manually requesting it after every task completion, it should be automated."

This hook ensures completeness checks happen automatically at the right confidence level, reducing cognitive load while maintaining quality.
