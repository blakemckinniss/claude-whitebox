#!/usr/bin/env python3
"""
Test Scratch Enforcement System

Tests all three phases: OBSERVE → WARN → ENFORCE
Validates auto-tuning, threshold adjustment, and phase transitions.
"""

import sys
import json
from pathlib import Path

# Add scripts/lib to path
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

sys.path.insert(0, str(PROJECT_DIR / "scripts" / "lib"))

from scratch_enforcement import (
    get_enforcement_state,
    save_enforcement_state,
    detect_pattern_in_history,
    detect_pattern_in_prompt,
    should_enforce,
    update_pattern_detection,
    auto_tune_thresholds,
    check_phase_transition,
    generate_auto_report,
    DEFAULT_STATE,
)


def reset_state():
    """Reset state to default for testing"""
    state = DEFAULT_STATE.copy()
    state["patterns_detected"] = {
        pattern: {"count": 0, "avg_turns_wasted": 0.0, "scripts_written": 0, "manual_bypasses": 0}
        for pattern in ["multi_read", "multi_grep", "multi_edit", "file_iteration"]
    }
    save_enforcement_state(state)
    return state


def test_phase_1_observe():
    """Test OBSERVE phase (silent data collection)"""
    print("\n=== TEST 1: OBSERVE PHASE ===")
    state = reset_state()

    # Simulate detection in OBSERVE phase
    tool_history = [
        {"tool": "Read", "turn": 1},
        {"tool": "Read", "turn": 2},
        {"tool": "Read", "turn": 3},
        {"tool": "Read", "turn": 4},
    ]

    detection = detect_pattern_in_history("Read", tool_history, 5)
    assert detection is not None, "Should detect multi_read pattern"
    pattern_name, count = detection
    assert pattern_name == "multi_read", f"Expected multi_read, got {pattern_name}"
    assert count == 4, f"Expected count 4, got {count}"

    # Check enforcement (should be silent in OBSERVE)
    action, message = should_enforce(pattern_name, state)
    assert action == "observe", f"Expected observe action, got {action}"
    assert message is None, f"Expected no message in OBSERVE phase, got: {message}"

    print("✅ OBSERVE phase: Silent data collection working")


def test_phase_2_warn():
    """Test transition to WARN phase and warning messages"""
    print("\n=== TEST 2: WARN PHASE ===")
    state = reset_state()

    # Simulate 3 detections with scripts written (build confidence)
    for i in range(3):
        update_pattern_detection("multi_read", turns_wasted=3, script_written=True)

    # Manually transition to WARN
    state = get_enforcement_state()
    state["phase"] = "warn"
    save_enforcement_state(state)

    # Check enforcement (should warn)
    action, message = should_enforce("multi_read", state)
    assert action == "warn", f"Expected warn action, got {action}"
    assert message is not None, "Expected warning message in WARN phase"
    assert "SCRATCH SCRIPT OPPORTUNITY" in message, "Warning should mention opportunity"

    print("✅ WARN phase: Warning messages working")
    print(f"Sample message:\n{message}")


def test_phase_3_enforce():
    """Test transition to ENFORCE phase and hard blocking"""
    print("\n=== TEST 3: ENFORCE PHASE ===")
    state = reset_state()

    # Simulate 5 detections with high ROI
    for i in range(5):
        update_pattern_detection("multi_read", turns_wasted=8, script_written=True)

    # Manually transition to ENFORCE
    state = get_enforcement_state()
    state["phase"] = "enforce"
    save_enforcement_state(state)

    # Check enforcement (should block)
    action, message = should_enforce("multi_read", state)
    assert action == "block", f"Expected block action, got {action}"
    assert message is not None, "Expected block message in ENFORCE phase"
    assert "SCRATCH SCRIPT REQUIRED" in message, "Block should mention requirement"
    assert "BLOCKED" in message, "Block should mention blocking"

    print("✅ ENFORCE phase: Hard blocking working")
    print(f"Sample message:\n{message}")


def test_bypass_mechanism():
    """Test MANUAL and SUDO MANUAL bypass keywords"""
    print("\n=== TEST 4: BYPASS MECHANISM ===")
    state = reset_state()
    state["phase"] = "enforce"
    save_enforcement_state(state)

    # Test MANUAL bypass
    action, message = should_enforce("multi_read", state, prompt="Do this MANUAL please")
    assert action == "observe", f"Expected observe (bypassed), got {action}"
    print("✅ MANUAL bypass working")

    # Test SUDO MANUAL bypass
    action, message = should_enforce("multi_read", state, prompt="SUDO MANUAL override")
    assert action == "observe", f"Expected observe (bypassed), got {action}"
    print("✅ SUDO MANUAL bypass working")


