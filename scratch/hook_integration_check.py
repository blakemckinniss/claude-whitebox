#!/usr/bin/env python3
"""
Hook Integration Check
Validates hook dependencies and potential conflicts
"""

import json
import ast
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = ROOT / ".claude/hooks"
SETTINGS_FILE = ROOT / ".claude/settings.json"

def extract_file_operations(hook_file):
    """Extract file operations from hook code"""
    try:
        with open(hook_file) as f:
            content = f.read()

        # Look for file operations
        reads = set(re.findall(r'open\(["\']([^"\']+)["\'].*["\']r', content))
        writes = set(re.findall(r'open\(["\']([^"\']+)["\'].*["\']w', content))
        appends = set(re.findall(r'open\(["\']([^"\']+)["\'].*["\']a', content))

        # Also check Path operations
        reads.update(re.findall(r'Path\(["\']([^"\']+)["\']\)\.read', content))
        writes.update(re.findall(r'Path\(["\']([^"\']+)["\']\)\.write', content))

        return {
            "reads": reads,
            "writes": writes,
            "appends": appends
        }
    except:
        return {"reads": set(), "writes": set(), "appends": set()}

def extract_imports(hook_file):
    """Extract imports from hook"""
    try:
        with open(hook_file) as f:
            content = f.read()

        imports = set()
        for line in content.split('\n'):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                imports.add(line.strip())

        return imports
    except:
        return set()

def check_state_file_conflicts():
    """Check for hooks writing to same state files"""
    state_writers = defaultdict(list)

    for hook_file in HOOKS_DIR.glob("*.py"):
        ops = extract_file_operations(hook_file)
        for file_path in ops["writes"] | ops["appends"]:
            if ".json" in file_path or ".jsonl" in file_path:
                state_writers[file_path].append(hook_file.name)

    conflicts = {k: v for k, v in state_writers.items() if len(v) > 1}
    return conflicts

def check_external_dependencies():
    """Check hooks using external APIs"""
    external_hooks = {}

    for hook_file in HOOKS_DIR.glob("*.py"):
        try:
            with open(hook_file) as f:
                content = f.read()

            # Check for API usage
            apis = []
            if "OPENROUTER_API_KEY" in content or "openrouter" in content.lower():
                apis.append("OpenRouter")
            if "TAVILY_API_KEY" in content or "tavily" in content.lower():
                apis.append("Tavily")
            if "ANTHROPIC_API_KEY" in content:
                apis.append("Anthropic")

            if apis:
                external_hooks[hook_file.name] = apis
        except:
            pass

    return external_hooks

def check_hook_chains():
    """Identify hooks that call other hooks"""
    chains = {}

    for hook_file in HOOKS_DIR.glob("*.py"):
        try:
            with open(hook_file) as f:
                content = f.read()

            # Look for subprocess calls to other hooks
            called_hooks = re.findall(r'\.claude/hooks/([a-z_]+\.py)', content)
            if called_hooks:
                chains[hook_file.name] = called_hooks
        except:
            pass

    return chains

def check_blocking_vs_advisory():
    """Categorize hooks by blocking behavior"""
    blocking = []
    advisory = []

    for hook_file in HOOKS_DIR.glob("*.py"):
        try:
            with open(hook_file) as f:
                content = f.read()

            # Check for exit(1) or sys.exit(1) = blocking
            if re.search(r'(sys\.)?exit\(1\)', content):
                blocking.append(hook_file.name)
            else:
                advisory.append(hook_file.name)
        except:
            pass

    return blocking, advisory

def load_settings():
    """Load settings.json"""
    with open(SETTINGS_FILE) as f:
        return json.load(f)

def get_hook_event_map():
    """Map hooks to their events"""
    settings = load_settings()
    hook_events = defaultdict(list)

    for event_type, event_hooks in settings.get("hooks", {}).items():
        for hook_group in event_hooks:
            for hook_def in hook_group.get("hooks", []):
                if hook_def.get("type") == "command":
                    cmd = hook_def["command"]
                    if ".claude/hooks/" in cmd:
                        filename = cmd.split(".claude/hooks/")[1].split()[0]
                        hook_events[filename].append(event_type)

    return hook_events

