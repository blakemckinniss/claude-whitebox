#!/usr/bin/env python3
"""
Find TRUE race conditions: multiple hooks writing to same file in SAME event.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

def check_writes_state(script_path):
    """Check if a script writes to session state"""
    if not Path(script_path).exists():
        return None

    content = Path(script_path).read_text()

    # Check for state writing functions/patterns
    writes = {
        'session_state': 'save_session_state' in content or 'record_command_run' in content,
        'lessons': '.write_text' in content and 'lessons.md' in content,
        'evidence': '.write_text' in content and 'evidence' in content,
        'punch_list': 'json.dump' in content and 'punch_list' in content,
    }

    return {k: v for k, v in writes.items() if v}

def main():
    with open('.claude/settings.json') as f:
        config = json.load(f)

    print("=" * 80)
    print("TRUE RACE CONDITION DETECTOR")
    print("=" * 80)
    print("\nSearching for: Multiple hooks writing SAME file in SAME event")
    print()

    # Analyze each event
    races_found = []

    for event_type, matchers in config['hooks'].items():
        print(f"\n{event_type}:")
        print("-" * 80)

        # Track writers per file
        writers = defaultdict(list)

        for matcher in matchers:
            hooks = matcher.get('hooks', [])

            for hook in hooks:
                if hook['type'] != 'command':
                    continue

                cmd = hook['command']
                match = re.search(r'python3 \$CLAUDE_PROJECT_DIR/(.*\.py)', cmd)
                if not match:
                    continue

                script_path = match.group(1)
                script_name = Path(script_path).stem

                # Check what this script writes
                writes = check_writes_state(script_path)

                if writes:
                    for file_type in writes.keys():
                        writers[file_type].append(script_name)
                    print(f"  ✍️  {script_name:30} writes: {', '.join(writes.keys())}")

        # Detect races (multiple writers to same file)
        for file_type, hook_list in writers.items():
            if len(hook_list) > 1:
                races_found.append({
                    'event': event_type,
                    'file': file_type,
                    'writers': hook_list
                })

    # Report
    print("\n" + "=" * 80)
    print("RACE CONDITION RESULTS")
    print("=" * 80)

    if not races_found:
        print("\n✅ NO RACE CONDITIONS FOUND")
        print("\n   All hooks write to different files, or only one writer per file.")
        print("   Sequential execution ensures no collisions.")
    else:
        print(f"\n⚠️  FOUND {len(races_found)} RACE CONDITION(S)")
        print()

        for i, race in enumerate(races_found, 1):
            print(f"{i}. {race['event']} → {race['file']}")
            print(f"   Writers: {', '.join(race['writers'])}")
            print(f"   Risk: Both hooks run sequentially in same event,")
            print(f"         but second hook may overwrite first hook's changes")
            print(f"   Fix: Consolidate writes into single hook")
            print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print("\n📊 Current configuration:")
    print(f"   • Total events with hooks: {len(config['hooks'])}")
    print(f"   • Events analyzed: {len(config['hooks'])}")
    print(f"   • Race conditions: {len(races_found)}")

    if races_found:
        print("\n🔧 Recommended fixes:")
        print("   1. Merge hooks that write to same file into single hook")
        print("   2. Use file locking (fcntl) if merge not feasible")
        print("   3. Read-modify-write pattern with proper state merging")
    else:
        print("\n✅ Configuration is race-condition free!")
        print("   All state writes are properly isolated.")

if __name__ == '__main__':
    main()
