# Hook Compliance Audit Report

**Date:** 2025-11-23
**Scope:** All hooks in `.claude/hooks/` (77 files)
**Documentation Source:** Official Claude Code Hooks Documentation

---

## Executive Summary

**Compliance Score:** 0/100

- **Critical Issues:** 0
- **High Priority Issues:** 23 (path traversal validation)
- **Medium Priority Issues:** 5 (missing JSONDecodeError handling)
- **Warnings:** 34 (f-string usage, missing try/except)

**Event Coverage:** 6/10 official hook events utilized

---

## Compliance Issues by Category

### 1. Security Issues (23 HIGH PRIORITY)

**Issue:** Missing path traversal validation in file_path handling

**Affected Hooks:**
- auto_documentarian.py
- auto_guardian.py
- auto_janitor.py
- batching_analyzer.py
- block_main_write.py
- command_prerequisite_gate*.py
- confidence_gate.py
- constitutional_guard.py
- debt_tracker.py
- detect_*_auto_learn.py
- detect_tool_failure.py
- enforce_reasoning_rigor.py
- evidence_tracker.py
- file_operation_gate.py
- performance_reward.py
- post_tool_command_suggester.py
- pre_write_audit.py (also uses shell=True)
- root_pollution_gate.py
- tier_gate.py
- trigger_skeptic.py

**Official Requirement:**
> "Block path traversal - Check for `..` in file paths"
> (Security Best Practices section)

**Recommendation:**
```python
def validate_file_path(file_path: str) -> bool:
    """Validate file path to prevent path traversal attacks."""
    if '..' in file_path:
        return False
    return True

# Usage:
if file_path and not validate_file_path(file_path):
    print(f"Security: Path traversal detected in {file_path}", file=sys.stderr)
    sys.exit(2)
```

---

### 2. Error Handling Issues (5 MEDIUM PRIORITY)

**Issue:** Missing JSONDecodeError handling for stdin parsing

**Affected Hooks:**
- force_playwright.py
- meta_cognition_performance.py
- performance_gate_v1_backup.py
- performance_reward.py
- sanity_check.py

**Official Requirement:**
> "Validate and sanitize inputs - Never trust input data blindly"
> (Security Best Practices section)

**Recommendation:**
```python
try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
    sys.exit(1)
```

---

### 3. Shell Injection Risk (1 HIGH PRIORITY)

**Issue:** Uses `shell=True` in subprocess calls

**Affected Hook:**
- pre_write_audit.py

**Official Requirement:**
> "Never use shell commands with `shell=True`"
> (Security Considerations section)

**Recommendation:**
Either remove `shell=True` or add extensive documentation:
```python
# SECURITY WARNING: shell=True is used here for command execution.
# This is intentional but requires careful input validation to prevent injection.
# Ensure all variables are properly validated before use.
subprocess.run(command, shell=True, ...)
```

---

### 4. Missing Try/Except Blocks (6 WARNINGS)

**Affected Hooks:**
- detect_confidence_reward.py
- force_playwright.py
- meta_cognition_performance.py
- performance_gate_v1_backup.py
- performance_reward.py
- sanity_check.py

**Recommendation:**
Add try/except wrapper to prevent ungraceful failures:
```python
try:
    # Main hook logic
    ...
except Exception as e:
    print(f"Hook error: {e}", file=sys.stderr)
    sys.exit(1)
```

---

### 5. F-String Usage in Commands (28 WARNINGS)

**Issue:** Using f-strings in shell commands without explicit quoting validation

**Affected Hooks:** 28 hooks use f-strings in command construction

**Official Requirement:**
> "Always quote shell variables - Use `\"$VAR\"` not `$VAR`"
> (Security Best Practices section)

**Recommendation:**
Review each f-string usage to ensure proper quoting:
```python
# Good
command = f'ls "{file_path}"'  # Quoted

# Bad
command = f'ls {file_path}'  # Unquoted - fails on spaces
```

---

## Official Documentation Compliance

### Exit Code Semantics ✓

All hooks correctly use exit codes per documentation:
- **Exit 0:** Success (stdout in verbose, JSON parsed)
- **Exit 2:** Blocking error (stderr to Claude/user, JSON ignored)
- **Other:** Non-blocking error (stderr in verbose)

### Hook Event Coverage

| Event Type | Hooks Registered | Documentation Status |
|------------|------------------|----------------------|
| PreToolUse | 33 | ✓ Properly configured |
| PostToolUse | 21 | ✓ Properly configured |
| UserPromptSubmit | 20 | ✓ Properly configured |
| SessionStart | 2 | ✓ Properly configured (startup matcher) |
| SessionEnd | 2 | ✓ Properly configured |
| Stop | 5 | ✓ Properly configured |
| **PermissionRequest** | **0** | ⚠ Not utilized |
| **SubagentStop** | **0** | ⚠ Not utilized |
| **PreCompact** | **0** | ⚠ Not utilized |
| **Notification** | **0** | ⚠ Not utilized |

### Hook-Specific Output Formats

