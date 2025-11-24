# Background Execution Strategy

## Problem: Unutilized Capability

Claude has `run_in_background` parameter for Bash tool, but **NEVER uses it**.

### Current State
- Background execution: 0 uses (searched entire codebase)
- BashOutput tool: 0 uses (for monitoring background processes)
- KillShell tool: 0 uses (for terminating background processes)

### Impact
- Long-running commands block entire session
- Test suites, builds, downloads all executed synchronously
- No parallel Bash operations (single-threaded execution)

## Opportunity: Massive Parallelism Gains

### Use Cases for Background Execution

1. **Test Suites** (slow, independent)
   ```bash
   # Current: Blocks for 30s
   pytest tests/ --verbose

   # Better: Run in background, continue working
   pytest tests/ --verbose
   [run_in_background: true]

   # Check status later
   BashOutput(bash_id)
   ```

2. **Build Operations** (slow, CPU-intensive)
   ```bash
   # Current: Blocks for 60s
   npm run build

   # Better: Build in background
   npm run build
   [run_in_background: true]

   # Continue with other tasks while building
   ```

3. **Downloads/Installs** (slow, network I/O)
   ```bash
   # Current: Blocks for 120s
   pip install -r requirements.txt

   # Better: Install in background
   pip install -r requirements.txt
   [run_in_background: true]

   # Check completion later
   ```

4. **Database Operations** (slow, I/O-bound)
   ```bash
   # Current: Blocks for 45s
   python scripts/migrate_database.py

   # Better: Migrate in background
   python scripts/migrate_database.py
   [run_in_background: true]
   ```

5. **File Processing** (slow, CPU/I/O)
   ```bash
   # Current: Blocks for 90s
   python scripts/process_10000_files.py

   # Better: Process in background
   python scripts/process_10000_files.py
   [run_in_background: true]
   ```

6. **Multiple Independent Operations**
   ```bash
   # Current: Sequential (3 minutes total)
   pytest tests/unit/ && npm run lint && mypy src/

   # Better: All 3 in parallel backgrounds
   Message 1:
     Bash(pytest tests/unit/, run_in_background=true)
     Bash(npm run lint, run_in_background=true)
     Bash(mypy src/, run_in_background=true)

   Message 2 (after 30s):
     BashOutput(test_id)
     BashOutput(lint_id)
     BashOutput(mypy_id)
   ```

## Detection Heuristics

### When to Use Background Execution

**Automatic triggers:**
- Command contains: `pytest`, `npm test`, `cargo test` → Background
- Command contains: `npm run build`, `cargo build`, `make` → Background
- Command contains: `pip install`, `npm install`, `cargo install` → Background
- Command estimated runtime >5 seconds → Background
- Multiple independent Bash calls in same response → All background

**Manual indicators:**
- User says "run tests" (tests always slow)
- User says "build" or "compile"
- User says "install dependencies"
- User says "while that runs" (explicit parallelism intent)

### When NOT to Use Background

**Synchronous requirements:**
- Next operation depends on output (git status before git add)
- Interactive commands (git rebase -i, vim)
- Commands that modify session state (cd, export)
- Fast commands (<2 seconds estimated)
- Single command where result is immediately needed

## Enforcement Strategy

### Three-Layer System (Similar to Batching)

1. **Detection Hook** (PreToolUse:Bash)
   - Analyze command for slow operation patterns
   - Check if multiple Bash calls in same response
   - SUGGEST (not block) background execution if detected

2. **Recommendation Injector** (UserPromptSubmit)
   - Detect user intent for slow operations
   - Inject background execution guidance
   - Example: "run tests" → "Use run_in_background=true"

3. **Telemetry Tracker** (PostToolUse:Bash)
   - Track background vs foreground ratio
   - Measure time savings (estimated)
   - Report underutilization warnings

## Implementation Plan

### Hook 1: Background Operation Detector

