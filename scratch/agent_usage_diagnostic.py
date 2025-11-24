#!/usr/bin/env python3
"""
Agent Usage Diagnostic - Why aren't agents being used?

Analyzes:
1. Agent definitions vs actual invocation patterns
2. Barriers to usage (complexity, unclear triggers)
3. Competition from direct script execution
4. Recommendations for making agents actually useful
"""

import os
import json
import re
from pathlib import Path
from collections import defaultdict

def find_project_root():
    """Find project root by looking for scripts/lib/core.py"""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "scripts" / "lib" / "core.py").exists():
            return parent
    return Path.cwd()

ROOT = find_project_root()
AGENTS_DIR = ROOT / ".claude" / "agents"
HOOKS_DIR = ROOT / ".claude" / "hooks"
CLAUDE_MD = ROOT / "CLAUDE.md"

def parse_agent(agent_path):
    """Parse agent frontmatter and content"""
    with open(agent_path) as f:
        content = f.read()

    # Extract YAML frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            body = parts[2]

            metadata = {}
            for line in frontmatter.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()

            return {
                'name': metadata.get('name', ''),
                'description': metadata.get('description', ''),
                'tools': metadata.get('tools', ''),
                'model': metadata.get('model', 'inherit'),
                'body': body.strip(),
                'scripts_called': re.findall(r'python3 scripts/[^\s]+', body),
            }
    return None

def analyze_agents():
    """Analyze all agents"""
    agents = {}
    for agent_file in AGENTS_DIR.glob("*.md"):
        agent_data = parse_agent(agent_file)
        if agent_data:
            agents[agent_data['name']] = agent_data
    return agents

def analyze_invocation_patterns():
    """Check how agents are referenced in docs/hooks"""
    patterns = {
        'claude_md': [],
        'hooks': defaultdict(list),
        'epistemology': [],
    }

    # CLAUDE.md references
    if CLAUDE_MD.exists():
        with open(CLAUDE_MD) as f:
            for i, line in enumerate(f, 1):
                if 'agent' in line.lower() or 'subagent' in line.lower():
                    patterns['claude_md'].append((i, line.strip()))

    # Hook references
    for hook_file in HOOKS_DIR.glob("*.py"):
        with open(hook_file) as f:
            for i, line in enumerate(f, 1):
                if 'subagent_type' in line or 'Task tool' in line:
                    patterns['hooks'][hook_file.name].append((i, line.strip()))

    # Epistemology references
    epi_file = ROOT / "scripts" / "lib" / "epistemology.py"
    if epi_file.exists():
        with open(epi_file) as f:
            for i, line in enumerate(f, 1):
                if 'subagent_type' in line:
                    patterns['epistemology'].append((i, line.strip()))

    return patterns

def identify_barriers():
    """Identify why agents might not be used"""
    barriers = {
        'invocation_complexity': [],
        'unclear_triggers': [],
        'script_competition': [],
        'tool_scoping_unclear': [],
    }

    agents = analyze_agents()

    for name, agent in agents.items():
        # Invocation complexity
        if not agent['description']:
            barriers['unclear_triggers'].append(f"{name}: No clear trigger in description")
        elif 'proactively' not in agent['description'].lower():
            barriers['unclear_triggers'].append(f"{name}: Not marked as proactive")

        # Script competition
        if agent['scripts_called']:
            scripts = [s.split('/')[-1] for s in agent['scripts_called']]
            barriers['script_competition'].append(
                f"{name}: Calls {scripts} - user might just call script directly"
            )

        # Tool scoping value
        if agent['tools'] == 'Bash, Read, Glob, Grep':
            barriers['tool_scoping_unclear'].append(
                f"{name}: No unique tool restriction (all read-only tools)"
            )

    return barriers

