#!/usr/bin/env python3
"""Hook Redundancy Audit - Finds duplicate functionality and consolidation opportunities."""

import json
import re
from pathlib import Path
from collections import defaultdict

HOOKS_DIR = Path(__file__).parent.parent / ".claude/hooks"
SETTINGS = Path(__file__).parent.parent / ".claude/settings.json"

def extract_hook_patterns():
    """Extract what each hook checks/validates."""
    results = []

    for hook_file in sorted(HOOKS_DIR.glob("*.py")):
        with open(hook_file) as f:
            content = f.read()

        # Extract key patterns
        checks_confidence = "confidence" in content.lower()
        checks_tier = "tier" in content.lower() or "ignorance" in content.lower() or "hypothesis" in content.lower()
        reads_state_file = "state.json" in content or "session_" in content
        reads_transcript = "transcript" in content.lower()
        checks_tool_input = "tool_input" in content
        writes_file = ".write(" in content or "Write" in content
        reads_settings = "settings.json" in content
        imports_subprocess = "subprocess" in content

        # Check for common validation patterns
        path_validation = "file_path" in content or "path" in content.lower()
        scratch_check = "scratch" in content.lower()
        production_check = "scripts/ops" in content or "production" in content.lower()

        results.append({
            "hook": hook_file.name,
            "checks_confidence": checks_confidence,
            "checks_tier": checks_tier,
            "reads_state": reads_state_file,
            "reads_transcript": reads_transcript,
            "checks_tool_input": checks_tool_input,
            "writes_file": writes_file,
            "path_validation": path_validation,
            "scratch_check": scratch_check,
            "production_check": production_check,
            "imports_subprocess": imports_subprocess
        })

    return results

def find_functional_overlaps(patterns):
    """Group hooks by functionality."""
    groups = defaultdict(list)

    for p in patterns:
        if p["checks_tier"] and p["checks_confidence"]:
            groups["confidence_tier_checks"].append(p["hook"])
        if p["reads_state"]:
            groups["reads_session_state"].append(p["hook"])
        if p["path_validation"] and p["scratch_check"]:
            groups["scratch_path_validation"].append(p["hook"])
        if p["production_check"]:
            groups["production_checks"].append(p["hook"])
        if p["reads_transcript"]:
            groups["transcript_readers"].append(p["hook"])

    return groups

def analyze_hook_chains():
    """Analyze which hooks run together and could be consolidated."""
    with open(SETTINGS) as f:
        settings = json.load(f)

    chains = {}

    for event, matchers in settings.get("hooks", {}).items():
        all_hooks = []
        for matcher_block in matchers:
            pattern = matcher_block.get("matcher", "*")
            hooks = [h.get("command", "").split("/")[-1].replace('"', '')
                     for h in matcher_block.get("hooks", [])]
            all_hooks.extend(hooks)
        chains[event] = all_hooks

    return chains

def find_gate_patterns():
    """Find hooks that are gates (can block operations)."""
    gates = []

    for hook_file in HOOKS_DIR.glob("*.py"):
        with open(hook_file) as f:
            content = f.read()

        # Gates typically: exit non-zero, print BLOCK, or raise
        is_gate = (
            'sys.exit(1)' in content or
            'exit(1)' in content or
            '"BLOCK"' in content or
            "'BLOCK'" in content or
            '"decision": "block"' in content or
            '"decision":"block"' in content
        )

        if is_gate:
            gates.append(hook_file.name)

    return gates