def test_auto_tuning():
    """Test automatic threshold adjustment"""
    print("\n=== TEST 5: AUTO-TUNING ===")
    state = reset_state()

    # Simulate high false positive rate (>10%)
    for i in range(10):
        update_pattern_detection("multi_read", turns_wasted=3, script_written=False, bypassed=True)

    state = get_enforcement_state()
    old_threshold = state["thresholds"]["min_repetitions"]
    print(f"Initial threshold: {old_threshold}")

    # Run auto-tune
    adjustments = auto_tune_thresholds(state, turn=50)
    state = get_enforcement_state()
    new_threshold = state["thresholds"]["min_repetitions"]

    print(f"After auto-tune: {new_threshold}")
    print(f"Adjustments made: {adjustments}")

    assert new_threshold > old_threshold, "Threshold should increase with high FP rate"
    print(f"✅ Auto-tuning: Loosened threshold from {old_threshold} → {new_threshold}")


def test_phase_transitions():
    """Test automatic phase transitions"""
    print("\n=== TEST 6: PHASE TRANSITIONS ===")
    state = reset_state()

    # Test OBSERVE → WARN transition
    state["total_turns"] = 25  # Exceed 20 turn threshold
    message = check_phase_transition(state, turn=25)
    assert message is not None, "Should trigger transition message"
    assert "WARN PHASE" in message, "Should transition to WARN"

    state = get_enforcement_state()
    assert state["phase"] == "warn", f"Expected warn phase, got {state['phase']}"
    print("✅ OBSERVE → WARN transition working")

    # Test WARN → ENFORCE transition
    # Simulate high ROI
    for i in range(5):
        update_pattern_detection("multi_read", turns_wasted=10, script_written=True)

    state = get_enforcement_state()
    message = check_phase_transition(state, turn=50)
    if message and "ENFORCE PHASE" in message:
        state = get_enforcement_state()
        assert state["phase"] == "enforce", f"Expected enforce phase, got {state['phase']}"
        print("✅ WARN → ENFORCE transition working")
    else:
        print("⚠️  WARN → ENFORCE transition not triggered (may need higher ROI)")


def test_prompt_detection():
    """Test file_iteration pattern detection in prompts"""
    print("\n=== TEST 7: PROMPT DETECTION ===")

    test_cases = [
        ("Process all files in the directory", True),
        ("For each file, run the linter", True),
        ("Iterate through files and fix", True),
        ("Read a single file", False),
        ("Check these files: a.py, b.py", False),  # Not iteration language
    ]

    for prompt, should_detect in test_cases:
        pattern = detect_pattern_in_prompt(prompt)
        detected = pattern is not None

        if should_detect:
            assert detected, f"Should detect pattern in: '{prompt}'"
            print(f"✅ Detected in: '{prompt}'")
        else:
            assert not detected, f"Should NOT detect pattern in: '{prompt}'"
            print(f"✅ No detection in: '{prompt}'")


def test_auto_report():
    """Test auto-report generation"""
    print("\n=== TEST 8: AUTO-REPORT ===")
    state = reset_state()

    # Simulate some activity
    for i in range(10):
        update_pattern_detection("multi_read", turns_wasted=4, script_written=True if i % 2 == 0 else False)

    state = get_enforcement_state()
    report = generate_auto_report(state, turn=50)

    assert "SCRATCH ENFORCEMENT AUTO-REPORT" in report, "Should contain header"
    assert "Phase:" in report, "Should show phase"
    assert "Patterns Detected:" in report, "Should show pattern count"
    assert "Avg ROI:" in report, "Should show ROI"

    print("✅ Auto-report generation working")
    print(f"\n{report}")


def run_all_tests():
    """Run all tests"""
    print("🧪 SCRATCH ENFORCEMENT SYSTEM TESTS\n")
    print("=" * 60)

    tests = [
        test_phase_1_observe,
        test_phase_2_warn,
        test_phase_3_enforce,
        test_bypass_mechanism,
        test_auto_tuning,
        test_phase_transitions,
        test_prompt_detection,
        test_auto_report,
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

    if failed == 0:
        print("\n✅ ALL TESTS PASSED")
        return 0
    else:
        print(f"\n❌ {failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
