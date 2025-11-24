# Meta-Hook Enforcer Documentation

**File:** `.claude/hooks/hook_documentation_enforcer.py`
**Type:** PreToolUse Hook (Write operations to `.claude/hooks/*.py`)
**Purpose:** Prevents hook code that violates official Claude Code documentation

---

## Overview

The Hook Documentation Enforcer is a **meta-hook** that validates other hooks before they're written. It acts as a guardian, ensuring all hooks comply with official Claude Code hooks documentation standards.

### Key Features

1. **Blocks non-compliant hook code** before it's written
2. **Provides detailed error messages** explaining violations
3. **References official documentation** for each requirement
4. **Allows SUDO bypass** for intentional deviations
5. **Shows warnings** for deprecated patterns

---

## What It Validates

### 1. Exit Code Semantics ✓

**Requirement:** Exit code 2 must be paired with stderr output

**Per official docs:**
- Exit 0: Success (stdout in verbose mode)
- Exit 2: Blocking error (only stderr used as error message)
- Other: Non-blocking error

**Validated pattern:**
```python
print(f"Error: {reason}", file=sys.stderr)
sys.exit(2)
```

**Violation example:**
```python
sys.exit(2)  # ✗ No stderr output before exit 2
```

### 2. JSONDecodeError Handling ✓

**Requirement:** Hooks parsing stdin must handle JSONDecodeError

**Per official docs:** "Validate and sanitize inputs - never trust blindly"

**Validated pattern:**
```python
try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON: {e}", file=sys.stderr)
    sys.exit(1)
```

**Violation example:**
```python
try:
    input_data = json.load(sys.stdin)
except:  # ✗ Too broad, doesn't specifically handle JSONDecodeError
    sys.exit(0)
```

### 3. Path Traversal Prevention ✓

**Requirement:** File path handling must check for `..`

**Per official docs:** "Block path traversal - Check for .. in file paths"

**Validated patterns:**
```python
if '..' in file_path:
    print("Security: Path traversal detected", file=sys.stderr)
    sys.exit(2)

# OR

def validate_file_path(file_path: str) -> bool:
    if '..' in file_path:
        return False
    return True
```

**Violation example:**
```python
file_path = input_data.get('file_path', '')
# Process file_path without validation  ✗
```

### 4. shell=True Documentation ✓

**Requirement:** shell=True requires security documentation

**Per official docs:** "Never use shell=True without validation"

**Validated pattern:**
```python
# SECURITY WARNING: shell=True requires careful input validation
# All variables are validated before use
subprocess.run(command, shell=True, ...)
```

**Violation example:**
```python
subprocess.run(command, shell=True, ...)  # ✗ No security warning
```

### 5. Hook Event Names ✓

**Requirement:** Hook events must be official

**Official events:**
- PreToolUse, PermissionRequest, PostToolUse
- Notification, UserPromptSubmit
- Stop, SubagentStop, PreCompact
- SessionStart, SessionEnd

**Validated pattern:**
```python
{
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",  # ✓ Official event
        ...
    }
}
```

**Violation example:**
```python
{
    "hookSpecificOutput": {
        "hookEventName": "CustomEvent",  # ✗ Not an official event
        ...
    }
}
```

### 6. Output Schema Compliance ⚠

**Requirement:** Use modern hookSpecificOutput schema

**Deprecated (warns):**
```python
{
    "decision": "approve",  # Old PreToolUse format
    "reason": "..."
}
```

**Current (recommended):**
```python
{
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "permissionDecisionReason": "..."
    }
}
```

---

## How It Works

### Trigger Conditions

The enforcer runs when:
1. Tool is `Write` (not Edit - too complex to validate edits)
2. File path contains `.claude/hooks/`
3. File extension is `.py`
4. File is NOT `hook_documentation_enforcer.py` (self-exclusion)

### Validation Process

```
Write to .claude/hooks/*.py
    ↓
hook_documentation_enforcer.py runs
    ↓
Parse code with AST
    ↓
Run 5 validation checks
    ↓
Any CRITICAL/HIGH violations? ─→ YES ─→ BLOCK (deny with reason)
    ↓ NO
Any MEDIUM violations? ─→ YES ─→ BLOCK (deny with reason)
    ↓ NO
Any warnings? ─→ YES ─→ ALLOW (with warnings shown)
    ↓ NO
ALLOW (silent pass)
```

### Output Formats

