#!/usr/bin/env python3
"""Monitor process cleanup over time"""

import subprocess
import time

print("Monitoring test_hooks.py processes for 30 seconds...")
print("Time | Count | PIDs")
print("-" * 60)

for i in range(6):  # 6 samples over 30 seconds
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )

    test_procs = [
        line for line in result.stdout.split('\n')
        if 'test_hooks.py' in line and 'grep' not in line
    ]

    count = len(test_procs)
    pids = [line.split()[1] for line in test_procs]

    print(f"{i*5:>4}s | {count:>5} | {', '.join(pids[:10])}")

    if i < 5:  # Don't sleep on last iteration
        time.sleep(5)

print("\nIf count remains high (>5), there may be a cleanup issue.")
