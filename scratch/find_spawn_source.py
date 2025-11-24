#!/usr/bin/env python3
"""Find what's spawning test_hooks.py repeatedly"""

import subprocess
import time

print("Sampling parent processes of test_hooks.py...")
print("="  * 70)

parents = {}

for i in range(5):
    result = subprocess.run(
        ["ps", "-eo", "pid,ppid,cmd"],
        capture_output=True,
        text=True
    )

    for line in result.stdout.split('\n'):
        if 'test_hooks.py' in line and 'grep' not in line:
            parts = line.split()
            if len(parts) >= 3:
                pid = parts[0]
                ppid = parts[1]

                if ppid not in parents:
                    parents[ppid] = {
                        'count': 0,
                        'example_cmd': ' '.join(parts[2:])[:80]
                    }
                parents[ppid]['count'] += 1

    time.sleep(2)

print("\nParent Process Analysis:")
print("-" * 70)

for ppid, data in sorted(parents.items(), key=lambda x: x[1]['count'], reverse=True):
    print(f"\nPPID {ppid}: Spawned {data['count']} test_hooks.py processes")

    # Get parent process info
    parent_result = subprocess.run(
        ["ps", "-p", ppid, "-o", "pid,cmd"],
        capture_output=True,
        text=True
    )

    parent_lines = parent_result.stdout.strip().split('\n')
    if len(parent_lines) > 1:
        print(f"  Parent Command: {parent_lines[1]}")
    else:
        print(f"  Parent: <no longer running>")

print("\n" + "=" * 70)
print("DIAGNOSIS:")

if len(parents) > 1:
    print("⚠️  Multiple different parents spawning test_hooks.py")
    print("   This suggests a hook loop or recursive trigger.")
elif len(parents) == 1:
    ppid = list(parents.keys())[0]
    count = parents[ppid]['count']
    if count > 10:
        print(f"❌ PPID {ppid} spawned {count} instances")
        print("   Likely cause: Background hook triggering itself")
    else:
        print(f"✅ Normal: PPID {ppid} spawned {count} instances over 10s")
else:
    print("✅ No test_hooks.py processes found (system healthy)")
