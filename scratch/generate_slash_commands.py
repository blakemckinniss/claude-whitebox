#!/usr/bin/env python3
"""Generate slash commands for all ops scripts."""

import os
from pathlib import Path

# Find project root
def find_project_root():
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "scripts" / "lib" / "core.py").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root")

PROJECT_ROOT = find_project_root()
COMMANDS_DIR = PROJECT_ROOT / ".claude" / "commands"
OPS_DIR = PROJECT_ROOT / "scripts" / "ops"

# Command definitions: name -> (description, arg_hint, bash_command)
COMMANDS = {
    "council": (
        "🏛️ The Council - Parallel multi-perspective analysis (Judge, Critic, Skeptic, Thinker, Oracle)",
        "[proposal]",
        'python3 scripts/ops/council.py "$ARGUMENTS"'
    ),
    "judge": (
        "⚖️ The Judge - Value assurance, ROI, YAGNI, anti-bikeshedding",
        "[proposal]",
        'python3 scripts/ops/judge.py "$ARGUMENTS"'
    ),
    "critic": (
        "🥊 The Critic - The 10th Man, attacks assumptions and exposes blind spots",
        "[idea]",
        'python3 scripts/ops/critic.py "$ARGUMENTS"'
    ),
    "consult": (
        "🔮 The Oracle - High-level reasoning via OpenRouter",
        "[question]",
        'python3 scripts/ops/consult.py "$ARGUMENTS"'
    ),
    "think": (
        "🧠 The Thinker - Decomposes complex problems into sequential steps",
        "[problem]",
        'python3 scripts/ops/think.py "$ARGUMENTS"'
    ),
    "skeptic": (
        "🔍 The Skeptic - Hostile review, finds ways things will fail",
        "[proposal]",
        'python3 scripts/ops/skeptic.py "$ARGUMENTS"'
    ),
    "research": (
        "🌐 The Researcher - Live web search via Tavily API",
        "[query]",
        'python3 scripts/ops/research.py "$ARGUMENTS"'
    ),
    "verify": (
        "🤥 Reality Check - Verifies system state (file_exists, grep_text, port_open, command_success)",
        "[check_type] [target] [expected?]",
        'python3 scripts/ops/verify.py $ARGUMENTS'
    ),
    "scope": (
        "🏁 The Finish Line - Manage Definition of Done (init, check, status)",
        "[init|check|status] [args...]",
        'python3 scripts/ops/scope.py $ARGUMENTS'
    ),
    "audit": (
        "🛡️ The Sheriff - Code quality audit (security, complexity, style)",
        "[file_path]",
        'python3 scripts/ops/audit.py $ARGUMENTS'
    ),
    "void": (
        "🕳️ The Void Hunter - Completeness check (finds stubs, missing CRUD, error handling gaps)",
        "[file_or_dir]",
        'python3 scripts/ops/void.py $ARGUMENTS'
    ),
    "inventory": (
        "🖇️ MacGyver Scan - Scans for available binaries and system tools",
        "[--compact]",
        'python3 scripts/ops/inventory.py $ARGUMENTS'
    ),
    "drift": (
        "⚖️ The Court - Checks project consistency and style drift",
        "",
        'python3 scripts/ops/drift_check.py'
    ),
    "spark": (
        "⚡ Synapse Fire - Retrieve associative memories for a topic",
        "[topic]",
        'python3 scripts/ops/spark.py "$ARGUMENTS"'
    ),
}

def generate_command_file(name, description, arg_hint, bash_command):
    """Generate a slash command markdown file."""
    content = f"""---
description: {description}
argument-hint: {arg_hint}
allowed-tools: Bash
---

!`{bash_command}`
"""

    output_path = COMMANDS_DIR / f"{name}.md"
    output_path.write_text(content)
    print(f"✅ Created: {name}.md")

def main():
    """Generate all slash command files."""
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"📁 Generating slash commands in {COMMANDS_DIR}")
    print(f"📊 Total commands: {len(COMMANDS)}\n")

    for name, (description, arg_hint, bash_command) in COMMANDS.items():
        generate_command_file(name, description, arg_hint, bash_command)

    print(f"\n✅ All {len(COMMANDS)} slash commands created")
    print("\n💡 Usage:")
    print("   /council \"Should we rewrite in Rust?\"")
    print("   /verify file_exists .env")
    print("   /scope status")

if __name__ == "__main__":
    main()
