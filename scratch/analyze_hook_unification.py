#!/usr/bin/env python3
"""
Analyze UserPromptSubmit hooks for unification opportunities.
Goal: Reduce hook count WITHOUT losing functionality.
"""

import json
from pathlib import Path
from collections import defaultdict

# Load settings
with open('.claude/settings.json') as f:
    config = json.load(f)

# Get UserPromptSubmit hooks
user_prompt_hooks = []
for matcher in config['hooks'].get('UserPromptSubmit', []):
    for hook in matcher.get('hooks', []):
        if hook['type'] == 'command':
            # Extract script path
            cmd = hook['command']
            if 'python3' in cmd and '.py' in cmd:
                script_path = cmd.split('/')[-1].replace('.py', '')
                user_prompt_hooks.append(script_path)

print("=" * 80)
print("USERPROMPTSUBMIT HOOK UNIFICATION ANALYSIS")
print("=" * 80)
print(f"\nCurrent: {len(user_prompt_hooks)} hooks")
print()

# Read each hook to understand purpose
hooks_analysis = []

for hook_name in user_prompt_hooks:
    hook_path = Path(f'.claude/hooks/{hook_name}.py')

    if not hook_path.exists():
        hooks_analysis.append({
            'name': hook_name,
            'purpose': 'FILE NOT FOUND',
            'category': 'ERROR',
            'writes_state': False,
            'injects_context': False,
        })
        continue

    content = hook_path.read_text()

    # Extract docstring
    purpose = "Unknown"
    for line in content.split('\n')[0:10]:
        if 'Purpose:' in line:
            purpose = line.split('Purpose:')[1].strip()
            break
        elif '"""' in line and line.count('"""') == 1:
            # Multi-line docstring
            idx = content.index(line) + len(line)
            rest = content[idx:idx+200]
            if 'Purpose:' in rest:
                purpose = rest.split('Purpose:')[1].split('\n')[0].strip()
            break

    # Categorize
    category = 'OTHER'
    if 'confidence' in hook_name or 'tier' in hook_name:
        category = 'CONFIDENCE_SYSTEM'
    elif 'detect' in hook_name or 'check' in hook_name:
        category = 'DETECTION'
    elif 'suggester' in hook_name or 'advice' in hook_name or 'enforcer' in hook_name:
        category = 'SUGGESTION'
    elif 'init' in hook_name or 'tracker' in hook_name:
        category = 'STATE_MANAGEMENT'
    elif 'intervention' in hook_name or 'sycophant' in hook_name or 'skeptic' in hook_name:
        category = 'BEHAVIORAL_CONTROL'
    elif 'workflow' in hook_name or 'prerequisite' in hook_name:
        category = 'WORKFLOW_ENFORCEMENT'

    # Check if writes state
    writes_state = any(x in content for x in [
        'save_session_state',
        'json.dump',
        '.write_text(',
        'record_command_run'
    ])

    # Check if injects context
    injects_context = 'additionalContext' in content and 'additionalContext": ""' not in content

    hooks_analysis.append({
        'name': hook_name,
        'purpose': purpose,
        'category': category,
        'writes_state': writes_state,
        'injects_context': injects_context,
        'size': len(content)
    })

# Group by category
by_category = defaultdict(list)
for hook in hooks_analysis:
    by_category[hook['category']].append(hook)

print("HOOKS BY CATEGORY:")
print("-" * 80)

for category, hooks in sorted(by_category.items()):
    print(f"\n{category} ({len(hooks)} hooks):")
    for hook in hooks:
        state_marker = " [WRITES]" if hook['writes_state'] else ""
        context_marker = " [INJECTS]" if hook['injects_context'] else ""
        print(f"  • {hook['name']:30} {state_marker}{context_marker}")
        if hook['purpose'] != 'Unknown':
            print(f"    └─ {hook['purpose'][:70]}")

# Identify unification opportunities
print("\n" + "=" * 80)
print("UNIFICATION OPPORTUNITIES")
print("=" * 80)

opportunities = []

# Check for hooks that could be merged
for category, hooks in by_category.items():
    if len(hooks) > 1:
        # Check if hooks in same category don't write state (safe to merge)
        non_writers = [h for h in hooks if not h['writes_state']]

        if len(non_writers) > 1:
            opportunities.append({
                'type': 'MERGE_BY_CATEGORY',
                'category': category,
                'hooks': [h['name'] for h in non_writers],
                'reason': f'All {len(non_writers)} hooks are read-only detectors/checkers in same category',
                'savings': len(non_writers) - 1,
                'risk': 'LOW'
            })

# Check for hooks with very similar names
similar_pairs = [
    (['detect_confidence_penalty', 'detect_confidence_reward'], 'Confidence tracking (penalty/reward)'),
    (['intent_classifier', 'command_suggester'], 'Intent analysis and suggestions'),
    (['prerequisite_checker', 'best_practice_enforcer'], 'Rule enforcement'),
]

