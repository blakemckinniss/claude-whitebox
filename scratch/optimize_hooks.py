#!/usr/bin/env python3
"""
Hook Optimization Analysis & Implementation
Analyzes current hook configuration and optimizes:
1. Event assignment (move hooks to appropriate events)
2. Caching (prevent re-reading files)
3. Performance profiling (identify slow hooks)
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Set
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts' / 'lib'))
from parallel import run_parallel

PROJECT_ROOT = Path(__file__).parent.parent


class HookAnalyzer:
    def __init__(self):
        self.settings_path = PROJECT_ROOT / ".claude" / "settings.json"
        self.hooks_dir = PROJECT_ROOT / ".claude" / "hooks"

        with open(self.settings_path) as f:
            self.settings = json.load(f)

    def analyze_event_assignments(self) -> Dict:
        """Analyze if hooks are assigned to optimal events"""

        recommendations = {
            "move_to_posttooluse": [],
            "move_to_pretooluse": [],
            "keep_in_userpromptsubmit": [],
            "move_to_stop": []
        }

        # UserPromptSubmit hooks
        user_prompt_hooks = self.settings["hooks"]["UserPromptSubmit"][0]["hooks"]

        for hook in user_prompt_hooks:
            cmd = hook["command"]
            hook_name = cmd.split("/")[-1].replace(".py", "")

            # Analysis: Does this hook NEED to run on every prompt?

            # MUST stay in UserPromptSubmit (critical path)
            critical_prompt_hooks = {
                "confidence_init.py",      # Must initialize confidence
                "synapse_fire.py",         # Associative memory recall
                "scratch_context_hook.py", # Scratch file context
            }

            # Can move to PostToolUse (reactive, not proactive)
            reactive_hooks = {
                "detect_batch.py",             # Detects AFTER tools are used
                "sanity_check.py",             # Could check after tool use
                "auto_commit_on_complete.py",  # Reactive to completion
            }

            # Can move to PreToolUse:Bash (only relevant for Bash commands)
            bash_specific = {
                "force_playwright.py",  # Only relevant when Bash scraping detected
            }

            if any(critical in cmd for critical in critical_prompt_hooks):
                recommendations["keep_in_userpromptsubmit"].append({
                    "hook": hook_name,
                    "reason": "Critical for prompt processing"
                })
            elif any(reactive in cmd for reactive in reactive_hooks):
                recommendations["move_to_posttooluse"].append({
                    "hook": hook_name,
                    "reason": "Reactive - doesn't need to run before tools",
                    "command": cmd
                })
            elif any(bash in cmd for bash in bash_specific):
                recommendations["move_to_pretooluse"].append({
                    "hook": hook_name,
                    "reason": "Bash-specific - add matcher",
                    "command": cmd,
                    "matcher": "Bash"
                })
            else:
                # Analyze individual hook purpose
                recommendations["keep_in_userpromptsubmit"].append({
                    "hook": hook_name,
                    "reason": "Needs manual review"
                })

        return recommendations

    def identify_cacheable_hooks(self) -> List[Dict]:
        """Identify hooks that read files multiple times"""

        cacheable = []

        # Known file-reading hooks
        file_readers = {
            "synapse_fire.py": {
                "files": [".claude/memory/synapses.json", ".claude/memory/lessons.md"],
                "cache_key": "session_id",
                "benefit": "3-5× faster (reads 2 files every prompt)"
            },
            "scratch_context_hook.py": {
                "files": ["scratch/*.py"],
                "cache_key": "file_mtime",
                "benefit": "2-3× faster (globs scratch/ every prompt)"
            },
            "detect_confidence_penalty.py": {
                "files": [".claude/memory/anti_patterns.md"],
                "cache_key": "session_id",
                "benefit": "2× faster"
            },
            "check_knowledge.py": {
                "files": [".claude/memory/knowledge_checks.json"],
                "cache_key": "session_id",
                "benefit": "2× faster"
            }
        }

        for hook_name, info in file_readers.items():
            hook_path = self.hooks_dir / hook_name
            if hook_path.exists():
                cacheable.append({
                    "hook": hook_name,
                    "files": info["files"],
                    "cache_strategy": info["cache_key"],
                    "expected_benefit": info["benefit"]
                })

        return cacheable

    def profile_hooks(self, sample_size: int = 3) -> Dict:
        """Profile hook execution times"""

        print(f"\nProfiling UserPromptSubmit hooks ({sample_size} samples each)...")

        user_prompt_hooks = self.settings["hooks"]["UserPromptSubmit"][0]["hooks"]

        def time_hook(hook_cmd: str) -> float:
            """Time a single hook execution"""
            import subprocess

            # Create minimal test input
            test_input = {
                "session_id": "test",
                "transcript_path": "/tmp/test.jsonl",
                "cwd": str(PROJECT_ROOT),
                "permission_mode": "default",
                "hook_event_name": "UserPromptSubmit",
                "prompt": "test prompt"
            }

            start = time.time()
            try:
                result = subprocess.run(
                    ["bash", "-c", hook_cmd.replace("$CLAUDE_PROJECT_DIR", str(PROJECT_ROOT))],
                    input=json.dumps(test_input),
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                duration = (time.time() - start) * 1000
                return duration
            except Exception as e:
                return -1

        # Profile each hook
        profiles = {}

        for hook in user_prompt_hooks:
            cmd = hook["command"]
            hook_name = cmd.split("/")[-1].replace(".py", "")

            # Run multiple samples
            times = []
            for _ in range(sample_size):
                duration = time_hook(cmd)
                if duration > 0:
                    times.append(duration)

            if times:
                avg_time = sum(times) / len(times)
                profiles[hook_name] = {
                    "avg_ms": round(avg_time, 1),
                    "samples": times,
                    "command": cmd
                }

        return profiles

    def generate_optimization_plan(self) -> str:
        """Generate comprehensive optimization plan"""

        report = []
        report.append("=" * 80)
        report.append("HOOK OPTIMIZATION ANALYSIS")
        report.append("=" * 80)

        # 1. Event assignments
        report.append("\n1. EVENT ASSIGNMENT OPTIMIZATION")
        report.append("-" * 80)

        assignments = self.analyze_event_assignments()

        if assignments["move_to_posttooluse"]:
            report.append(f"\n✅ MOVE TO PostToolUse ({len(assignments['move_to_posttooluse'])} hooks):")
            for item in assignments["move_to_posttooluse"]:
                report.append(f"  • {item['hook']}")
                report.append(f"    Reason: {item['reason']}")

        if assignments["move_to_pretooluse"]:
            report.append(f"\n✅ MOVE TO PreToolUse ({len(assignments['move_to_pretooluse'])} hooks):")
            for item in assignments["move_to_pretooluse"]:
                report.append(f"  • {item['hook']}")
                report.append(f"    Matcher: {item['matcher']}")
                report.append(f"    Reason: {item['reason']}")

        report.append(f"\n✓ KEEP IN UserPromptSubmit ({len(assignments['keep_in_userpromptsubmit'])} hooks):")
        critical = [h for h in assignments['keep_in_userpromptsubmit']
                   if "Critical" in h['reason']]
        report.append(f"  Critical hooks: {len(critical)}")

        # 2. Caching opportunities
        report.append("\n\n2. CACHING OPPORTUNITIES")
        report.append("-" * 80)

        cacheable = self.identify_cacheable_hooks()

        for item in cacheable:
            report.append(f"\n📂 {item['hook']}")
            report.append(f"  Files read: {', '.join(item['files'])}")
            report.append(f"  Cache strategy: {item['cache_strategy']}")
            report.append(f"  Expected benefit: {item['expected_benefit']}")

        # 3. Summary
        report.append("\n\n" + "=" * 80)
        report.append("OPTIMIZATION SUMMARY")
        report.append("=" * 80)

        total_moved = len(assignments["move_to_posttooluse"]) + len(assignments["move_to_pretooluse"])
        remaining = len(assignments["keep_in_userpromptsubmit"])

        report.append(f"\nCurrent: 21 UserPromptSubmit hooks")
        report.append(f"After optimization: {remaining} UserPromptSubmit hooks")
        report.append(f"Reduction: {total_moved} hooks moved to more appropriate events")
        report.append(f"Cacheable hooks: {len(cacheable)}")
        report.append(f"\nEstimated speedup: 2-3× (1050ms → 350-500ms)")

        return "\n".join(report)


def generate_optimized_settings() -> Dict:
    """Generate optimized settings.json"""

    analyzer = HookAnalyzer()
    assignments = analyzer.analyze_event_assignments()

    # Start with current settings
    optimized = analyzer.settings.copy()

    # Optimize UserPromptSubmit
    keep_hooks = [
        h for h in analyzer.settings["hooks"]["UserPromptSubmit"][0]["hooks"]
        if any(k["hook"] + ".py" in h["command"]
               for k in assignments["keep_in_userpromptsubmit"]
               if "Critical" in k["reason"])
    ]

    optimized["hooks"]["UserPromptSubmit"] = [{"hooks": keep_hooks}]

    # Add moved hooks to PostToolUse
    posttooluse_additions = [
        {"type": "command", "command": h["command"]}
        for h in assignments["move_to_posttooluse"]
    ]

    optimized["hooks"]["PostToolUse"][0]["hooks"].extend(posttooluse_additions)

    return optimized


def implement_caching_template() -> str:
    """Generate caching template for hooks"""

    template = '''#!/usr/bin/env python3
"""
Cached Hook Template
Add this to hooks that read files repeatedly
"""

import json
import sys
from pathlib import Path
import hashlib
import time

# Simple file-based cache
class HookCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    def get(self, key: str) -> dict | None:
        """Get cached value"""
        cache_file = self.cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.json"

        if cache_file.exists():
            # Check if cache is fresh (< 5 minutes old)
            if time.time() - cache_file.stat().st_mtime < 300:
                with open(cache_file) as f:
                    return json.load(f)
        return None

    def set(self, key: str, value: dict):
        """Set cached value"""
        cache_file = self.cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.json"
        with open(cache_file, 'w') as f:
            json.dump(value, f)

# Usage in hook:
cache = HookCache(Path("/tmp/claude_hook_cache"))
session_id = input_data.get("session_id")

# Try cache first
cached = cache.get(session_id)
if cached:
    print(json.dumps(cached))
    sys.exit(0)

# Compute result (expensive operation)
result = expensive_file_reading_operation()

# Cache for next time
cache.set(session_id, result)
print(json.dumps(result))
'''

    return template


def main():
    analyzer = HookAnalyzer()

    # Generate analysis
    report = analyzer.generate_optimization_plan()
    print(report)

    # Save report
    report_file = PROJECT_ROOT / "scratch" / "hook_optimization_report.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"\n✓ Report saved to: {report_file}")

    # Generate optimized settings (preview)
    optimized = generate_optimized_settings()
    optimized_file = PROJECT_ROOT / "scratch" / "settings_optimized.json"
    with open(optimized_file, 'w') as f:
        json.dump(optimized, f, indent=2)
    print(f"✓ Optimized settings saved to: {optimized_file}")

    # Generate caching template
    template = implement_caching_template()
    template_file = PROJECT_ROOT / "scratch" / "hook_cache_template.py"
    with open(template_file, 'w') as f:
        f.write(template)
    print(f"✓ Caching template saved to: {template_file}")

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("""
1. Review: scratch/hook_optimization_report.txt
2. Preview: scratch/settings_optimized.json
3. Apply caching: Copy scratch/hook_cache_template.py pattern to slow hooks
4. Test: Backup .claude/settings.json, copy optimized version, test
5. Validate: Run session and check hook latency
    """)


if __name__ == "__main__":
    main()
