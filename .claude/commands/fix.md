---
description: 🔧 The Fixer - Fix all issues, fill gaps, and verify work
argument-hint: [scope]
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Task
---

Comprehensive issue resolution and verification workflow.

## Scope

If `$ARGUMENTS` provided, use as focus area. Otherwise, analyze:
1. Recent conversation for unresolved issues
2. Git status for uncommitted changes
3. Last tool errors or failures

## Execution Protocol

### Phase 1: Discovery
- Scan for TODO/FIXME/XXX comments in changed files
- Check for incomplete implementations (stub functions, placeholder values)
- Review any test failures or lint errors
- Identify gaps between stated intent and actual implementation

### Phase 2: Fix
For each issue found:
1. Diagnose root cause (don't just patch symptoms)
2. Implement fix
3. Verify fix works (run relevant tests/checks)

### Phase 3: Gap Analysis
- Cross-reference implementation against requirements
- Check error handling completeness
- Verify edge cases are covered
- Ensure public APIs have proper validation

### Phase 4: Verification
- Run `void` on modified files (completeness check)
- Run `audit` on modified files (security check)
- Run relevant tests
- Confirm no regressions introduced

### Phase 5: Report
Summarize:
- Issues found and fixed
- Gaps filled
- Remaining concerns (if any)
- Confidence level in the fixes

## Rules
- Fix root causes, not symptoms
- If a fix requires changing multiple files, grep for all usages first
- Don't introduce new issues while fixing old ones
- If blocked after 2 attempts, use `/think` before 3rd try
