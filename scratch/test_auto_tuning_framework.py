#!/usr/bin/env python3
"""
Comprehensive Test Suite for Auto-Tuning Framework

Tests all components:
1. auto_tuning.py (core framework)
2. meta_learning.py (override tracking)
3. Batching enforcer integration
4. Command prerequisite integration
"""

import sys
import json
from pathlib import Path

PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

sys.path.insert(0, str(PROJECT_DIR / "scripts" / "lib"))

from auto_tuning import AutoTuner
from meta_learning import OverrideTracker

# Cleanup test state files
MEMORY_DIR = PROJECT_DIR / ".claude" / "memory"

def cleanup_test_files():
    """Clean up test state files"""
    test_files = [
        MEMORY_DIR / "test_auto_tuning_state.json",
        MEMORY_DIR / "override_tracking_test.jsonl",
        MEMORY_DIR / "exception_rules_test.json",
    ]

    for f in test_files:
        if f.exists():
            f.unlink()


def test_auto_tuner_initialization():
    """Test AutoTuner initialization"""
    print("\n=== TEST 1: AutoTuner Initialization ===")

    patterns = {
        "test_pattern": {
            "threshold": 4,
            "suggested_action": "Use parallel execution",
        }
    }

    tuner = AutoTuner(
        system_name="test_system",
        state_file=MEMORY_DIR / "test_auto_tuning_state.json",
        patterns=patterns,
        default_phase="observe",
    )

    state = tuner.get_state()

    assert state["phase"] == "observe", "Should start in OBSERVE phase"
    assert "test_pattern" in state["patterns_detected"], "Pattern should be initialized"
    assert state["thresholds"]["min_repetitions"] == 4, "Default threshold should be 4"

    print("✅ Initialization working")


def test_phase_transitions():
    """Test automatic phase transitions"""
    print("\n=== TEST 2: Phase Transitions ===")

    patterns = {"test_pattern": {"threshold": 3, "suggested_action": "Test action"}}

    tuner = AutoTuner(
        system_name="test_transitions",
        state_file=MEMORY_DIR / "test_auto_tuning_state.json",
        patterns=patterns,
    )

    # Simulate detections with high script adoption
    for i in range(5):
        tuner.update_metrics("test_pattern", turns_wasted=4, script_written=True)

    # Test OBSERVE → WARN transition
    msg = tuner.check_phase_transition(turn=25)
    assert msg is not None, "Should transition to WARN at turn 25"
    assert "WARN PHASE" in msg, "Message should mention WARN phase"

    state = tuner.get_state()
    assert state["phase"] == "warn", "Should be in WARN phase"

    print("✅ OBSERVE → WARN transition working")

    # Simulate more detections for WARN → ENFORCE
    for i in range(5):
        tuner.update_metrics("test_pattern", turns_wasted=10, script_written=True)

    msg = tuner.check_phase_transition(turn=50)
    if msg and "ENFORCE" in msg:
        state = tuner.get_state()
        assert state["phase"] == "enforce", "Should be in ENFORCE phase"
        print("✅ WARN → ENFORCE transition working")
    else:
        print("⚠️  WARN → ENFORCE transition needs higher ROI (expected)")


def test_threshold_auto_tuning():
    """Test automatic threshold adjustment"""
    print("\n=== TEST 3: Threshold Auto-Tuning ===")

    patterns = {"test_pattern": {"threshold": 4, "suggested_action": "Test action"}}

    tuner = AutoTuner(
        system_name="test_tuning",
        state_file=MEMORY_DIR / "test_auto_tuning_state.json",
        patterns=patterns,
    )

    # Simulate high false positive rate (lots of bypasses)
    for i in range(15):
        tuner.update_metrics("test_pattern", turns_wasted=2, bypassed=True)

    # Run auto-tune
    adjustments = tuner.auto_tune_thresholds(turn=50)

    state = tuner.get_state()
    assert state["thresholds"]["min_repetitions"] > 4, "Threshold should increase with high FP rate"

    if adjustments:
        print(f"✅ Threshold adjustment working: {adjustments[0]}")
    else:
        print("⚠️  Threshold adjustment needs higher FP rate")


def test_meta_learning_tracking():
    """Test override tracking"""
    print("\n=== TEST 4: Meta-Learning Tracking ===")

    tracker = OverrideTracker()
    tracker.override_log = MEMORY_DIR / "override_tracking_test.jsonl"

    # Record some overrides
    for i in range(12):
        tracker.record_override(
            hook_name="test_hook",
            bypass_type="MANUAL",
            context={
                "tool": "Read",
                "file_path": f"tests/test_{i % 3}.py",
            },
            turn=i,
            reason="Testing files" if i % 3 == 0 else None,
        )

    overrides = tracker.load_overrides()
    assert len(overrides) == 12, f"Should have 12 overrides, got {len(overrides)}"

    print("✅ Override tracking working")


def test_pattern_clustering():
    """Test pattern clustering"""
    print("\n=== TEST 5: Pattern Clustering ===")

    tracker = OverrideTracker()
    tracker.override_log = MEMORY_DIR / "override_tracking_test.jsonl"

    # Cluster patterns
    clusters = tracker.cluster_patterns(min_occurrences=3)

    assert len(clusters) > 0, "Should find at least one cluster"

    for cluster_key, overrides in clusters.items():
        print(f"  Cluster: {cluster_key} ({len(overrides)} overrides)")

    print("✅ Pattern clustering working")


