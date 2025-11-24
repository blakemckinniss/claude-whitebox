#!/usr/bin/env python3
"""
Precise hook unification analysis.
Fix: Distinguish between json.dumps (hook output) and json.dump (file write).
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
            cmd = hook['command']
            if 'python3' in cmd and '.py' in cmd:
                script_path = cmd.split('/')[-1].replace('.py', '')
                user_prompt_hooks.append(script_path)

print("=" * 80)
print("PRECISE HOOK UNIFICATION ANALYSIS")
print("=" * 80)
print(f"\nCurrent: {len(user_prompt_hooks)} hooks\n")

# Analyze each hook
hooks_data = []

for hook_name in user_prompt_hooks:
    hook_path = Path(f'.claude/hooks/{hook_name}.py')

    if not hook_path.exists():
        continue

    content = hook_path.read_text()

    # Extract purpose from docstring
    purpose = "Unknown"
    lines = content.split('\n')
    for i, line in enumerate(lines[:15]):
        if 'Purpose:' in line:
            purpose = line.split('Purpose:')[1].strip()
            break

    # Check for ACTUAL state writes (not json.dumps for output)
    writes_state = False
    if 'save_session_state' in content:
        writes_state = True
    elif 'json.dump(' in content and 'open(' in content:  # json.dump to file
        writes_state = True
    elif '.write_text(' in content:
        writes_state = True
    elif 'record_command_run' in content:
        writes_state = True

    # Check for context injection
    injects_context = False
    if 'additionalContext":' in content:
        # Find what's after additionalContext
        match_lines = [l for l in lines if 'additionalContext' in l and '""' not in l]
        if match_lines:
            injects_context = True

    hooks_data.append({
        'name': hook_name,
        'purpose': purpose,
        'writes_state': writes_state,
        'injects_context': injects_context,
        'lines': len(lines),
    })

# Display
print("HOOK INVENTORY:")
print("-" * 80)
print(f"{'Hook Name':<35} {'State':<8} {'Context':<9} {'Purpose':<40}")
print("-" * 80)

for hook in sorted(hooks_data, key=lambda x: x['name']):
    state_mark = "[WRITE]" if hook['writes_state'] else "  ---  "
    context_mark = "[INJECT]" if hook['injects_context'] else "   ---  "
    purpose_short = hook['purpose'][:38] if len(hook['purpose']) > 38 else hook['purpose']

    print(f"{hook['name']:<35} {state_mark:<8} {context_mark:<9} {purpose_short}")

# Count writers
writers = [h for h in hooks_data if h['writes_state']]
injectors = [h for h in hooks_data if h['injects_context']]
read_only = [h for h in hooks_data if not h['writes_state'] and h['injects_context']]

print(f"\n📊 Statistics:")
print(f"   • Total hooks: {len(hooks_data)}")
print(f"   • Write state: {len(writers)}")
print(f"   • Inject context (read-only): {len(read_only)}")
print(f"   • Silent (no output): {len([h for h in hooks_data if not h['injects_context']])}")

# Analyze for unification by reading actual code
print("\n" + "=" * 80)
print("UNIFICATION CANDIDATES (Manual Code Review)")
print("=" * 80)

# Group hooks by similarity
groups = {
    'State Initializers': ['confidence_init'],
    'Confidence Detectors': ['detect_low_confidence', 'detect_confidence_penalty'],
    'Pattern Detectors': ['detect_gaslight', 'detect_batch'],
    'Checkers/Validators': ['check_knowledge', 'sanity_check', 'prerequisite_checker'],
    'Advisors/Suggesters': ['pre_advice', 'command_suggester', 'best_practice_enforcer'],
    'Intent/Workflow': ['intent_classifier', 'enforce_workflow', 'ecosystem_mapper'],
    'Behavioral Controls': ['intervention', 'anti_sycophant'],
    'Unique Functions': ['synapse_fire', 'force_playwright', 'auto_commit_on_complete'],
}

print()
for group_name, hook_list in groups.items():
    # Check which hooks actually exist
    existing = [h for h in hook_list if any(hd['name'] == h for hd in hooks_data)]

    if len(existing) > 1:
        print(f"📦 {group_name} ({len(existing)} hooks):")
        for hook_name in existing:
            hook_info = next((h for h in hooks_data if h['name'] == hook_name), None)
            if hook_info:
                markers = []
                if hook_info['writes_state']:
                    markers.append('W')
                if hook_info['injects_context']:
                    markers.append('I')
                marker_str = f"[{','.join(markers)}]" if markers else ""
                print(f"   • {hook_name:35} {marker_str}")

        # Suggest merge strategy
        writers_in_group = [h for h in existing if any(hd['name'] == h and hd['writes_state'] for hd in hooks_data)]

        if len(writers_in_group) > 1:
            print(f"   ⚠️  Multiple state writers - HIGH RISK to merge")
        elif len(existing) > 1:
            print(f"   ✓  Could merge into unified_{group_name.lower().replace(' ', '_').replace('/', '_')}.py")
        print()

print("=" * 80)
print("CONSERVATIVE RECOMMENDATIONS")
print("=" * 80)

print("""
After detailed review, here are the SAFEST unifications:

1. **Pattern Detectors** → unified_pattern_detector.py
   Merge: detect_gaslight, detect_batch
   • Both are read-only pattern matchers
   • Both inject warning context when pattern matches
   • Low coupling, easy to config-drive
   • Savings: 1 hook
   • Risk: VERY LOW

2. **Confidence Detectors** → unified_confidence_detector.py
   Merge: detect_low_confidence, detect_confidence_penalty
   • Both detect confidence issues
   • Both inject warnings
   • Similar trigger logic
   • Savings: 1 hook
   • Risk: LOW

3. **Advisors** → unified_advisor.py
   Merge: pre_advice, command_suggester, best_practice_enforcer
   • All provide guidance/suggestions
   • Different phases: prerequisite → command → best practice
   • Can run in sequence within single hook
   • Savings: 2 hooks
   • Risk: MEDIUM (complex logic)

DO NOT MERGE (too risky or functionally unique):
  - confidence_init (state initializer - must run first)
  - synapse_fire (associative memory - unique algorithm)
  - intervention (bikeshedding - specific detection)
  - anti_sycophant (opinion blocker - specific detection)
  - force_playwright (browser automation trigger)
  - auto_commit_on_complete (completion detector)
  - prerequisite_checker (complex prerequisite logic)
  - sanity_check (logic validation)
  - check_knowledge (knowledge gap detection)
  - intent_classifier (intent analysis)
  - ecosystem_mapper (workflow mapping)
  - enforce_workflow (workflow enforcement)

REALISTIC SAVINGS:
  Conservative: 19 → 17 hooks (merge pattern + confidence detectors)
  Moderate: 19 → 15 hooks (add advisor merge)

RECOMMENDATION: Start with Pattern Detectors only
  • Test for 1 week
  • If stable, add Confidence Detectors
  • Monitor context pollution throughout
""")
