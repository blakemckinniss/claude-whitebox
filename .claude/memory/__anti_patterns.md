# 🚫 The Blacklist: Forbidden Code Patterns

This document defines code patterns that are **strictly forbidden** in this project.
The Sentinel Protocol enforces these rules automatically.

## 1. Security Sins

### Hardcoded Secrets
❌ **Never put keys/tokens in strings. Use `os.getenv`.**
```python
# BAD
api_key = "sk-proj-abc123"
token = "ghp_secret123"

# GOOD
api_key = os.getenv("API_KEY")
```

### Shell Injection
❌ **Never use `subprocess.run(cmd, shell=True)` with user input.**
```python
# BAD
subprocess.run(f"rm -rf {user_input}", shell=True)

# GOOD
subprocess.run(["rm", "-rf", user_input])
```

### Blind Exception Catching
❌ **Never use `except:` or `except Exception:`. Catch specific errors.**
```python
# BAD
try:
    risky_operation()
except:
    pass

# GOOD
try:
    risky_operation()
except FileNotFoundError as e:
    logger.error(f"File not found: {e}")
```

### SQL Injection
❌ **Never use f-strings or string concatenation for SQL queries.**
```python
# BAD
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# GOOD
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

## 2. Architectural Debt

### God Functions
❌ **No function > 50 lines. Break it down.**
- If a function exceeds 50 lines, split it into smaller, focused functions
- Each function should do one thing well
- Use helper functions liberally

### Global State Mutation
❌ **No global variables modified by functions.**
```python
# BAD
counter = 0
def increment():
    global counter
    counter += 1

# GOOD
def increment(counter):
    return counter + 1
```

### Magic Numbers
❌ **No unexplained integers. Use named constants.**
```python
# BAD
if age > 18:
    allow_access()

# GOOD
LEGAL_AGE = 18
if age > LEGAL_AGE:
    allow_access()
```

### Path Hardcoding
❌ **No absolute paths like `/home/user/`. Use `pathlib` or relative paths.**
```python
# BAD
with open("/home/user/data.txt") as f:
    content = f.read()

# GOOD
from pathlib import Path
data_file = Path(__file__).parent / "data.txt"
with open(data_file) as f:
    content = f.read()
```

### Excessive Nesting
❌ **Cyclomatic complexity > 10. Refactor deeply nested code.**
- If you have more than 3 levels of nesting, refactor
- Use early returns to reduce nesting
- Extract complex conditions into helper functions

## 3. Insidious Drift

### Mixed Naming Conventions
❌ **Do not mix `camelCase` and `snake_case`.**
```python
# BAD
def getUserName():  # camelCase
    user_id = 123  # snake_case

# GOOD
def get_user_name():
    user_id = 123
```

### Zombie Code
❌ **Do not leave commented-out code blocks.**
```python
# BAD
def process_data(data):
    # old_method(data)
    # result = legacy_transform(data)
    return new_method(data)

# GOOD
def process_data(data):
    return new_method(data)
```

### Lazy Imports
❌ **No `from module import *`.**
```python
# BAD
from os import *

# GOOD
from os import path, environ
```

### Print Debugging
❌ **No `print()` in production code. Use `logger`.**
```python
# BAD
def process():
    print("Starting process")
    result = compute()
    print(f"Result: {result}")

# GOOD
def process():
    logger.info("Starting process")
    result = compute()
    logger.info(f"Result: {result}")
```

### Leftover Debug Tools
❌ **No `pdb.set_trace()` or `breakpoint()` in commits.**
```python
# BAD
def debug_me():
    import pdb; pdb.set_trace()
    return result

# GOOD
def debug_me():
    return result
```

### TODO Commits
❌ **Do not commit code with `TODO: Implement this`.**
```python
# BAD
def new_feature():
    # TODO: Implement this
    pass

# GOOD
# Either implement it, or create a GitHub issue and remove the TODO
def new_feature():
    raise NotImplementedError("Feature pending - see issue #123")
```

## 4. SDK Compliance Violations

### Missing Dry-Run Support
❌ **All mutating scripts must support `--dry-run`.**
- Any script that writes files, modifies databases, or calls APIs must check `args.dry_run`

### Missing Error Handling
❌ **All scripts must use try/except with `finalize(success=False)`.**
- Never let exceptions bubble to the user without logging
- Always call `finalize()` to set proper exit codes

### Missing Logging
❌ **All scripts must use `logger` instead of `print()`.**
- Import from `core`: `from core import logger`
- Use appropriate levels: `logger.info()`, `logger.warning()`, `logger.error()`

### Bypassing Core Library
❌ **Do not reimplement `setup_script()` or `finalize()`.**
- Always use the SDK: `from core import setup_script, finalize`
- Follow the scaffolder template pattern

---

## Enforcement

These patterns are detected automatically by:
1. **The Sentinel (`.claude/ops/audit.py`)** - Static analysis + custom regex
2. **Pre-Write Hook (`.claude/hooks/pre_write_audit.py`)** - Blocks deadly sins before write
3. **Manual Review** - Code reviews reference this document

## Severity Levels

- 🔴 **CRITICAL**: Security issues (secrets, injection) - Block commit
- 🟡 **WARNING**: Architectural debt (complexity, globals) - Require fix
- 🔵 **INFO**: Style drift (naming, formatting) - Suggest fix

---

*This document is living. Add new anti-patterns as they are discovered.*
*Last updated: 2025-11-20*
