#!/usr/bin/env python3
"""
Hook Dependency Analyzer

Analyzes all hooks to determine dependency graph for parallel execution.
Output: Batches of hooks that can run in parallel.
"""
import json
import re
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Hook dependency rules (manual analysis)
# Format: hook_name -> [list of hooks it depends on]
KNOWN_DEPENDENCIES = {
    # Confidence hooks
    "detect_low_confidence.py": ["confidence_init.py"],
    "detect_confidence_penalty.py": ["confidence_init.py"],
    "detect_confidence_reward.py": ["command_tracker.py"],
    "confidence_gate.py": ["confidence_init.py"],

    # Command tracking
    "command_prerequisite_gate.py": ["command_tracker.py"],

    # Evidence tracking
    "evidence_tracker.py": [],

    # Tier gates
    "tier_gate.py": ["confidence_init.py"],

    # Performance gates
    "performance_reward.py": ["command_tracker.py"],
}

# Hooks that read/write session state (potential conflicts)
STATE_DEPENDENT_HOOKS = [
    "confidence_init.py",
    "command_tracker.py",
    "evidence_tracker.py",
    "session_init.py",
]


def load_settings():
    """Load settings.json"""
    settings_path = PROJECT_ROOT / ".claude" / "settings.json"
    with open(settings_path) as f:
        return json.load(f)


def analyze_hook_file(hook_path):
    """Analyze a hook file for dependencies"""
    content = hook_path.read_text()

    dependencies = {
        "reads_state": False,
        "writes_state": False,
        "calls_external": False,
        "pure_check": False,
    }

    # Check for state file operations
    if re.search(r'session_\w+_state\.json', content):
        if re.search(r'json\.dump|write_text|\.write\(', content):
            dependencies["writes_state"] = True
        if re.search(r'json\.load|read_text|\.read\(', content):
            dependencies["reads_state"] = True

    # Check for external calls
    if re.search(r'subprocess|requests|OpenRouter|Tavily', content):
        dependencies["calls_external"] = True

    # Pure check (just outputs message)
    if re.search(r'sys\.exit\(0\)|print\(.*\)\s*$', content, re.MULTILINE):
        dependencies["pure_check"] = True

    return dependencies


def build_dependency_graph():
    """Build complete dependency graph"""
    settings = load_settings()
    hooks_dir = PROJECT_ROOT / ".claude" / "hooks"

    graph = {
        "UserPromptSubmit": [],
        "PreToolUse": {},
        "PostToolUse": [],
        "SessionStart": [],
        "SessionEnd": [],
        "Stop": [],
    }

    # Analyze UserPromptSubmit hooks
    if "UserPromptSubmit" in settings["hooks"]:
        for hook_config in settings["hooks"]["UserPromptSubmit"][0]["hooks"]:
            command = hook_config["command"]
            hook_name = command.split("/")[-1].replace("python3 ", "").split()[-1]

            hook_path = hooks_dir / hook_name
            if hook_path.exists():
                analysis = analyze_hook_file(hook_path)
                graph["UserPromptSubmit"].append({
                    "name": hook_name,
                    "command": command,
                    "analysis": analysis,
                    "dependencies": KNOWN_DEPENDENCIES.get(hook_name, [])
                })

    # Analyze PreToolUse hooks
    if "PreToolUse" in settings["hooks"]:
        for tool_config in settings["hooks"]["PreToolUse"]:
            matcher = tool_config.get("matcher", "default")
            graph["PreToolUse"][matcher] = []

            for hook_config in tool_config.get("hooks", []):
                command = hook_config["command"]
                hook_name = command.split("/")[-1].replace("python3 ", "").split()[-1]

                hook_path = hooks_dir / hook_name
                if hook_path.exists():
                    analysis = analyze_hook_file(hook_path)
                    graph["PreToolUse"][matcher].append({
                        "name": hook_name,
                        "command": command,
                        "analysis": analysis,
                        "dependencies": KNOWN_DEPENDENCIES.get(hook_name, [])
                    })

    # Analyze PostToolUse hooks
    if "PostToolUse" in settings["hooks"]:
        for hook_config in settings["hooks"]["PostToolUse"][0]["hooks"]:
            command = hook_config["command"]
            hook_name = command.split("/")[-1].replace("python3 ", "").split()[-1]

            hook_path = hooks_dir / hook_name
            if hook_path.exists():
                analysis = analyze_hook_file(hook_path)
                graph["PostToolUse"].append({
                    "name": hook_name,
                    "command": command,
                    "analysis": analysis,
                    "dependencies": KNOWN_DEPENDENCIES.get(hook_name, [])
                })

    return graph