```python
# .claude/hooks/detect_background_opportunity.py

SLOW_COMMANDS = [
    "pytest", "test", "npm test", "cargo test",
    "npm run build", "cargo build", "make",
    "pip install", "npm install", "cargo install",
    "docker build", "docker-compose up",
]

def should_use_background(command):
    # Pattern matching
    for pattern in SLOW_COMMANDS:
        if pattern in command.lower():
            return True

    # Estimated runtime (very rough heuristic)
    if any(x in command for x in ["pytest tests/", "npm run"]):
        return True

    return False

# Hook logic
if should_use_background(command):
    print("""
    💡 BACKGROUND EXECUTION OPPORTUNITY

    This command appears to be slow (>5s).

    RECOMMENDATION: Use run_in_background=true

    Benefits:
    - Continue working while command runs
    - Check results later with BashOutput tool
    - Parallel execution of multiple commands

    Example:
      Bash(
        command="pytest tests/",
        run_in_background=true
      )

      [Do other work]

      BashOutput(bash_id=<shell_id>)
    """)
```

### Hook 2: Multi-Bash Detector

```python
# .claude/hooks/detect_parallel_bash.py (PreToolUse:Bash)

# Track Bash calls in current response
if "bash_calls_in_response" not in state:
    state["bash_calls_in_response"] = 0

state["bash_calls_in_response"] += 1

if state["bash_calls_in_response"] >= 2:
    print("""
    ⚡ MULTIPLE BASH OPERATIONS DETECTED

    You're executing 2+ Bash commands in this response.

    RECOMMENDATION: Use run_in_background=true for all

    Pattern:
      Bash(cmd1, run_in_background=true)
      Bash(cmd2, run_in_background=true)
      Bash(cmd3, run_in_background=true)

      [Single response, 3 parallel processes]

      Later: BashOutput to collect results

    Benefits: 3x+ speedup for independent operations
    """)
```

### Hook 3: Background Usage Telemetry

```python
# .claude/hooks/background_telemetry.py (PostToolUse:Bash)

# Track usage
if "run_in_background" in tool_params:
    is_background = tool_params["run_in_background"]
else:
    is_background = False

# Record metric
telemetry.append({
    "tool": "Bash",
    "background": is_background,
    "command": tool_params.get("command", "")[:100],
    "timestamp": time.time()
})

# Periodic report
if turn % 20 == 0:
    background_ratio = sum(t["background"] for t in telemetry) / len(telemetry)

    if background_ratio < 0.1:  # <10% background usage
        print(f"""
        ⚠️ BACKGROUND EXECUTION UNDERUTILIZED

        Background usage: {background_ratio:.0%} (Target: >30%)

        You have run {len(telemetry)} Bash commands, but only
        {sum(t["background"] for t in telemetry)} in background.

        IMPACT: Wasted time waiting for slow operations.

        SOLUTION: Use run_in_background=true for:
        - Tests (pytest, npm test)
        - Builds (npm run build, cargo build)
        - Installs (pip install, npm install)
        - Long-running scripts (>5s)
        """)
```

## Documentation Updates

### CLAUDE.md Addition

**New Hard Block #12:**
```markdown
12. **Background Execution:** For slow operations (tests, builds, installs),
    you MUST use run_in_background=true. Blocking on slow commands wastes
    session time. Use BashOutput to check results later. Multiple independent
    Bash operations MUST run in parallel backgrounds.
```

**New Section: § Background Execution Protocol**
```markdown
## 🔄 Background Execution Protocol

**MANDATE:** Slow operations (>5s) MUST run in background.

### When to Use Background

**Always Background:**
- Test suites: pytest, npm test, cargo test
- Builds: npm run build, cargo build, make
- Installs: pip install, npm install
- Long scripts: >5 second estimated runtime

**Pattern:**
```python
# Start background process
Bash(
  command="pytest tests/",
  run_in_background=true
)

# Continue with other work
[Read files, analyze code, write docs]

# Check results later
BashOutput(bash_id="<shell_id>")
```

### Multiple Parallel Backgrounds

For independent operations, run ALL in parallel:

```python
# Single response with 3 backgrounds
Bash("pytest tests/unit/", run_in_background=true)
Bash("npm run lint", run_in_background=true)
Bash("mypy src/", run_in_background=true)

# Later: collect all results
BashOutput(test_shell_id)
BashOutput(lint_shell_id)
BashOutput(mypy_shell_id)
```

**Speedup:** 3x+ for independent operations

### When NOT to Use Background

- Fast commands (<2s)
- Dependent operations (git status before git add)
- Interactive commands (rebase -i, vim)
- Session state changes (cd, export)

### Tools

- `BashOutput(bash_id)` - Check background process output
- `KillShell(shell_id)` - Terminate background process
- `/tasks` - List all running background shells
```

