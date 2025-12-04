#!/usr/bin/env python3
"""
Capabilities Index Generator: Extracts and categorizes all hook/op functionality.

This script scans all hooks and ops, extracts their docstrings, and generates
a structured capabilities index. This prevents Claude from proposing "new"
functionality that already exists.

Usage:
    python capabilities.py [--regenerate] [--json]

The generated index is saved to .claude/memory/__capabilities.md
"""

import ast
import json
import re
import sys
from pathlib import Path
from datetime import datetime

# =============================================================================
# PATHS
# =============================================================================

CLAUDE_DIR = Path(__file__).parent.parent
HOOKS_DIR = CLAUDE_DIR / "hooks"
OPS_DIR = CLAUDE_DIR / "ops"
COMMANDS_DIR = CLAUDE_DIR / "commands"
MEMORY_DIR = CLAUDE_DIR / "memory"
OUTPUT_FILE = MEMORY_DIR / "__capabilities.md"
OUTPUT_JSON = MEMORY_DIR / "__capabilities.json"

# =============================================================================
# CATEGORIES (functional grouping)
# =============================================================================

# Keywords that indicate category membership
CATEGORY_KEYWORDS = {
    "gates_security": ["security", "injection", "xss", "sql", "command injection", "vulnerability", "audit"],
    "gates_workflow": ["commit", "upkeep", "production", "deferral", "todo", "fixme"],
    "gates_quality": ["error", "suppression", "integration", "blind", "read before"],
    "gates_scope": ["scope", "drift", "goal", "anchor", "expansion"],
    "gates_reasoning": ["think", "assumption", "counterfactual", "sunk cost", "reasoning"],
    "injectors_context": ["context", "inject", "surface", "pointer", "resource"],
    "injectors_memory": ["memory", "lesson", "decision", "spark", "remember"],
    "injectors_ops": ["ops", "tool", "script", "awareness", "nudge"],
    "trackers": ["track", "velocity", "state", "monitor", "gain"],
    "lifecycle": ["session", "start", "end", "cleanup", "init", "compact"],
    "verification": ["verify", "check", "audit", "void", "gap"],
    "research": ["research", "docs", "probe", "web", "fetch"],
    "decision": ["council", "oracle", "think", "judge", "critic"],
    "memory_ops": ["remember", "spark", "evidence", "lesson"],
}


def categorize(name: str, docstring: str) -> str:
    """Categorize a hook/op based on name and docstring."""
    text = f"{name} {docstring}".lower()

    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[category] = score

    if scores:
        return max(scores, key=scores.get)
    return "other"


def extract_docstring(filepath: Path) -> tuple[str, str]:
    """Extract module docstring and first-line summary from Python file."""
    try:
        source = filepath.read_text()
        tree = ast.parse(source)
        docstring = ast.get_docstring(tree) or ""

        # Get first meaningful line as summary
        lines = [l.strip() for l in docstring.split("\n") if l.strip()]
        summary = lines[0] if lines else filepath.stem

        # Clean up summary
        summary = re.sub(r"^(Hook|Script|Tool)[:\s]+", "", summary, flags=re.IGNORECASE)
        summary = summary.rstrip(".")

        return summary, docstring
    except (SyntaxError, IOError):
        return filepath.stem, ""


def extract_command_purpose(filepath: Path) -> str:
    """Extract purpose from slash command markdown file."""
    try:
        content = filepath.read_text()
        # Look for description in frontmatter or first paragraph
        lines = content.split("\n")
        for line in lines[:10]:
            if line.strip() and not line.startswith("#") and not line.startswith("-"):
                return line.strip()[:100]
        return filepath.stem
    except IOError:
        return filepath.stem


def scan_hooks() -> list[dict]:
    """Scan all hooks and extract their purposes."""
    hooks = []
    for f in sorted(HOOKS_DIR.glob("*.py")):
        if f.name.startswith("_"):
            continue
        summary, docstring = extract_docstring(f)
        category = categorize(f.stem, docstring)
        hooks.append({
            "name": f.stem,
            "type": "hook",
            "summary": summary,
            "category": category,
            "path": str(f.relative_to(CLAUDE_DIR.parent)),
        })
    return hooks


def scan_ops() -> list[dict]:
    """Scan all ops and extract their purposes."""
    ops = []
    for f in sorted(OPS_DIR.glob("*.py")):
        if f.name.startswith("_") or f.name == "capabilities.py":
            continue
        summary, docstring = extract_docstring(f)
        category = categorize(f.stem, docstring)
        ops.append({
            "name": f.stem,
            "type": "op",
            "summary": summary,
            "category": category,
            "path": str(f.relative_to(CLAUDE_DIR.parent)),
        })
    return ops


