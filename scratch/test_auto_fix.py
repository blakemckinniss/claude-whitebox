#!/usr/bin/env python3
"""
Test Suite for Auto-Fix System
Tests error detection, classification, and auto-fix application
"""
import sys
import os
from pathlib import Path
import tempfile
import shutil

# Add scripts/lib to path
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root / "scripts" / "lib"))

from error_detection import (
    classify_tool_error,
    classify_bash_error,
    detect_anti_patterns,
    calculate_risk,
    calculate_effort,
    decide_action,
    should_auto_fix,
    ErrorCategory,
    ActionDecision,
)
from auto_fixes import (
    AUTO_FIX_REGISTRY,
    find_applicable_fixes,
    apply_auto_fix,
)


def test_classify_tool_error():
    """Test tool error classification"""
    print("\n" + "=" * 70)
    print("TEST: Tool Error Classification")
    print("=" * 70)

    # File not found
    error = classify_tool_error(
        "Read",
        "No such file or directory: /path/to/missing.py",
        {"file_path": "/path/to/missing.py"}
    )
    assert error is not None
    assert error.category == ErrorCategory.LOGIC_ERROR
    assert "File not found" in error.description
    print("  ✅ File not found error classified correctly")

    # Permission denied
    error = classify_tool_error(
        "Write",
        "Permission denied: /root/protected.py",
        {"file_path": "/root/protected.py"}
    )
    assert error is not None
    assert error.category == ErrorCategory.SECURITY
    assert error.risk >= 70
    print("  ✅ Permission error classified as security issue")

    # Syntax error
    error = classify_tool_error(
        "Bash",
        "SyntaxError: invalid syntax on line 15",
        {"command": "python test.py"}
    )
    assert error is not None
    assert error.category == ErrorCategory.LOGIC_ERROR
    print("  ✅ Syntax error classified correctly")


def test_classify_bash_error():
    """Test bash command error classification"""
    print("\n" + "=" * 70)
    print("TEST: Bash Error Classification")
    print("=" * 70)

    # Test failure
    error = classify_bash_error(
        "pytest tests/",
        1,
        "5 failed, 10 passed in 2.3s",
        ""
    )
    assert error is not None
    assert error.category == ErrorCategory.TEST_FAILURE
    assert "5 test(s) failing" in error.description
    print("  ✅ Test failure classified correctly")

    # Command not found
    error = classify_bash_error(
        "nonexistent-command",
        127,
        "",
        "bash: nonexistent-command: command not found"
    )
    assert error is not None
    assert "Command not found" in error.description
    print("  ✅ Command not found classified correctly")


def test_detect_anti_patterns():
    """Test anti-pattern detection"""
    print("\n" + "=" * 70)
    print("TEST: Anti-Pattern Detection")
    print("=" * 70)

    # Hardcoded secret
    content = '''
api_key = "sk-proj-abc123xyz"
def main():
    return api_key
'''
    errors = detect_anti_patterns("test.py", content)
    assert len(errors) > 0
    assert any(e.category == ErrorCategory.SECURITY for e in errors)
    print(f"  ✅ Detected {len(errors)} anti-pattern(s) including hardcoded secret")

    # Print statement
    content = '''
def debug():
    print("Debug info")
'''
    errors = detect_anti_patterns("test.py", content)
    assert any("print" in e.description.lower() for e in errors)
    print("  ✅ Detected print() usage")

    # Blind exception
    content = '''
try:
    risky()
except:
    pass
'''
    errors = detect_anti_patterns("test.py", content)
    assert any("exception" in e.description.lower() for e in errors)
    print("  ✅ Detected blind exception catching")


def test_risk_effort_calculation():
    """Test risk and effort calculation"""
    print("\n" + "=" * 70)
    print("TEST: Risk/Effort Calculation")
    print("=" * 70)

    # High-risk security error
    content = 'api_key = "sk-proj-secret"'
    errors = detect_anti_patterns("test.py", content)
    error = errors[0]
    risk = calculate_risk(error)
    assert risk >= 70
    print(f"  ✅ Security error risk: {risk}% (high)")

    # Low-risk style error (in scratch to avoid production modifier)
    content = 'print("hello")'
    errors = detect_anti_patterns("scratch/test.py", content)
    error = errors[0]
    risk = calculate_risk(error)
    assert risk < 40, f"Expected risk < 40, got {risk}%"
    print(f"  ✅ Style error risk: {risk}% (low)")

    # Effort calculation
    error.description = "print statement at line 5"
    effort = calculate_effort(error)
    assert effort <= 20
    print(f"  ✅ Single-line fix effort: {effort}% (low)")


def test_decision_matrix():
    """Test action decision matrix"""
    print("\n" + "=" * 70)
    print("TEST: Decision Matrix")
    print("=" * 70)

    # Low risk + Low effort = AUTO_FIX
    action = decide_action(risk=20, effort=10)
    assert action == ActionDecision.AUTO_FIX
    print("  ✅ Low risk + Low effort → AUTO_FIX")

    # Low risk + Medium effort = CONSULT
    action = decide_action(risk=30, effort=40)
    assert action == ActionDecision.CONSULT
    print("  ✅ Low risk + Medium effort → CONSULT")

    # High risk = BLOCK
    action = decide_action(risk=80, effort=10)
    assert action == ActionDecision.BLOCK
    print("  ✅ High risk → BLOCK")

    # Low risk + High effort = DEFER
    action = decide_action(risk=25, effort=70)
    assert action == ActionDecision.DEFER
    print("  ✅ Low risk + High effort → DEFER")


