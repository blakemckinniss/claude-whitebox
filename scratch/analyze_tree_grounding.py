#!/usr/bin/env python3
"""
Tree Grounding Analysis - Should we inject directory structure into hooks?

Research Questions:
1. What's the actual directory structure of the project?
2. How many files/directories exist? (Token cost analysis)
3. What hooks would benefit from tree grounding?
4. What's the semantic relevance threshold?
5. What are the trade-offs?
"""

import os
import json
from pathlib import Path
from collections import defaultdict

def get_tree_structure(root, max_depth=3, ignore=[".git", "__pycache__", ".mypy_cache", ".ruff_cache", "node_modules"]):
    """Generate project tree structure"""
    tree = []

    def walk_tree(path, depth=0, prefix=""):
        if depth > max_depth:
            return

        try:
            entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        except PermissionError:
            return

        for i, entry in enumerate(entries):
            if entry.name in ignore or entry.name.startswith('.'):
                continue

            is_last = i == len(entries) - 1
            current_prefix = "└── " if is_last else "├── "
            tree.append(f"{prefix}{current_prefix}{entry.name}")

            if entry.is_dir():
                extension = "    " if is_last else "│   "
                walk_tree(entry, depth + 1, prefix + extension)

    tree.append(str(root))
    walk_tree(root)
    return "\n".join(tree)

def analyze_file_distribution():
    """Analyze file types and distribution"""
    stats = defaultdict(int)
    total_files = 0
    total_dirs = 0

    for root, dirs, files in os.walk("."):
        # Skip ignored dirs
        dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", ".mypy_cache", ".ruff_cache"]]

        total_dirs += len(dirs)
        total_files += len(files)

        for f in files:
            ext = Path(f).suffix or "no_ext"
            stats[ext] += 1

    return stats, total_files, total_dirs

def estimate_token_cost(tree_structure):
    """Rough token estimate (1 token ≈ 4 chars)"""
    chars = len(tree_structure)
    tokens = chars / 4
    return int(tokens)

def analyze_current_context_hooks():
    """Check which hooks already inject context"""
    context_hooks = []

    hooks_dir = Path(".claude/hooks")
    for hook_file in hooks_dir.glob("*.py"):
        with open(hook_file) as f:
            content = f.read()
            if "additionalContext" in content:
                context_hooks.append(hook_file.name)

    return context_hooks

def analyze_semantic_relevance():
    """Identify scenarios where tree grounding would help"""
    scenarios = {
        "file_creation": {
            "benefit": "Know where to put new files (src/ vs scripts/ vs scratch/)",
            "hooks": ["PreToolUse:Write", "UserPromptSubmit"],
            "relevance": "HIGH - prevents wrong directory placement"
        },
        "codebase_navigation": {
            "benefit": "Understand project layout before searching",
            "hooks": ["UserPromptSubmit"],
            "relevance": "MEDIUM - helpful for new features spanning multiple modules"
        },
        "refactoring": {
            "benefit": "Know what files/dirs exist before restructuring",
            "hooks": ["UserPromptSubmit"],
            "relevance": "HIGH - prevents duplication, knows full scope"
        },
        "import_resolution": {
            "benefit": "Know available modules before writing imports",
            "hooks": ["PreToolUse:Write"],
            "relevance": "MEDIUM - could reduce hallucinated imports"
        },
        "context_loss": {
            "benefit": "Re-ground after long conversation",
            "hooks": ["UserPromptSubmit (conditional)"],
            "relevance": "LOW - agents can just use Glob when needed"
        }
    }
    return scenarios

