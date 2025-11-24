# Threading & Parallelization - Best Practices Guide

## Core Principle

**I/O-bound = Threads (cheap, many)**
**CPU-bound = Processes (expensive, few)**

---

## When to Use parallel.run_parallel()

### ✅ USE for I/O-Bound Operations

1. **File Operations**
   ```python
   from parallel import run_parallel

   def read_file(filepath):
       with open(filepath) as f:
           return f.read()

   results = run_parallel(read_file, files, max_workers=50)
   ```

2. **Subprocess Calls**
   ```python
   def run_command(cmd):
       return subprocess.run(cmd, timeout=10, capture_output=True)

   run_parallel(run_command, commands, max_workers=20)
   ```

3. **Network/API Calls**
   ```python
   def fetch_url(url):
       return requests.get(url, timeout=5)

   run_parallel(fetch_url, urls, max_workers=50)
   ```

### ❌ DO NOT use for CPU-Bound

```python
# BAD: GIL prevents true parallelism
run_parallel(cpu_intensive_hash, data, max_workers=50)

# GOOD: Use ProcessPoolExecutor for CPU work
from concurrent.futures import ProcessPoolExecutor
with ProcessPoolExecutor() as executor:
    results = executor.map(cpu_intensive_hash, data)
```

---

## max_workers Guidelines

| Operation Type | Recommended max_workers | Rationale |
|----------------|------------------------|-----------|
| Network I/O | 50-100 | Threads mostly idle waiting for network |
| File I/O | 20-50 | Disk I/O can saturate with too many threads |
| Subprocess | 10-20 | Each process consumes resources |
| CPU-bound | os.cpu_count() | More threads = contention |

```python
from parallel import optimal_workers

# Auto-calculate
workers = optimal_workers(len(items), io_bound=True)  # Returns min(100, len(items))
workers = optimal_workers(len(items), io_bound=False) # Returns min(cpu_count, len(items))
```

---

## Error Handling Patterns

### Fail-Safe (Default)
```python
results = run_parallel(func, items)

for item, result, error in results:
    if error:
        print(f"Failed {item}: {error}")
    else:
        print(f"Success: {result}")
```

### Fail-Fast
```python
results = run_parallel(func, items, fail_fast=True)
# Stops on first error
```

### Successes Only
```python
from parallel import batch_map

results = batch_map(func, items)
# Returns only successful results
```

---

## Subprocess Best Practices

### Always Add Timeout
```python
# Context-aware timeouts
timeout = {
    'git push': 30,
    'pytest': 60,
    'npm install': 120,
    'default': 10
}.get(command_type, 10)

subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)
```

### Parallel Subprocess
```python
def run_cmd(cmd):
    return subprocess.run(
        cmd,
        timeout=10,
        capture_output=True,
        text=True,
        check=False  # Don't raise on non-zero exit
    )

results = run_parallel(run_cmd, commands, max_workers=10)
```

---

## Hook Optimization Strategies

### Strategy 1: Consolidation (2-4h effort, 2.6× speedup)

Merge related hooks:
- Memory hooks → unified_memory_manager.py
- Detection hooks → unified_pattern_detector.py
- Epistemology hooks → unified_epistemology_tracker.py

### Strategy 2: Internal Parallelization (30min effort, 2× speedup)

Within each hook, parallelize internal operations:

```python
# hook.py
def run():
    # Parallel analysis
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(check_pattern1): 'pattern1',
            executor.submit(check_pattern2): 'pattern2',
            executor.submit(check_pattern3): 'pattern3',
        }

        results = {name: future.result() for future, name in futures.items()}

    return results
```

### Strategy 3: Categorize Dependencies (External, 10× speedup)

Requires Claude Code core changes:

```json
{
  "dependent": ["command_tracker.py", "session_context.py"],
  "independent": ["all", "other", "hooks"]
}
```

Then execute independent hooks in parallel.

---

## Agent Delegation (CRITICAL)

### ❌ WRONG: Sequential
```
Turn 1: Spawn Agent A → wait
Turn 2: Spawn Agent B → wait
Turn 3: Spawn Agent C → wait
Total: 3× wait time
```

### ✅ RIGHT: Parallel
```
Turn 1: Spawn A, B, C simultaneously (single message, multiple Task calls)
Total: 1× wait time (3× faster)
```

**Key Insight:** Each agent gets FREE separate context window!

---

## Common Anti-Patterns

### 1. Sequential Loop with I/O
```python
# BAD
for file in files:
    content = open(file).read()
    process(content)

# GOOD
def read_and_process(file):
    return process(open(file).read())

run_parallel(read_and_process, files, max_workers=50)
```

### 2. Nested Loops
```python
# BAD
for dir in dirs:
    for file in glob(dir + "/*.py"):
        process(file)

# GOOD
all_files = [f for d in dirs for f in glob(d + "/*.py")]
run_parallel(process, all_files, max_workers=50)
```

### 3. Low max_workers for I/O
```python
# SUBOPTIMAL
run_parallel(fetch_url, 1000_urls, max_workers=5)  # Takes 200× longer than needed

# OPTIMAL
run_parallel(fetch_url, 1000_urls, max_workers=100)  # 20× faster
```

---

## Performance Measurement

### Before Optimization
```python
import time

start = time.time()
for item in items:
    process(item)
duration = time.time() - start
print(f"Sequential: {duration:.2f}s")
```

### After Optimization
```python
start = time.time()
run_parallel(process, items, max_workers=50)
duration = time.time() - start
print(f"Parallel: {duration:.2f}s")
print(f"Speedup: {sequential_duration / duration:.1f}×")
```

---

## Summary Checklist

Before writing code, ask:

- [ ] Am I iterating over 3+ items?
- [ ] Does each iteration involve I/O (file, network, subprocess)?
- [ ] Are iterations independent (no shared state)?
- [ ] Is this I/O-bound (not CPU-bound)?

**If all YES → Use run_parallel()**

- [ ] Choose max_workers based on I/O type
- [ ] Add timeout to subprocess calls
- [ ] Handle errors gracefully
- [ ] Measure speedup

---

## Quick Reference

```python
from parallel import run_parallel, batch_map, optimal_workers

# Basic usage
results = run_parallel(func, items, max_workers=50, desc="Processing")

# Successes only
results = batch_map(func, items, max_workers=50)

# Auto-calculate workers
workers = optimal_workers(len(items), io_bound=True)
results = run_parallel(func, items, max_workers=workers)

# Extract results
for item, result, error in results:
    if error:
        handle_error(item, error)
    else:
        use_result(result)
```

---

**Remember:** Threads are cheap for I/O. Don't be afraid to use 50-100 workers.