def scan_commands() -> list[dict]:
    """Scan slash commands for their purposes."""
    commands = []
    for f in sorted(COMMANDS_DIR.glob("*.md")):
        if f.name == "README.md":
            continue
        purpose = extract_command_purpose(f)
        commands.append({
            "name": f.stem,
            "type": "command",
            "summary": purpose,
            "category": "command",
            "path": str(f.relative_to(CLAUDE_DIR.parent)),
        })
    return commands


def generate_markdown(capabilities: list[dict]) -> str:
    """Generate markdown capabilities index."""
    lines = [
        "# Capabilities Index",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "**PURPOSE:** Before proposing new functionality, check if it exists here.",
        "",
        "---",
        "",
    ]

    # Group by category
    by_category = {}
    for cap in capabilities:
        cat = cap["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(cap)

    # Category display names
    category_names = {
        "gates_security": "🔒 Security Gates",
        "gates_workflow": "📋 Workflow Gates",
        "gates_quality": "✅ Quality Gates",
        "gates_scope": "🎯 Scope Control",
        "gates_reasoning": "🧠 Reasoning Guards",
        "injectors_context": "💉 Context Injectors",
        "injectors_memory": "🧠 Memory Injectors",
        "injectors_ops": "🔧 Ops Awareness",
        "trackers": "📊 Trackers",
        "lifecycle": "🔄 Lifecycle Hooks",
        "verification": "🔍 Verification Tools",
        "research": "🌐 Research Tools",
        "decision": "⚖️ Decision Tools",
        "memory_ops": "💾 Memory Operations",
        "command": "⌨️ Slash Commands",
        "other": "📦 Other",
    }

    # Sort categories
    cat_order = list(category_names.keys())
    sorted_cats = sorted(by_category.keys(), key=lambda c: cat_order.index(c) if c in cat_order else 999)

    for cat in sorted_cats:
        items = by_category[cat]
        display_name = category_names.get(cat, cat.replace("_", " ").title())
        lines.append(f"## {display_name}")
        lines.append("")

        for item in sorted(items, key=lambda x: x["name"]):
            name = item["name"]
            summary = item["summary"][:80]
            item_type = item["type"]

            if item_type == "hook":
                lines.append(f"- **{name}** - {summary}")
            elif item_type == "op":
                lines.append(f"- `{name}.py` - {summary}")
            else:
                lines.append(f"- `/{name}` - {summary}")

        lines.append("")

    # Add duplication prevention notice
    lines.extend([
        "---",
        "",
        "## Before Creating New Functionality",
        "",
        "1. **Search this index** for similar capabilities",
        "2. **Read the existing implementation** if found",
        "3. **Justify why existing is insufficient** before creating new",
        "4. **Consider extending** existing over creating new",
        "",
        "**Anti-pattern:** Creating `new_security_gate.py` when `content_gate.py` already handles security.",
        "",
    ])

    return "\n".join(lines)


def main():
    """Generate capabilities index."""
    regenerate = "--regenerate" in sys.argv or "-r" in sys.argv
    output_json = "--json" in sys.argv

    # Check if regeneration needed
    if OUTPUT_FILE.exists() and not regenerate:
        age_hours = (datetime.now().timestamp() - OUTPUT_FILE.stat().st_mtime) / 3600
        if age_hours < 24:
            print(f"Capabilities index is fresh ({age_hours:.1f}h old). Use --regenerate to force.")
            if output_json:
                print(json.dumps({"status": "fresh", "age_hours": age_hours}))
            return

    print("Scanning capabilities...")

    # Scan all sources
    hooks = scan_hooks()
    ops = scan_ops()
    commands = scan_commands()

    all_caps = hooks + ops + commands

    print(f"  Found: {len(hooks)} hooks, {len(ops)} ops, {len(commands)} commands")

    # Generate markdown
    markdown = generate_markdown(all_caps)

    # Save
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(markdown)
    print(f"  Saved: {OUTPUT_FILE}")

    if output_json:
        OUTPUT_JSON.write_text(json.dumps(all_caps, indent=2))
        print(f"  Saved: {OUTPUT_JSON}")

    # Print summary
    by_cat = {}
    for cap in all_caps:
        cat = cap["category"]
        by_cat[cat] = by_cat.get(cat, 0) + 1

    print("\nCapabilities by category:")
    for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
