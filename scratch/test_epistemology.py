#!/usr/bin/env python3
"""
Test script for Epistemological Protocol
Validates that state tracking and confidence updates work correctly
"""
import sys
import json
from pathlib import Path

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import (
    initialize_session_state,
    load_session_state,
    assess_initial_confidence,
    update_confidence,
    check_tier_gate,
    apply_penalty,
    get_confidence_tier,
    get_session_state_file
)

def test_session_initialization():
    """Test that session state initializes correctly"""
    print("=== Test 1: Session Initialization ===")

    session_id = "test_session_001"
    state = initialize_session_state(session_id)

    assert state["confidence"] == 0, "Initial confidence should be 0"
    assert state["risk"] == 0, "Initial risk should be 0"
    assert state["turn_count"] == 0, "Initial turn count should be 0"
    assert len(state["evidence_ledger"]) == 0, "Evidence ledger should be empty"

    print("✓ Session initializes at 0% confidence, 0% risk")

    # Verify file was created
    state_file = get_session_state_file(session_id)
    assert state_file.exists(), "State file should exist"
    print(f"✓ State file created: {state_file}")

    return session_id


def test_initial_confidence_assessment():
    """Test initial confidence assessment based on prompt complexity"""
    print("\n=== Test 2: Initial Confidence Assessment ===")

    test_cases = [
        ("What is Python?", 15, "simple question"),
        ("Fix the bug in auth.py", 25, "contextual request"),
        ("Should we migrate to GraphQL?", 10, "architecture decision"),
        ("Make it better", 5, "vague request"),
    ]

    for prompt, expected, description in test_cases:
        confidence = assess_initial_confidence(prompt)
        print(f"  '{prompt[:30]}...' → {confidence}% ({description})")
        assert confidence <= 70, "Initial confidence should not exceed 70%"

    print("✓ Initial assessment works, max 70%")


def test_evidence_gathering():
    """Test that evidence gathering increases confidence"""
    print("\n=== Test 3: Evidence Gathering ===")

    session_id = "test_session_002"
    state = initialize_session_state(session_id)

    # Simulate reading a file
    new_conf, boost = update_confidence(
        session_id=session_id,
        tool_name="Read",
        tool_input={"file_path": "/test/config.py"},
        turn=1,
        reason="Read config file"
    )

    assert new_conf == boost, "First read should boost from 0"
    assert boost == 10, "First file read should be +10%"
    print(f"✓ Read file: 0% → {new_conf}% (+{boost}%)")

    # Read same file again (diminishing returns)
    new_conf2, boost2 = update_confidence(
        session_id=session_id,
        tool_name="Read",
        tool_input={"file_path": "/test/config.py"},
        turn=2,
        reason="Re-read config file"
    )

    assert boost2 == 2, "Re-reading same file should be +2%"
    print(f"✓ Re-read same file: {new_conf}% → {new_conf2}% (+{boost2}% diminishing returns)")

    # Simulate web search
    new_conf3, boost3 = update_confidence(
        session_id=session_id,
        tool_name="Bash",
        tool_input={"command": "python3 scripts/ops/research.py 'FastAPI'"},
        turn=3,
        reason="Research FastAPI"
    )

    assert boost3 == 20, "Research should be +20%"
    print(f"✓ Web search: {new_conf2}% → {new_conf3}% (+{boost3}%)")


def test_tier_gates():
    """Test that tier gates block inappropriate actions"""
    print("\n=== Test 4: Tier Gates ===")

    session_id = "test_session_003"
    state = initialize_session_state(session_id)

    # Try to write production code at 0% confidence
    allowed, message = check_tier_gate(
        tool_name="Write",
        tool_input={"file_path": "scripts/auth.py"},
        current_confidence=0
    )

    assert not allowed, "Should block production write at 0% confidence"
    print("✓ Blocked production write at 0% confidence")

    # Try to write to scratch at 0% confidence
    allowed2, message2 = check_tier_gate(
        tool_name="Write",
        tool_input={"file_path": "scratch/test.py"},
        current_confidence=0
    )

    assert not allowed2, "Should block scratch write at 0% confidence (requires 31%)"
    print("✓ Blocked scratch write at 0% confidence (requires 31%)")

    # Set confidence to 40% and try scratch
    state["confidence"] = 40
    allowed3, message3 = check_tier_gate(
        tool_name="Write",
        tool_input={"file_path": "scratch/test.py"},
        current_confidence=40
    )

    assert allowed3, "Should allow scratch write at 40% confidence"
    print("✓ Allowed scratch write at 40% confidence")

    # Try production at 40%
    allowed4, message4 = check_tier_gate(
        tool_name="Write",
        tool_input={"file_path": "scripts/auth.py"},
        current_confidence=40
    )

    assert not allowed4, "Should block production write at 40% (requires 71%)"
    print("✓ Blocked production write at 40% confidence (requires 71%)")

    # Set confidence to 75% and try production
    allowed5, message5 = check_tier_gate(
        tool_name="Write",
        tool_input={"file_path": "scripts/auth.py"},
        current_confidence=75
    )

    assert allowed5, "Should allow production write at 75% confidence"
    print("✓ Allowed production write at 75% confidence")


def test_tier_names():
    """Test tier name retrieval"""
    print("\n=== Test 5: Tier Names ===")

    test_cases = [
        (0, "IGNORANCE"),
        (30, "IGNORANCE"),
        (31, "HYPOTHESIS"),
        (70, "HYPOTHESIS"),
        (71, "CERTAINTY"),
        (100, "CERTAINTY"),
    ]

    for confidence, expected_tier in test_cases:
        tier_name, desc = get_confidence_tier(confidence)
        assert tier_name == expected_tier, f"At {confidence}%, tier should be {expected_tier}"
        print(f"  {confidence}% → {tier_name}")

    print("✓ Tier boundaries correct")


def test_penalties():
    """Test confidence penalties"""
    print("\n=== Test 6: Confidence Penalties ===")

    session_id = "test_session_004"
    state = initialize_session_state(session_id)

    # Build up some confidence
    state["confidence"] = 50
    from lib.epistemology import save_session_state
    save_session_state(session_id, state)

    # Apply hallucination penalty
    new_conf = apply_penalty(
        session_id=session_id,
        penalty_type="hallucination",
        turn=1,
        reason="Claimed verification without tool"
    )

    assert new_conf == 30, "Hallucination penalty should be -20%"
    print(f"✓ Hallucination penalty: 50% → {new_conf}% (-20%)")

    # Apply tier violation penalty
    new_conf2 = apply_penalty(
        session_id=session_id,
        penalty_type="tier_violation",
        turn=2,
        reason="Attempted production write at low confidence"
    )

    assert new_conf2 == 20, "Tier violation penalty should be -10%"
    print(f"✓ Tier violation penalty: 30% → {new_conf2}% (-10%)")


def cleanup_test_files():
    """Clean up test session files"""
    memory_dir = Path(__file__).resolve().parent.parent / ".claude" / "memory"
    for file in memory_dir.glob("session_test_*.json"):
        file.unlink()
    print("\n✓ Cleaned up test files")


if __name__ == "__main__":
    print("Testing Epistemological Protocol Implementation\n")

    try:
        test_session_initialization()
        test_initial_confidence_assessment()
        test_evidence_gathering()
        test_tier_gates()
        test_tier_names()
        test_penalties()
        cleanup_test_files()

        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED")
        print("="*50)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