def create_execution_batches(hook_list):
    """Create batches of hooks that can run in parallel"""
    # Separate state-modifying hooks from pure checks
    state_writers = []
    state_readers = []
    pure_checks = []
    others = []

    for hook in hook_list:
        if hook["analysis"]["writes_state"]:
            state_writers.append(hook)
        elif hook["analysis"]["reads_state"]:
            state_readers.append(hook)
        elif hook["analysis"]["pure_check"]:
            pure_checks.append(hook)
        else:
            others.append(hook)

    # Build batches
    batches = []

    # Batch 1: State initialization (must run first, sequentially)
    init_hooks = [h for h in state_writers if "init" in h["name"].lower()]
    if init_hooks:
        batches.append({
            "batch_id": 1,
            "parallel": False,
            "hooks": init_hooks,
            "reason": "State initialization (sequential)"
        })

    # Batch 2: Pure checks (all parallel)
    if pure_checks:
        batches.append({
            "batch_id": 2,
            "parallel": True,
            "hooks": pure_checks,
            "reason": "Pure checks (no dependencies)"
        })

    # Batch 3: State readers (parallel, depend on init)
    if state_readers:
        batches.append({
            "batch_id": 3,
            "parallel": True,
            "hooks": state_readers,
            "reason": "State readers (parallel after init)"
        })

    # Batch 4: State writers (sequential to avoid conflicts)
    remaining_writers = [h for h in state_writers if h not in init_hooks]
    if remaining_writers:
        batches.append({
            "batch_id": 4,
            "parallel": False,
            "hooks": remaining_writers,
            "reason": "State writers (sequential to avoid conflicts)"
        })

    # Batch 5: Others (parallel)
    if others:
        batches.append({
            "batch_id": 5,
            "parallel": True,
            "hooks": others,
            "reason": "Misc hooks (parallel)"
        })

    return batches


def main():
    print("="*70)
    print("HOOK DEPENDENCY ANALYSIS")
    print("="*70)

    graph = build_dependency_graph()

    # Analyze UserPromptSubmit (biggest bottleneck)
    print("\n1. USERPROMPTSUBMIT HOOKS")
    print("-"*70)

    user_prompt_hooks = graph["UserPromptSubmit"]
    print(f"Total hooks: {len(user_prompt_hooks)}")
    print(f"Estimated latency (sequential): {len(user_prompt_hooks) * 50}ms\n")

    # Categorize
    state_writers = sum(1 for h in user_prompt_hooks if h["analysis"]["writes_state"])
    state_readers = sum(1 for h in user_prompt_hooks if h["analysis"]["reads_state"])
    pure_checks = sum(1 for h in user_prompt_hooks if h["analysis"]["pure_check"])
    external_calls = sum(1 for h in user_prompt_hooks if h["analysis"]["calls_external"])

    print(f"State writers: {state_writers}")
    print(f"State readers: {state_readers}")
    print(f"Pure checks: {pure_checks}")
    print(f"External calls: {external_calls}")

    # Create batches
    print("\n2. EXECUTION BATCHES (Optimized)")
    print("-"*70)

    batches = create_execution_batches(user_prompt_hooks)

    total_parallel = 0
    total_sequential = 0

    for batch in batches:
        mode = "PARALLEL" if batch["parallel"] else "SEQUENTIAL"
        hook_count = len(batch["hooks"])

        if batch["parallel"]:
            total_parallel += hook_count
            latency = 50  # Max of parallel hooks
        else:
            total_sequential += hook_count
            latency = hook_count * 50

        print(f"\nBatch {batch['batch_id']}: {mode} ({hook_count} hooks, ~{latency}ms)")
        print(f"  Reason: {batch['reason']}")
        print(f"  Hooks:")
        for hook in batch["hooks"]:
            print(f"    - {hook['name']}")

    # Calculate improvement
    original_latency = len(user_prompt_hooks) * 50
    optimized_latency = sum(
        50 if b["parallel"] else len(b["hooks"]) * 50
        for b in batches
    )
    speedup = original_latency / optimized_latency

    print("\n3. PERFORMANCE IMPROVEMENT")
    print("-"*70)
    print(f"Original latency: {original_latency}ms (all sequential)")
    print(f"Optimized latency: {optimized_latency}ms (batched)")
    print(f"Speedup: {speedup:.1f}×")
    print(f"\nParallel hooks: {total_parallel}/{len(user_prompt_hooks)}")
    print(f"Sequential hooks: {total_sequential}/{len(user_prompt_hooks)}")

    # Save results
    output = {
        "analysis": {
            "total_hooks": len(user_prompt_hooks),
            "state_writers": state_writers,
            "state_readers": state_readers,
            "pure_checks": pure_checks,
            "external_calls": external_calls
        },
        "batches": batches,
        "performance": {
            "original_latency_ms": original_latency,
            "optimized_latency_ms": optimized_latency,
            "speedup": speedup,
            "parallel_count": total_parallel,
            "sequential_count": total_sequential
        }
    }

    output_path = PROJECT_ROOT / "scratch" / "hook_dependency_graph.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n✅ Dependency graph saved: {output_path}")

    # Analyze PreToolUse hooks
    print("\n4. PRETOOLUSE HOOKS")
    print("-"*70)

    for matcher, hooks in graph["PreToolUse"].items():
        if len(hooks) > 1:
            print(f"\n{matcher}: {len(hooks)} hooks")
            for hook in hooks:
                print(f"  - {hook['name']}")

    # Analyze PostToolUse hooks
    print("\n5. POSTTOOLUSE HOOKS")
    print("-"*70)

    post_hooks = graph["PostToolUse"]
    print(f"Total hooks: {len(post_hooks)}")

    post_batches = create_execution_batches(post_hooks)
    print(f"Can be parallelized into {len(post_batches)} batches")


if __name__ == "__main__":
    main()
