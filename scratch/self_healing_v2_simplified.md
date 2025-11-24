# Self-Healing System V2: Detection + Triage (NOT Auto-Fix)

## Philosophy Shift

**REJECTED:** Autonomous auto-fix system (Judge + Critic both say NO)
**ACCEPTED:** Fast detection + human-in-loop remediation with strong guardrails

## Core Principle

> "Don't make the system heal itself. Make the system **safe to operate manually**, fast."
> — The Critic

## What We Actually Build

### 1. Error Detection Layer (AUTOMATIC)
**Purpose:** Catch errors the moment they happen
**Scope:** Read-only, no modifications

**Detectors:**
- Tool failures (PostToolUse hook)
- Test failures (PostBash hook for pytest/npm test)
- Anti-pattern violations (already exists in pre_write_audit.py)
- Gaslighting loops (already exists in detect_gaslight.py)
- Verification failures (integrate with verify.py)

**Output:** Structured error report in `.claude/memory/error_ledger.jsonl`

### 2. Risk Classification (AUTOMATIC)
**Purpose:** Triage errors by severity, NOT effort
**Scope:** Label only, no decisions

**Risk Levels:**
- **CRITICAL (90-100):** Data loss, security breach, production outage
- **HIGH (70-89):** Breaking changes, API modifications
- **MEDIUM (40-69):** Logic errors, test failures
- **LOW (10-39):** Style drift, warnings
- **INFO (0-9):** Suggestions, optimizations

**Algorithm:** Simple deterministic rules (no ML, no heuristics)
```python
def classify_risk(error):
    if "security" in error.tags: return 95
    if "data_loss" in error.tags: return 90
    if "breaking_change" in error.tags: return 75
    if "test_failure" in error.tags: return 50
    if "style" in error.tags: return 20
    return 30  # default
```

### 3. Remediation Suggestion Engine (AUTOMATIC)
**Purpose:** Generate 1-3 fix options with risk assessment
**Scope:** Read-only, suggestions only

**Output Format:**
```json
{
  "error_id": "err-2025-11-23-001",
  "description": "Hardcoded API key in research.py:45",
  "risk": 95,
  "detected_at": "turn-15",
  "suggestions": [
    {
      "approach": "Migrate to environment variable",
      "steps": [
        "1. Add API_KEY to .env",
        "2. Replace hardcoded string with os.getenv('API_KEY')",
        "3. Run verify.py grep_text to confirm"
      ],
      "risk_after_fix": 10,
      "reversible": true,
      "one_click": false
    },
    {
      "approach": "Remove API key (disable feature)",
      "steps": [
        "1. Comment out API call",
        "2. Add TODO for proper implementation"
      ],
      "risk_after_fix": 0,
      "reversible": true,
      "one_click": true
    }
  ],
  "recommended_action": "suggestions[0]",
  "requires_approval": true
}
```

### 4. User Decision Interface (MANUAL)
**Purpose:** Present options, let user decide
**Scope:** AskUserQuestion tool

**Flow:**
1. Detect error → Log to error_ledger.jsonl
2. Generate suggestions → Present via AskUserQuestion
3. User selects option → Execute with verification
4. Verify result → Log outcome to fix_ledger.jsonl

**Example:**
```
Error detected: Hardcoded API key (CRITICAL risk)

Suggested fixes:
1. Migrate to os.getenv (recommended)
2. Remove feature temporarily
3. Defer to punch list

Which approach? [1/2/3/defer]
```

### 5. One-Click Remediation Library (SEMI-AUTOMATIC)
**Purpose:** Pre-approved, reversible fixes for common issues
**Scope:** User-triggered, not autonomous

**Characteristics:**
- MUST be deterministic (no guessing)
- MUST be reversible (git revert or built-in undo)
- MUST pass verify after execution
- MUST log to fix_ledger.jsonl

**Example One-Click Fixes:**
```python
ONE_CLICK_FIXES = {
    "print_to_logger": {
        "pattern": r'print\(',
        "replacement": "logger.info(",
        "verify": lambda: run_audit(file) == 0,
        "reversible": True,
        "risk": 5,
    },
    "wildcard_import": {
        "pattern": r'from \w+ import \*',
        "replacement": lambda m: generate_explicit_imports(m),
        "verify": lambda: run_tests() == 0,
        "reversible": True,
        "risk": 15,
    },
}
```

**Invocation:** User says "apply fix #1" or selects from AskUserQuestion

### 6. Guardrails & Safety Checks

#### Before Fix Execution
```python
def can_apply_fix(fix):
    # 1. Check confidence tier
    if confidence < 71: return False, "Need CERTAINTY tier"

    # 2. Check if file was read
    if file not in read_files: return False, "Must read file first"

    # 3. Check risk threshold
    if fix.risk > 60: return False, "Requires council approval"

    # 4. Check turn depth
    if turn > 20: return False, "Session too deep, use /compact"

    # 5. Check token budget
    if tokens > 150000: return False, "Approaching token limit"

    return True, None
```

#### After Fix Execution
```python
def verify_fix(fix):
    # 1. Run verify.py (mandatory)
    if not verify_command_passed(): return False

    # 2. Run audit.py (mandatory for production)
    if is_production and not audit_passed(): return False

    # 3. Run void.py (check for new stubs)
    if void_found_stubs(): return False

    # 4. Run tests if exist
    if has_tests() and not tests_passed(): return False

    return True
```

## What We DO NOT Build

