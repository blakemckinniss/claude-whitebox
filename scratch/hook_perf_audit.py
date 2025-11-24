#!/usr/bin/env python3
"""Hook Performance Audit - Measures execution time of all hooks."""

import subprocess
import time
import json
import os
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

HOOKS_DIR = Path(__file__).parent.parent / ".claude/hooks"
SETTINGS = Path(__file__).parent.parent / ".claude/settings.json"

def time_hook(hook_path: str, timeout: float = 5.0) -> dict:
    """Time a single hook execution."""
    start = time.perf_counter()
    try:
        result = subprocess.run(
            ["python3", hook_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(HOOKS_DIR.parent.parent)}
        )
        elapsed = time.perf_counter() - start
        return {
            "hook": Path(hook_path).name,
            "time_ms": round(elapsed * 1000, 2),
            "exit_code": result.returncode,
            "stdout_len": len(result.stdout),
            "stderr_len": len(result.stderr),
            "status": "ok" if result.returncode == 0 else "error"
        }
    except subprocess.TimeoutExpired:
        return {
            "hook": Path(hook_path).name,
            "time_ms": timeout * 1000,
            "exit_code": -1,
            "stdout_len": 0,
            "stderr_len": 0,
            "status": "timeout"
        }
    except Exception as e:
        return {
            "hook": Path(hook_path).name,
            "time_ms": (time.perf_counter() - start) * 1000,
            "exit_code": -2,
            "stdout_len": 0,
            "stderr_len": 0,
            "status": f"exception: {e}"
        }

def count_hooks_per_lifecycle() -> dict:
    """Count hooks triggered per lifecycle event."""
    with open(SETTINGS) as f:
        settings = json.load(f)

    counts = {}
    for event, matchers in settings.get("hooks", {}).items():
        hook_count = 0
        for matcher_block in matchers:
            hooks = matcher_block.get("hooks", [])
            hook_count += len(hooks)
        counts[event] = hook_count
    return counts

def get_hooks_for_tool(tool_name: str) -> list:
    """Get all hooks that would run for a specific tool."""
    with open(SETTINGS) as f:
        settings = json.load(f)

    import re
    hooks = []
    for matcher_block in settings.get("hooks", {}).get("PreToolUse", []):
        pattern = matcher_block.get("matcher", "")
        if re.match(pattern, tool_name):
            for hook in matcher_block.get("hooks", []):
                cmd = hook.get("command", "")
                if ".py" in cmd:
                    hook_file = cmd.split("/")[-1].replace('"', '')
                    hooks.append(hook_file)
    return hooks

def analyze_hook_complexity():
    """Analyze hook file complexity."""
    results = []
    for hook_file in HOOKS_DIR.glob("*.py"):
        with open(hook_file) as f:
            content = f.read()

        lines = content.count("\n")
        imports = content.count("import ")
        subprocess_calls = content.count("subprocess.")
        file_ops = content.count("open(") + content.count("Path(")
        json_ops = content.count("json.")

        results.append({
            "hook": hook_file.name,
            "lines": lines,
            "imports": imports,
            "subprocess_calls": subprocess_calls,
            "file_ops": file_ops,
            "json_ops": json_ops,
            "complexity_score": lines + (imports * 2) + (subprocess_calls * 10) + (file_ops * 3) + (json_ops * 2)
        })

    return sorted(results, key=lambda x: x["complexity_score"], reverse=True)

