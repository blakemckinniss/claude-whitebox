#!/usr/bin/env python3
"""
Test suite for Reinforcement Learning layer
Validates: reward detection, penalty detection, motivation mechanics
"""
import sys
import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIDENCE_CMD = str(PROJECT_ROOT / "scripts" / "ops" / "confidence.py")

def run_command(cmd):
    """Run command and return output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def test_reinforcement_schedule():
    """Test that gain/loss commands work correctly"""
    print("📊 Test 1: Reinforcement schedule")

    # Reset
    run_command(f"python3 {CONFIDENCE_CMD} reset")

    # Apply positive reinforcement
    stdout, _, _ = run_command(f"python3 {CONFIDENCE_CMD} gain read_file 'test.py'")
    assert "+10%" in stdout
    print("✅ Positive reinforcement applied: +10%")

    # Apply negative reinforcement
    stdout, _, _ = run_command(f"python3 {CONFIDENCE_CMD} loss skip_verification 'Forgot to verify'")
    assert "-20%" in stdout
    assert "WARNING" in stdout  # Should warn about dropping below threshold
    print("✅ Negative reinforcement applied: -20%")

def test_status_display():
    """Test enhanced status display with reinforcement stats"""
    print("\n📊 Test 2: Enhanced status display")

    # Reset and add some activity
    run_command(f"python3 {CONFIDENCE_CMD} reset")
    run_command(f"python3 {CONFIDENCE_CMD} gain read_file")
    run_command(f"python3 {CONFIDENCE_CMD} gain use_researcher")
    run_command(f"python3 {CONFIDENCE_CMD} loss write_without_read")

    stdout, _, _ = run_command(f"python3 {CONFIDENCE_CMD} status")

    # Check components
    assert "Current Confidence:" in stdout
    assert "Reinforcement Stats:" in stdout
    assert "Total Gains:" in stdout
    assert "Total Losses:" in stdout
    assert "Net Score:" in stdout
    assert "Recent Activity" in stdout
    assert "📈" in stdout  # Gain icon
    assert "📉" in stdout  # Loss icon
    print("✅ Status display shows reinforcement stats")

def test_agent_bonus():
    """Test that agent delegation provides bonus rewards"""
    print("\n📊 Test 3: Agent delegation bonus")

    run_command(f"python3 {CONFIDENCE_CMD} reset")

    # Manual research
    run_command(f"python3 {CONFIDENCE_CMD} gain research_manual")
    stdout1, _, _ = run_command(f"python3 {CONFIDENCE_CMD} status")

    # Reset and try agent research
    run_command(f"python3 {CONFIDENCE_CMD} reset")
    run_command(f"python3 {CONFIDENCE_CMD} gain use_researcher")
    stdout2, _, _ = run_command(f"python3 {CONFIDENCE_CMD} status")

    # Agent should give more confidence
    # Manual = +20%, Agent = +25%
    assert "20%" in stdout1
    assert "25%" in stdout2
    print("✅ Agent delegation provides bonus: +25% vs +20% manual")

def test_loss_aversion():
    """Test that losses create visible setback (loss aversion psychology)"""
    print("\n📊 Test 4: Loss aversion mechanics")

    # Build up confidence
    run_command(f"python3 {CONFIDENCE_CMD} reset")
    run_command(f"python3 {CONFIDENCE_CMD} gain read_file")
    run_command(f"python3 {CONFIDENCE_CMD} gain research_manual")
    run_command(f"python3 {CONFIDENCE_CMD} gain probe")
    run_command(f"python3 {CONFIDENCE_CMD} gain verify")

    # Should be at 100% now
    stdout, _, _ = run_command(f"python3 {CONFIDENCE_CMD} status")
    assert "100%" in stdout
    assert "CERTAINTY" in stdout

    # Apply penalty
    stdout, _, _ = run_command(f"python3 {CONFIDENCE_CMD} loss modify_unexamined")

    # Should drop to 60% and lose production access
    assert "60%" in stdout
    assert "WARNING" in stdout
    assert "dropped below production threshold" in stdout
    print("✅ Loss aversion: Penalty drops tier and shows warning")

def test_motivation_tips():
    """Test that status provides actionable tips based on tier"""
    print("\n📊 Test 5: Motivational tips")

    # Ignorance tier
    run_command(f"python3 {CONFIDENCE_CMD} reset")
    stdout, _, _ = run_command(f"python3 {CONFIDENCE_CMD} status")
    assert "💡 Tip:" in stdout
    assert "/research" in stdout or "/probe" in stdout
    print("✅ Ignorance tier provides research/probe tips")

    # Hypothesis tier
    run_command(f"python3 {CONFIDENCE_CMD} gain probe")
    run_command(f"python3 {CONFIDENCE_CMD} gain research_manual")
    stdout, _, _ = run_command(f"python3 {CONFIDENCE_CMD} status")
    assert "💡 Tip:" in stdout
    assert "/verify" in stdout
    print("✅ Hypothesis tier provides verification tips")

    # Certainty tier
    run_command(f"python3 {CONFIDENCE_CMD} gain verify")
    stdout, _, _ = run_command(f"python3 {CONFIDENCE_CMD} status")
    assert "All tiers unlocked" in stdout
    assert "Confidence can still drop" in stdout  # Warning
    print("✅ Certainty tier shows completion + warning")

def test_reinforcement_log():
    """Test that all actions are logged with timestamps"""
    print("\n📊 Test 6: Reinforcement log persistence")

    run_command(f"python3 {CONFIDENCE_CMD} reset")
    run_command(f"python3 {CONFIDENCE_CMD} gain read_file 'core.py'")
    run_command(f"python3 {CONFIDENCE_CMD} gain use_council 'Architecture decision'")
    run_command(f"python3 {CONFIDENCE_CMD} loss skip_verification 'Forgot to verify'")

    stdout, _, _ = run_command(f"python3 {CONFIDENCE_CMD} status")

    # Check log entries
    assert "read_file" in stdout
    assert "use_council" in stdout
    assert "skip_verification" in stdout
    assert "Recent Activity" in stdout
    print("✅ Reinforcement log tracks all actions")

def test_list_command():
    """Test that list command shows all available actions"""
    print("\n📊 Test 7: Action listing")

    stdout, _, _ = run_command(f"python3 {CONFIDENCE_CMD} list")

    # Check sections
    assert "POSITIVE REINFORCEMENT ACTIONS" in stdout
    assert "NEGATIVE REINFORCEMENT ACTIONS" in stdout

    # Check some key actions
    assert "use_researcher" in stdout
    assert "modify_unexamined" in stdout
    assert "+25%" in stdout  # researcher bonus
    assert "-40%" in stdout  # modify_unexamined penalty
    print("✅ List command shows all actions with values")

def main():
    print("🎮 Testing Reinforcement Learning Layer\n")

    try:
        test_reinforcement_schedule()
        test_status_display()
        test_agent_bonus()
        test_loss_aversion()
        test_motivation_tips()
        test_reinforcement_log()
        test_list_command()

        print("\n" + "="*60)
        print("✅ ALL REINFORCEMENT TESTS PASSED")
        print("="*60)
        print("\n📋 Reinforcement Layer Validated:")
        print("   • Positive/negative reinforcement working")
        print("   • Agent delegation provides bonus rewards")
        print("   • Loss aversion creates visible setbacks")
        print("   • Motivational tips guide behavior")
        print("   • Activity log tracks all actions")
        print("   • List command shows reinforcement schedule")
        print("\n🎯 Carrot-on-a-stick mechanics operational!")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
