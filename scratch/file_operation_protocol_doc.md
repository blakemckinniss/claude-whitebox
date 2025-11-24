# File Operation Validation Protocol (22nd Protocol)

## Problem Statement

Claude frequently attempts invalid file operations that fail with confusing errors:

1. **Read to non-existent file**: Wastes turns and adds noise
2. **Read to directory**: Confuses file vs directory paths
3. **Write without Read first**: Overwrites files blindly without understanding context
4. **Write to directory path**: Attempts to write a file to a directory
5. **Edit non-existent file**: Should use Write for new files
6. **Edit without Read first**: Cannot edit safely without seeing current content

These errors break the "Read before Write/Edit" rule and cause iteration loops.

## Solution: File Operation Gate

PreToolUse hook that validates Read/Write/Edit operations BEFORE execution against filesystem reality.

### Architecture

```
User Prompt → PreToolUse Hook → File Operation Gate
                                        ↓
                                   Validation
                                        ↓
                        ┌───────────────┴───────────────┐
                        ↓                               ↓
                   ALLOW (valid)                   BLOCK (invalid)
                        ↓                               ↓
                Execute tool                    Return error message
```

### Validation Rules

**Read:**
- ✅ File must exist
- ✅ Path must be a file (not directory)
- ✅ Path must be within workspace (security)
- ✅ File must be readable
- Side effect: Track file as "read" for later Write/Edit checks

**Write:**
- ✅ Parent directory must exist
- ✅ Parent must be a directory (not file)
- ✅ Path must not be a directory
- ✅ Path must be within workspace (security)
- ✅ If file exists, must have been Read first
- Side effect: Track file as "read" for later Edit operations

**Edit:**
- ✅ File must exist (use Write for new files)
- ✅ Path must be a file (not directory)
- ✅ Path must be within workspace (security)
- ✅ File must have been Read first (context requirement)
- ✅ File must be writable

### State Tracking

The gate persists `files_read` set in session state to enforce "Read before Write/Edit" across turns:

```python
state = {
    "files_read": [
        "/home/user/project/src/main.py",
        "/home/user/project/README.md"
    ]
}
```

### Bypass Mechanism

Use `SUDO` keyword in prompt to bypass validation (e.g., emergency recovery).

### Error Messages

All blocks include:
- 🚫 Clear block reason
- Path that caused the issue
- Why it failed
- Suggested corrective action

Example:
```
🚫 EDIT BLOCKED: File was not read first

Path: src/auth.py

Reason: You must Read file before editing to understand context.

Action: Read file first using Read tool.

(Use SUDO keyword to bypass)
```

## Implementation

**Hook:** `.claude/hooks/file_operation_gate.py`
**Library:** `scratch/file_operation_validator.py` (reusable validation logic)
**Tests:** `scratch/test_file_operation_gate.py` (10/10 passing)
**Config:** Added to `.claude/settings.json` matcher `(Read|Write|Edit)`

## Benefits

1. **Prevents Wasted Turns**: Blocks invalid operations before execution
2. **Enforces Context Rule**: Cannot Write/Edit without Reading first
3. **Clear Error Messages**: Actionable guidance instead of tool errors
4. **Security**: Prevents path traversal outside workspace
5. **Type Safety**: Ensures files vs directories are used correctly

## Testing Results

```
🧪 File Operation Gate Tests

✅ Test 1: Read non-existent file - BLOCKED
✅ Test 2: Read directory - BLOCKED
✅ Test 3: Valid read - ALLOWED
✅ Test 4: Write without read - BLOCKED
✅ Test 5: Write to directory - BLOCKED
✅ Test 6: Write new file - ALLOWED
✅ Test 7: Edit non-existent file - BLOCKED
✅ Test 8: Edit without read - BLOCKED
✅ Test 9: Read then Edit - ALLOWED
✅ Test 10: SUDO bypass - ALLOWED

📊 Results: 10 passed, 0 failed
```

## Integration with Existing Protocols

- **Complements Command Prerequisite Gate**: Enforces Read→Edit workflow
- **Works with Confidence Gate**: Validates operations at any tier
- **Works with Tier Gate**: Physical validation before tier check
- **Works with Root Pollution Gate**: Both check paths, but different concerns

## Philosophy

**Physical Reality > Internal Model**

The filesystem is ground truth. Claude's internal assumptions about file existence, types, or prior reads are unreliable. This gate enforces objective verification BEFORE attempting operations.

## Related Protocols

- **Reality Check Protocol (15)**: Verifies claims after execution
- **File Operation Protocol (22)**: Verifies file operations before execution

Together they form "Pre-flight + Post-flight verification" safety system.

---

**Status:** ✅ Implemented and tested
**Coverage:** 10/10 test cases passing
**Next Steps:** Monitor false positive rate in production use
