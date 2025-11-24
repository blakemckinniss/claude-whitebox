#!/usr/bin/env python3
"""
Analyze hooks for race condition risks.
Checks which hooks read/write to shared session state files.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

# Files that are shared session state
STATE_FILES = {
    '.claude/memory/session_.*_state.json': 'Session State',
    '.claude/memory/punch_list.json': 'Punch List',
    '.claude/memory/evidence.json': 'Evidence Log',
    '.claude/memory/commands_run.json': 'Command Tracker',
    '.claude/memory/active_context.md': 'Active Context',
    '.claude/memory/lessons.md': 'Lessons',
}

def analyze_hook_file(hook_path):
    """Check what state files a hook reads/writes"""
    if not Path(hook_path).exists():
        return {'reads': set(), 'writes': set(), 'error': 'File not found'}

    try:
        content = Path(hook_path).read_text()
    except Exception as e:
        return {'reads': set(), 'writes': set(), 'error': str(e)}

    reads = set()
    writes = set()

    # Look for file operations
    for pattern, label in STATE_FILES.items():
        # Check for reads
        if re.search(rf'open\(["\'].*{pattern.replace(".*", ".*?")}["\'].*["\']r', content):
            reads.add(label)
        if re.search(rf'\.read_text\(\)|json\.load', content) and pattern.replace('.*', '') in content:
            reads.add(label)

        # Check for writes
        if re.search(rf'open\(["\'].*{pattern.replace(".*", ".*?")}["\'].*["\']w', content):
            writes.add(label)
        if re.search(rf'\.write_text\(|json\.dump', content) and pattern.replace('.*', '') in content:
            writes.add(label)

    return {'reads': reads, 'writes': writes}

def main():
    # Load settings
    with open('.claude/settings.json') as f:
        config = json.load(f)

    # Track conflicts
    conflicts = defaultdict(list)

    print("=" * 80)
    print("RACE CONDITION ANALYSIS")
    print("=" * 80)

    # Analyze each event type
    for event_type, matchers in config['hooks'].items():
        print(f"\n{event_type} ({len(matchers)} matcher(s)):")
        print("-" * 80)

        writers = defaultdict(list)
        readers = defaultdict(list)

        for matcher in matchers:
            matcher_name = matcher.get('matcher', 'default')
            hooks = matcher.get('hooks', [])

            for hook in hooks:
                if hook['type'] != 'command':
                    continue

                # Extract script path
                cmd = hook['command']
                match = re.search(r'python3 \$CLAUDE_PROJECT_DIR/(.*\.py)', cmd)
                if not match:
                    continue

                script_path = match.group(1)
                script_name = Path(script_path).stem

                # Analyze the script
                result = analyze_hook_file(script_path)

                if 'error' in result:
                    print(f"  ⚠️  {script_name}: {result['error']}")
                    continue

                # Track readers and writers
                for state_file in result['reads']:
                    readers[state_file].append(script_name)

                for state_file in result['writes']:
                    writers[state_file].append(script_name)

                    # Check if multiple writers in same event
                    if len(writers[state_file]) > 1:
                        conflicts[event_type].append({
                            'file': state_file,
                            'writers': writers[state_file]
                        })

                # Print if it touches state
                if result['reads'] or result['writes']:
                    ops = []
                    if result['reads']:
                        ops.append(f"R: {', '.join(result['reads'])}")
                    if result['writes']:
                        ops.append(f"W: {', '.join(result['writes'])}")
                    print(f"  • {script_name:30} {' | '.join(ops)}")

    # Report conflicts
    print("\n" + "=" * 80)
    print("RACE CONDITION RISKS")
    print("=" * 80)

    if not conflicts:
        print("✅ No obvious race conditions detected")
    else:
        for event_type, issues in conflicts.items():
            print(f"\n⚠️  {event_type}:")
            for issue in issues:
                print(f"  • {issue['file']}: {len(issue['writers'])} writers")
                print(f"    Writers: {', '.join(issue['writers'])}")

    # Check cross-event conflicts (harder to detect)
    print("\n" + "=" * 80)
    print("CROSS-EVENT CONFLICTS (Manual Review Needed)")
    print("=" * 80)
    print("⚠️  UserPromptSubmit (19 hooks) runs BEFORE every response")
    print("⚠️  PostToolUse (4 hooks) runs AFTER every tool")
    print("⚠️  If both write to same file → RACE CONDITION")
    print("\nRecommendation: Limit writes to ONE hook per state file per event")

if __name__ == '__main__':
    main()
