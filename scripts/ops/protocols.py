#!/usr/bin/env python3
"""
Protocol Management CLI - Discovery & Management for Protocol Enforcer System

Provides CLI interface to:
- List registered protocols with descriptions
- Show detailed protocol information
- Check current session status
- View statistics and analytics
- Test feature predicates
- Manually trigger protocol checks

USAGE:
    protocols.py list                    # List protocols
    protocols.py show <protocol_id>      # Show protocol details
    protocols.py status                  # Show triggered rules this session
    protocols.py stats                   # Show statistics
    protocols.py test                    # Run predicate tests
    protocols.py trigger <protocol_id>   # Manually trigger protocol check
"""
import sys
import os
import json

# Add scripts/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
# Find project root by looking for 'scripts' directory
_current = _script_dir
while _current != '/':
    if os.path.exists(os.path.join(_current, 'scripts', 'lib', 'core.py')):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with scripts/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, 'scripts', 'lib'))
from core import setup_script, finalize, logger, handle_debug
from protocol_registry import (
    ProtocolRegistry,
    SituationSnapshot,
    REGISTRY_STATE_FILE,
)


def cmd_list(registry: ProtocolRegistry) -> None:
    """List registered protocols grouped by category"""
    protocols = registry.list_protocols()

    if not protocols:
        logger.warning("No protocols registered")
        return

    print("\n" + "="*80)
    print("📋 REGISTERED PROTOCOLS")
    print("="*80 + "\n")

    # Group by category
    by_category = {}
    for p in protocols:
        cat = p['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(p)

    # Display by category
    for category in sorted(by_category.keys()):
        print(f"┌─ {category.upper()} " + "─" * (70 - len(category)))

        for p in by_category[category]:
            print("│")
            print(f"│ [{p['id']}]")
            print(f"│   {p['description']}")
            print(f"│   Command: {p['command'] or 'N/A'} | Rules: {p['rules_count']}")

        print("└" + "─" * 78)
        print()


def cmd_show(registry: ProtocolRegistry, protocol_id: str) -> None:
    """Show detailed protocol information including rules"""
    if not protocol_id:
        logger.error("Missing protocol_id argument")
        print("\nUsage: protocols.py show <protocol_id>")
        finalize(False)

    protocol = registry.get_protocol(protocol_id)

    if not protocol:
        logger.error(f"Protocol not found: {protocol_id}")
        finalize(False)

    print("\n" + "="*80)
    print(f"📜 PROTOCOL: {protocol['id']}")
    print("="*80 + "\n")

    print(f"Description: {protocol.get('description', 'N/A')}")
    print(f"Category:    {protocol.get('category', 'N/A')}")
    print(f"Command:     {protocol.get('command', 'N/A')}")
    print(f"Rules:       {len(protocol.get('rules', []))}")

    print("\n" + "─"*80)
    print("RULES:")
    print("─"*80 + "\n")

    for i, rule in enumerate(protocol.get("rules", []), 1):
        print(f"{i}. {rule['id']}")
        print(f"   Enforcement: {rule.get('enforcement', 'suggest').upper()}")
        print(f"   Priority:    {rule.get('priority', 5)}")

        trigger = rule.get("trigger", {})
        print(f"   Events:      {', '.join(trigger.get('event_types', []))}")

        features = trigger.get('features', [])
        if features:
            print(f"   Features:    {', '.join(features)}")

        prereqs = trigger.get('prerequisites_missing', [])
        if prereqs:
            print(f"   Prerequisites Missing: {', '.join(prereqs)}")

        # Show message preview (first 100 chars)
        message = rule.get('message', '').strip()
        if message:
            preview = message.split('\n')[0][:100]
            print(f"   Message:     {preview}...")

        print()


def cmd_status(registry: ProtocolRegistry) -> None:
    """Show current session's triggered rules from state file"""
    if not REGISTRY_STATE_FILE.exists():
        print("\n⚠️  No session state found. Protocol system not yet active.")
        return

    with open(REGISTRY_STATE_FILE) as f:
        state = json.load(f)

    print("\n" + "="*80)
    print("🚦 SESSION STATUS")
    print("="*80 + "\n")

    print(f"Total Evaluations: {state.get('total_evaluations', 0)}")
    print(f"Initialized:       {state.get('initialized_at', 'Unknown')}")

    print("\n" + "─"*80)
    print("TRIGGERED RULES:")
    print("─"*80 + "\n")

    triggered = state.get('rules_triggered', {})
    if not triggered:
        print("No rules triggered yet.")
    else:
        # Sort by count (most triggered first)
        sorted_rules = sorted(triggered.items(), key=lambda x: x[1], reverse=True)

        for rule_id, count in sorted_rules:
            # Try to find the rule in registry to get details
            rule_info = None
            for protocol in registry.definitions.values():
                for rule in protocol.get('rules', []):
                    if rule['id'] == rule_id:
                        rule_info = rule
                        break
                if rule_info:
                    break

            enforcement = rule_info.get('enforcement', 'unknown') if rule_info else 'unknown'
            print(f"  {rule_id}")
            print(f"    Count: {count} | Enforcement: {enforcement}")

    print("\n" + "─"*80)
    print("BYPASSED RULES:")
    print("─"*80 + "\n")

    bypassed = state.get('rules_bypassed', {})
    if not bypassed:
        print("No rules bypassed yet."
        )
    else:
        for rule_id, count in bypassed.items():
            print(f"  {rule_id}: {count} bypasses")

    print()


def cmd_stats(registry: ProtocolRegistry) -> None:
    """Show statistics and analytics about protocol usage"""
    stats = registry.get_stats()

    print("\n" + "="*80)
    print("📊 PROTOCOL STATISTICS")
    print("="*80 + "\n")

    print(f"Protocols Registered: {stats['protocols_count']}")
    print(f"Total Rules:          {stats['rules_count']}")
    print(f"Total Evaluations:    {stats['total_evaluations']}")

    # Breakdown by enforcement level
    print("\n" + "─"*80)
    print("RULES BY ENFORCEMENT:")
    print("─"*80 + "\n")

    by_enforcement = {'observe': 0, 'suggest': 0, 'warn': 0, 'block': 0}
    for protocol in registry.definitions.values():
        for rule in protocol.get('rules', []):
            enforcement = rule.get('enforcement', 'suggest')
            by_enforcement[enforcement] = by_enforcement.get(enforcement, 0) + 1

    for level, count in by_enforcement.items():
        print(f"  {level.upper():10} {count:3} rules")

    # Breakdown by category
    print("\n" + "─"*80)
    print("PROTOCOLS BY CATEGORY:")
    print("─"*80 + "\n")

    by_category = {}
    for protocol in registry.definitions.values():
        cat = protocol.get('category', 'workflow')
        by_category[cat] = by_category.get(cat, 0) + 1

    for category, count in sorted(by_category.items()):
        print(f"  {category:15} {count:3} protocols")

    # Top triggered rules
    print("\n" + "─"*80)
    print("TOP TRIGGERED RULES:")
    print("─"*80 + "\n")

    triggered = stats.get('rules_triggered', {})
    if not triggered:
        print("No rules triggered yet.")
    else:
        sorted_rules = sorted(triggered.items(), key=lambda x: x[1], reverse=True)[:10]

        for i, (rule_id, count) in enumerate(sorted_rules, 1):
            print(f"  {i:2}. {rule_id:40} {count:3} triggers")

    # Bypass rate
    print("\n" + "─"*80)
    print("BYPASS ANALYSIS:")
    print("─"*80 + "\n")

    bypassed = stats.get('rules_bypassed', {})
    if not bypassed:
        print("No rules bypassed yet.")
    else:
        for rule_id, bypass_count in bypassed.items():
            trigger_count = triggered.get(rule_id, 0)
            total = trigger_count + bypass_count
            bypass_rate = (bypass_count / total * 100) if total > 0 else 0

            print(f"  {rule_id:40} {bypass_count:3} bypasses / {total:3} total ({bypass_rate:.1f}%)")

    print()


def cmd_test(registry: ProtocolRegistry) -> None:
    """Run feature predicate tests with known test cases"""
    print("\n" + "="*80)
    print("🧪 FEATURE PREDICATE TESTS")
    print("="*80 + "\n")

    # Define test cases
    test_cases = [
        {
            "name": "Fixed Claim Detection",
            "snapshot": SituationSnapshot(
                event_type="PostToolUse",
                turn=5,
                tool_output="The bug is fixed and working now."
            ),
            "expected_rules": ["verify_fixed_claims"]
        },
        {
            "name": "Production Write Detection",
            "snapshot": SituationSnapshot(
                event_type="PreToolUse",
                turn=5,
                tool_name="Write",
                tool_input={"file_path": "scripts/ops/new_tool.py"}
            ),
            "expected_rules": ["audit_production_write"]
        },
        {
            "name": "Commit Request Detection",
            "snapshot": SituationSnapshot(
                event_type="UserPromptSubmit",
                turn=5,
                prompt="Please commit these changes and push to remote"
            ),
            "expected_rules": ["upkeep_before_commit"]
        },
        {
            "name": "Opinion Request Detection",
            "snapshot": SituationSnapshot(
                event_type="UserPromptSubmit",
                turn=5,
                prompt="What do you think about using Redis here?"
            ),
            "expected_rules": ["anti_sycophant_opinion"]
        },
        {
            "name": "Complex Decision Detection",
            "snapshot": SituationSnapshot(
                event_type="UserPromptSubmit",
                turn=5,
                prompt="Should we migrate from REST to GraphQL? What are the trade-offs?"
            ),
            "expected_rules": ["council_complex_decision"]
        },
        {
            "name": "Blocking Error Detection",
            "snapshot": SituationSnapshot(
                event_type="PostToolUse",
                turn=5,
                tool_error="ModuleNotFoundError: No module named 'pandas'"
            ),
            "expected_rules": ["detour_blocking_error"]
        },
        {
            "name": "Repeated Failures Detection",
            "snapshot": SituationSnapshot(
                event_type="PostToolUse",
                turn=10,
                tool_error="Test failed again",
                session_state={"failure_counts": {"test_foo.py": 3}}
            ),
            "expected_rules": ["think_repeated_failures"]
        },
        {
            "name": "Low Confidence Production Write",
            "snapshot": SituationSnapshot(
                event_type="PreToolUse",
                turn=5,
                tool_name="Write",
                tool_input={"file_path": "scripts/ops/critical.py"},
                session_state={"confidence": 50}
            ),
            "expected_rules": ["tier_production_write"]
        },
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        print(f"Test: {test['name']}")

        matches = registry.evaluate(test['snapshot'])
        triggered_rule_ids = [m.rule_id for m in matches]

        # Check if expected rules were triggered
        expected = test['expected_rules']
        all_matched = all(rule_id in triggered_rule_ids for rule_id in expected)

        if all_matched and matches:
            print("  ✅ PASS")
            for m in matches:
                print(f"     Triggered: {m.rule_id} ({m.enforcement.value})")
            passed += 1
        elif not expected and not matches:
            print("  ✅ PASS (no rules expected, none triggered)")
            passed += 1
        else:
            print("  ❌ FAIL")
            print(f"     Expected: {expected}")
            print(f"     Triggered: {triggered_rule_ids}")
            failed += 1

        print()

    print("─"*80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("─"*80 + "\n")


def cmd_trigger(registry: ProtocolRegistry, protocol_id: str, context: str) -> None:
    """Manually trigger a protocol check with optional context"""
    if not protocol_id:
        logger.error("Missing protocol_id argument")
        print("\nUsage: protocols.py trigger <protocol_id> [--context 'text']")
        finalize(False)

    protocol = registry.get_protocol(protocol_id)

    if not protocol:
        logger.error(f"Protocol not found: {protocol_id}")
        finalize(False)

    print("\n" + "="*80)
    print(f"🔍 MANUAL TRIGGER: {protocol_id}")
    print("="*80 + "\n")

    # Create a snapshot from context
    snapshot = SituationSnapshot(
        event_type="UserPromptSubmit",
        turn=999,  # Arbitrary high turn for manual test
        prompt=context or "",
        session_state={"confidence": 50}  # Moderate confidence for testing
    )

    # Evaluate only rules from this protocol
    all_matches = registry.evaluate(snapshot)
    protocol_matches = [m for m in all_matches if m.protocol == protocol_id]

    if not protocol_matches:
        print(f"⚠️  No rules triggered for protocol '{protocol_id}'")
        print(f"\nContext used: {context or '(empty)'}")
        print("\nTry providing context with --context flag that matches trigger conditions.")
    else:
        print(f"✅ {len(protocol_matches)} rule(s) triggered:\n")

        for match in protocol_matches:
            print(f"┌─ {match.rule_id}")
            print(f"│  Enforcement: {match.enforcement.value.upper()}")
            print(f"│  Priority:    {match.priority}")
            print("│")
            print("│  Features matched:")
            for feature in match.features_matched:
                if feature.matched:
                    print(f"│    ✓ {feature.name}: {feature.details or feature.value}")
            print("│")
            print("│  Message:")
            for line in match.message.strip().split('\n'):
                print(f"│    {line}")
            print("└" + "─"*78)
            print()

    print()


def main():
    parser = setup_script(__doc__)

    # Subcommands
    parser.add_argument(
        "command",
        choices=["list", "show", "status", "stats", "test", "trigger"],
        help="Command to execute"
    )
    parser.add_argument(
        "protocol_id",
        nargs="?",
        help="Protocol ID (for show/trigger commands)"
    )
    parser.add_argument(
        "--context",
        help="Context text for trigger command"
    )

    args = parser.parse_args()
    handle_debug(args)

    try:
        # Initialize registry
        registry = ProtocolRegistry()

        # Route to command handler
        if args.command == "list":
            cmd_list(registry)
        elif args.command == "show":
            cmd_show(registry, args.protocol_id)
        elif args.command == "status":
            cmd_status(registry)
        elif args.command == "stats":
            cmd_stats(registry)
        elif args.command == "test":
            cmd_test(registry)
        elif args.command == "trigger":
            cmd_trigger(registry, args.protocol_id, args.context)
        else:
            logger.error(f"Unknown command: {args.command}")
            finalize(False)

        finalize(success=True)

    except Exception as e:
        logger.error(f"Operation failed: {e}")
        finalize(success=False)


if __name__ == "__main__":
    main()