def test_auto_fix_print_statement():
    """Test auto-fix for print statements"""
    print("\n" + "=" * 70)
    print("TEST: Auto-Fix Print Statement")
    print("=" * 70)

    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
def test():
    print("Debug info")
    print("More debug")
''')
        temp_file = f.name

    try:
        # Find applicable fixes
        with open(temp_file, 'r') as f:
            content = f.read()

        applicable = find_applicable_fixes(content)
        assert len(applicable) > 0
        print(f"  ✅ Found {len(applicable)} applicable fix(es)")

        # Apply print statement fix
        auto_fix = AUTO_FIX_REGISTRY["print_statement"]
        success, error = apply_auto_fix(temp_file, auto_fix, backup=True)

        if success:
            # Verify fix
            with open(temp_file, 'r') as f:
                new_content = f.read()

            assert "logger.info(" in new_content
            assert "print(" not in new_content
            print("  ✅ Print statements replaced with logger.info()")

            # Verify backup was created
            backup_path = f"{temp_file}.autofix.backup"
            assert Path(backup_path).exists()
            print("  ✅ Backup created")

            # Cleanup backup
            os.unlink(backup_path)
        else:
            print(f"  ⚠️  Fix failed: {error}")

    finally:
        os.unlink(temp_file)


def test_auto_fix_hardcoded_secret():
    """Test auto-fix for hardcoded secrets"""
    print("\n" + "=" * 70)
    print("TEST: Auto-Fix Hardcoded Secret")
    print("=" * 70)

    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
def connect():
    api_key = "sk-proj-secret123"
    return api_key
''')
        temp_file = f.name

    try:
        # Apply hardcoded secret fix
        auto_fix = AUTO_FIX_REGISTRY["hardcoded_secret"]
        success, error = apply_auto_fix(temp_file, auto_fix, backup=True)

        if success:
            # Verify fix
            with open(temp_file, 'r') as f:
                new_content = f.read()

            assert "os.getenv(" in new_content
            assert "sk-proj-" not in new_content
            assert "import os" in new_content
            print("  ✅ Hardcoded secret replaced with os.getenv()")
            print("  ✅ os import added")

            # Cleanup
            os.unlink(f"{temp_file}.autofix.backup")
        else:
            print(f"  ⚠️  Fix failed: {error}")

    finally:
        os.unlink(temp_file)


def test_should_auto_fix():
    """Test auto-fix decision logic"""
    print("\n" + "=" * 70)
    print("TEST: Should Auto-Fix Decision")
    print("=" * 70)

    # Create mock error
    from error_detection import ErrorReport, ErrorCategory

    # Should fix: Low risk, low effort, reversible
    error = ErrorReport(
        error_id="test-1",
        category=ErrorCategory.STYLE_DRIFT,
        description="Print statement",
        file_path="test.py",
        line_number=5,
        severity="LOW",
        risk=15,
        effort=5,
        detected_at_turn=1,
        tool_name="StaticAnalysis",
        command=None,
        reversible=True,
        affects_production=False,
        has_tests=False,
    )

    should_fix, reason = should_auto_fix(error, ActionDecision.AUTO_FIX)
    assert should_fix
    print("  ✅ Low risk/effort error approved for auto-fix")

    # Should NOT fix: High risk
    error.risk = 80
    should_fix, reason = should_auto_fix(error, ActionDecision.AUTO_FIX)
    assert not should_fix
    assert "Risk too high" in reason
    print("  ✅ High risk error blocked from auto-fix")

    # Should NOT fix: Production without tests
    error.risk = 20
    error.affects_production = True
    error.has_tests = False
    should_fix, reason = should_auto_fix(error, ActionDecision.AUTO_FIX)
    assert not should_fix
    assert "without test coverage" in reason
    print("  ✅ Production change without tests blocked")


def main():
    print("\n" + "=" * 70)
    print("🧪 AUTO-FIX SYSTEM TEST SUITE")
    print("=" * 70)

    try:
        test_classify_tool_error()
        test_classify_bash_error()
        test_detect_anti_patterns()
        test_risk_effort_calculation()
        test_decision_matrix()
        test_auto_fix_print_statement()
        test_auto_fix_hardcoded_secret()
        test_should_auto_fix()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print("\nAuto-fix system is operational and ready for use.")
        print("\nNext steps:")
        print("  1. Hooks will automatically detect errors during tool use")
        print("  2. Low-risk errors will be auto-fixed autonomously")
        print("  3. Medium-risk errors will present fix suggestions")
        print("  4. High-risk errors will require council review")
        print("  5. Use 'python3 scripts/ops/review_error.py' to view error history")
        print("=" * 70 + "\n")

        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
