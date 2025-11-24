#!/usr/bin/env python3
"""
Test Pattern Detection System
Validates hallucination, insanity, falsehood, and loop detectors
"""
import sys
from pathlib import Path

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.pattern_detection import (
    detect_hallucination,
    detect_insanity,
    detect_falsehood,
    detect_loop,
    analyze_patterns,
)


def test_hallucination_detection():
    """Test hallucination detector"""
    print("=== Test 1: Hallucination Detection ===")

    # Transcript with hallucination (claims verification without tool)
    transcript = [
        {"role": "user", "content": "Check if the tests pass"},
        {
            "role": "assistant",
            "content": "I verified the tests and they all pass successfully.",
        },
    ]

    # Evidence ledger WITHOUT verify tool
    evidence_ledger = [
        {"tool": "Read", "target": "tests/test_foo.py"},
    ]

    result = detect_hallucination(transcript, evidence_ledger)

    assert result is not None, "Should detect hallucination"
    assert result["type"] == "hallucination", "Should be hallucination type"
    assert "verified" in result["claim"].lower(), "Should detect 'verified' claim"
    print(f"✓ Detected hallucination: {result['message']}")

    # Negative case: Actual verification
    transcript_valid = [
        {"role": "user", "content": "Check if the tests pass"},
        {
            "role": "assistant",
            "content": "I verified the tests and they all pass successfully.",
        },
    ]

    evidence_ledger_valid = [
        {"tool": "Bash", "target": "python3 scripts/ops/verify.py command_success pytest"},
    ]

    result_valid = detect_hallucination(transcript_valid, evidence_ledger_valid)

    assert (
        result_valid is None
    ), "Should NOT detect hallucination when verification actually done"
    print("✓ No false positive on valid verification")


def test_insanity_detection():
    """Test insanity detector (repeated failures)"""
    print("\n=== Test 2: Insanity Detection ===")

    # Transcript with same command failing 3 times
    transcript = [
        {
            "role": "assistant",
            "content": '<invoke name="Bash"><parameter name="command">npm install broken-package</parameter></invoke>',
        },
        {
            "role": "function",
            "content": "<error>Exit code 1\nERROR: Package not found</error>",
        },
        {
            "role": "assistant",
            "content": '<invoke name="Bash"><parameter name="command">npm install broken-package</parameter></invoke>',
        },
        {
            "role": "function",
            "content": "<error>Exit code 1\nERROR: Package not found</error>",
        },
        {
            "role": "assistant",
            "content": '<invoke name="Bash"><parameter name="command">npm install broken-package</parameter></invoke>',
        },
        {
            "role": "function",
            "content": "<error>Exit code 1\nERROR: Package not found</error>",
        },
    ]

    result = detect_insanity(transcript)

    assert result is not None, "Should detect insanity"
    assert result["type"] == "insanity", "Should be insanity type"
    assert result["failures"] >= 3, "Should count 3+ failures"
    print(
        f"✓ Detected insanity: {result['failures']} repeated failures of {result['tool']}"
    )

    # Negative case: Only 2 failures
    transcript_valid = transcript[:4]  # Only first 2 attempts

    result_valid = detect_insanity(transcript_valid)

    # Should not detect with only 2 failures
    if result_valid:
        assert result_valid["failures"] < 3, "Should require 3+ failures"
    print("✓ No false positive on 2 failures (< threshold)")


