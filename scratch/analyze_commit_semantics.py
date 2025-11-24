#!/usr/bin/env python3
"""
Commit Semantic Analysis
Purpose: Extract maximum semantic value from git commit history for context grounding
"""
import subprocess
import json
import re
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path

def get_commit_data(limit=100):
    """Extract comprehensive commit data"""
    # Get commit subjects first
    result = subprocess.run(
        ["git", "log", f"-{limit}", "--format=%H|%h|%s|%an|%ae|%ai|%P"],
        capture_output=True,
        text=True,
        timeout=10
    )

    commits = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split('|')
        if len(parts) >= 6:
            commit_hash = parts[0]

            # Get body separately
            body_result = subprocess.run(
                ["git", "log", "-1", "--format=%b", commit_hash],
                capture_output=True,
                text=True,
                timeout=5
            )

            commits.append({
                'hash': parts[0],
                'short_hash': parts[1],
                'subject': parts[2],
                'body': body_result.stdout.strip() if body_result.returncode == 0 else '',
                'author': parts[3],
                'email': parts[4],
                'date': parts[5],
                'parents': parts[6].split() if len(parts) > 6 else []
            })

    return commits

def get_commit_files(commit_hash):
    """Get files changed in a commit"""
    result = subprocess.run(
        ["git", "show", "--stat", "--format=", commit_hash],
        capture_output=True,
        text=True,
        timeout=5
    )

    files = []
    for line in result.stdout.split('\n'):
        if '|' in line:
            filepath = line.split('|')[0].strip()
            if filepath and not filepath.startswith('commit'):
                files.append(filepath)

    return files

def extract_commit_type(subject):
    """Parse conventional commit type"""
    match = re.match(r'^(\w+)(?:\(([^)]+)\))?: (.+)$', subject)
    if match:
        return {
            'type': match.group(1),
            'scope': match.group(2),
            'description': match.group(3)
        }
    return {'type': 'unknown', 'scope': None, 'description': subject}

def categorize_files(files):
    """Categorize files by purpose"""
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

def analyze_temporal_patterns(commits):
    """Analyze temporal patterns in commits"""
    hours = defaultdict(int)
    days = defaultdict(int)

    for commit in commits:
        try:
            dt = datetime.fromisoformat(commit['date'].replace(' -0500', ''))
            hours[dt.hour] += 1
            days[dt.strftime('%A')] += 1
        except:
            continue

    return {
        'peak_hours': sorted(hours.items(), key=lambda x: x[1], reverse=True)[:3],
        'peak_days': sorted(days.items(), key=lambda x: x[1], reverse=True)[:3]
    }

def extract_semantic_themes(commits):
    """Extract high-level themes from commit messages"""
    themes = Counter()
    keywords = [
        'protocol', 'hook', 'performance', 'parallel', 'epistemology',
        'quality', 'automation', 'testing', 'memory', 'oracle',
        'research', 'probe', 'verify', 'audit', 'swarm', 'agent'
    ]

    for commit in commits:
        text = f"{commit['subject']} {commit['body']}".lower()
        for keyword in keywords:
            if keyword in text:
                themes[keyword] += 1

    return themes.most_common(10)

def analyze_file_hotspots(commits):
    """Identify frequently modified files"""
    file_changes = Counter()

    for commit in commits[:30]:  # Last 30 commits
        files = get_commit_files(commit['hash'])
        for f in files:
            file_changes[f] += 1

    return file_changes.most_common(15)

def extract_feature_evolution(commits):
    """Track feature implementation timeline"""
    features = []

    for commit in commits:
        parsed = extract_commit_type(commit['subject'])
        if parsed['type'] in ['feat', 'feature']:
            features.append({
                'date': commit['date'][:10],
                'scope': parsed['scope'],
                'description': parsed['description'],
                'hash': commit['short_hash']
            })

    return features

def analyze_quality_gates(commits):
    """Analyze quality gate adoption"""
    quality_mentions = {
        'audit': 0,
        'void': 0,
        'drift': 0,
        'verify': 0,
        'test': 0
    }

    for commit in commits:
        text = f"{commit['subject']} {commit['body']}".lower()
        for gate in quality_mentions:
            if gate in text:
                quality_mentions[gate] += 1

    return quality_mentions

def main():
    """Run comprehensive commit analysis"""
    print("🔍 COMMIT SEMANTIC ANALYSIS")
    print("="*60)

    # Get commit data
    commits = get_commit_data(limit=100)
    print(f"\n📊 Analyzing {len(commits)} commits")

    # 1. Commit type distribution
    print("\n📋 COMMIT TYPE DISTRIBUTION")
    types = Counter([extract_commit_type(c['subject'])['type'] for c in commits])
    for commit_type, count in types.most_common(8):
        print(f"  {commit_type:12s} : {count:3d} commits ({count/len(commits)*100:.1f}%)")

    # 2. Scope distribution
    print("\n🎯 SCOPE DISTRIBUTION")
    scopes = Counter([extract_commit_type(c['subject'])['scope'] for c in commits if extract_commit_type(c['subject'])['scope']])
    for scope, count in scopes.most_common(8):
        print(f"  {scope:12s} : {count:3d} commits")

    # 3. Temporal patterns
    print("\n⏰ TEMPORAL PATTERNS")
    temporal = analyze_temporal_patterns(commits)
    print("  Peak Hours:")
    for hour, count in temporal['peak_hours']:
        print(f"    {hour:02d}:00 - {count} commits")
    print("  Peak Days:")
    for day, count in temporal['peak_days']:
        print(f"    {day:10s} - {count} commits")

    # 4. Semantic themes
    print("\n🧠 SEMANTIC THEMES")
    themes = extract_semantic_themes(commits)
    for theme, count in themes:
        print(f"  {theme:15s} : {count:3d} mentions")

    # 5. File hotspots
    print("\n🔥 FILE HOTSPOTS (Last 30 commits)")
    hotspots = analyze_file_hotspots(commits)
    for filepath, changes in hotspots[:10]:
        print(f"  {changes:2d}x : {filepath}")

    # 6. Feature evolution
    print("\n🚀 FEATURE EVOLUTION (Last 20 features)")
    features = extract_feature_evolution(commits)
    for feat in features[:20]:
        scope_str = f"({feat['scope']})" if feat['scope'] else ""
        print(f"  {feat['date']} [{feat['hash']}] {scope_str:12s} {feat['description']}")

    # 7. Quality gate adoption
    print("\n🛡️ QUALITY GATE ADOPTION")
    quality = analyze_quality_gates(commits)
    for gate, count in sorted(quality.items(), key=lambda x: x[1], reverse=True):
        print(f"  {gate:10s} : {count:3d} mentions")

    # 8. Recent high-impact commits
    print("\n💎 HIGH-IMPACT COMMITS (Last 10)")
    for commit in commits[:10]:
        files = get_commit_files(commit['hash'])
        categories = categorize_files(files)
        impact_score = len(files) * (1 + len(categories))

        parsed = extract_commit_type(commit['subject'])
        print(f"\n  [{commit['short_hash']}] {parsed['type']:8s} - {parsed['description'][:50]}")
        print(f"    Files: {len(files)}, Categories: {', '.join(categories.keys())}")
        print(f"    Impact Score: {impact_score}")

    print("\n" + "="*60)
    print("✅ Analysis complete")

if __name__ == "__main__":
    main()
