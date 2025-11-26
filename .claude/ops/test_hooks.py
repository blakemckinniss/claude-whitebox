#!/usr/bin/env python3
"""
Hook Test Suite: Comprehensive testing for Claude Code hooks.

Tests all hooks in .claude/hooks/ for:
- Syntax validity
- Import errors
- Structural correctness
- Dry-run execution (with mock event)
- Performance (execution time)

Can run in quiet mode for background execution during SessionStart.
"""
import sys
import os
import json
import subprocess
import time
from pathlib import Path

# Add .claude/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
_current = _script_dir
while _current != "/":
    if os.path.exists(os.path.join(_current, ".claude", "lib", "core.py")):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with .claude/lib/core.py")

sys.path.insert(0, os.path.join(_project_root, ".claude", "lib"))
from core import setup_script, finalize, logger, handle_debug  # noqa: E402
from hook_registry import HookRegistry  # noqa: E402


def test_hook_execution(hook_path: Path, event_type: str, timeout_ms: int = 500) -> dict:
    """
    Test hook execution with mock event data.

    Returns:
        Dict with test results (success, duration, error)
    """
    # Create mock event based on type
    mock_events = {
        "SessionStart": {
            "eventName": "SessionStart",
            "sessionId": "test-session",
            "timestamp": "2025-01-01T00:00:00Z"
        },
        "SessionEnd": {
            "eventName": "SessionEnd",
            "sessionId": "test-session",
            "timestamp": "2025-01-01T00:00:00Z"
        },
        "UserPromptSubmit": {
            "eventName": "UserPromptSubmit",
            "sessionId": "test-session",
            "userMessage": "test prompt",
            "conversationTurn": 1
        },
        "PostToolUse": {
            "eventName": "PostToolUse",
            "sessionId": "test-session",
            "toolName": "Read",
            "toolParams": {"file_path": "/test"},
            "result": "test result"
        },
        "PreToolUse": {
            "eventName": "PreToolUse",
            "sessionId": "test-session",
            "toolName": "Write",
            "toolParams": {"file_path": "/test", "content": "test"}
        }
    }

    event_data = mock_events.get(event_type, mock_events["UserPromptSubmit"])

    result = {
        "success": False,
        "duration_ms": 0,
        "error": None,
        "stdout": "",
        "stderr": ""
    }

    try:
        start = time.time()

        # Run hook with mock event via stdin
        process = subprocess.run(
            [sys.executable, str(hook_path)],
            input=json.dumps(event_data),
            capture_output=True,
            text=True,
            timeout=timeout_ms / 1000.0
        )

        duration = (time.time() - start) * 1000  # ms
        result["duration_ms"] = int(duration)
        result["stdout"] = process.stdout
        result["stderr"] = process.stderr

        # Check exit code
        if process.returncode == 0:
            result["success"] = True
        else:
            result["error"] = f"Exit code {process.returncode}: {process.stderr[:200]}"

    except subprocess.TimeoutExpired:
        result["error"] = f"Timeout after {timeout_ms}ms"
    except Exception as e:
        result["error"] = f"Execution failed: {str(e)}"

    return result