def main():
    print("=" * 70)
    print("HOOK PERFORMANCE AUDIT")
    print("=" * 70)

    # 1. Hooks per lifecycle
    print("\n## HOOKS PER LIFECYCLE EVENT\n")
    counts = count_hooks_per_lifecycle()
    total = 0
    for event, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {event:20s}: {count:3d} hooks")
        total += count
    print(f"  {'TOTAL':20s}: {total:3d} hooks registered")

    # 2. Hooks per tool operation
    print("\n## HOOKS PER TOOL OPERATION (PreToolUse)\n")
    for tool in ["Write", "Edit", "Bash", "Read", "Task", "Grep", "Glob"]:
        hooks = get_hooks_for_tool(tool)
        print(f"  {tool:10s}: {len(hooks):2d} hooks")
        if len(hooks) > 5:
            for h in hooks[:5]:
                print(f"             - {h}")
            print(f"             ... and {len(hooks)-5} more")

    # 3. Complexity analysis
    print("\n## TOP 15 COMPLEX HOOKS (by complexity score)\n")
    complexity = analyze_hook_complexity()
    print(f"  {'Hook':45s} {'Lines':>6s} {'Score':>6s}")
    print(f"  {'-'*45} {'-'*6} {'-'*6}")
    for item in complexity[:15]:
        print(f"  {item['hook']:45s} {item['lines']:6d} {item['complexity_score']:6d}")

    # 4. Time hooks
    print("\n## HOOK EXECUTION TIMES (dry run)\n")
    print("  Timing all hooks (5s timeout each)...")

    hook_files = list(HOOKS_DIR.glob("*.py"))
    results = []

    # Run timing in parallel for speed
    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(time_hook, str(h)): h for h in hook_files}
        for future in as_completed(futures):
            results.append(future.result())

    # Sort by time
    results = sorted(results, key=lambda x: x["time_ms"], reverse=True)

    print(f"\n  {'Hook':45s} {'Time(ms)':>10s} {'Status':>10s}")
    print(f"  {'-'*45} {'-'*10} {'-'*10}")

    slow_hooks = [r for r in results if r["time_ms"] > 100]
    for r in results[:20]:
        status_icon = "✅" if r["status"] == "ok" else "⚠️" if r["status"] == "error" else "🔴"
        print(f"  {r['hook']:45s} {r['time_ms']:10.1f} {status_icon} {r['status']}")

    # 5. Summary
    print("\n## PERFORMANCE SUMMARY\n")
    total_time = sum(r["time_ms"] for r in results)
    avg_time = total_time / len(results) if results else 0
    slow_count = len([r for r in results if r["time_ms"] > 100])
    error_count = len([r for r in results if r["status"] != "ok"])

    print(f"  Total hooks:        {len(results)}")
    print(f"  Total time (all):   {total_time:.0f}ms ({total_time/1000:.1f}s)")
    print(f"  Average time:       {avg_time:.1f}ms")
    print(f"  Slow hooks (>100ms): {slow_count}")
    print(f"  Error hooks:        {error_count}")

    # 6. Bottleneck analysis
    print("\n## CRITICAL BOTTLENECKS\n")

    # Calculate per-operation overhead
    write_hooks = get_hooks_for_tool("Write")
    write_time = sum(r["time_ms"] for r in results if r["hook"] in write_hooks)

    bash_hooks = get_hooks_for_tool("Bash")
    bash_time = sum(r["time_ms"] for r in results if r["hook"] in bash_hooks)

    print(f"  PreToolUse:Write overhead: ~{write_time:.0f}ms ({len(write_hooks)} hooks)")
    print(f"  PreToolUse:Bash overhead:  ~{bash_time:.0f}ms ({len(bash_hooks)} hooks)")

    # UserPromptSubmit hooks
    with open(SETTINGS) as f:
        settings = json.load(f)
    prompt_hooks = []
    for block in settings.get("hooks", {}).get("UserPromptSubmit", []):
        for h in block.get("hooks", []):
            cmd = h.get("command", "")
            if ".py" in cmd:
                prompt_hooks.append(cmd.split("/")[-1].replace('"', ''))

    prompt_time = sum(r["time_ms"] for r in results if r["hook"] in prompt_hooks)
    print(f"  UserPromptSubmit overhead: ~{prompt_time:.0f}ms ({len(prompt_hooks)} hooks)")

    # PostToolUse hooks
    post_hooks = []
    for block in settings.get("hooks", {}).get("PostToolUse", []):
        for h in block.get("hooks", []):
            cmd = h.get("command", "")
            if ".py" in cmd:
                post_hooks.append(cmd.split("/")[-1].replace('"', ''))

    post_time = sum(r["time_ms"] for r in results if r["hook"] in post_hooks)
    print(f"  PostToolUse overhead:      ~{post_time:.0f}ms ({len(post_hooks)} hooks)")

    print("\n  IMPACT PER TURN (Write + PostToolUse + UserPromptSubmit):")
    turn_overhead = write_time + post_time + prompt_time
    print(f"  ~{turn_overhead:.0f}ms minimum latency per interaction")

    # 7. Recommendations
    print("\n## RECOMMENDATIONS\n")

    if slow_count > 5:
        print(f"  🔴 CRITICAL: {slow_count} hooks take >100ms each")
        print("     Consider: batching, caching, or lazy loading")

    if len(write_hooks) > 10:
        print(f"  🔴 CRITICAL: {len(write_hooks)} hooks on Write operation")
        print("     Consider: consolidating into fewer gate hooks")

    if prompt_time > 500:
        print(f"  🟡 WARNING: UserPromptSubmit takes {prompt_time:.0f}ms")
        print("     Consider: deferring non-critical checks")

    if error_count > 0:
        print(f"  🟡 WARNING: {error_count} hooks have errors")
        print("     Review error hooks for stability issues")

if __name__ == "__main__":
    main()
