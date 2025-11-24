#!/usr/bin/env python3
"""
Circuit Breaker System Tests

Tests all circuit breaker patterns and memory cleanup functionality.
"""

import sys
import json
import time
import tempfile
from pathlib import Path

# Add scratch to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from circuit_breaker import (
    load_circuit_state,
    save_circuit_state,
    initialize_circuit,
    check_circuit_state,
    record_failure,
    record_success,
    add_event_to_window,
    count_events_in_window,
    check_threshold_exceeded,
    trip_circuit,
    reset_circuit,
    get_circuit_status,
    STATE_CLOSED,
    STATE_OPEN,
    STATE_HALF_OPEN,
)

from memory_cleanup import (
    count_lines,
    get_file_size_kb,
    get_file_age_days,
    should_rotate_telemetry,
    should_prune_session,
    truncate_evidence_ledger,
    get_memory_stats,
)


def test_circuit_initialization():
    """Test 1: Circuit breaker initialization"""
    print("\n" + "=" * 60)
    print("TEST 1: Circuit Breaker Initialization")
    print("=" * 60)

    config = {
        "circuit_breakers": {
            "test_circuit": {
                "enabled": True,
                "threshold": 3,
                "window_turns": 5,
                "cooldown_base_seconds": 5,
            }
        }
    }

    circuit = initialize_circuit("test_circuit", config)

    assert circuit["state"] == STATE_CLOSED, "Circuit should start CLOSED"
    assert circuit["failure_count"] == 0, "Failure count should be 0"
    assert circuit["trip_count"] == 0, "Trip count should be 0"
    assert circuit["exponential_backoff_level"] == 0, "Backoff should be 0"
    assert len(circuit["window"]) == 0, "Window should be empty"

    print("✅ Circuit initialized correctly")
    return True


def test_threshold_detection():
    """Test 2: Threshold exceeded detection"""
    print("\n" + "=" * 60)
    print("TEST 2: Threshold Exceeded Detection")
    print("=" * 60)

    config = {
        "circuit_breakers": {
            "test_circuit": {
                "enabled": True,
                "threshold": 3,
                "window_turns": 5,
                "cooldown_base_seconds": 5,
            }
        }
    }

    circuit = initialize_circuit("test_circuit", config)

    # Add 2 failures (below threshold)
    add_event_to_window(circuit, turn=1, event_type="failure")
    add_event_to_window(circuit, turn=2, event_type="failure")

    assert not check_threshold_exceeded(circuit), "Should NOT exceed threshold (2/3)"
    print("✅ 2 failures: threshold NOT exceeded")

    # Add 3rd failure (hits threshold)
    add_event_to_window(circuit, turn=3, event_type="failure")

    assert check_threshold_exceeded(circuit), "Should exceed threshold (3/3)"
    print("✅ 3 failures: threshold EXCEEDED")

    return True


def test_circuit_trip_and_recovery():
    """Test 3: Circuit trip and recovery flow"""
    print("\n" + "=" * 60)
    print("TEST 3: Circuit Trip and Recovery")
    print("=" * 60)

    session_id = "test_session"
    turn = 1

    # Trigger 3 failures to trip circuit
    for i in range(3):
        message = record_failure(
            circuit_name="tool_failure",
            session_id=session_id,
            turn=turn + i,
            reason=f"Test failure {i+1}",
        )

        if message:
            print(f"✅ Circuit tripped after {i+1} failures")
            assert "CIRCUIT BREAKER TRIPPED" in message
            break

    # Check circuit is OPEN
    action, message = check_circuit_state("tool_failure", session_id, turn + 10)
    assert action == "block", "Circuit should be OPEN (blocking)"
    print("✅ Circuit is OPEN (blocking)")

    # Wait for cooldown to expire
    state = load_circuit_state()
    circuit = state["circuits"]["tool_failure"]
    circuit["cooldown_expires_at"] = time.time() - 1  # Force expiry
    save_circuit_state(state)

    # Check circuit is HALF_OPEN
    action, message = check_circuit_state("tool_failure", session_id, turn + 11)
    assert action == "probe", "Circuit should be HALF_OPEN (probing)"
    print("✅ Circuit is HALF_OPEN (probing)")

    # Record success to close circuit
    message = record_success("tool_failure", session_id, turn + 12)
    assert "CLOSED" in message, "Circuit should close on success"
    print("✅ Circuit closed on successful probe")

    return True


def test_exponential_backoff():
    """Test 4: Exponential backoff on repeated trips"""
    print("\n" + "=" * 60)
    print("TEST 4: Exponential Backoff")
    print("=" * 60)

    config = {
        "circuit_breakers": {
            "test_circuit": {
                "enabled": True,
                "threshold": 3,
                "window_turns": 5,
                "cooldown_base_seconds": 5,
            }
        }
    }

    circuit = initialize_circuit("test_circuit", config)

    # Trip multiple times and check backoff increases
    cooldowns = []

    for trip_num in range(5):
        circuit["exponential_backoff_level"] = trip_num
        from circuit_breaker import calculate_cooldown

        cooldown = calculate_cooldown(circuit)
        cooldowns.append(cooldown)
        print(f"  Trip {trip_num + 1}: {cooldown:.0f}s cooldown")

    # Verify exponential growth
    assert cooldowns[0] == 5, "First cooldown should be 5s"
    assert cooldowns[1] == 10, "Second cooldown should be 10s"
    assert cooldowns[2] == 30, "Third cooldown should be 30s"
    assert cooldowns[3] == 60, "Fourth cooldown should be 60s"
    assert cooldowns[4] == 300, "Fifth cooldown should be 300s"

    print("✅ Exponential backoff working correctly")
    return True


