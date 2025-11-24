#!/usr/bin/env python3
"""
Hook Orchestrator - Async execution wrapper for lifecycle hooks

Philosophy: PostToolUse telemetry hooks are currently blocking Claude's response.
Solution: Fire-and-forget background workers for non-critical telemetry.

Current: 23 serial subprocess calls (~2-3s blocking time per tool use)
Target: <100ms orchestration overhead (async worker pool)

Usage:
    python3 hook_orchestrator.py PostToolUse <json_context>

Design:
    - Critical hooks (enforcement): Run synchronously, fail-fast
    - Telemetry hooks (logging): Run async, best-effort
    - Health monitoring: Track hook failures, auto-disable flaky hooks
"""

import asyncio
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any, Tuple
import os

# Hook classifications (move to config later)
HOOK_PRIORITY = {
    # CRITICAL: Must complete before returning (enforcement gates)
    "critical": [],

    # TELEMETRY: Can run async (logging, metrics)
    "telemetry": [
        "auto_commit_telemetry.py",
        "performance_telemetry_collector.py",
        "batching_telemetry.py",
        "background_telemetry.py",
        "scratch_enforcer.py",
        "org_drift_telemetry.py",
        "hook_performance_monitor.py",
        "command_tracker.py",
        "evidence_tracker.py",
    ],

    # LEARNING: Auto-tuning systems (can tolerate some failures)
    "learning": [
        "detect_failure_auto_learn.py",
        "detect_success_auto_learn.py",
        "detect_confidence_reward.py",
        "performance_reward.py",
    ],

    # DETECTION: Pattern detection (run sync but non-blocking on failure)
    "detection": [
        "detect_logical_fallacy.py",
        "detect_tool_failure.py",
        "detect_test_failure.py",
        "detect_batch.py",
        "sanity_check.py",
    ],

    # ADVISORY: Suggestions (async, non-critical)
    "advisory": [
        "auto_researcher.py",
        "post_tool_command_suggester.py",
        "auto_commit_on_complete.py",
        "auto_guardian.py",
        "auto_documentarian.py",
    ],
}