def main():
    print("=" * 70)
    print("HOOK REDUNDANCY AUDIT")
    print("=" * 70)

    # 1. Extract patterns
    patterns = extract_hook_patterns()

    # 2. Find overlaps
    overlaps = find_functional_overlaps(patterns)

    print("\n## FUNCTIONAL OVERLAPS\n")
    print("Hooks that share similar functionality and may be candidates for consolidation:\n")

    for group, hooks in sorted(overlaps.items(), key=lambda x: -len(x[1])):
        if len(hooks) > 2:
            print(f"  📦 {group} ({len(hooks)} hooks):")
            for h in hooks[:8]:
                print(f"     - {h}")
            if len(hooks) > 8:
                print(f"     ... and {len(hooks)-8} more")
            print()

    # 3. Gate hooks analysis
    gates = find_gate_patterns()
    print(f"\n## GATE HOOKS ({len(gates)} hooks can BLOCK operations)\n")

    for g in sorted(gates):
        print(f"  🚫 {g}")

    # 4. Hook chain analysis
    chains = analyze_hook_chains()

    print("\n## CONSOLIDATION OPPORTUNITIES\n")

    # Find hooks that always run together
    pretool_write_hooks = [h for h in chains.get("PreToolUse", []) if h.endswith(".py")]

    # Check for common patterns
    confidence_hooks = [h for h in pretool_write_hooks if "confidence" in h or "tier" in h]
    if len(confidence_hooks) > 1:
        print(f"  🔄 Confidence/Tier checking: {len(confidence_hooks)} separate hooks")
        for h in confidence_hooks:
            print(f"     - {h}")
        print("     → Could be ONE unified gate hook\n")

    # Check for prerequisite/validation chains
    prereq_hooks = [h for h in pretool_write_hooks if "gate" in h or "prereq" in h or "enforcer" in h]
    if len(prereq_hooks) > 3:
        print(f"  🔄 Prerequisite/Gate hooks: {len(prereq_hooks)} separate hooks")
        for h in prereq_hooks[:6]:
            print(f"     - {h}")
        if len(prereq_hooks) > 6:
            print(f"     ... and {len(prereq_hooks)-6} more")
        print("     → Could use a single dispatcher with pluggable validators\n")

    # 5. Telemetry/tracking redundancy
    telemetry_hooks = [p["hook"] for p in patterns if "telemetry" in p["hook"] or "tracker" in p["hook"] or "detect" in p["hook"]]
    print(f"  🔄 Telemetry/Detection hooks: {len(telemetry_hooks)} hooks")
    for h in telemetry_hooks[:8]:
        print(f"     - {h}")
    if len(telemetry_hooks) > 8:
        print(f"     ... and {len(telemetry_hooks)-8} more")
    print("     → Consider unified telemetry collector\n")

    # 6. State file access pattern
    state_readers = [p["hook"] for p in patterns if p["reads_state"]]
    print(f"  🔄 State file readers: {len(state_readers)} hooks read session state")
    print("     → Each hook loads JSON separately - consider shared state loader\n")

    # 7. Specific recommendations
    print("\n## SPECIFIC CONSOLIDATION RECOMMENDATIONS\n")

    print("  1️⃣  MERGE confidence_gate.py + tier_gate.py + confidence_init.py")
    print("      These all manage confidence/tier state - ONE hook can do it\n")

    print("  2️⃣  MERGE scratch_flat_enforcer.py + scratch_enforcer.py + scratch_enforcer_gate.py")
    print("      Three hooks all validating scratch/ paths\n")

    print("  3️⃣  MERGE org_drift_gate.py + org_drift_telemetry.py + root_pollution_gate.py")
    print("      All validate file organization\n")

    print("  4️⃣  CONSOLIDATE telemetry hooks into single collector:")
    print("      - batching_telemetry.py")
    print("      - background_telemetry.py")
    print("      - performance_telemetry_collector.py")
    print("      - command_tracker.py")
    print("      - evidence_tracker.py")
    print("      - token_tracker.py\n")

    print("  5️⃣  MERGE prerequisite checkers:")
    print("      - command_prerequisite_gate.py")
    print("      - prerequisite_checker.py")
    print("      - file_operation_gate.py\n")

    print("  6️⃣  LAZY LOAD expensive hooks (>500ms):")
    print("      - auto_commit_on_end.py (1007ms)")
    print("      - auto_commit_threshold.py (525ms)")
    print("      Only run on actual commit operations, not every Stop\n")

    # 8. Estimated savings
    print("\n## ESTIMATED PERFORMANCE IMPACT\n")
    print("  Current per-turn overhead: ~5233ms")
    print("  ")
    print("  If consolidated:")
    print("  - Reduce 15 Write hooks → 5 unified gates: -600ms")
    print("  - Reduce 21 PostToolUse → 10 unified:      -500ms")
    print("  - Reduce 21 UserPromptSubmit → 12:         -400ms")
    print("  - Lazy load auto_commit hooks:             -1500ms")
    print("  ")
    print("  Estimated new overhead: ~2233ms (57% reduction)")

if __name__ == "__main__":
    main()