def run_test_suite(project_root: Path, quiet: bool = False, performance_threshold: int = 500) -> dict:
    """
    Run comprehensive test suite on all hooks.

    Args:
        project_root: Project root path
        quiet: Suppress detailed output
        performance_threshold: Flag hooks slower than this (ms)

    Returns:
        Dict with test results summary
    """
    registry = HookRegistry(project_root)

    if not quiet:
        logger.info("🔍 Scanning hooks...")

    hooks = registry.scan_hooks()
    health_summary = registry.get_health_summary(hooks)

    if not quiet:
        logger.info(f"Found {len(hooks)} hooks")

    # Run execution tests on passing hooks
    execution_results = {}
    slow_hooks = []

    if not quiet:
        logger.info("🧪 Running execution tests...")

    for filename, metadata in hooks.items():
        # Skip if already failing syntax/import
        health = metadata.get("health", {})
        if not health.get("syntax_valid") or not health.get("imports_valid"):
            continue

        hook_path = Path(metadata["path"])
        event_type = metadata.get("event_type") or "UserPromptSubmit"

        exec_result = test_hook_execution(hook_path, event_type)
        execution_results[filename] = exec_result

        # Flag slow hooks
        if exec_result["success"] and exec_result["duration_ms"] > performance_threshold:
            slow_hooks.append({
                "filename": filename,
                "duration_ms": exec_result["duration_ms"]
            })

    # Compile final results
    results = {
        "timestamp": health_summary,
        "total_hooks": len(hooks),
        "health_summary": health_summary,
        "execution_results": execution_results,
        "slow_hooks": slow_hooks,
        "performance_threshold_ms": performance_threshold
    }

    # Save results
    results_path = project_root / ".claude" / "memory" / "hook_test_results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)

    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)

    if not quiet:
        logger.info(f"📝 Results saved: {results_path}")

    return results


def print_summary(results: dict):
    """Print human-readable test summary."""
    health = results["health_summary"]

    print(f"\n🧪 HOOK TEST RESULTS ({results['total_hooks']} hooks scanned)")
    print(f"✅ {health['passing']} passing")
    print(f"⚠️  {health['warnings']} warnings")
    print(f"❌ {health['failing']} failing")

    if health["failed_hooks"]:
        print("\nFAILURES:")
        for hook in health["failed_hooks"]:
            print(f"  ❌ {hook['filename']}")
            for error in hook["errors"][:1]:  # First error only
                # Truncate long errors
                error_short = error.split('\n')[0][:80]
                print(f"     {error_short}")

    if health["warned_hooks"]:
        print(f"\nWARNINGS: ({len(health['warned_hooks'])} hooks)")
        print("  (Run with --verbose to see details)")

    # Execution issues
    exec_failures = [
        (filename, result)
        for filename, result in results["execution_results"].items()
        if not result["success"]
    ]

    if exec_failures:
        print(f"\nEXECUTION FAILURES: ({len(exec_failures)})")
        for filename, result in exec_failures[:5]:  # First 5
            print(f"  ❌ {filename} - {result['error'][:60]}")

    # Performance issues
    if results["slow_hooks"]:
        print(f"\nSLOW HOOKS (>{results['performance_threshold_ms']}ms):")
        for hook in results["slow_hooks"][:5]:  # First 5
            print(f"  ⚠️  {hook['filename']} - {hook['duration_ms']}ms")

    print("\nRECOMMENDATIONS:")
    if health["failing"] > 0:
        print(f"  - Fix {health['failing']} failing hooks (syntax/import errors)")
    if len(exec_failures) > 0:
        print(f"  - Debug {len(exec_failures)} hooks with execution failures")
    if len(results["slow_hooks"]) > 0:
        print(f"  - Optimize {len(results['slow_hooks'])} slow hooks (consider caching/async)")
    if health["failing"] == 0 and len(exec_failures) == 0:
        print("  ✅ All hooks healthy!")


def main():
    parser = setup_script("Hook Test Suite")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Quiet mode (minimal output, for background execution)"
    )
    parser.add_argument(
        "--performance-threshold",
        type=int,
        default=500,
        metavar="MS",
        help="Flag hooks slower than this (default: 500ms)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed warnings and errors"
    )

    args = parser.parse_args()
    handle_debug(args)

    project_root = Path(_project_root)

    try:
        results = run_test_suite(
            project_root,
            quiet=args.quiet,
            performance_threshold=args.performance_threshold
        )

        if not args.quiet:
            print_summary(results)

        # Exit code based on failures
        if results["health_summary"]["failing"] > 0:
            logger.warning(f"{results['health_summary']['failing']} hooks failing")
            finalize(success=False)
        else:
            if not args.quiet:
                logger.info("✅ All hooks passing")
            finalize(success=True)

    except KeyboardInterrupt:
        logger.warning("Test suite interrupted")
        finalize(success=False)
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        finalize(success=False)


if __name__ == "__main__":
    main()