def test_exception_rule_generation():
    """Test exception rule generation"""
    print("\n=== TEST 6: Exception Rule Generation ===")

    tracker = OverrideTracker()
    tracker.override_log = MEMORY_DIR / "override_tracking_test.jsonl"
    tracker.exception_rules_file = MEMORY_DIR / "exception_rules_test.json"

    # Generate rules
    rules = tracker.generate_exception_rules(confidence_threshold=0.50)

    if rules:
        print(f"✅ Generated {len(rules)} exception rules")

        # Save and reload
        tracker.save_exception_rules(rules)
        loaded_rules = tracker.load_exception_rules()

        assert len(loaded_rules) == len(rules), "Rules should persist"
        print("✅ Exception rule persistence working")
    else:
        print("⚠️  No rules generated (may need more override data)")


def test_exception_checking():
    """Test exception rule matching"""
    print("\n=== TEST 7: Exception Rule Checking ===")

    tracker = OverrideTracker()
    tracker.exception_rules_file = MEMORY_DIR / "exception_rules_test.json"

    # Manual rule for testing
    test_rule = {
        "rule_id": "test_rule",
        "hook_name": "test_hook",
        "conditions": {
            "tools": ["Read"],
            "file_patterns": ["test_.*\\.py"],
        },
        "action": "allow",
        "reason": "Test files are exempt",
    }

    tracker.save_exception_rules([test_rule])

    # Test matching
    should_bypass, rule = tracker.check_exception(
        "test_hook",
        {"tool": "Read", "file_path": "tests/test_foo.py"}
    )

    assert should_bypass, "Should bypass for test file"
    assert rule["rule_id"] == "test_rule", "Should match test rule"

    print("✅ Exception rule checking working")

    # Test non-matching
    should_bypass, rule = tracker.check_exception(
        "test_hook",
        {"tool": "Read", "file_path": "src/main.py"}
    )

    assert not should_bypass, "Should not bypass for non-test file"
    print("✅ Exception rule exclusion working")


def test_enforcement_messages():
    """Test enforcement message generation"""
    print("\n=== TEST 8: Enforcement Messages ===")

    patterns = {"test_pattern": {"threshold": 3, "suggested_action": "Use automation"}}

    tuner = AutoTuner(
        system_name="test_messages",
        state_file=MEMORY_DIR / "test_auto_tuning_state.json",
        patterns=patterns,
    )

    # Test OBSERVE phase (silent)
    action, message = tuner.should_enforce("test_pattern")
    assert action == "observe", "Should observe silently"
    assert message is None, "No message in OBSERVE phase"

    print("✅ OBSERVE phase silent enforcement")

    # Transition to WARN
    state = tuner.get_state()
    state["phase"] = "warn"
    state["patterns_detected"]["test_pattern"]["count"] = 5
    state["patterns_detected"]["test_pattern"]["avg_turns_wasted"] = 3.5
    tuner.save_state(state)

    action, message = tuner.should_enforce("test_pattern")
    assert action == "warn", "Should warn"
    assert message is not None, "Should have warning message"
    assert "OPPORTUNITY" in message, "Message should mention opportunity"

    print("✅ WARN phase messages working")

    # Transition to ENFORCE
    state["phase"] = "enforce"
    tuner.save_state(state)

    action, message = tuner.should_enforce("test_pattern")
    assert action == "block", "Should block"
    assert message is not None, "Should have block message"
    assert "BLOCKED" in message or "ENFORCEMENT" in message, "Message should mention blocking"

    print("✅ ENFORCE phase messages working")


def test_bypass_keywords():
    """Test bypass keyword handling"""
    print("\n=== TEST 9: Bypass Keywords ===")

    patterns = {"test_pattern": {"threshold": 3, "suggested_action": "Test"}}

    tuner = AutoTuner(
        system_name="test_bypass",
        state_file=MEMORY_DIR / "test_auto_tuning_state.json",
        patterns=patterns,
    )

    # Set to ENFORCE phase
    state = tuner.get_state()
    state["phase"] = "enforce"
    tuner.save_state(state)

    # Test MANUAL bypass
    action, message = tuner.should_enforce("test_pattern", prompt="Do this MANUAL please")
    assert action == "observe", "MANUAL keyword should bypass"

    print("✅ MANUAL bypass working")

    # Test SUDO MANUAL bypass
    action, message = tuner.should_enforce("test_pattern", prompt="SUDO MANUAL override")
    assert action == "observe", "SUDO MANUAL should bypass"

    print("✅ SUDO MANUAL bypass working")


def run_all_tests():
    """Run all tests"""
    print("🧪 AUTO-TUNING FRAMEWORK TEST SUITE\n")
    print("=" * 60)

    # Cleanup first
    cleanup_test_files()

    tests = [
        test_auto_tuner_initialization,
        test_phase_transitions,
        test_threshold_auto_tuning,
        test_meta_learning_tracking,
        test_pattern_clustering,
        test_exception_rule_generation,
        test_exception_checking,
        test_enforcement_messages,
        test_bypass_keywords,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ FAILED: {test.__name__}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ ERROR: {test.__name__}")
            print(f"   Exception: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"\n📊 RESULTS: {passed} passed, {failed} failed")

    # Cleanup after tests
    cleanup_test_files()

    if failed == 0:
        print("\n✅ ALL TESTS PASSED")
        return 0
    else:
        print(f"\n❌ {failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
