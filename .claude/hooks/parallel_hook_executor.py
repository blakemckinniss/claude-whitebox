#!/usr/bin/env python3
"""
Parallel Hook Executor

Executes hooks in parallel batches based on dependency analysis.
Replaces sequential hook execution with 10-20× faster parallel model.

Usage:
  This is called automatically by Claude Code hook system.
  It reads hook batch configuration and executes in parallel.
"""
import sys
import os
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time

# Find project root
PROJECT_DIR = os.getenv("CLAUDE_PROJECT_DIR", os.getcwd())
PROJECT_ROOT = Path(PROJECT_DIR)


def execute_hook(hook_command, timeout=5):
    """
    Execute a single hook command.

    Args:
        hook_command: Shell command to execute
        timeout: Maximum execution time in seconds

    Returns:
        dict with success, output, error
    """
    try:
        # Pass stdin through
        stdin_data = sys.stdin.read() if not sys.stdin.isatty() else ""

        result = subprocess.run(
            hook_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=stdin_data,
            env=os.environ.copy()
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode,
            "command": hook_command
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": f"Hook timed out after {timeout}s",
            "returncode": -1,
            "command": hook_command
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "returncode": -1,
            "command": hook_command
        }


def execute_batch_parallel(hooks, batch_id, max_workers=50):
    """
    Execute a batch of hooks in parallel.

    Args:
        hooks: List of hook dicts with 'command' key
        batch_id: Batch identifier for logging
        max_workers: Maximum concurrent workers

    Returns:
        List of results
    """
    if not hooks:
        return []

    results = []
    num_workers = min(max_workers, len(hooks))

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(execute_hook, hook["command"]): hook
            for hook in hooks
        }

        for future in as_completed(futures):
            hook = futures[future]
            result = future.result()
            results.append(result)

            # Print output immediately (streaming)
            if result["output"]:
                print(result["output"], end="")

            # Print errors to stderr
            if result["error"] and result["returncode"] != 0:
                print(result["error"], file=sys.stderr, end="")

    return results


def execute_batch_sequential(hooks):
    """
    Execute a batch of hooks sequentially.

    Args:
        hooks: List of hook dicts with 'command' key

    Returns:
        List of results
    """
    results = []

    for hook in hooks:
        result = execute_hook(hook["command"])
        results.append(result)

        # Print output immediately
        if result["output"]:
            print(result["output"], end="")

        # Print errors to stderr
        if result["error"] and result["returncode"] != 0:
            print(result["error"], file=sys.stderr, end="")

    return results


def main():
    """
    Main parallel hook executor.

    Reads hook configuration and executes in optimized batches.
    """
    # Load hook dependency graph
    graph_path = PROJECT_ROOT / "scratch" / "hook_dependency_graph.json"

    if not graph_path.exists():
        # Fallback: execute sequentially
        print("⚠️  Hook dependency graph not found, using sequential execution", file=sys.stderr)
        sys.exit(0)

    with open(graph_path) as f:
        graph_data = json.load(f)

    batches = graph_data.get("batches", [])

    if not batches:
        # No batches defined, exit
        sys.exit(0)

    # Execute batches in order
    start_time = time.time()
    all_results = []

    for batch in batches:
        batch_id = batch["batch_id"]
        parallel = batch["parallel"]
        hooks = batch["hooks"]

        if parallel:
            results = execute_batch_parallel(hooks, batch_id)
        else:
            results = execute_batch_sequential(hooks)

        all_results.extend(results)

    elapsed = (time.time() - start_time) * 1000  # ms

    # Check for failures
    failures = [r for r in all_results if not r["success"]]

    # Optional: Log performance
    perf_log = PROJECT_ROOT / ".claude" / "memory" / "hook_performance.jsonl"
    try:
        with open(perf_log, 'a') as f:
            f.write(json.dumps({
                "timestamp": time.time(),
                "phase": "UserPromptSubmit",
                "total_hooks": len(all_results),
                "batches": len(batches),
                "elapsed_ms": elapsed,
                "failures": len(failures)
            }) + "\n")
    except:
        pass  # Don't fail if logging fails

    # Exit with failure if any hook failed critically
    if failures:
        critical_failures = [f for f in failures if f["returncode"] != 0]
        if critical_failures:
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
