#!/usr/bin/env python3
"""
Git Semantic Injector Hook
Triggers: SessionStart
Purpose: Inject semantic context from recent commit history
"""
import sys
import json
import subprocess
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

def get_recent_commits(days=7, limit=30):
    """Get commits from last N days"""
    result = subprocess.run(
        ["git", "log", f"--since={days} days ago", f"-{limit}",
         "--format=%H|%h|%s|%ai"],
        capture_output=True,
        text=True,
        timeout=5
    )

    commits = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split('|')
        if len(parts) >= 4:
            commits.append({
                'hash': parts[0],
                'short_hash': parts[1],
                'subject': parts[2],
                'date': parts[3]
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
    """Parse conventional commit"""
    match = re.match(r'^(\w+)(?:\(([^)]+)\))?: (.+)$', subject)
    if match:
        return {
            'type': match.group(1),
            'scope': match.group(2),
            'description': match.group(3)
        }
    return {'type': 'other', 'scope': None, 'description': subject}

def analyze_file_hotspots(commits):
    """Find frequently changed files"""
    file_changes = Counter()

    for commit in commits:
        files = get_commit_files(commit['hash'])
        for f in files:
            file_changes[f] += 1

    return file_changes.most_common(10)

def extract_feature_work(commits):
    """Get recent feature additions"""
    features = []

    for commit in commits:
        parsed = extract_commit_type(commit['subject'])
        if parsed['type'] == 'feat':
            try:
                dt = datetime.fromisoformat(commit['date'].replace(' -0500', ''))
                days_ago = (datetime.now() - dt).days
                features.append({
                    'scope': parsed['scope'],
                    'description': parsed['description'],
                    'hash': commit['short_hash'],
                    'days_ago': days_ago
                })
            except:
                pass

    return features[:5]

def analyze_quality_gates(commits):
    """Check quality gate usage"""
    gates = {'audit': 0, 'void': 0, 'drift': 0, 'verify': 0}

    for commit in commits:
        subject_lower = commit['subject'].lower()
        for gate in gates:
            if gate in subject_lower:
                gates[gate] += 1

    return gates

def extract_semantic_themes(commits):
    """Extract dominant themes"""
    keywords = [
        'protocol', 'hook', 'performance', 'parallel', 'epistemology',
        'memory', 'oracle', 'quality', 'automation'
    ]

    theme_counts = Counter()
    for commit in commits:
        subject_lower = commit['subject'].lower()
        for keyword in keywords:
            if keyword in subject_lower:
                theme_counts[keyword] += 1

    return theme_counts.most_common(5)

def generate_context():
    """Generate semantic context from commits"""
    commits = get_recent_commits(days=7, limit=30)

    if not commits:
        return None

    # Analyze commits
    features = extract_feature_work(commits)
    hotspots = analyze_file_hotspots(commits)
    quality = analyze_quality_gates(commits)
    themes = extract_semantic_themes(commits)

    # Build context message
    lines = ["🧠 GIT SEMANTIC CONTEXT (Last 7 days, {} commits):".format(len(commits))]

    # Recent work focus
    if features:
        lines.append("\nRecent Feature Work:")
        for feat in features:
            scope_str = f"({feat['scope']})" if feat['scope'] else ""
            days_str = "today" if feat['days_ago'] == 0 else f"{feat['days_ago']}d ago"
            lines.append(f"  • [{feat['hash']}] {scope_str} {feat['description'][:50]} ({days_str})")

    # File hotspots (warning signals)
    if hotspots:
        high_churn = [f for f, count in hotspots if count >= 5]
        if high_churn:
            lines.append("\n⚠️  High-Churn Files (≥5 changes):")
            for filepath, count in hotspots:
                if count >= 5:
                    lines.append(f"  • {filepath} ({count}x)")

    # Quality trends
    if any(quality.values()):
        lines.append("\n🛡️  Quality Gate Usage:")
        for gate, count in sorted(quality.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                lines.append(f"  ✅ {gate}.py: {count} mentions")
            else:
                lines.append(f"  ⚠️  {gate}.py: Not used recently")

    # Semantic themes
    if themes:
        lines.append("\n🧠 Dominant Themes:")
        for theme, count in themes:
            lines.append(f"  • {theme}: {count} mentions")

    # Recommendations
    lines.append("\n💡 Recommendations:")
    if quality['drift'] == 0:
        lines.append("  • Consider running drift_check.py (not seen in recent commits)")
    if any(count >= 8 for _, count in hotspots):
        lines.append("  • High file churn detected - consider refactoring or stabilizing")
    lines.append("  • Run /verify before claiming 'fixed' or 'done'")

    return '\n'.join(lines)

def main():
    """Hook entry point"""
    try:
        context = generate_context()

        if context:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context
                }
            }))
        else:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": ""
                }
            }))

    except Exception as e:
        # Silent failure - don't break session start
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": f"⚠️ Git semantic analysis failed: {e}"
            }
        }))

    sys.exit(0)

if __name__ == "__main__":
    main()