def test_memory_telemetry_rotation():
    """Test 5: Telemetry file rotation"""
    print("\n" + "=" * 60)
    print("TEST 5: Telemetry File Rotation")
    print("=" * 60)

    # Create temporary test file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False
    ) as temp_file:
        # Write 1500 lines (exceeds 1000 limit)
        for i in range(1500):
            temp_file.write(f'{{"line": {i}}}\n')

        temp_path = Path(temp_file.name)

    try:
        lines = count_lines(temp_path)
        assert lines == 1500, f"Should have 1500 lines, got {lines}"
        print(f"✅ Test file created: {lines} lines")

        # Check if rotation needed
        limits = {
            "telemetry_max_lines": 1000,
            "telemetry_max_kb": 50,
            "telemetry_max_age_days": 7,
        }

        should_rotate, reason = should_rotate_telemetry(temp_path, limits)
        assert should_rotate, "Should trigger rotation (1500 > 1000 lines)"
        assert "1500 lines" in reason
        print(f"✅ Rotation needed: {reason}")

    finally:
        temp_path.unlink()

    return True


def test_memory_session_pruning():
    """Test 6: Session file pruning"""
    print("\n" + "=" * 60)
    print("TEST 6: Session File Pruning")
    print("=" * 60)

    # Create temporary test session file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_state.json", delete=False
    ) as temp_file:
        json.dump({"session_id": "test", "confidence": 50}, temp_file)
        temp_path = Path(temp_file.name)

    try:
        # Modify timestamp to make it old (8 days ago)
        import os

        old_time = time.time() - (8 * 86400)  # 8 days ago
        os.utime(temp_path, (old_time, old_time))

        age_days = get_file_age_days(temp_path)
        print(f"  File age: {age_days:.1f} days")

        # Check if pruning needed
        limits = {"session_max_age_days": 7}

        should_prune, reason = should_prune_session(temp_path, limits)
        assert should_prune, "Should trigger pruning (8 days > 7 days)"
        assert "8." in reason  # Age should be ~8 days
        print(f"✅ Pruning needed: {reason}")

    finally:
        temp_path.unlink()

    return True


def test_evidence_ledger_truncation():
    """Test 7: Evidence ledger truncation"""
    print("\n" + "=" * 60)
    print("TEST 7: Evidence Ledger Truncation")
    print("=" * 60)

    # Create temporary session file with large evidence ledger
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_state.json", delete=False
    ) as temp_file:
        # Create 150 evidence entries (exceeds 100 limit)
        evidence = [{"turn": i, "boost": 10} for i in range(150)]
        state = {
            "session_id": "test",
            "confidence": 50,
            "evidence_ledger": evidence,
        }
        json.dump(state, temp_file)
        temp_path = Path(temp_file.name)

    try:
        # Truncate
        limits = {"evidence_ledger_max": 100}
        was_truncated = truncate_evidence_ledger(temp_path, limits)
        assert was_truncated, "Should truncate evidence ledger"
        print("✅ Evidence ledger truncated")

        # Verify truncation
        with open(temp_path) as f:
            state = json.load(f)

        assert len(state["evidence_ledger"]) == 100, "Should have exactly 100 entries"
        # Should keep LAST 100 entries
        assert state["evidence_ledger"][0]["turn"] == 50, "Should keep last 100 (50-149)"
        assert state["evidence_ledger"][-1]["turn"] == 149
        print("✅ Kept last 100 entries (50-149)")

    finally:
        temp_path.unlink()

    return True


def test_circuit_status_report():
    """Test 8: Circuit status reporting"""
    print("\n" + "=" * 60)
    print("TEST 8: Circuit Status Report")
    print("=" * 60)

    # Create test state with mixed circuits
    state = {
        "circuits": {
            "circuit_a": {
                "state": STATE_CLOSED,
                "trip_count": 0,
                "exponential_backoff_level": 0,
            },
            "circuit_b": {
                "state": STATE_OPEN,
                "trip_count": 2,
                "exponential_backoff_level": 2,
                "cooldown_expires_at": time.time() + 30,
                "last_trip_time": time.time(),
            },
            "circuit_c": {
                "state": STATE_HALF_OPEN,
                "trip_count": 1,
                "exponential_backoff_level": 1,
            },
        }
    }

    # Save state
    from circuit_breaker import CIRCUIT_STATE_FILE

    CIRCUIT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CIRCUIT_STATE_FILE, "w") as f:
        json.dump(state, f)

    # Get status report
    status = get_circuit_status()

    print("\nStatus Report:")
    print(status)
    print()

    assert "circuit_b: OPEN" in status, "Should show OPEN circuit"
    assert "circuit_c: HALF_OPEN" in status, "Should show HALF_OPEN circuit"
    assert "30s" in status or "29s" in status, "Should show cooldown time"

    print("✅ Status report generated correctly")
    return True


def run_all_tests():
    """Run all circuit breaker tests"""
    print("\n" + "=" * 60)
    print("CIRCUIT BREAKER & MEMORY CLEANUP TEST SUITE")
    print("=" * 60)

    tests = [
        ("Circuit Initialization", test_circuit_initialization),
        ("Threshold Detection", test_threshold_detection),
        ("Circuit Trip and Recovery", test_circuit_trip_and_recovery),
        ("Exponential Backoff", test_exponential_backoff),
        ("Telemetry Rotation", test_memory_telemetry_rotation),
        ("Session Pruning", test_memory_session_pruning),
        ("Evidence Truncation", test_evidence_ledger_truncation),
        ("Status Report", test_circuit_status_report),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED")
        return 0
    else:
        print(f"\n⚠️ {failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