## Performance Impact

### Real-World Scenarios

| Scenario | Foreground | Background | Speedup |
|----------|-----------|-----------|---------|
| Run tests while writing code | 30s blocked | 0s blocked | ∞ |
| 3 independent checks | 60s (3×20s) | 20s | 3x |
| Build + test + lint | 90s | 30s | 3x |
| Install deps + migrate DB | 150s | 60s | 2.5x |

### Key Insight: "Free" Time

**Foreground execution:**
```
Turn 1: pytest tests/ [wait 30s]
Turn 2: Read code [wait 2s]
Total: 32s
```

**Background execution:**
```
Turn 1: pytest tests/ (background) + Read code
Total: 2s (tests finish later, no blocking)
```

**Net gain:** 30 seconds of "free" work while tests run

## Risks & Mitigations

### Risk 1: Forgetting to Check Results

**Problem:** Start background process, never check BashOutput

**Mitigation:**
- Telemetry tracks unchecked backgrounds
- Warning if >5 backgrounds without BashOutput
- Auto-inject reminder after 3 turns

### Risk 2: Resource Exhaustion

**Problem:** 50 parallel backgrounds = system overload

**Mitigation:**
- Detection hook suggests max 5 parallel backgrounds
- Warning if >10 active backgrounds
- Use parallel.py for >10 operations instead

### Risk 3: Dependency Confusion

**Problem:** Start background B that depends on background A

**Mitigation:**
- Detection hook analyzes dependencies
- Suggests sequential if dependency detected
- User can override with explicit background

## Integration Steps

1. **Create detection hook:** `detect_background_opportunity.py`
2. **Create multi-bash detector:** `detect_parallel_bash.py`
3. **Create telemetry hook:** `background_telemetry.py`
4. **Register in settings.json:** PreToolUse:Bash, PostToolUse:Bash
5. **Update CLAUDE.md:** Hard Block #12, § Background Execution Protocol
6. **Create examples:** `scratch/background_examples.md`
7. **Test suite:** Validate detection logic

## Success Metrics

After 1 week:
- **Background usage ratio:** >30% for slow commands
- **Time savings:** 5+ minutes per day (estimated)
- **Parallel backgrounds:** 2+ per session average
- **User experience:** Faster perceived responsiveness

## Examples

### Example 1: Test While Coding

**Current Pattern (Blocking):**
```
User: "Run tests and fix any failures"

Claude:
  Turn 1: Bash("pytest tests/") [blocks 30s]
  Turn 2: Read test output
  Turn 3: Edit code to fix
  Turn 4: Bash("pytest tests/") [blocks 30s]

Total: 60s blocked waiting
```

**With Background:**
```
User: "Run tests and fix any failures"

Claude:
  Turn 1: Bash("pytest tests/", run_in_background=true)
          Read likely failure files
          Analyze code patterns
  Turn 2: BashOutput(test_shell)
          Edit code to fix
          Bash("pytest tests/", run_in_background=true)
  Turn 3: BashOutput(retest_shell)

Total: 0s blocked waiting (tests run while analyzing)
```

### Example 2: Triple Check

**Current Pattern:**
```
Claude:
  Bash("pytest tests/")     [30s]
  Bash("npm run lint")      [15s]
  Bash("mypy src/")         [20s]

Total: 65s sequential
```

**With Background:**
```
Claude (single response):
  Bash("pytest tests/", run_in_background=true)
  Bash("npm run lint", run_in_background=true)
  Bash("mypy src/", run_in_background=true)

  [Do other work for 20s]

  BashOutput(test_id)
  BashOutput(lint_id)
  BashOutput(mypy_id)

Total: 20s (max of 3 operations)
Speedup: 3.25x
```

## Next Steps

1. ✅ Strategy documented
2. ⏳ Create detection hook
3. ⏳ Create multi-bash detector
4. ⏳ Create telemetry hook
5. ⏳ Update CLAUDE.md
6. ⏳ Integration script
7. ⏳ Test suite
8. ⏳ Examples document
