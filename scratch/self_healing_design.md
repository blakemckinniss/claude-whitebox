# Self-Healing Error Detection & Remediation System

## Design Philosophy

**ANTI-PATTERN:** Building Skynet to fix typos (over-engineering)
**SOLUTION:** Lightweight detection + risk-based triage + existing tool leverage

## Architecture

### Phase 1: Error Detection & Classification
```
Error Source → Detector → Risk/Effort Quantification → Decision Matrix → Action
```

### Phase 2: Risk/Effort Matrix

| Risk | Effort | Action |
|------|--------|--------|
| Low | Low | **AUTO-FIX** (with logging) |
| Low | Medium | **CONSULT USER** (suggest fix) |
| Low | High | **DEFER** (add to punch list) |
| Medium | Low | **CONSULT USER** (explain risk) |
| Medium | Medium+ | **DEFER** (requires planning) |
| High | Any | **BLOCK + CONSULT** (mandatory approval) |

### Phase 3: Enforcement Zones

#### AUTO-FIX Zone (Low Risk + Low Effort)
- Anti-pattern violations (hardcoded secrets → os.getenv)
- Stub code removal (TODO/pass/... → proper implementation OR issue creation)
- Import cleanup (wildcard imports → explicit)
- Print → logger.info
- Missing SDK compliance (add setup_script/finalize)
- Test failures (with clear fix path)

**Constraints:**
- MUST be deterministic (no ML/heuristics)
- MUST be reversible (git revert)
- MUST pass audit/void after fix
- MUST log fix in .claude/memory/auto_fixes.jsonl

#### CONSULT Zone (Medium Risk OR Medium Effort)
- Architecture changes (function complexity > 10 lines to refactor)
- Security issues requiring judgment (SQL injection patterns)
- Breaking changes (API signature modifications)
- Performance issues requiring profiling

**Constraints:**
- Present 2-3 fix options with risk/effort scores
- Use oracle.py for technical risk assessment
- Require user approval before action

#### DEFER Zone (High Effort)
- Large-scale refactors
- Multi-file migrations
- Dependency upgrades
- Framework version bumps

**Constraints:**
- Add to scope.py punch list
- Estimate LOE (Lines of Effort, not time)
- Generate /think decomposition
- User decides when to tackle

### Phase 4: Detection Triggers

#### 1. Tool Failure Detection (PostToolUse Hook)
```python
# .claude/hooks/detect_tool_failure.py
if tool_result.error:
    error_type = classify_error(tool_result.error)
    risk, effort = quantify_fix(error_type)
    action = decide_action(risk, effort)
```

#### 2. Anti-Pattern Detection (PreWrite Hook - Already Exists)
```python
# .claude/hooks/pre_write_audit.py (EXTEND)
if anti_pattern_found:
    if auto_fixable(pattern):
        return auto_fix_and_retry()
    else:
        return block_with_suggestion()
```

#### 3. Test Failure Detection (PostBash Hook)
```python
# .claude/hooks/detect_test_failure.py
if "pytest" in command and exit_code != 0:
    failures = parse_pytest_output(stdout)
    for failure in failures:
        if is_trivial_fix(failure):
            apply_fix(failure)
        else:
            suggest_fix(failure)
```

#### 4. Gaslighting Loop Detection (Already Exists)
```python
# .claude/hooks/detect_gaslight.py (ALREADY IMPLEMENTED)
# Triggers sherlock agent for evidence-based debugging
```

### Phase 5: Risk/Effort Quantification

#### Risk Scoring (0-100)
```python
def calculate_risk(error):
    base_risk = {
        "security": 90,        # SQL injection, secrets
        "data_loss": 85,       # File deletions, DB drops
        "breaking_change": 70, # API changes
        "logic_error": 50,     # Wrong implementation
        "style_drift": 20,     # Formatting, naming
        "test_failure": 30,    # Tests failing
    }[error.category]

    # Modifiers
    if error.affects_production: base_risk += 10
    if error.reversible: base_risk -= 15
    if error.has_tests: base_risk -= 10

    return min(100, max(0, base_risk))
```

#### Effort Scoring (0-100)
```python
def calculate_effort(error):
    base_effort = {
        "single_line": 10,    # One-line fix
        "single_function": 25, # Refactor one function
        "single_file": 40,    # Multi-function changes
        "multi_file": 70,     # Cross-file changes
        "architecture": 95,   # System-wide changes
    }[error.scope]

    # Modifiers
    if error.has_automated_test: base_effort -= 10
    if error.requires_research: base_effort += 20
    if error.needs_council: base_effort += 15

    return min(100, max(0, base_effort))
```

### Phase 6: Auto-Fix Library

#### Fix Template Structure
```python
class AutoFix:
    pattern: str          # Regex or AST pattern to match
    risk: int            # 0-100
    effort: int          # 0-100
    reversible: bool     # Can git revert?
    fix_fn: Callable     # Function that applies fix
    test_fn: Callable    # Function that verifies fix worked

    def apply(self, file_path: str, match: Match) -> FixResult:
        # Apply fix
        # Run test_fn to verify
        # Log to auto_fixes.jsonl
        # Return result
```

#### Example: Hardcoded Secret Fix
```python
hardcoded_secret_fix = AutoFix(
    pattern=r'api_key\s*=\s*["\']sk-proj-[^"\']+["\']',
    risk=15,  # Low risk - just env var migration
    effort=10,  # Low effort - one line change
    reversible=True,
    fix_fn=lambda m: f'api_key = os.getenv("API_KEY")',
    test_fn=lambda: verify_grep_text(file, 'os.getenv("API_KEY")'),
)
```

### Phase 7: Logging & Auditability