def test_falsehood_detection():
    """Test falsehood detector (contradictions)"""
    print("\n=== Test 3: Falsehood Detection ===")

    # Transcript with contradiction
    transcript = [
        {
            "role": "assistant",
            "content": "The configuration file config.py does not exist.",
        },
        {
            "role": "assistant",
            "content": "I just read the configuration file config.py and it contains the database settings.",
        },
    ]

    result = detect_falsehood(transcript)

    assert result is not None, "Should detect falsehood"
    assert result["type"] == "falsehood", "Should be falsehood type"
    print(f"✓ Detected falsehood: {result['message']}")

    # Negative case: Contradiction WITH evidence between
    transcript_valid = [
        {
            "role": "assistant",
            "content": "The configuration file config.py does not exist.",
        },
        {
            "role": "user",
            "content": "Can you create it?",
        },  # New user input = evidence
        {
            "role": "assistant",
            "content": '<invoke name="Write"><parameter name="file_path">config.py</parameter></invoke>',
        },
        {
            "role": "assistant",
            "content": "I just read the configuration file config.py and it contains the database settings.",
        },
    ]

    result_valid = detect_falsehood(transcript_valid)

    assert (
        result_valid is None
    ), "Should NOT detect falsehood when evidence gathered between statements"
    print("✓ No false positive when evidence gathered between statements")


def test_loop_detection():
    """Test loop detector (repeated proposals)"""
    print("\n=== Test 4: Loop Detection ===")

    # Transcript with repeated proposal
    transcript = [
        {"role": "assistant", "content": "Let me try using the subprocess module"},
        {"role": "assistant", "content": "I'll use the subprocess module instead"},
        {"role": "assistant", "content": "We should try the subprocess module"},
    ]

    result = detect_loop(transcript)

    assert result is not None, "Should detect loop"
    assert result["type"] == "loop", "Should be loop type"
    assert result["occurrences"] >= 3, "Should count 3+ occurrences"
    print(f"✓ Detected loop: {result['occurrences']} similar proposals")

    # Negative case: Different proposals
    transcript_valid = [
        {"role": "assistant", "content": "Let me try using the subprocess module"},
        {"role": "assistant", "content": "I'll use the requests library instead"},
        {"role": "assistant", "content": "We should try the os module"},
    ]

    result_valid = detect_loop(transcript_valid)

    assert result_valid is None, "Should NOT detect loop for different proposals"
    print("✓ No false positive for different proposals")


def test_analyze_patterns():
    """Test full pattern analysis"""
    print("\n=== Test 5: Full Pattern Analysis ===")

    # Transcript with multiple violations
    transcript = [
        {
            "role": "assistant",
            "content": "I verified the tests pass.",  # Hallucination
        },
        {
            "role": "assistant",
            "content": "File foo.py exists.",  # Will contradict
        },
        {
            "role": "assistant",
            "content": "File foo.py does not exist.",  # Contradiction
        },
        {"role": "assistant", "content": "Let me use subprocess"},  # Start loop
        {"role": "assistant", "content": "I'll use subprocess instead"},  # Loop
        {"role": "assistant", "content": "We should use subprocess"},  # Loop
    ]

    evidence_ledger = []  # No evidence

    violations = analyze_patterns(transcript, evidence_ledger)

    assert len(violations) > 0, "Should detect at least one violation"
    print(f"✓ Detected {len(violations)} total violations:")

    for v in violations:
        print(f"  - {v['type']}: {v.get('message', 'no message')[:80]}...")


def test_edge_cases():
    """Test edge cases"""
    print("\n=== Test 6: Edge Cases ===")

    # Empty transcript
    result = analyze_patterns([], [])
    assert len(result) == 0, "Should handle empty transcript"
    print("✓ Handles empty transcript")

    # Very short transcript
    short_transcript = [{"role": "user", "content": "Hello"}]
    result = analyze_patterns(short_transcript, [])
    assert len(result) == 0, "Should handle short transcript"
    print("✓ Handles short transcript")

    # No assistant messages
    user_only = [
        {"role": "user", "content": "Question 1"},
        {"role": "user", "content": "Question 2"},
    ]
    result = analyze_patterns(user_only, [])
    assert len(result) == 0, "Should handle user-only transcript"
    print("✓ Handles user-only transcript")


if __name__ == "__main__":
    print("Testing Pattern Detection System\n")

    try:
        test_hallucination_detection()
        test_insanity_detection()
        test_falsehood_detection()
        test_loop_detection()
        test_analyze_patterns()
        test_edge_cases()

        print("\n" + "=" * 50)
        print("✅ ALL PATTERN DETECTION TESTS PASSED")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