**Blocked (has violations):**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🚫 HOOK VALIDATION FAILED\n\n..."
  }
}
```

**Allowed (with warnings):**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "✓ Hook validation passed with warnings\n\n..."
  }
}
```

**Allowed (clean):**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow"
  }
}
```

---

## Bypass Mechanism

### SUDO Keyword

If the user prompt contains "SUDO", the enforcer allows the write with a warning:

```
User: "SUDO write the hook even though it has issues"
  ↓
Enforcer: ALLOW (shows violations as warning, doesn't block)
```

**Use cases for SUDO bypass:**
1. Prototyping a hook (fix violations later)
2. Temporary workaround for edge case
3. Intentional deviation from standards (document why)

---

## Example Validations

### Example 1: Missing JSONDecodeError Handling

**Code being written:**
```python
#!/usr/bin/env python3
import sys
import json

try:
    data = json.load(sys.stdin)
except:
    sys.exit(0)

# Rest of hook...
```

**Enforcer output:**
```
🚫 HOOK VALIDATION FAILED

File: my_new_hook.py

MEDIUM PRIORITY VIOLATIONS:
  ! Missing JSONDecodeError handling for stdin parsing
    Per official docs: 'Validate and sanitize inputs'
    Required pattern:
      try:
          input_data = json.load(sys.stdin)
      except json.JSONDecodeError as e:
          print(f'Error: Invalid JSON: {e}', file=sys.stderr)
          sys.exit(1)

Per official Claude Code hooks documentation:
  - /en/hooks-guide (Best practices)
  - /en/hooks (Event types, schemas)
  - /en/hooks#security-considerations (Security)

Fix violations before writing hook code.

(Use SUDO keyword to bypass)
```

**Result:** ✗ BLOCKED

### Example 2: Missing Path Traversal Check

**Code being written:**
```python
#!/usr/bin/env python3
import sys
import json

input_data = json.load(sys.stdin)
file_path = input_data.get('file_path', '')

# Process file without validation
with open(file_path) as f:
    content = f.read()
```

**Enforcer output:**
```
🚫 HOOK VALIDATION FAILED

File: file_processor.py

HIGH PRIORITY VIOLATIONS:
  ✗ Missing path traversal validation for file_path
    Per official docs: 'Block path traversal - Check for .. in file paths'
    Required pattern:
      if '..' in file_path:
          print('Security: Path traversal detected', file=sys.stderr)
          sys.exit(2)

Per official Claude Code hooks documentation:
  - /en/hooks-guide (Best practices)
  - /en/hooks (Event types, schemas)
  - /en/hooks#security-considerations (Security)

Fix violations before writing hook code.

(Use SUDO keyword to bypass)
```

**Result:** ✗ BLOCKED

### Example 3: Deprecated Schema (Warning Only)

**Code being written:**
```python
output = {
    "decision": "approve",  # Old format
    "reason": "File approved"
}
print(json.dumps(output))
```

**Enforcer output:**
```
✓ Hook validation passed with warnings

⚠️ WARNINGS:
  ⚠ Uses deprecated 'decision' field for PreToolUse
    Per official docs: Use 'hookSpecificOutput.permissionDecision' instead
    Deprecated: {'decision': 'approve|block'}
    Current:    {'hookSpecificOutput': {'permissionDecision': 'allow|deny|ask'}}
```

**Result:** ✓ ALLOWED (with warning)

### Example 4: Clean Hook

**Code being written:**
```python
#!/usr/bin/env python3
import sys
import json

try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON: {e}", file=sys.stderr)
    sys.exit(1)

file_path = input_data.get('file_path', '')

# Validate path traversal
if '..' in file_path:
    print("Security: Path traversal detected", file=sys.stderr)
    sys.exit(2)

# Rest of hook logic...

output = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow"
    }
}
print(json.dumps(output))
sys.exit(0)
```

**Enforcer output:** (none - silent pass)

**Result:** ✓ ALLOWED

---

## Benefits

### 1. Prevents Technical Debt

By enforcing standards at write-time, the enforcer prevents accumulation of non-compliant code that would need refactoring later.

### 2. Education

The detailed error messages teach developers official documentation requirements as they code.

### 3. Consistency

All hooks follow the same patterns, making the codebase easier to maintain.

### 4. Security

Critical security requirements (path traversal, input validation) are enforced automatically.

### 5. Future-Proof

As official documentation evolves, the enforcer can be updated to reflect new requirements.

---

## Limitations

### 1. Only Validates Write Operations

Edit operations are not validated because it's difficult to predict the final content after an edit.

**Workaround:** Read the file, make changes, then Write (which will be validated).

### 2. AST-Based Analysis Only

The enforcer can't detect logical issues, only syntactic patterns.

**Example of what it can't catch:**
```python
# Technically has path traversal check, but logic is wrong
if '..' not in file_path:  # Should be "in", not "not in"
    print("Security: Path traversal detected", file=sys.stderr)
    sys.exit(2)