#### Auto-Fix Ledger
```json
// .claude/memory/auto_fixes.jsonl
{
  "turn": 15,
  "file": "scripts/ops/research.py",
  "error": "hardcoded_secret",
  "fix": "migrated to os.getenv",
  "risk": 15,
  "effort": 10,
  "verified": true,
  "timestamp": "2025-11-23T12:15:00"
}
```

#### User Consultation Log
```json
// .claude/memory/deferred_fixes.jsonl
{
  "turn": 20,
  "error": "high_complexity_function",
  "risk": 60,
  "effort": 50,
  "action": "deferred",
  "reason": "requires architectural review",
  "scope_id": "scope-2025-11-23-001"
}
```

## Implementation Plan

### Step 1: Core Error Classification Engine
**File:** `scripts/lib/error_detection.py`
**Functions:**
- `classify_error(error_message: str) -> ErrorType`
- `calculate_risk(error: ErrorType) -> int`
- `calculate_effort(error: ErrorType) -> int`
- `decide_action(risk: int, effort: int) -> Action`

### Step 2: Auto-Fix Library
**File:** `scripts/lib/auto_fixes.py`
**Contains:** 10-15 deterministic fix templates for common issues
**Test:** Each fix has unit test proving correctness

### Step 3: Detection Hooks
**Files:**
- `.claude/hooks/detect_tool_failure.py` (PostToolUse)
- `.claude/hooks/detect_test_failure.py` (PostBash)
- **Extend:** `.claude/hooks/pre_write_audit.py` (add auto-fix capability)

### Step 4: User Consultation Interface
**File:** `scripts/ops/review_error.py`
**Usage:** `python3 scripts/ops/review_error.py --error-id <id>`
**Output:** Risk/effort matrix + 2-3 fix options + oracle assessment

### Step 5: Integration with Existing Systems
- **Epistemology:** Auto-fixes give +5% confidence, defers give -5%
- **Scope Protocol:** Deferred fixes auto-added to punch list
- **Council Protocol:** High-risk decisions trigger council
- **Verify Protocol:** All auto-fixes MUST pass verify before claiming success

## Decision Matrix Examples

### Example 1: Hardcoded API Key
- **Risk:** 90 (security critical)
- **Effort:** 10 (one-line change)
- **Action:** CONSULT (risk too high for auto-fix)
- **Presentation:** "Critical security issue detected. Fix: migrate to os.getenv. Apply fix? [y/N]"

### Example 2: Print Instead of Logger
- **Risk:** 10 (style drift)
- **Effort:** 5 (one-line change)
- **Action:** AUTO-FIX
- **Log:** "Auto-fixed: replaced print() with logger.info() in research.py:45"

### Example 3: Function Complexity > 10
- **Risk:** 40 (maintainability)
- **Effort:** 60 (requires decomposition)
- **Action:** DEFER
- **Output:** "Function 'process_data' has complexity 15. Added to punch list for refactoring."

### Example 4: SQL Injection Pattern
- **Risk:** 95 (security critical)
- **Effort:** 20 (rewrite query)
- **Action:** BLOCK + CONSULT (mandatory council review)
- **Output:** "CRITICAL: SQL injection detected. Cannot proceed. Council consultation required."

## Anti-Reward Hacking Safeguards

### 1. Paired Metrics
Auto-fixes must not degrade other metrics:
- Fix must pass audit + void
- Fix must not break existing tests
- Fix must maintain or improve complexity score

### 2. Recursive Loop Detection
Track auto-fix attempts in session state:
- Max 2 auto-fix attempts per error
- If 2nd attempt fails, escalate to CONSULT
- Track in `.claude/memory/fix_attempts.jsonl`

### 3. Mandatory Verification
FORBIDDEN to claim "Fixed" without:
1. Auto-fix applied
2. Verify command passed
3. Logged in auto_fixes.jsonl

### 4. User Override Keyword
User can say "SUDO" to bypass auto-fix and force consultation:
```
User: "SUDO - don't auto-fix the print statements, I want them for debugging"
Claude: "Auto-fix disabled for this session. Proceeding with manual review."
```

## Turn Depth & Token Budget Checks

### Before Auto-Fix
```python
if turn_depth > 20:
    # Too deep in session, defer to avoid context bloat
    action = "DEFER"
if token_usage > 150000:
    # Approaching limit, consult instead of auto-fixing
    action = "CONSULT"
```

### Before Council Consultation
```python
if turn_depth > 15 and token_usage > 100000:
    # Recommend /compact before expensive council call
    suggest_compact()
```

## Success Metrics

### Phase 1 (Week 1)
- [ ] 5 auto-fix templates implemented
- [ ] 90% detection accuracy on known anti-patterns
- [ ] 0% false-positive auto-fixes (all fixes pass verify)

### Phase 2 (Week 2)
- [ ] 15 auto-fix templates implemented
- [ ] User consultation interface operational
- [ ] Deferred fixes integrate with scope.py

### Phase 3 (Week 3)
- [ ] Tool failure detection hook operational
- [ ] Test failure detection hook operational
- [ ] Council integration for high-risk decisions

## Definition of Done

System is considered operational when:
1. It detects 10+ error types automatically
2. It correctly triages errors into AUTO-FIX / CONSULT / DEFER buckets
3. It applies 5+ auto-fixes without human intervention (with 100% verify pass rate)
4. It consults user on medium-risk issues (with risk/effort matrix)
5. It defers high-effort tasks (with scope.py integration)
6. It generates audit trail in auto_fixes.jsonl
7. It prevents reward hacking (paired metrics, loop detection, mandatory verify)
8. It respects turn depth and token budget constraints

---

**Next Steps:** Await user approval before implementation.
**Risk:** Medium (architectural change to hook system)
**Effort:** High (15 new tools + 3 hooks + integration)
**Recommendation:** Consult user on scope and priorities.
