#!/usr/bin/env python3
"""
Test suite for The Epistemological Protocol enforcement
Validates: detection hooks, gating hooks, confidence tracking
"""
import sys
import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIDENCE_CMD = str(PROJECT_ROOT / "scripts" / "ops" / "confidence.py")
DETECT_HOOK = str(PROJECT_ROOT / ".claude" / "hooks" / "detect_low_confidence.py")
GATE_HOOK = str(PROJECT_ROOT / ".claude" / "hooks" / "confidence_gate.py")

def run_command(cmd):
    """Run command and return output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def test_detection_hook(prompt, expected_warning=False):
    """Test UserPromptSubmit detection hook"""
    input_data = {"prompt": prompt}
    result = subprocess.run(
        ["python3", DETECT_HOOK],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )
    output = json.loads(result.stdout)
    context = output["hookSpecificOutput"]["additionalContext"]

    if expected_warning:
        assert context != "", f"Expected warning for prompt: {prompt}"
        print(f"✅ Detection hook warned as expected: {prompt[:50]}...")
    else:
        assert context == "", f"Unexpected warning for prompt: {prompt}"
        print(f"✅ Detection hook silent as expected: {prompt[:50]}...")

def test_gate_hook(tool_name, file_path, expected_block=False):
    """Test PreToolUse gating hook"""
    input_data = {
        "toolName": tool_name,
        "toolParams": {"file_path": file_path}
    }
    result = subprocess.run(
        ["python3", GATE_HOOK],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )
    output = json.loads(result.stdout)
    action = output["hookSpecificOutput"]["action"]

    if expected_block:
        assert action == "deny", f"Expected block for: {file_path}"
        print(f"✅ Gate hook blocked as expected: {file_path}")
    else:
        assert action == "allow", f"Expected allow for: {file_path}"
        print(f"✅ Gate hook allowed as expected: {file_path}")

def main():
    print("📉 Testing Epistemological Protocol Enforcement\n")

    # Reset confidence to 0%
    print("🔄 Resetting confidence to 0%...")
    run_command(f"python3 {CONFIDENCE_CMD} reset")

    # Test 1: Check initial state
    print("\n📊 Test 1: Initial state should be 0% (Ignorance)")
    stdout, _, _ = run_command(f"python3 {CONFIDENCE_CMD} status")
    assert "0%" in stdout
    assert "IGNORANCE" in stdout
    print("✅ Initial state verified")

    # Test 2: Detection hook should warn on coding requests at 0%
    print("\n📊 Test 2: Detection hook warnings")
    test_detection_hook("write a function to parse JSON", expected_warning=True)
    test_detection_hook("implement a sorting algorithm", expected_warning=True)
    test_detection_hook("what is Python?", expected_warning=False)  # Not coding

    # Test 3: Gate hook should block production writes at 0%
    print("\n📊 Test 3: Gate hook blocking (0% confidence)")
    test_gate_hook("Write", "scripts/ops/new_tool.py", expected_block=True)
    test_gate_hook("Edit", "scripts/lib/core.py", expected_block=True)
    test_gate_hook("Write", "scratch/test.py", expected_block=False)  # Scratch allowed

    # Test 4: Add evidence to reach Hypothesis tier (31-70%)
    print("\n📊 Test 4: Adding evidence to reach Hypothesis tier")
    run_command(f"python3 {CONFIDENCE_CMD} add read 'core.py' 10")
    run_command(f"python3 {CONFIDENCE_CMD} add research 'Python docs' 20")
    run_command(f"python3 {CONFIDENCE_CMD} add probe 'json.loads' 30")

    stdout, _, _ = run_command(f"python3 {CONFIDENCE_CMD} status")
    assert "60%" in stdout
    assert "HYPOTHESIS" in stdout
    print("✅ Reached Hypothesis tier (60%)")

    # Test 5: Gate should still block production at 60%
    print("\n📊 Test 5: Gate hook still blocking at 60% (< 71%)")
    test_gate_hook("Write", "scripts/ops/new_tool.py", expected_block=True)

    # Test 6: Add verification to reach Certainty tier (71%+)
    print("\n📊 Test 6: Adding verification to reach Certainty tier")
    run_command(f"python3 {CONFIDENCE_CMD} add verify 'file exists' 40")

    stdout, _, _ = run_command(f"python3 {CONFIDENCE_CMD} status")
    assert "100%" in stdout
    assert "CERTAINTY" in stdout
    print("✅ Reached Certainty tier (100%)")

    # Test 7: Gate should allow production writes at 100%
    print("\n📊 Test 7: Gate hook allows production at 100%")
    test_gate_hook("Write", "scripts/ops/new_tool.py", expected_block=False)
    test_gate_hook("Edit", "scripts/lib/core.py", expected_block=False)

    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED")
    print("="*60)
    print("\n📋 Epistemological Protocol Enforcement Validated:")
    print("   • Detection hook warns at low confidence")
    print("   • Gate hook blocks production writes at <71%")
    print("   • Scratch writes always allowed (experimentation)")
    print("   • Evidence accumulation works correctly")
    print("   • Confidence tiers enforce proper workflow")

if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