❌ Autonomous auto-fix (too risky)
❌ ML-based risk classification (too unpredictable)
❌ Effort estimation (irrelevant for triage)
❌ Complex decision matrices (over-engineering)
❌ Fix recommendation AI (use oracle.py if needed)
❌ Self-modifying code without approval (trust violation)

## What We DO Build

✅ Fast error detection (hooks)
✅ Simple risk classification (deterministic rules)
✅ Structured suggestion generation (templates)
✅ User decision interface (AskUserQuestion)
✅ One-click remediation library (user-triggered)
✅ Comprehensive logging (error_ledger + fix_ledger)
✅ Mandatory verification (verify.py after every fix)

## Implementation Plan

### Phase 1: Detection Infrastructure (Week 1)
**Files:**
- `.claude/hooks/detect_tool_failure.py` (PostToolUse)
- `.claude/hooks/detect_test_failure.py` (PostBash)
- `scripts/lib/error_detection.py` (core logic)
- `.claude/memory/error_ledger.jsonl` (storage)

**Deliverable:** All errors logged to error_ledger.jsonl with risk classification

### Phase 2: Suggestion Engine (Week 1)
**Files:**
- `scripts/lib/fix_suggestions.py` (template library)
- `scripts/ops/review_error.py` (CLI tool to view errors)

**Deliverable:** `review_error.py --error-id <id>` shows 1-3 fix options

### Phase 3: User Interface Integration (Week 2)
**Integration:**
- Errors trigger AskUserQuestion with fix options
- User selects → Execute → Verify → Log

**Deliverable:** Errors auto-present fix options during session

### Phase 4: One-Click Fix Library (Week 2)
**Files:**
- `scripts/lib/one_click_fixes.py` (10-15 pre-approved fixes)
- Each fix has unit test proving correctness

**Deliverable:** User can say "apply fix #1" and it executes safely

### Phase 5: Integration with Existing Protocols (Week 3)
**Integrations:**
- **Epistemology:** Successful fixes +10%, failed fixes -15%
- **Verify Protocol:** All fixes MUST pass verify
- **Scope Protocol:** User can defer fixes to punch list
- **Council Protocol:** High-risk fixes trigger council

**Deliverable:** Self-healing integrated with all existing systems

## Success Metrics

### Detection Accuracy
- [ ] 95%+ error detection rate (no missed errors)
- [ ] 0% false positives (all detected errors are real)
- [ ] <1s detection latency (real-time)

### Suggestion Quality
- [ ] 90%+ user acceptance of recommendations
- [ ] 3+ fix options per error
- [ ] 100% reversibility for one-click fixes

### Safety & Reliability
- [ ] 0% unauthorized modifications (all fixes require approval)
- [ ] 100% verification pass rate (all fixes pass verify)
- [ ] 100% auditability (all fixes logged)

### User Experience
- [ ] <5s from error detection to fix presentation
- [ ] 1-click execution for common issues
- [ ] Clear risk communication (no jargon)

## Anti-Reward Hacking Safeguards

### 1. Mandatory User Approval
FORBIDDEN to apply ANY fix without user selection via AskUserQuestion

### 2. Mandatory Verification
FORBIDDEN to claim "Fixed" without verify.py passing

### 3. Comprehensive Logging
EVERY fix attempt logged to fix_ledger.jsonl with:
- Error ID
- Fix applied
- Verification result
- User who approved
- Timestamp

### 4. Rollback Capability
ALL one-click fixes MUST have undo function:
```python
fix = ONE_CLICK_FIXES["print_to_logger"]
fix.apply(file)
if not verify_passed():
    fix.undo(file)  # Automatic rollback
    log_failure()
```

### 5. Risk Threshold Enforcement
High-risk fixes (>60) automatically escalate to council:
```python
if risk > 60:
    return f"Run: python3 scripts/ops/council.py '{error_description}'"
```

## Comparison: V1 (Rejected) vs V2 (Approved)

| Aspect | V1 (Auto-Fix) | V2 (Detection + Triage) |
|--------|---------------|-------------------------|
| **Philosophy** | System heals itself | Human operates safely |
| **Autonomy** | High (auto-applies fixes) | Low (suggests fixes) |
| **Risk** | High (silent failures) | Low (explicit approval) |
| **Complexity** | Very high (matrix + ML) | Low (rules + templates) |
| **Ownership** | Unclear (blame shifting) | Clear (user approves) |
| **Learning** | Low (incidents vanish) | High (user sees fixes) |
| **Rollback** | Complex (track history) | Simple (git revert) |
| **Auditability** | Medium (auto-fixes hidden) | High (all logged) |
| **Trust** | Low (black box) | High (transparent) |

## Definition of Done

System is operational when:
1. ✅ Detects 10+ error types automatically
2. ✅ Classifies risk correctly (95%+ accuracy)
3. ✅ Generates 1-3 fix suggestions per error
4. ✅ Presents suggestions via AskUserQuestion
5. ✅ Executes user-selected fix with verification
6. ✅ Logs all errors + fixes to ledger files
7. ✅ Provides 1-click execution for 10+ common fixes
8. ✅ Integrates with verify/scope/council protocols
9. ✅ Respects confidence tiers (no fixes at <71%)
10. ✅ Zero unauthorized modifications (all approved)

---

**Verdict:** Proceed with V2 (simplified, human-in-loop design)
**Risk:** Low (read-only detection + user-approved remediation)
**Effort:** Medium (5 new tools + 2 hooks + integration)
**Next Step:** Await user approval