def generate_recommendations():
    """Generate actionable recommendations"""
    agents = analyze_agents()
    barriers = identify_barriers()

    recommendations = []

    # Recommendation 1: Auto-invocation hooks
    recommendations.append({
        'title': 'Add Auto-Invocation Hooks',
        'problem': 'Agents require explicit invocation - LLM forgets to use them',
        'solution': 'Create PreToolUse hooks that auto-spawn agents for specific patterns',
        'example': '''
# In .claude/hooks/auto_researcher.py (PreToolUse)
if tool_name == "Bash" and "pip install" in command:
    # Large package docs → spawn researcher agent automatically
    if should_research_library(command):
        return {
            "allow": False,
            "message": "Auto-spawning researcher agent for library documentation..."
        }
        # Then spawn Task tool with subagent_type='researcher'
''',
    })

    # Recommendation 2: Clear value props in descriptions
    recommendations.append({
        'title': 'Strengthen Agent Descriptions with Clear Triggers',
        'problem': 'Agent descriptions don\'t clearly state WHEN to invoke',
        'solution': 'Rewrite descriptions with regex-like trigger patterns',
        'example': '''
Current: "Use proactively for deep documentation searches"
Better: "AUTO-INVOKE when: fetching docs for libraries, researching APIs,
         investigating >500 line outputs. PREVENTS: main context pollution"
''',
    })

    # Recommendation 3: Script → Agent promotion
    recommendations.append({
        'title': 'Automatic Script → Agent Promotion',
        'problem': 'Users call scripts directly, missing agent benefits',
        'solution': 'PostToolUse hook detects large script outputs → auto-spawns researcher',
        'example': '''
# In .claude/hooks/auto_promote.py (PostToolUse)
if tool_name == "Bash" and "research.py" in command:
    output_size = len(result['output'])
    if output_size > 1000:
        # Recommend: "This output is large. Should I spawn researcher agent to compress?"
''',
    })

    # Recommendation 4: Agent-only capabilities
    recommendations.append({
        'title': 'Give Agents Capabilities Scripts Cannot Have',
        'problem': 'Agents are just script wrappers - no unique value',
        'solution': 'Add agent-only features via tool scoping or special access',
        'examples': [
            'sherlock: ONLY agent with verify.py access (main assistant blocked)',
            'script-smith: ONLY agent that can Write to scripts/ (main assistant blocked)',
            'researcher: Auto-compression API (input >500 lines → output <50 words)',
        ],
    })

    # Recommendation 5: Delete or merge
    recommendations.append({
        'title': 'Delete Agents Without Unique Value',
        'problem': f'{len(agents)} agents but unclear differentiation',
        'solution': 'Keep only agents with EXCLUSIVE capabilities',
        'keep': [
            'sherlock (read-only tool scoping)',
            'script-smith (write permission + quality gates)',
            'researcher (context compression API)',
        ],
        'delete': [
            'council-advisor (just calls council.py)',
            'critic (just calls critic.py)',
            'runner (just calls bash)',
        ],
    })

    return recommendations

def main():
    print("=" * 70)
    print("AGENT USAGE DIAGNOSTIC")
    print("=" * 70)
    print()

    # Analyze agents
    agents = analyze_agents()
    print(f"📊 Found {len(agents)} agents:")
    for name, agent in sorted(agents.items()):
        print(f"  - {name}")
        print(f"    Description: {agent['description'][:60]}...")
        print(f"    Tools: {agent['tools']}")
        print(f"    Scripts called: {len(agent['scripts_called'])}")
        print()

    # Invocation patterns
    patterns = analyze_invocation_patterns()
    print("\n📝 Invocation Patterns:")
    print(f"  - CLAUDE.md mentions: {len(patterns['claude_md'])}")
    print(f"  - Hook references: {sum(len(v) for v in patterns['hooks'].values())}")
    print(f"  - Epistemology refs: {len(patterns['epistemology'])}")
    print()

    # Barriers
    barriers = identify_barriers()
    print("\n🚧 Barriers to Usage:")
    for category, items in barriers.items():
        if items:
            print(f"\n  {category.replace('_', ' ').title()}:")
            for item in items[:3]:  # Show first 3
                print(f"    - {item}")
    print()

    # Recommendations
    recommendations = generate_recommendations()
    print("\n" + "=" * 70)
    print("💡 RECOMMENDATIONS TO MAKE AGENTS ACTUALLY USEFUL")
    print("=" * 70)
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['title']}")
        print(f"   Problem: {rec['problem']}")
        print(f"   Solution: {rec['solution']}")
        if 'example' in rec:
            print(f"   Example:\n{rec['example']}")
        if 'keep' in rec:
            print(f"   Keep: {rec['keep']}")
            print(f"   Delete: {rec['delete']}")
        print()

if __name__ == "__main__":
    main()