#### PreToolUse Hooks
**Official Schema:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask",
    "permissionDecisionReason": "string",
    "updatedInput": {} // optional
  }
}
```

**Current Status:** Some hooks may be using deprecated `decision` field

**Recommendation:** Migrate to `hookSpecificOutput.permissionDecision`

#### PostToolUse Hooks
**Official Schema:**
```json
{
  "decision": "block|undefined",
  "reason": "string",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "string"
  }
}
```

**Current Status:** ✓ Compliant

#### UserPromptSubmit Hooks
**Official Schema:**
```json
{
  "decision": "block|undefined",
  "reason": "string",
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "string"
  }
}
```

**Special Behavior:** Stdout with exit 0 adds context (JSON not required)

**Current Status:** ✓ Compliant

---

## Environment Variables

### CLAUDE_PROJECT_DIR ✓
All hooks properly use `$CLAUDE_PROJECT_DIR` in settings.json configuration.

### CLAUDE_ENV_FILE
**Status:** Not currently utilized
**Use Case:** SessionStart hooks can persist environment variables
**Recommendation:** Consider using for session initialization

Example:
```python
# In SessionStart hook
if os.getenv('CLAUDE_ENV_FILE'):
    env_file = os.environ['CLAUDE_ENV_FILE']
    with open(env_file, 'a') as f:
        f.write('export NODE_ENV=production\n')
```

---

## Matchers Compliance

### PreToolUse Matchers ✓
All matchers are valid tool names or regex patterns per documentation.

Examples:
- `mcp__.*` - Matches all MCP tools
- `(Read|Write|Edit)` - Matches multiple tools
- `Bash` - Matches specific tool

### SessionStart Matchers ✓
Uses `startup` matcher correctly per documentation.

**Available matchers per docs:**
- `startup` - Invoked from startup ✓ USED
- `resume` - Invoked from --resume
- `clear` - Invoked from /clear
- `compact` - Invoked from compact

---

## Security Best Practices Checklist

Per official documentation "Security Best Practices" section:

| Practice | Compliance | Notes |
|----------|------------|-------|
| ✗ Validate and sanitize inputs | PARTIAL | 23 hooks missing path traversal checks |
| ✓ Always quote shell variables | MOSTLY | 28 warnings for f-string usage |
| ✗ Block path traversal | NO | Missing `..` checks in file_path handlers |
| ✓ Use absolute paths | YES | All hooks use $CLAUDE_PROJECT_DIR |
| ✗ Skip sensitive files | PARTIAL | Some hooks check .env, others don't |

---

## Recommendations

### Immediate Actions (HIGH PRIORITY)

1. **Add path traversal validation** to all 23 hooks handling `file_path`
   - Use provided validation function
   - Exit code 2 with security warning

2. **Add JSONDecodeError handling** to 5 hooks parsing stdin
   - Wrap json.load() in try/except
   - Exit code 1 with error message

3. **Document shell=True usage** in pre_write_audit.py
   - Add security warning comment
   - Validate all inputs before subprocess call

### Medium Priority Actions

1. **Add try/except blocks** to 6 hooks without error handling
   - Prevent ungraceful failures
   - Log errors to stderr

2. **Review f-string usage** in 28 hooks
   - Ensure proper variable quoting
   - Prevent shell injection

### Low Priority Actions

1. **Consider using unused hook events:**
   - PermissionRequest: Auto-allow/deny permissions
   - SubagentStop: Validate subagent completion
   - PreCompact: Add context before compaction
   - Notification: Custom notification handling

2. **Migrate deprecated fields:**
   - PreToolUse: `decision` → `permissionDecision`
   - Ensure all hooks use `hookSpecificOutput`

3. **Remove backup files:**
   - command_prerequisite_gate_v1_backup.py
   - native_batching_enforcer_v1_backup.py
   - performance_gate_v1_backup.py
   - tier_gate_v1_backup.py

---

## Compliance Improvement Plan

### Phase 1: Critical Security Fixes (Day 1)
- Add path traversal validation (23 files)
- Add JSONDecodeError handling (5 files)
- Document shell=True usage (1 file)

### Phase 2: Error Handling (Day 2)
- Add try/except blocks (6 files)
- Review f-string quoting (28 files)

### Phase 3: Documentation Alignment (Day 3)
- Migrate deprecated fields
- Add hook-specific output schemas
- Remove backup files

### Phase 4: Feature Expansion (Optional)
- Implement PermissionRequest hooks
- Implement SubagentStop hooks
- Implement PreCompact hooks
- Implement Notification hooks

---

## Testing Recommendations

1. **Security Testing:**
   - Test with `..` in file paths (should block)
   - Test with malformed JSON input (should fail gracefully)
   - Test with special characters in commands

2. **Functional Testing:**
   - Test exit code 0 (success path)
   - Test exit code 2 (blocking path)
   - Test JSON output parsing
   - Test stderr/stdout routing

3. **Integration Testing:**
   - Test multiple hooks in parallel
   - Test hook deduplication
   - Test hook timeout (60s default)
   - Test environment variable access

---

## Conclusion

The hook system is **functionally compliant** with official documentation but has **security gaps** that need immediate attention:

1. **23 hooks** lack path traversal validation
2. **5 hooks** lack proper error handling
3. **1 hook** uses shell=True without documentation

All issues are **automatable** and can be fixed with the provided scripts:
- `scratch/audit_hooks_compliance.py` - Automated auditing
- `scratch/fix_hook_compliance.py` - Automated fixes
- `scratch/hook_docs_mapping.py` - Documentation mapping

**Estimated time to full compliance:** 4-6 hours

**Risk if not fixed:** Path traversal attacks, ungraceful failures, potential command injection

---

## References

1. Official Hooks Guide: `/en/hooks-guide`
2. Official Hooks Reference: `/en/hooks`
3. Security Considerations: `/en/hooks#security-considerations`
4. Hook Input Schemas: `/en/hooks#hook-input`
5. Hook Output Schemas: `/en/hooks#hook-output`
