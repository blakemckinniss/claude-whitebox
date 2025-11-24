#!/usr/bin/env python3
"""
Prototype: Parallel Hook Execution
Demonstrates how to refactor Claude Code's hook system for parallel execution
"""

import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple
from pathlib import Path

# Find project root
current = Path(__file__).resolve()
while current != current.parent:
    if (current / "scripts" / "lib" / "core.py").exists():
        PROJECT_ROOT = current
        break
    current = current.parent
else:
    raise RuntimeError("Could not find project root")


class HookResult:
    """Result of a hook execution"""
    def __init__(self, hook_name: str, success: bool, output: str, error: str, duration_ms: float):
        self.hook_name = hook_name
        self.success = success
        self.output = output
        self.error = error
        self.duration_ms = duration_ms


def execute_hook(hook: Dict[str, Any], context: Dict[str, Any]) -> HookResult:
    """Execute a single hook"""
    start_time = time.time()
    hook_name = hook.get("command", "unknown")

    try:
        # Run hook command
        result = subprocess.run(
            ["bash", "-c", hook["command"]],
            capture_output=True,
            text=True,
            timeout=5,  # 5s timeout per hook
            cwd=str(PROJECT_ROOT)
        )

        duration_ms = (time.time() - start_time) * 1000

        return HookResult(
            hook_name=hook_name,
            success=result.returncode == 0,
            output=result.stdout,
            error=result.stderr,
            duration_ms=duration_ms
        )

    except subprocess.TimeoutExpired:
        duration_ms = (time.time() - start_time) * 1000
        return HookResult(
            hook_name=hook_name,
            success=False,
            output="",
            error=f"Hook timeout after 5s",
            duration_ms=duration_ms
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return HookResult(
            hook_name=hook_name,
            success=False,
            output="",
            error=str(e),
            duration_ms=duration_ms
        )


def categorize_hooks(hooks: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
    """
    Categorize hooks into independent (parallel-safe) and dependent (must be sequential)

    Rules:
    - State-modifying hooks (write files, update session state) = dependent
    - Read-only hooks (analysis, reporting, context injection) = independent
    """

    # Known dependent patterns (ORDER MATTERS)
    dependent_patterns = [
        "command_tracker.py",  # Must run first to track commands
        "session_context.py",  # Updates session state
        "auto_remember.py",    # Writes to memory files
    ]

    independent = []
    dependent = []

    for hook in hooks:
        command = hook.get("command", "")

        # Check if hook matches dependent pattern
        is_dependent = any(pattern in command for pattern in dependent_patterns)

        if is_dependent:
            dependent.append(hook)
        else:
            independent.append(hook)

    return independent, dependent


def execute_hooks_parallel(hooks: List[Dict[str, Any]], context: Dict[str, Any], max_workers: int = 10) -> List[HookResult]:
    """
    Execute hooks with intelligent parallelization

    Strategy:
    1. Categorize hooks into independent (parallel-safe) vs dependent (sequential)
    2. Run independent hooks in parallel (ThreadPoolExecutor)
    3. Run dependent hooks sequentially (preserve order)
    4. Aggregate results
    """

    independent, dependent = categorize_hooks(hooks)

    print(f"Executing {len(hooks)} hooks:")
    print(f"  - {len(independent)} independent (parallel)")
    print(f"  - {len(dependent)} dependent (sequential)")

    results = []

    # Phase 1: Execute dependent hooks sequentially (order matters)
    for hook in dependent:
        result = execute_hook(hook, context)
        results.append(result)
        print(f"  [SEQUENTIAL] {result.hook_name}: {result.duration_ms:.0f}ms")

    # Phase 2: Execute independent hooks in parallel
    if independent:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(execute_hook, hook, context): hook
                for hook in independent
            }

            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                print(f"  [PARALLEL] {result.hook_name}: {result.duration_ms:.0f}ms")

    return results


def benchmark_comparison():
    """Compare sequential vs parallel execution"""

    # Load actual hooks from settings
    settings_path = PROJECT_ROOT / ".claude" / "settings.json"
    with open(settings_path) as f:
        settings = json.load(f)

    hooks = settings["hooks"]["UserPromptSubmit"][0]["hooks"]

    context = {}  # Mock context

    print("="*70)
    print("HOOK EXECUTION BENCHMARK")
    print("="*70)

    # Sequential execution
    print("\n1. SEQUENTIAL EXECUTION (Current)")
    print("-"*70)
    start = time.time()
    sequential_results = []
    for hook in hooks:
        result = execute_hook(hook, context)
        sequential_results.append(result)
    sequential_time = (time.time() - start) * 1000
    print(f"Total time: {sequential_time:.0f}ms")

    # Parallel execution
    print("\n2. PARALLEL EXECUTION (Proposed)")
    print("-"*70)
    start = time.time()
    parallel_results = execute_hooks_parallel(hooks, context, max_workers=10)
    parallel_time = (time.time() - start) * 1000
    print(f"Total time: {parallel_time:.0f}ms")

    # Comparison
    print("\n" + "="*70)
    print("PERFORMANCE COMPARISON")
    print("="*70)
    speedup = sequential_time / parallel_time
    print(f"Sequential: {sequential_time:.0f}ms")
    print(f"Parallel:   {parallel_time:.0f}ms")
    print(f"Speedup:    {speedup:.1f}x")
    print(f"Savings:    {sequential_time - parallel_time:.0f}ms per user prompt")

    # Per-hook breakdown
    print("\nPer-hook timing:")
    for result in sorted(parallel_results, key=lambda r: r.duration_ms, reverse=True):
        print(f"  {result.duration_ms:>6.0f}ms - {result.hook_name}")


def generate_implementation_guide():
    """Generate guide for implementing parallel hooks in Claude Code"""

    guide = """
================================================================================
PARALLEL HOOK EXECUTION - IMPLEMENTATION GUIDE
================================================================================

PROBLEM:
  Current: 21 hooks run sequentially (~1050ms latency per user prompt)
  Impact: Every user message has >1s delay before Claude starts responding

SOLUTION:
  Intelligent parallel execution with dependency awareness

IMPLEMENTATION STEPS:

1. CREATE HOOK CATEGORIZATION SYSTEM
   Location: .claude/hooks/hook_categories.json
   Content: {
     "dependent": [
       "command_tracker.py",
       "session_context.py",
       "auto_remember.py"
     ],
     "independent": [
       ... all other hooks ...
     ]
   }

2. REFACTOR HOOK EXECUTOR
   Location: Claude Code core (requires Claude team)
   Changes:
   - Read hook categories
   - Use ThreadPoolExecutor for independent hooks
   - Preserve sequential execution for dependent hooks
   - Aggregate results

3. ADD HOOK METADATA
   Each hook should declare:
   - reads: [list of files/state it reads]
   - writes: [list of files/state it modifies]
   - dependencies: [list of hooks that must run before this one]

4. VALIDATION
   - Test that dependent hooks still execute in order
   - Verify no race conditions on shared state
   - Measure actual speedup

EXPECTED RESULTS:
  - 10-20x speedup (1050ms → 50-100ms)
  - No behavioral changes (same outputs)
  - Better user experience (faster response)

ALTERNATIVE (SIMPLER):
  If Claude Code doesn't support parallel hooks:
  - Consolidate multiple hooks into fewer multi-purpose hooks
  - Move slow operations to background processes
  - Cache hook results where possible

================================================================================
    """

    print(guide)


def main():
    print("\n")
    benchmark_comparison()
    print("\n")
    generate_implementation_guide()


if __name__ == "__main__":
    main()
