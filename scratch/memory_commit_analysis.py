#!/usr/bin/env python3
"""Analyze .claude/memory/ to determine what should be committed vs ignored."""

import json
from pathlib import Path

memory_dir = Path(".claude/memory")

# Categories
TEMPLATES = []  # Config files that define structure
SHARED_KNOWLEDGE = []  # Knowledge base for the SDK
RUNTIME_STATE = []  # Session-specific transient data
TELEMETRY = []  # Performance logs

for file in sorted(memory_dir.rglob("*")):
    if file.is_dir():
        continue
    
    rel_path = str(file.relative_to(memory_dir))
    
    # Categorize
    if file.name.startswith("session_") and file.name.endswith("_state.json"):
        RUNTIME_STATE.append(rel_path)
    elif "telemetry" in file.name or "debt_ledger" in file.name:
        TELEMETRY.append(rel_path)
    elif file.name in ["active_context.md", "upkeep_log.md", "performance_dashboard.md"]:
        RUNTIME_STATE.append(rel_path)
    elif file.name in ["lessons.md", "decisions.md", "anti_patterns.md", "synapses.json"]:
        SHARED_KNOWLEDGE.append(rel_path)
    elif "config" in file.name or "registry" in file.name or file.name == "settings_baseline.json":
        TEMPLATES.append(rel_path)
    elif "_state.json" in file.name or "_enforcement_state" in file.name:
        RUNTIME_STATE.append(rel_path)
    elif file.suffix in [".jsonl"]:
        TELEMETRY.append(rel_path)
    elif file.parent.name == "context_audit":
        TELEMETRY.append(rel_path)
    elif file.parent.name == "deliberations":
        TELEMETRY.append(rel_path)
    elif file.parent.name == "session_digests":
        TELEMETRY.append(rel_path)
    else:
        # Fallback
        if "test" in file.name:
            RUNTIME_STATE.append(rel_path)
        else:
            TEMPLATES.append(rel_path)

print("## COMMIT TO GIT (SDK Knowledge Base)")
print("These define the SDK's behavior and shared knowledge:\n")
for f in sorted(TEMPLATES + SHARED_KNOWLEDGE):
    print(f"  .claude/memory/{f}")

print("\n## IGNORE (Runtime/Telemetry)")
print("These are session-specific or accumulate indefinitely:\n")
for f in sorted(RUNTIME_STATE + TELEMETRY):
    print(f"  .claude/memory/{f}")

print("\n## Recommended .gitignore additions:")
print("""
# Session-specific runtime state
.claude/memory/session_*_state.json
.claude/memory/active_context.md
.claude/memory/upkeep_log.md
.claude/memory/performance_dashboard.md

# Telemetry (grows unbounded)
.claude/memory/*_telemetry.jsonl
.claude/memory/debt_ledger.jsonl
.claude/memory/context_audit/
.claude/memory/deliberations/
.claude/memory/session_digests/

# Enforcement runtime state (auto-tuning)
.claude/memory/*_enforcement_state.json
.claude/memory/*_state.json
.claude/memory/tier_gate_state.json
.claude/memory/scratch_enforcement_state.json
.claude/memory/confidence_state.json
.claude/memory/batching_enforcement_state.json
.claude/memory/auto_commit_state.json
""")