for pair, reason in similar_pairs:
    if all(any(h['name'] == p for h in hooks_analysis) for p in pair):
        opportunities.append({
            'type': 'MERGE_SIMILAR',
            'hooks': pair,
            'reason': reason,
            'savings': len(pair) - 1,
            'risk': 'MEDIUM'
        })

# Display opportunities
if not opportunities:
    print("\n✅ No obvious unification opportunities found")
    print("   All hooks serve distinct purposes")
else:
    print(f"\nFound {len(opportunities)} potential unifications:\n")

    total_savings = sum(o['savings'] for o in opportunities)

    for i, opp in enumerate(opportunities, 1):
        print(f"{i}. [{opp['risk']}] {opp['type']}")
        print(f"   Merge: {', '.join(opp['hooks'])}")
        print(f"   Reason: {opp['reason']}")
        print(f"   Saves: {opp['savings']} hook(s)")
        print()

    print(f"Total potential savings: {total_savings} hooks")
    print(f"New count: {len(user_prompt_hooks)} → {len(user_prompt_hooks) - total_savings}")

# Deep analysis - check for functional overlap
print("\n" + "=" * 80)
print("FUNCTIONAL OVERLAP ANALYSIS")
print("=" * 80)

# Read all hook contents for pattern matching
overlaps = []

detection_hooks = [h for h in hooks_analysis if h['category'] == 'DETECTION']
if len(detection_hooks) > 2:
    print(f"\n⚠️  DETECTION category has {len(detection_hooks)} hooks:")
    print("   These all follow 'detect pattern → inject warning' pattern")
    print("   Potential: Single 'pattern_matcher.py' with config-driven rules")
    print()
    overlaps.append('DETECTION hooks could use rule-based dispatcher')

suggestion_hooks = [h for h in hooks_analysis if h['category'] == 'SUGGESTION']
if len(suggestion_hooks) > 1:
    print(f"⚠️  SUGGESTION category has {len(suggestion_hooks)} hooks:")
    print("   These all suggest commands/actions to user")
    print("   Potential: Single 'advisor.py' with multi-phase suggestions")
    print()
    overlaps.append('SUGGESTION hooks could share advisor engine')

print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)

print("""
Based on analysis, here are safe unification strategies:

1. **DETECTION CONSOLIDATION** (Recommended)
   Merge all detect_* hooks into single pattern matcher:
   - detect_gaslight
   - detect_low_confidence
   - detect_confidence_penalty
   - detect_batch

   Approach: Config-driven regex patterns → context injection
   Risk: LOW (all read-only, similar structure)
   Savings: ~3 hooks

2. **SUGGESTION CONSOLIDATION** (Recommended)
   Merge suggestion hooks into single advisor:
   - command_suggester
   - prerequisite_checker
   - best_practice_enforcer

   Approach: Multi-phase advisor (prerequisites → suggestions → best practices)
   Risk: MEDIUM (different trigger conditions)
   Savings: ~2 hooks

3. **CONFIDENCE SYSTEM CONSOLIDATION** (Advanced)
   Merge confidence tracking:
   - confidence_init
   - detect_confidence_penalty (PostToolUse)
   - detect_confidence_reward (PostToolUse)

   Approach: Unified confidence manager
   Risk: HIGH (crosses event boundaries, writes state)
   Savings: ~2 hooks

4. **DO NOT MERGE:**
   - synapse_fire (unique associative memory)
   - intervention (bikeshedding detection)
   - anti_sycophant (opinion request blocker)
   - enforce_workflow (workflow enforcement)
   - sanity_check (logic validation)
   - force_playwright (browser automation trigger)

   Reason: Each has unique, non-overlapping functionality

CONSERVATIVE APPROACH:
  Start with #1 (DETECTION) only → Test stability → Then #2 if needed
  Expected reduction: 19 → 16 hooks (safe, minimal risk)

AGGRESSIVE APPROACH:
  Combine #1 + #2 → Test → Add #3 if stable
  Expected reduction: 19 → 12 hooks (higher risk, requires careful testing)
""")

print("\n" + "=" * 80)
print("NEXT STEPS")
print("=" * 80)
print("""
1. Review recommendations above
2. Choose conservative or aggressive approach
3. Create unified hook scripts in scratch/ first
4. Test with backup of current settings.json
5. Monitor for context pollution, instruction conflicts
6. Rollback if instability detected

Files to create:
  - scratch/unified_pattern_detector.py (consolidates detect_*)
  - scratch/unified_advisor.py (consolidates suggester/enforcer)

Validation:
  - Compare output of old vs new hooks on same inputs
  - Ensure all warnings/suggestions still fire correctly
  - Measure latency improvement
""")