def main():
    print("=== TREE GROUNDING ANALYSIS ===\n")

    # 1. Generate tree structure
    print("1. PROJECT STRUCTURE (3 levels deep):")
    print("-" * 50)
    tree = get_tree_structure(Path("."), max_depth=3)
    print(tree)
    print()

    # 2. Token cost
    tokens = estimate_token_cost(tree)
    print(f"2. TOKEN COST: ~{tokens} tokens")
    print(f"   Per-turn injection cost: {tokens} tokens")
    print(f"   Budget impact: {tokens / 200000 * 100:.2f}% of 200K budget")
    print()

    # 3. File distribution
    stats, total_files, total_dirs = analyze_file_distribution()
    print("3. FILE DISTRIBUTION:")
    print(f"   Total files: {total_files}")
    print(f"   Total dirs: {total_dirs}")
    print(f"   By extension:")
    for ext, count in sorted(stats.items(), key=lambda x: -x[1])[:10]:
        print(f"      {ext}: {count}")
    print()

    # 4. Current context hooks
    print("4. CURRENT CONTEXT INJECTION HOOKS:")
    current = analyze_current_context_hooks()
    for hook in current:
        print(f"   • {hook}")
    print()

    # 5. Semantic relevance scenarios
    print("5. SEMANTIC RELEVANCE ANALYSIS:")
    scenarios = analyze_semantic_relevance()
    for name, details in scenarios.items():
        print(f"\n   {name.upper().replace('_', ' ')}:")
        print(f"      Benefit: {details['benefit']}")
        print(f"      Target Hooks: {', '.join(details['hooks'])}")
        print(f"      Relevance: {details['relevance']}")
    print()

    # 6. Trade-offs
    print("6. TRADE-OFFS:")
    print("\n   PROS:")
    print("      ✓ Prevents directory confusion (scripts/ vs scratch/ vs .claude/)")
    print("      ✓ Better file placement decisions")
    print("      ✓ Reduces 'where should this go?' questions")
    print("      ✓ Helps with refactoring scope awareness")
    print("      ✓ Could reduce hallucinated paths")
    print("\n   CONS:")
    print(f"      ✗ Token cost: ~{tokens} per turn (if injected every time)")
    print("      ✗ Noise: Most prompts don't need full tree")
    print("      ✗ Redundancy: Agents can glob when needed")
    print("      ✗ Staleness: Tree changes during session")
    print("      ✗ Context pollution: Adds irrelevant info")
    print()

    # 7. Recommendation
    print("7. RECOMMENDATION:")
    print("\n   CONDITIONAL INJECTION (Smart Trigger):")
    print("      • Detect keywords: 'create', 'new file', 'where', 'structure', 'refactor'")
    print("      • Inject ONLY when relevant (not every prompt)")
    print("      • Use shallow tree (2 levels max) to reduce tokens")
    print("      • Cache tree structure (regenerate only on Write/Edit)")
    print()
    print("   ALTERNATIVE: LAZY LOADING")
    print("      • Don't inject proactively")
    print("      • Let Claude use Glob when needed")
    print("      • Add to CLAUDE.md as best practice reminder")
    print()
    print("   HYBRID APPROACH:")
    print("      • SessionStart: Inject shallow tree (2 levels) ONCE")
    print("      • UserPromptSubmit: Inject only on structure-related queries")
    print("      • Keep token cost low via caching + selective injection")
    print()

    # 8. Generate example shallow tree
    print("8. EXAMPLE SHALLOW TREE (2 levels, low token cost):")
    print("-" * 50)
    shallow_tree = get_tree_structure(Path("."), max_depth=2)
    print(shallow_tree)
    shallow_tokens = estimate_token_cost(shallow_tree)
    print(f"\n   Token cost: ~{shallow_tokens} tokens ({shallow_tokens / tokens * 100:.1f}% of full tree)")
    print()

    # Save analysis
    analysis = {
        "full_tree_tokens": tokens,
        "shallow_tree_tokens": shallow_tokens,
        "total_files": total_files,
        "total_dirs": total_dirs,
        "file_stats": dict(stats),
        "current_context_hooks": current,
        "scenarios": scenarios,
        "recommendation": "CONDITIONAL_INJECTION"
    }

    with open("scratch/tree_grounding_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2, default=str)

    print("Analysis saved to: scratch/tree_grounding_analysis.json")

if __name__ == "__main__":
    main()
