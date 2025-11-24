#!/usr/bin/env python3
"""
Hook Performance Profiler
Profiles all UserPromptSubmit hooks to identify bottlenecks
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts' / 'lib'))
from parallel import run_parallel

PROJECT_ROOT = Path(__file__).parent.parent


class HookProfiler:
    def __init__(self):
        self.settings_path = PROJECT_ROOT / ".claude" / "settings.json"
        with open(self.settings_path) as f:
            self.settings = json.load(f)

    def create_test_input(self, prompt: str = "test prompt") -> Dict:
        """Create test input for hooks"""
        return {
            "session_id": "profile_test",
            "transcript_path": "/tmp/test.jsonl",
            "cwd": str(PROJECT_ROOT),
            "permission_mode": "default",
            "hook_event_name": "UserPromptSubmit",
            "prompt": prompt
        }

    def profile_hook(self, hook_cmd: str, samples: int = 5) -> Dict:
        """Profile a single hook"""
        hook_name = hook_cmd.split("/")[-1].replace(".py", "")

        timings = []
        errors = 0

        for i in range(samples):
            test_input = self.create_test_input(f"test prompt {i}")

            start = time.time()
            try:
                result = subprocess.run(
                    ["bash", "-c", hook_cmd.replace("$CLAUDE_PROJECT_DIR", str(PROJECT_ROOT))],
                    input=json.dumps(test_input),
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                duration_ms = (time.time() - start) * 1000
                timings.append(duration_ms)

                if result.returncode != 0:
                    errors += 1

            except subprocess.TimeoutExpired:
                timings.append(10000)  # 10s timeout
                errors += 1
            except Exception as e:
                errors += 1

        if not timings:
            return {
                "hook": hook_name,
                "avg_ms": -1,
                "min_ms": -1,
                "max_ms": -1,
                "samples": 0,
                "errors": errors,
                "command": hook_cmd
            }

        return {
            "hook": hook_name,
            "avg_ms": round(sum(timings) / len(timings), 1),
            "min_ms": round(min(timings), 1),
            "max_ms": round(max(timings), 1),
            "std_dev": round(self._std_dev(timings), 1),
            "samples": len(timings),
            "errors": errors,
            "command": hook_cmd
        }

    def _std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if not values:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def profile_all_hooks(self, samples: int = 5) -> List[Dict]:
        """Profile all UserPromptSubmit hooks"""
        hooks = self.settings["hooks"]["UserPromptSubmit"][0]["hooks"]

        print(f"Profiling {len(hooks)} hooks ({samples} samples each)...")

        # Profile hooks in parallel
        def profile_wrapper(hook):
            cmd = hook["command"]
            return self.profile_hook(cmd, samples)

        results = run_parallel(
            profile_wrapper,
            hooks,
            max_workers=10,
            desc="Profiling hooks"
        )

        # Extract successful results
        profiles = []
        for item, result, error in results:
            if error is None and result:
                profiles.append(result)

        return sorted(profiles, key=lambda x: x["avg_ms"], reverse=True)

    def generate_report(self, profiles: List[Dict]) -> str:
        """Generate profiling report"""
        report = []
        report.append("="*80)
        report.append("HOOK PERFORMANCE PROFILE")
        report.append("="*80)

        # Summary stats
        total_time = sum(p["avg_ms"] for p in profiles)
        successful = sum(1 for p in profiles if p["errors"] == 0)

        report.append(f"\nHooks profiled: {len(profiles)}")
        report.append(f"Successful: {successful}/{len(profiles)}")
        report.append(f"Total avg time: {total_time:.1f}ms")
        report.append("")

        # Top 10 slowest
        report.append("\n🐌 TOP 10 SLOWEST HOOKS")
        report.append("-"*80)
        report.append(f"{'Hook':<30} {'Avg (ms)':<10} {'Min':<8} {'Max':<8} {'StdDev':<8}")
        report.append("-"*80)

        for profile in profiles[:10]:
            hook = profile["hook"][:28]
            avg = profile["avg_ms"]
            min_t = profile["min_ms"]
            max_t = profile["max_ms"]
            std = profile["std_dev"]

            report.append(f"{hook:<30} {avg:<10.1f} {min_t:<8.1f} {max_t:<8.1f} {std:<8.1f}")

        # Categorize by performance
        report.append("\n\n📊 PERFORMANCE CATEGORIES")
        report.append("-"*80)

        critical = [p for p in profiles if p["avg_ms"] > 100]  # >100ms
        slow = [p for p in profiles if 50 < p["avg_ms"] <= 100]  # 50-100ms
        medium = [p for p in profiles if 20 < p["avg_ms"] <= 50]  # 20-50ms
        fast = [p for p in profiles if p["avg_ms"] <= 20]  # <20ms

        report.append(f"\n🔴 CRITICAL (>100ms): {len(critical)} hooks")
        for p in critical:
            report.append(f"   • {p['hook']}: {p['avg_ms']:.1f}ms")

        report.append(f"\n🟡 SLOW (50-100ms): {len(slow)} hooks")
        for p in slow:
            report.append(f"   • {p['hook']}: {p['avg_ms']:.1f}ms")

        report.append(f"\n🟢 MEDIUM (20-50ms): {len(medium)} hooks")
        for p in medium:
            report.append(f"   • {p['hook']}: {p['avg_ms']:.1f}ms")

        report.append(f"\n✅ FAST (<20ms): {len(fast)} hooks")
        for p in fast:
            report.append(f"   • {p['hook']}: {p['avg_ms']:.1f}ms")

        # Optimization recommendations
        report.append("\n\n🎯 OPTIMIZATION PRIORITIES")
        report.append("-"*80)

        if critical:
            report.append("\nPRIORITY 1 - Optimize critical hooks (>100ms):")
            for p in critical:
                report.append(f"   • {p['hook']}")
                report.append(f"     Current: {p['avg_ms']:.1f}ms")
                report.append(f"     Target: <50ms (2× improvement)")

        if slow:
            report.append("\nPRIORITY 2 - Optimize slow hooks (50-100ms):")
            for p in slow:
                report.append(f"   • {p['hook']}")
                report.append(f"     Current: {p['avg_ms']:.1f}ms")
                report.append(f"     Target: <20ms (3-5× improvement)")

        # Errors
        errors = [p for p in profiles if p["errors"] > 0]
        if errors:
            report.append("\n\n⚠️  HOOKS WITH ERRORS")
            report.append("-"*80)
            for p in errors:
                report.append(f"   • {p['hook']}: {p['errors']}/{p['samples']} failed")

        # Total impact
        report.append("\n\n💡 OPTIMIZATION IMPACT")
        report.append("-"*80)

        if critical:
            critical_time = sum(p["avg_ms"] for p in critical)
            report.append(f"\nOptimizing critical hooks:")
            report.append(f"  Current: {critical_time:.1f}ms")
            report.append(f"  Target (50% reduction): {critical_time * 0.5:.1f}ms")
            report.append(f"  Savings: {critical_time * 0.5:.1f}ms per prompt")

        if slow:
            slow_time = sum(p["avg_ms"] for p in slow)
            report.append(f"\nOptimizing slow hooks:")
            report.append(f"  Current: {slow_time:.1f}ms")
            report.append(f"  Target (70% reduction): {slow_time * 0.3:.1f}ms")
            report.append(f"  Savings: {slow_time * 0.7:.1f}ms per prompt")

        potential_savings = sum(p["avg_ms"] for p in critical + slow) * 0.6
        report.append(f"\n🚀 TOTAL POTENTIAL SAVINGS: {potential_savings:.1f}ms per prompt")
        report.append(f"   ({potential_savings / total_time * 100:.1f}% improvement)")

        report.append("\n" + "="*80)

        return "\n".join(report)


def main():
    profiler = HookProfiler()

    # Profile all hooks
    profiles = profiler.profile_all_hooks(samples=5)

    # Generate report
    report = profiler.generate_report(profiles)
    print("\n" + report)

    # Save report
    report_file = PROJECT_ROOT / "scratch" / "hook_profile_report.txt"
    with open(report_file, 'w') as f:
        f.write(report)

    print(f"\n✓ Report saved to: {report_file}")

    # Save detailed JSON
    json_file = PROJECT_ROOT / "scratch" / "hook_profile_data.json"
    with open(json_file, 'w') as f:
        json.dump(profiles, f, indent=2)

    print(f"✓ Detailed data saved to: {json_file}")


if __name__ == "__main__":
    main()
