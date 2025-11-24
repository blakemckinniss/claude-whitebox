#!/usr/bin/env python3
"""Batch quality check for all modified/new files"""
import subprocess
import sys

files = [
    ".claude/hooks/meta_cognition_performance.py",
    ".claude/hooks/detect_failure_auto_learn.py",
    ".claude/hooks/detect_sequential_agents.py",
    ".claude/hooks/detect_success_auto_learn.py",
    ".claude/hooks/hook_performance_monitor.py",
    ".claude/hooks/parallel_agent_reminder.py",
    ".claude/hooks/parallel_hook_executor.py",
    ".claude/hooks/scratch_context_hook.py",
    "scripts/lib/council_engine.py",
    "scripts/lib/epistemology.py",
    "scripts/lib/oracle.py",
    "scripts/lib/parallel.py",
    "scripts/lib/agent_delegation.py",
    "scripts/ops/oracle.py",
    "scripts/ops/upkeep.py",
    "scripts/ops/consolidate_lessons.py",
    "scripts/ops/oracle_batch.py",
]

print("🛡️ Running audit.py...")
for f in files:
    result = subprocess.run(["python3", "scripts/ops/audit.py", f], capture_output=True)
    if result.returncode != 0:
        print(f"❌ AUDIT FAILED: {f}")
        sys.exit(1)

print("✅ All audits passed")

print("\n🔍 Running void.py...")
for f in files:
    result = subprocess.run(["python3", "scripts/ops/void.py", "--stub-only", f], capture_output=True)
    if result.returncode != 0:
        print(f"❌ VOID FAILED: {f}")
        sys.exit(1)

print("✅ All void checks passed")

print("\n⚖️ Running drift_check.py...")
for f in files:
    result = subprocess.run(["python3", "scripts/ops/drift_check.py", f], capture_output=True)
    if result.returncode != 0:
        print(f"⚠️ DRIFT WARNING: {f}")

print("\n✅ Quality checks complete")
