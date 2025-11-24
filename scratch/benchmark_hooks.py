#!/usr/bin/env python3
"""
Hook Performance Benchmark - Measure serial vs async execution

Test scenarios:
1. PostToolUse with all 23 hooks (current bottleneck)
2. SessionStart with 6 hooks (startup time)
3. UserPromptSubmit with 22 hooks (prompt latency)

Expected results:
- Serial PostToolUse: ~2-3s
- Async PostToolUse: <500ms (if mostly telemetry)
- ROI: 4-6x speedup for PostToolUse lifecycle
"""

import json
import subprocess
import time
from pathlib import Path
import sys

def benchmark_lifecycle(lifecycle: str, mode: str, iterations: int = 3) -> float:
    """Run hook orchestrator and measure execution time"""
    script = Path(__file__).parent / "hook_orchestrator.py"

    # Sample context (minimal valid JSON)
    context = {
        "lifecycle": lifecycle,
        "timestamp": time.time(),
        "test": True,
    }

    times = []

    for i in range(iterations):
        start = time.time()

        try:
            result = subprocess.run(
                ["python3", str(script), lifecycle, mode],
                input=json.dumps(context),
                capture_output=True,
                text=True,
                timeout=30,
            )

            duration = time.time() - start
            times.append(duration)

            print(f"  Run {i+1}: {duration:.3f}s (exit {result.returncode})")

            # Print stderr for diagnostics
            if result.stderr:
                for line in result.stderr.split('\n'):
                    if 'EXECUTION:' in line or 'HOOK FAILED:' in line:
                        print(f"    {line}")

        except subprocess.TimeoutExpired:
            print(f"  Run {i+1}: TIMEOUT")
            times.append(30.0)
        except Exception as e:
            print(f"  Run {i+1}: ERROR - {e}")

    avg_time = sum(times) / len(times) if times else 0
    return avg_time


def main():
    print("=== HOOK ORCHESTRATOR BENCHMARK ===\n")

    lifecycles = ["PostToolUse", "SessionStart", "UserPromptSubmit"]
    results = {}

    for lifecycle in lifecycles:
        print(f"\n{lifecycle} Lifecycle:")
        print("-" * 50)

        print(f"\nSERIAL MODE (current behavior):")
        serial_time = benchmark_lifecycle(lifecycle, "serial", iterations=3)

        print(f"\nASYNC MODE (new behavior):")
        async_time = benchmark_lifecycle(lifecycle, "async", iterations=3)

        speedup = serial_time / async_time if async_time > 0 else 0

        results[lifecycle] = {
            "serial": serial_time,
            "async": async_time,
            "speedup": speedup,
        }

        print(f"\nRESULTS:")
        print(f"  Serial avg: {serial_time:.3f}s")
        print(f"  Async avg:  {async_time:.3f}s")
        print(f"  Speedup:    {speedup:.2f}x")
        print(f"  Savings:    {(serial_time - async_time):.3f}s per invocation")

    print("\n\n=== SUMMARY ===")
    print(f"{'Lifecycle':<20} {'Serial':<10} {'Async':<10} {'Speedup':<10}")
    print("-" * 60)

    for lifecycle, data in results.items():
        print(f"{lifecycle:<20} {data['serial']:>8.3f}s {data['async']:>8.3f}s {data['speedup']:>8.2f}x")

    # Calculate session impact
    print("\n=== SESSION IMPACT (100 tool uses) ===")
    for lifecycle in ["PostToolUse"]:  # Most frequent
        if lifecycle in results:
            serial_100 = results[lifecycle]["serial"] * 100
            async_100 = results[lifecycle]["async"] * 100
            savings = serial_100 - async_100

            print(f"{lifecycle}:")
            print(f"  Serial:  {serial_100:.1f}s ({serial_100/60:.1f} minutes)")
            print(f"  Async:   {async_100:.1f}s ({async_100/60:.1f} minutes)")
            print(f"  Savings: {savings:.1f}s ({savings/60:.1f} minutes per 100 tool uses)")


if __name__ == "__main__":
    main()
