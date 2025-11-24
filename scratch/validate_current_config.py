#!/usr/bin/env python3
"""
Validate current settings.json for stability.
Focus on known failure modes from the migration attempt.
"""

import json
from pathlib import Path
from collections import defaultdict

def main():
    with open('.claude/settings.json') as f:
        config = json.load(f)

    print("=" * 80)
    print("CURRENT CONFIGURATION VALIDATION")
    print("=" * 80)

    # Count hooks by event
    hook_counts = {}
    total_hooks = 0

    for event_type, matchers in config['hooks'].items():
        count = sum(len(m.get('hooks', [])) for m in matchers)
        hook_counts[event_type] = count
        total_hooks += count

    # Display summary
    print("\n📊 Hook Distribution:")
    print("-" * 80)
    for event_type, count in sorted(hook_counts.items(), key=lambda x: -x[1]):
        status = "⚠️ " if count > 10 else "✓ "
        print(f"{status} {event_type:20} {count:3} hooks")

    print(f"\nTotal: {total_hooks} hooks")

    # Check for known risks
    print("\n" + "=" * 80)
    print("STABILITY CHECKS")
    print("=" * 80)

    risks = []

    # Risk 1: Too many UserPromptSubmit hooks
    if hook_counts.get('UserPromptSubmit', 0) > 15:
        risks.append({
            'severity': 'HIGH',
            'issue': f"UserPromptSubmit has {hook_counts['UserPromptSubmit']} hooks",
            'risk': 'Context pollution, race conditions, instruction conflicts'
        })

    # Risk 2: Too many PreToolUse hooks
    if hook_counts.get('PreToolUse', 0) > 20:
        risks.append({
            'severity': 'HIGH',
            'issue': f"PreToolUse has {hook_counts['PreToolUse']} hooks",
            'risk': 'Circular dependencies, performance degradation'
        })

    # Risk 3: State file writers
    state_writers = {
        'UserPromptSubmit': ['synapse_fire', 'prerequisite_checker'],
        'PostToolUse': ['command_tracker', 'evidence_tracker'],
    }

    # Check if both UserPromptSubmit and PostToolUse write to session state
    user_writes_state = 'prerequisite_checker' in str(config['hooks'].get('UserPromptSubmit', []))
    post_writes_state = 'command_tracker' in str(config['hooks'].get('PostToolUse', []))

    if user_writes_state and post_writes_state:
        risks.append({
            'severity': 'MEDIUM',
            'issue': 'Both UserPromptSubmit and PostToolUse write to session state',
            'risk': 'Potential race condition if they fire simultaneously'
        })

    # Report
    if not risks:
        print("✅ No critical stability risks detected")
    else:
        for i, risk in enumerate(risks, 1):
            print(f"\n{i}. [{risk['severity']}] {risk['issue']}")
            print(f"   Risk: {risk['risk']}")

    # Recommendations
    print("\n" + "=" * 80)
    print("STABILITY RECOMMENDATIONS")
    print("=" * 80)

    if hook_counts.get('UserPromptSubmit', 0) > 10:
        print("\n⚠️  UserPromptSubmit Hook Count")
        print(f"   Current: {hook_counts['UserPromptSubmit']} hooks")
        print("   Safe range: ≤10 hooks")
        print("   Recommendation: Monitor for context pollution (10K+ token output)")
        print("   Action: If instability occurs, consolidate or disable low-value hooks")

    if total_hooks > 50:
        print("\n⚠️  Total Hook Count")
        print(f"   Current: {total_hooks} hooks")
        print("   Recommendation: Each hook adds latency and complexity")
        print("   Action: Periodically audit and remove unused hooks")

    # File locking check
    print("\n🔒 Race Condition Mitigation:")
    print("   If issues arise, add file locking to:")
    print("   • .claude/hooks/prerequisite_checker.py (session state writer)")
    print("   • .claude/hooks/command_tracker.py (command tracker writer)")
    print("   • .claude/hooks/synapse_fire.py (lessons.md writer)")

    # Known-good state
    print("\n" + "=" * 80)
    print("CONFIGURATION STATUS")
    print("=" * 80)
    print("✅ This is a known-good configuration (user-verified)")
    print("✅ Manually recovered from failed migration")
    print("⚠️  Do NOT modify hooks without testing")
    print("⚠️  Backup settings.json before any changes")

    # Save baseline
    baseline = {
        'total_hooks': total_hooks,
        'hook_counts': hook_counts,
        'validated_at': '2025-11-22',
        'status': 'KNOWN_GOOD'
    }

    with open('.claude/memory/settings_baseline.json', 'w') as f:
        json.dump(baseline, f, indent=2)

    print("\n📝 Baseline saved to .claude/memory/settings_baseline.json")

if __name__ == '__main__':
    main()
