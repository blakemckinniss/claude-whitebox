# Batching Examples

## ✅ CORRECT (Parallel Execution)

### Example 1: Reading Multiple Files
```
Assistant sends SINGLE message with:
- Read(src/auth.py)
- Read(src/api.py)
- Read(src/database.py)

Result: All 3 files read simultaneously, single response
Time: ~2 seconds total
```

### Example 2: Multiple Search Patterns
```
Assistant sends SINGLE message with:
- Grep(pattern="class User")
- Grep(pattern="def authenticate")
- Grep(pattern="import jwt")

Result: All 3 searches execute in parallel
Time: ~1 second total
```

### Example 3: Multiple Web Fetches
```
Assistant sends SINGLE message with:
- WebFetch(url=fastapi_docs)
- WebFetch(url=pydantic_docs)
- WebFetch(url=sqlalchemy_docs)

Result: All URLs fetched concurrently
Time: ~3 seconds (vs 9 seconds sequential)
```

## ❌ INCORRECT (Sequential Execution) - BLOCKED

### Example 1: Sequential Reads (BLOCKED)
```
Turn 1: Read(src/auth.py)
[Wait 2 seconds for response]
Turn 2: Read(src/api.py)
[Wait 2 seconds for response]
Turn 3: Read(src/database.py)
[Wait 2 seconds for response]

Result: BLOCKED by native_batching_enforcer.py
Error: "🚫 SEQUENTIAL READ DETECTED - use parallel invocation"
```

### Example 2: Sequential Web Fetches (BLOCKED)
```
Turn 1: WebFetch(fastapi_docs)
[Wait 3 seconds]
Turn 2: WebFetch(pydantic_docs)

Result: BLOCKED on Turn 2
Error: "🚫 SEQUENTIAL WEB OPERATION DETECTED"
```

## ✅ LEGITIMATE SEQUENTIAL (Allowed)

### Example 1: Dependency Chain
```
Turn 1: Read(.env) to get API_KEY value
Turn 2: Read(config/{API_KEY}.json) using extracted value

Rationale: File path depends on content from previous read
Enforcement: NOT BLOCKED (dependency exists)
```

### Example 2: Conditional Logic
```
Turn 1: Glob(pattern="**/*.test.js") to check if tests exist
Turn 2: IF tests exist, Read(package.json) to check test command

Rationale: Second operation is conditional on first result
Enforcement: NOT BLOCKED (conditional flow)
```

### Example 3: Iterative Refinement
```
Turn 1: Grep(pattern="class.*User") to find User classes
Turn 2: Analyze results
Turn 3: Grep(pattern="def.*validate") in specific files found in step 1

Rationale: Second search informed by first search results
Enforcement: NOT BLOCKED (iterative refinement)
```

## 🛡️ Bypass for Special Cases

User can explicitly request sequential execution:

```
User: "SEQUENTIAL: Read auth.py first, analyze it thoroughly,
       then based on your analysis read api.py"

Result: native_batching_enforcer.py checks for "SEQUENTIAL" keyword
        and allows sequential execution
```

## 📊 Performance Comparison

| Operation | Sequential | Parallel | Speedup |
|-----------|-----------|----------|---------|
| Read 3 files | 6s (3×2s) | 2s | 3x |
| Grep 5 patterns | 5s (5×1s) | 1s | 5x |
| WebFetch 4 URLs | 12s (4×3s) | 3s | 4x |
| Read 10 files | 20s (10×2s) | 2s | 10x |

## 🎯 Smart Batching Limits

### Context-Aware Batching

**Scenario:** User asks "Analyze all files in src/"

**Wrong Approach:**
```
Glob(src/**/*.py) → 100 files
Read all 100 files in parallel
Result: Context overflow (exceeds 200K tokens)
```

**Correct Approach:**
```
Option 1: Use Task agent (separate context)
  Task(subagent_type="Explore", prompt="Analyze src/ directory")

Option 2: Write script with parallel.py
  Write(scratch/analyze_src.py)
  - Uses run_parallel() with max_workers=50
  - Processes 100 files with progress bar
  - Returns summary only
```

### File Count Thresholds

| Tool | Threshold | Action |
|------|-----------|--------|
| Read | <10 files | Parallel native invocation |
| Read | 10-50 files | Task agent with Explore |
| Read | >50 files | Script with parallel.py |
| Grep | <20 patterns | Parallel native invocation |
| Grep | >20 patterns | Script with batch_map() |
| WebFetch | <5 URLs | Parallel native invocation |
| WebFetch | >5 URLs | Script or rate limit handling |

## 🔍 Detection Hook Logic

```python
# Simplified pseudo-code
if current_tool in ["Read", "WebFetch", "WebSearch"]:
    same_tool_count_in_turn = count_tools_in_current_turn(current_tool)

    if same_tool_count_in_turn >= 1:
        # Already called once this turn
        # Second call = sequential pattern
        BLOCK with error message

elif current_tool in ["Grep", "Glob"]:
    same_tool_count_in_turn = count_tools_in_current_turn(current_tool)

    if same_tool_count_in_turn >= 2:
        # More than 2 calls = potentially inefficient
        WARN (don't block, just suggest)
```

## 📈 Telemetry Metrics

Example telemetry entry:
```json
{
  "timestamp": 1700000000.123,
  "session_id": "abc123",
  "turn": 5,
  "tools_in_turn": 3,
  "unique_tools": 1,
  "batchable_tools": 3,
  "is_batched": true,
  "efficiency_score": 1.0,
  "estimated_time_saved_ms": 4000
}
```

**Efficiency Score Calculation:**
- 1.0 = Perfect batching (multiple batchable tools in one turn)
- 0.5 = Mixed (some batching, some not)
- 0.0 = Sequential (one tool per turn)

**Time Savings Estimation:**
- Assumes 2s per turn roundtrip
- Batching N tools saves (N-1) × 2s
- Example: 3 Reads in 1 turn = saves 4 seconds

## 🎓 Learning from Telemetry

After 10 turns, if batching ratio < 50%, inject warning:

```
⚠️ BATCHING EFFICIENCY REPORT (Last 24h):
   • Batching Ratio: 35% (Target: >80%)
   • Time Saved: 12.5s
   • Avg Tools/Turn: 1.2

RECOMMENDATION: Use more parallel tool invocations.
```

This trains Claude to recognize patterns and adjust behavior.