```

### 3. False Positives Possible

Some valid code might be flagged if it uses non-standard patterns.

**Workaround:** Use SUDO bypass and document why the deviation is needed.

### 4. Self-Modification Risk

The enforcer can't validate itself (self-exclusion to prevent infinite loop).

**Mitigation:** Manually review changes to `hook_documentation_enforcer.py`.

---

## Configuration

### Registration in settings.json

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/hook_documentation_enforcer.py"
          }
        ]
      }
    ]
  }
}
```

**Placement:** Should run BEFORE other Write hooks so it can block early.

### Disabling the Enforcer

**Temporary (per-write):**
Use SUDO keyword in prompt.

**Permanent:**
Comment out the hook in settings.json:
```json
{
  "matcher": "Write",
  "hooks": [
    // {
    //   "type": "command",
    //   "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/hook_documentation_enforcer.py"
    // }
  ]
}
```

---

## Testing

### Test 1: Valid Hook

```bash
cat > /tmp/test_hook.py <<'EOF'
#!/usr/bin/env python3
import sys
import json

try:
    data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}))
EOF

echo '{"toolName": "Write", "toolInput": {"file_path": ".claude/hooks/test.py", "content": "'"$(cat /tmp/test_hook.py | sed 's/"/\\"/g')"'"}}' | \
  python3 .claude/hooks/hook_documentation_enforcer.py
```

**Expected:** `"permissionDecision": "allow"`

### Test 2: Missing JSONDecodeError

```bash
cat > /tmp/bad_hook.py <<'EOF'
#!/usr/bin/env python3
import sys
import json

data = json.load(sys.stdin)  # No error handling
EOF

echo '{"toolName": "Write", "toolInput": {"file_path": ".claude/hooks/bad.py", "content": "'"$(cat /tmp/bad_hook.py | sed 's/"/\\"/g')"'"}}' | \
  python3 .claude/hooks/hook_documentation_enforcer.py
```

**Expected:** `"permissionDecision": "deny"` with JSONDecodeError violation

---

## Maintenance

### Updating Validation Rules

When official documentation changes:

1. Update validation methods in `HookValidator` class
2. Add/modify checks in respective methods
3. Test with known good/bad examples
4. Update this documentation

### Adding New Checks

```python
def check_new_requirement(self):
    """
    Requirement: Description of new requirement

    Official docs: Reference to documentation
    """
    # Detection logic
    if violation_detected:
        self.violations.append((
            "SEVERITY",  # CRITICAL, HIGH, or MEDIUM
            "Detailed explanation\n"
            "Per official docs: ...\n"
            "Required pattern:\n"
            "  code example"
        ))
```

Then call it in `validate_all()`:
```python
def validate_all(self):
    # ... existing checks ...
    self.check_new_requirement()
    return len(self.violations) == 0
```

---

## Official Documentation References

All requirements enforced by this meta-hook come from:

1. **Hooks Guide:** `/en/hooks-guide`
   - Quickstart and best practices
   - Example implementations
   - Security considerations

2. **Hooks Reference:** `/en/hooks`
   - Event types and descriptions
   - Input/output schemas
   - Exit code semantics
   - Matcher syntax

3. **Security Considerations:** `/en/hooks#security-considerations`
   - Path traversal prevention
   - Input validation
   - Shell injection prevention
   - Security best practices checklist

---

## Conclusion

The Hook Documentation Enforcer is a **meta-level quality gate** that ensures all hooks comply with official standards. By catching violations at write-time, it prevents technical debt and educates developers on proper hook implementation.

**Key Principle:** If it's in the official documentation, it's enforced by the meta-hook.

---

**Status:** ✓ ACTIVE
**Registered:** settings.json → PreToolUse → Write matcher
**Self-Validates:** No (self-excluded to prevent recursion)
**Bypass:** SUDO keyword in prompt
