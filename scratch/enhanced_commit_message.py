#!/usr/bin/env python3
"""
Enhanced Commit Message Generator
Purpose: Generate rich, semantic commit messages with metadata
"""
import subprocess
import re
from collections import Counter
from pathlib import Path

def get_staged_files():
    """Get list of staged files"""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        timeout=5
    )
    return [f for f in result.stdout.strip().split('\n') if f]

def categorize_files(files):
    """Categorize files by system component"""
    categories = {
        'hooks': [],
        'libraries': [],
        'scripts': [],
        'docs': [],
        'memory': [],
        'config': [],
        'tests': [],
        'projects': []
    }

    for f in files:
        if '.claude/hooks' in f:
            categories['hooks'].append(f)
        elif 'scripts/lib' in f:
            categories['libraries'].append(f)
        elif 'scripts/ops' in f:
            categories['scripts'].append(f)
        elif f.endswith('.md'):
            categories['docs'].append(f)
        elif '.claude/memory' in f:
            categories['memory'].append(f)
        elif 'settings.json' in f or '.claude/config' in f:
            categories['config'].append(f)
        elif 'tests/' in f or f.startswith('test_'):
            categories['tests'].append(f)
        elif 'projects/' in f:
            categories['projects'].append(f)

    return {k: v for k, v in categories.items() if v}

def get_diff_stats():
    """Get line addition/deletion stats"""
    result = subprocess.run(
        ["git", "diff", "--cached", "--shortstat"],
        capture_output=True,
        text=True,
        timeout=5
    )

    # Parse: " 3 files changed, 120 insertions(+), 45 deletions(-)"
    match = re.search(r'(\d+) files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletions?\(-\))?', result.stdout)
    if match:
        return {
            'files': int(match.group(1)),
            'insertions': int(match.group(2) or 0),
            'deletions': int(match.group(3) or 0)
        }
    return {'files': 0, 'insertions': 0, 'deletions': 0}

def extract_protocols_mentioned(files):
    """Identify which protocols are affected by file changes"""
    protocol_keywords = {
        'oracle': 'Oracle Protocol',
        'research': 'Research Protocol',
        'probe': 'Probe Protocol',
        'xray': 'X-Ray Protocol',
        'elephant': 'Elephant Protocol',
        'epistemology': 'Epistemological Protocol',
        'synapse': 'Synapse Protocol',
        'sentinel': 'Sentinel Protocol',
        'cartesian': 'Cartesian Protocol',
        'macgyver': 'MacGyver Protocol',
        'judge': 'Judge Protocol',
        'critic': 'Critic Protocol',
        'verify': 'Reality Check Protocol',
        'scope': 'Finish Line Protocol',
        'void': 'Void Hunter Protocol',
        'council': 'Council Protocol',
        'swarm': 'Swarm Protocol',
        'upkeep': 'Upkeep Protocol'
    }

    protocols = set()
    for f in files:
        filename = Path(f).stem.lower()
        for keyword, protocol_name in protocol_keywords.items():
            if keyword in filename:
                protocols.add(protocol_name)

    return sorted(protocols)

def run_quality_gates(files):
    """Run quality checks and capture results"""
    results = {
        'audit': {'passed': False, 'issues': 0},
        'void': {'passed': False, 'stubs': 0}
    }

    # Filter Python files
    python_files = [f for f in files if f.endswith('.py') and Path(f).exists()]

    if python_files:
        # Run audit
        try:
            audit_result = subprocess.run(
                ["python3", "scripts/ops/audit.py"] + python_files[:10],
                capture_output=True,
                text=True,
                timeout=30
            )
            if "CRITICAL" not in audit_result.stdout:
                results['audit']['passed'] = True
            # Count issues
            results['audit']['issues'] = audit_result.stdout.count("HIGH") + audit_result.stdout.count("CRITICAL")
        except:
            pass

        # Run void
        try:
            void_result = subprocess.run(
                ["python3", "scripts/ops/void.py"] + python_files[:10],
                capture_output=True,
                text=True,
                timeout=30
            )
            if "stub" not in void_result.stdout.lower():
                results['void']['passed'] = True
            results['void']['stubs'] = void_result.stdout.lower().count("stub")
        except:
            pass

    return results

def determine_commit_type_and_scope(files, categories):
    """Infer commit type and scope from changed files"""
    # Type inference
    if any('fix' in f.lower() for f in files):
        commit_type = 'fix'
    elif any('test' in f.lower() for f in files):
        commit_type = 'test'
    elif categories.get('docs'):
        commit_type = 'docs'
    elif categories.get('hooks') or categories.get('libraries'):
        commit_type = 'feat'
    elif categories.get('config') or categories.get('memory'):
        commit_type = 'chore'
    else:
        commit_type = 'chore'

    # Scope inference
    if categories.get('hooks') and categories.get('libraries'):
        scope = 'system'
    elif categories.get('hooks'):
        scope = 'hooks'
    elif categories.get('libraries'):
        scope = 'lib'
    elif categories.get('scripts'):
        scope = 'ops'
    elif categories.get('docs'):
        scope = 'docs'
    else:
        scope = None

    return commit_type, scope

def calculate_impact_score(files, categories):
    """Calculate commit impact score"""
    return len(files) * (1 + len(categories))

def generate_enhanced_message(short_description):
    """Generate full commit message with semantic metadata"""
    files = get_staged_files()
    if not files:
        return None

    categories = categorize_files(files)
    stats = get_diff_stats()
    protocols = extract_protocols_mentioned(files)
    quality = run_quality_gates(files)
    commit_type, scope = determine_commit_type_and_scope(files, categories)
    impact = calculate_impact_score(files, categories)

    # Build commit message
    lines = []

    # Subject line
    scope_str = f"({scope})" if scope else ""
    lines.append(f"{commit_type}{scope_str}: {short_description}")
    lines.append("")

    # Impact summary
    lines.append("Impact Analysis:")
    lines.append(f"  Files changed: {stats['files']} ({', '.join(f'{k}: {len(v)}' for k, v in categories.items())})")
    lines.append(f"  Lines: +{stats['insertions']} -{stats['deletions']}")
    lines.append(f"  Impact score: {impact}")

    if protocols:
        lines.append(f"  Protocols affected: {', '.join(protocols)}")

    # Quality gates
    lines.append("")
    lines.append("Quality Gates:")
    if quality['audit']['passed']:
        lines.append(f"  ✅ audit.py (0 critical issues)")
    else:
        lines.append(f"  ⚠️ audit.py ({quality['audit']['issues']} issues)")

    if quality['void']['passed']:
        lines.append(f"  ✅ void.py (0 stubs)")
    else:
        lines.append(f"  ⚠️ void.py ({quality['void']['stubs']} stubs found)")

    # File changes
    if len(files) <= 10:
        lines.append("")
        lines.append("Files Changed:")
        for f in files:
            lines.append(f"  • {f}")

    # Footer
    lines.append("")
    lines.append("🤖 Generated with [Claude Code](https://claude.com/claude-code)")
    lines.append("")
    lines.append("Co-Authored-By: Claude <noreply@anthropic.com>")

    return '\n'.join(lines)

def main():
    """CLI entry point"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: enhanced_commit_message.py '<short description>'")
        print("\nExample:")
        print("  enhanced_commit_message.py 'Add git semantic injection hook'")
        sys.exit(1)

    description = sys.argv[1]
    message = generate_enhanced_message(description)

    if message:
        print(message)
    else:
        print("Error: No staged files found")
        sys.exit(1)

if __name__ == "__main__":
    main()