def main():
    print("🔗 HOOK INTEGRATION ANALYSIS\n")
    print("=" * 60)

    # 1. State file conflicts
    print("\n📁 STATE FILE CONFLICTS:")
    conflicts = check_state_file_conflicts()

    if conflicts:
        print(f"   ⚠️  {len(conflicts)} files with multiple writers:")
        for file_path, writers in sorted(conflicts.items()):
            print(f"\n   {file_path}:")
            for writer in writers:
                print(f"      • {writer}")
    else:
        print("   ✅ No write conflicts detected")

    # 2. External dependencies
    print("\n\n🌐 EXTERNAL API DEPENDENCIES:")
    external = check_external_dependencies()

    if external:
        print(f"   • {len(external)} hooks using external APIs:")
        for hook, apis in sorted(external.items()):
            print(f"      {hook}: {', '.join(apis)}")
    else:
        print("   ✅ No external API dependencies")

    # 3. Hook chains
    print("\n\n🔗 HOOK CHAINS:")
    chains = check_hook_chains()

    if chains:
        print(f"   • {len(chains)} hooks calling other hooks:")
        for hook, called in sorted(chains.items()):
            print(f"      {hook} → {', '.join(set(called))}")
    else:
        print("   ✅ No hook chains detected")

    # 4. Blocking behavior
    print("\n\n🚫 BLOCKING BEHAVIOR:")
    blocking, advisory = check_blocking_vs_advisory()

    print(f"   • Blocking (hard gates): {len(blocking)}")
    print(f"   • Advisory (suggestions): {len(advisory)}")

    ratio = len(blocking) / (len(blocking) + len(advisory)) * 100 if (len(blocking) + len(advisory)) > 0 else 0
    print(f"   • Blocking ratio: {ratio:.1f}%")

    if ratio > 30:
        print(f"\n   ⚠️  High blocking ratio - may be over-constraining!")

    # 5. Event distribution
    print("\n\n📍 HOOK-TO-EVENT MAPPING:")
    hook_events = get_hook_event_map()

    # Find hooks registered to multiple events
    multi_event = {h: e for h, e in hook_events.items() if len(e) > 1}

    if multi_event:
        print(f"   • {len(multi_event)} hooks registered to multiple events:")
        for hook, events in sorted(multi_event.items())[:10]:
            print(f"      {hook}: {', '.join(events)}")
        if len(multi_event) > 10:
            print(f"      ... and {len(multi_event) - 10} more")
    else:
        print("   ✅ Each hook registered to single event")

    # 6. Critical path analysis (PreToolUse hooks)
    print("\n\n⚡ CRITICAL PATH (PreToolUse Hooks):")
    settings = load_settings()
    pre_tool_hooks = settings.get("hooks", {}).get("PreToolUse", [])

    total_pre_hooks = sum(len(hg.get("hooks", [])) for hg in pre_tool_hooks)
    print(f"   • Total PreToolUse hooks: {total_pre_hooks}")

    # Group by tool matcher
    for hook_group in pre_tool_hooks:
        matcher = hook_group.get("matcher", "all")
        count = len(hook_group.get("hooks", []))
        print(f"      {matcher}: {count} hooks")

    if total_pre_hooks > 15:
        print(f"\n   ⚠️  Many PreToolUse hooks - may impact latency")

    # Summary
    print("\n" + "=" * 60)
    print("📋 INTEGRATION SUMMARY:")

    issues = []
    if conflicts:
        issues.append(f"{len(conflicts)} file write conflicts")
    if ratio > 30:
        issues.append("high blocking ratio")
    if total_pre_hooks > 15:
        issues.append("many pre-tool hooks")

    if issues:
        print(f"   ⚠️  Potential issues: {', '.join(issues)}")
    else:
        print(f"   ✅ Integration looks healthy!")

    print(f"\n   Key metrics:")
    print(f"   • {len(external)} hooks with external deps")
    print(f"   • {len(blocking)} blocking hooks")
    print(f"   • {total_pre_hooks} pre-tool hooks (critical path)")
    print(f"   • {len(conflicts)} write conflicts")

if __name__ == "__main__":
    main()
