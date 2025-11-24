#!/usr/bin/env python3
"""
Deep analysis of hooks for race conditions.
Actually reads hook scripts and checks for state file access.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

def get_hook_scripts():
    """Get all hook script paths from settings.json"""
    with open('.claude/settings.json') as f:
        config = json.load(f)

    scripts = []
    for event_type, matchers in config['hooks'].items():
        for matcher in matchers:
            hooks = matcher.get('hooks', [])
            for hook in hooks:
                if hook['type'] != 'command':
                    continue

                cmd = hook['command']
                match = re.search(r'python3 \$CLAUDE_PROJECT_DIR/(.*\.py)', cmd)
                if match:
                    script_path = match.group(1)
                    scripts.append({
                        'event': event_type,
                        'matcher': matcher.get('matcher', 'default'),
                        'path': script_path,
                        'name': Path(script_path).stem
                    })

    return scripts

def analyze_state_access(script_path):
    """Analyze what state files a script accesses"""
    if not Path(script_path).exists():
        return None

    try:
        content = Path(script_path).read_text()
    except:
        return None

    # Look for state file patterns
    state_patterns = {
        'session_state': r'session_.*state\.json',
        'punch_list': r'punch_list\.json',
        'evidence': r'evidence\.json',
        'commands_run': r'(commands_run|command_tracker)',
        'lessons': r'lessons\.md',
        'active_context': r'active_context\.md',
        'upkeep_log': r'upkeep_log\.md',
    }

    accesses = {
        'reads': set(),
        'writes': set(),
    }

    for state_name, pattern in state_patterns.items():
        # Check for file operations
        if re.search(pattern, content, re.IGNORECASE):
            # Look for reads
            if re.search(r'(open\([^)]*["\']r|json\.load|\.read_text\(\)|Path\([^)]*\)\.read)', content):
                accesses['reads'].add(state_name)

            # Look for writes
            if re.search(r'(open\([^)]*["\']w|json\.dump|\.write_text\(|Path\([^)]*\)\.write)', content):
                accesses['writes'].add(state_name)

    return accesses

def main():
    scripts = get_hook_scripts()

    # Group by event type
    by_event = defaultdict(list)
    for script in scripts:
        by_event[script['event']].append(script)

    print("=" * 80)
    print("HOOK STATE ACCESS ANALYSIS")
    print("=" * 80)

    # Analyze each event
    all_writes = defaultdict(lambda: defaultdict(list))

    for event_type, event_scripts in sorted(by_event.items()):
        print(f"\n{event_type} ({len(event_scripts)} hooks)")
        print("-" * 80)

        for script in event_scripts:
            accesses = analyze_state_access(script['path'])

            if accesses is None:
                print(f"  ⚠️  {script['name']:30} [FILE NOT FOUND]")
                continue

            if not accesses['reads'] and not accesses['writes']:
                continue

            # Track writes for conflict detection
            for state_file in accesses['writes']:
                all_writes[event_type][state_file].append(script['name'])

            # Display
            parts = []
            if accesses['reads']:
                parts.append(f"R: {', '.join(sorted(accesses['reads']))}")
            if accesses['writes']:
                parts.append(f"W: {', '.join(sorted(accesses['writes']))}")

            print(f"  {'📖' if accesses['reads'] and not accesses['writes'] else '✍️ '} {script['name']:30} {' | '.join(parts)}")

    # Detect conflicts
    print("\n" + "=" * 80)
    print("RACE CONDITION DETECTION")
    print("=" * 80)

    conflicts = []

    # Check for multiple writers in same event
    for event_type, state_files in all_writes.items():
        for state_file, writers in state_files.items():
            if len(writers) > 1:
                conflicts.append({
                    'type': 'SAME_EVENT_MULTIPLE_WRITERS',
                    'event': event_type,
                    'file': state_file,
                    'writers': writers
                })

    # Check for cross-event conflicts (events that can fire simultaneously)
    # UserPromptSubmit fires before every response
    # PostToolUse fires after every tool
    # These can overlap!
    user_prompt_writes = all_writes.get('UserPromptSubmit', {})
    post_tool_writes = all_writes.get('PostToolUse', {})

    for state_file in set(user_prompt_writes.keys()) & set(post_tool_writes.keys()):
        conflicts.append({
            'type': 'CROSS_EVENT_CONFLICT',
            'events': ['UserPromptSubmit', 'PostToolUse'],
            'file': state_file,
            'writers': {
                'UserPromptSubmit': user_prompt_writes[state_file],
                'PostToolUse': post_tool_writes[state_file]
            }
        })

    if not conflicts:
        print("✅ No race conditions detected")
    else:
        print(f"⚠️  Found {len(conflicts)} potential race condition(s)\n")

        for i, conflict in enumerate(conflicts, 1):
            print(f"{i}. {conflict['type']}")
            if conflict['type'] == 'SAME_EVENT_MULTIPLE_WRITERS':
                print(f"   Event: {conflict['event']}")
                print(f"   File: {conflict['file']}")
                print(f"   Writers: {', '.join(conflict['writers'])}")
            elif conflict['type'] == 'CROSS_EVENT_CONFLICT':
                print(f"   Events: {' + '.join(conflict['events'])}")
                print(f"   File: {conflict['file']}")
                for event, writers in conflict['writers'].items():
                    print(f"   {event}: {', '.join(writers)}")
            print()

    # Summary
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    if len(by_event.get('UserPromptSubmit', [])) > 10:
        print(f"⚠️  UserPromptSubmit has {len(by_event['UserPromptSubmit'])} hooks")
        print("   → High risk of race conditions and context pollution")
        print("   → Consider reducing to <10 hooks")
        print()

    if conflicts:
        print("🔧 Fix race conditions by:")
        print("   1. Ensure only ONE hook writes to each state file per event")
        print("   2. Use file locks (fcntl) if multiple writers unavoidable")
        print("   3. Consolidate related state updates into single hook")
        print()

    print(f"📊 Total hooks: {sum(len(scripts) for scripts in by_event.values())}")
    print(f"📊 Events with hooks: {len(by_event)}")

if __name__ == '__main__':
    main()