class HookOrchestrator:
    def __init__(self, lifecycle: str, context: Dict[str, Any]):
        self.lifecycle = lifecycle
        self.context = context
        self.project_dir = os.getenv("CLAUDE_PROJECT_DIR", os.getcwd())
        self.hooks_dir = Path(self.project_dir) / ".claude" / "hooks"
        self.results = []

    def get_hooks_for_lifecycle(self) -> List[str]:
        """Extract hook commands from settings.json for given lifecycle"""
        settings_path = Path(self.project_dir) / ".claude" / "settings.json"

        try:
            with open(settings_path) as f:
                settings = json.load(f)
        except Exception as e:
            print(f"ERROR: Cannot read settings.json: {e}", file=sys.stderr)
            return []

        hooks = settings.get("hooks", {}).get(self.lifecycle, [])
        commands = []

        for hook_group in hooks:
            for hook in hook_group.get("hooks", []):
                if hook.get("type") == "command":
                    cmd = hook["command"]
                    # Extract script name from command
                    if ".claude/hooks/" in cmd:
                        script = cmd.split(".claude/hooks/")[1].split()[0]
                        commands.append(script)

        return commands

    def classify_hook(self, hook_name: str) -> str:
        """Determine hook priority class"""
        for priority, hooks in HOOK_PRIORITY.items():
            if hook_name in hooks:
                return priority
        return "critical"  # Unknown hooks default to critical (safe)

    def run_hook_sync(self, hook_name: str) -> Tuple[str, int, str, str, float]:
        """Execute single hook synchronously"""
        start = time.time()
        hook_path = self.hooks_dir / hook_name

        try:
            result = subprocess.run(
                ["python3", str(hook_path)],
                input=json.dumps(self.context),
                capture_output=True,
                text=True,
                timeout=10,  # 10s timeout per hook
                env={**os.environ, "CLAUDE_PROJECT_DIR": self.project_dir}
            )
            duration = time.time() - start
            return (hook_name, result.returncode, result.stdout, result.stderr, duration)
        except subprocess.TimeoutExpired:
            duration = time.time() - start
            return (hook_name, -1, "", f"TIMEOUT after {duration:.1f}s", duration)
        except Exception as e:
            duration = time.time() - start
            return (hook_name, -1, "", f"ERROR: {e}", duration)

    async def run_hook_async(self, hook_name: str) -> Tuple[str, int, str, str, float]:
        """Execute single hook asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.run_hook_sync, hook_name)

    def execute_serial(self, hooks: List[str]) -> List[Tuple[str, int, str, str, float]]:
        """Current behavior: serial execution"""
        start_total = time.time()
        results = []

        for hook in hooks:
            result = self.run_hook_sync(hook)
            results.append(result)

        duration_total = time.time() - start_total
        print(f"SERIAL EXECUTION: {len(hooks)} hooks in {duration_total:.3f}s", file=sys.stderr)
        return results

    async def execute_async(self, hooks: List[str]) -> List[Tuple[str, int, str, str, float]]:
        """New behavior: async execution with priority handling"""
        start_total = time.time()

        # Classify hooks by priority
        critical = []
        async_hooks = []

        for hook in hooks:
            priority = self.classify_hook(hook)
            if priority == "critical":
                critical.append(hook)
            else:
                async_hooks.append(hook)

        results = []

        # Phase 1: Run critical hooks serially (must complete)
        if critical:
            print(f"CRITICAL: Running {len(critical)} hooks serially...", file=sys.stderr)
            for hook in critical:
                result = self.run_hook_sync(hook)
                results.append(result)
                # Stop on critical failure
                if result[1] != 0:
                    print(f"CRITICAL FAILURE: {hook} failed, aborting", file=sys.stderr)
                    return results

        # Phase 2: Fire async hooks (best-effort)
        if async_hooks:
            print(f"ASYNC: Launching {len(async_hooks)} hooks in parallel...", file=sys.stderr)
            tasks = [self.run_hook_async(hook) for hook in async_hooks]
            async_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in async_results:
                if isinstance(result, Exception):
                    print(f"ASYNC ERROR: {result}", file=sys.stderr)
                else:
                    results.append(result)

        duration_total = time.time() - start_total
        print(f"ASYNC EXECUTION: {len(hooks)} hooks in {duration_total:.3f}s", file=sys.stderr)
        print(f"  Critical: {len(critical)} (serial)", file=sys.stderr)
        print(f"  Async: {len(async_hooks)} (parallel)", file=sys.stderr)

        return results

    def aggregate_output(self, results: List[Tuple[str, int, str, str, float]]) -> str:
        """Combine hook outputs (preserve current behavior)"""
        output_parts = []

        for hook_name, returncode, stdout, stderr, duration in results:
            if stdout.strip():
                output_parts.append(stdout.strip())

            # Log failures to stderr
            if returncode != 0:
                print(f"HOOK FAILED: {hook_name} (exit {returncode}, {duration:.3f}s)", file=sys.stderr)
                if stderr.strip():
                    print(f"  {stderr.strip()}", file=sys.stderr)

        return "\n".join(output_parts) if output_parts else ""

    def run(self, mode: str = "async") -> str:
        """Main execution entry point"""
        hooks = self.get_hooks_for_lifecycle()

        if not hooks:
            print(f"No hooks found for lifecycle: {self.lifecycle}", file=sys.stderr)
            return ""

        if mode == "serial":
            results = self.execute_serial(hooks)
        else:
            results = asyncio.run(self.execute_async(hooks))

        self.results = results
        return self.aggregate_output(results)

    def print_stats(self):
        """Performance analysis"""
        if not self.results:
            return

        print("\n=== HOOK PERFORMANCE STATS ===", file=sys.stderr)

        total_time = sum(r[4] for r in self.results)
        max_time = max(r[4] for r in self.results)

        print(f"Total CPU time: {total_time:.3f}s", file=sys.stderr)
        print(f"Longest hook: {max_time:.3f}s", file=sys.stderr)

        # Top 5 slowest
        sorted_results = sorted(self.results, key=lambda r: r[4], reverse=True)
        print("\nTop 5 slowest hooks:", file=sys.stderr)
        for hook_name, _, _, _, duration in sorted_results[:5]:
            print(f"  {duration:.3f}s - {hook_name}", file=sys.stderr)

        # Failure summary
        failures = [r for r in self.results if r[1] != 0]
        if failures:
            print(f"\nFailures: {len(failures)}/{len(self.results)}", file=sys.stderr)
            for hook_name, code, _, stderr, _ in failures:
                print(f"  {hook_name}: exit {code}", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("Usage: hook_orchestrator.py <lifecycle> [mode]", file=sys.stderr)
        print("  lifecycle: SessionStart, PostToolUse, etc.", file=sys.stderr)
        print("  mode: serial | async (default: async)", file=sys.stderr)
        sys.exit(1)

    lifecycle = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "async"

    # Read context from stdin
    try:
        context = json.load(sys.stdin)
    except:
        context = {}

    orchestrator = HookOrchestrator(lifecycle, context)
    output = orchestrator.run(mode=mode)

    # Print aggregated output to stdout
    if output:
        print(output)

    # Print stats to stderr
    orchestrator.print_stats()


if __name__ == "__main__":
    main()
