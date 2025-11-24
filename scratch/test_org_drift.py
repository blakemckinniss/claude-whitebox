#!/usr/bin/env python3
"""
Comprehensive tests for Organizational Drift Detection
Tests catastrophic scenarios, auto-tuning, and false positive handling
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add scripts/lib to path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "scripts" / "lib"))

from org_drift import (
    detect_recursion,
    detect_root_pollution,
    detect_production_pollution,
    detect_filename_collision,
    calculate_depth,
    check_organizational_drift,
    is_excluded,
    load_state,
    save_state,
    auto_tune_thresholds,
)


def test_recursion_detection():
    """Test detection of recursive directory structures"""
    print("Testing recursion detection...")

    # Should detect
    assert detect_recursion("scripts/scripts/ops/audit.py") is not None
    assert detect_recursion(".claude/hooks/.claude/hooks/test.py") is not None
    assert detect_recursion("foo/bar/foo/test.py") is not None

    # Should NOT detect
    assert detect_recursion("scripts/ops/audit.py") is None
    assert detect_recursion(".claude/hooks/test.py") is None
    assert detect_recursion("projects/myapp/src/main.py") is None

    print("✅ Recursion detection passed")


def test_root_pollution_detection():
    """Test detection of files in repository root"""
    print("Testing root pollution detection...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Should detect pollution
        assert detect_root_pollution(f"{tmpdir}/test.py", tmpdir) is not None
        assert detect_root_pollution(f"{tmpdir}/foo.json", tmpdir) is not None

        # Should NOT detect (allowlisted)
        assert detect_root_pollution(f"{tmpdir}/README.md", tmpdir) is None
        assert detect_root_pollution(f"{tmpdir}/CLAUDE.md", tmpdir) is None
        assert detect_root_pollution(f"{tmpdir}/.gitignore", tmpdir) is None

        # Should NOT detect (not in root)
        assert detect_root_pollution(f"{tmpdir}/scripts/test.py", tmpdir) is None

    print("✅ Root pollution detection passed")


def test_production_pollution_detection():
    """Test detection of test files in production zones"""
    print("Testing production pollution detection...")

    # Should detect
    assert detect_production_pollution("scripts/ops/test_audit.py") is not None
    assert detect_production_pollution("scripts/lib/debug_foo.py") is not None
    assert detect_production_pollution(".claude/hooks/scratch_test.py") is not None
    assert detect_production_pollution("scripts/ops/temp_file.tmp") is not None

    # Should NOT detect (wrong zone)
    assert detect_production_pollution("scratch/test_foo.py") is None
    assert detect_production_pollution("projects/myapp/test_main.py") is None

    # Should NOT detect (valid production file)
    assert detect_production_pollution("scripts/ops/audit.py") is None
    assert detect_production_pollution(".claude/hooks/startup.py") is None

    print("✅ Production pollution detection passed")


def test_depth_calculation():
    """Test directory depth calculation"""
    print("Testing depth calculation...")

    assert calculate_depth("foo/bar/baz.py") == 3
    assert calculate_depth("scripts/ops/audit.py") == 3
    assert calculate_depth("test.py") == 1
    assert calculate_depth("") == 0
    assert calculate_depth("/") == 0

    print("✅ Depth calculation passed")


def test_exclusion_patterns():
    """Test exclusion of system directories"""
    print("Testing exclusion patterns...")

    # Should exclude
    assert is_excluded("node_modules/foo/bar.js")
    assert is_excluded("venv/lib/python3.9/site-packages/test.py")
    assert is_excluded("__pycache__/foo.pyc")
    assert is_excluded(".git/objects/abc123")
    assert is_excluded("scratch/archive/old/test.py")
    assert is_excluded("projects/myapp/src/main.py")

    # Should NOT exclude
    assert not is_excluded("scripts/ops/audit.py")
    assert not is_excluded(".claude/hooks/startup.py")
    assert not is_excluded("scratch/test.py")

    print("✅ Exclusion patterns passed")


def test_filename_collision_detection():
    """Test detection of duplicate filenames across production zones"""
    print("Testing filename collision detection...")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create production zones
        ops_dir = root / "scripts" / "ops"
        lib_dir = root / "scripts" / "lib"
        hooks_dir = root / ".claude" / "hooks"

        ops_dir.mkdir(parents=True)
        lib_dir.mkdir(parents=True)
        hooks_dir.mkdir(parents=True)

        # Create existing file
        (lib_dir / "epistemology.py").touch()

        # Should detect collision
        result = detect_filename_collision(str(ops_dir / "epistemology.py"), tmpdir)
        assert result is not None

        # Should NOT detect (different filename)
        result = detect_filename_collision(str(ops_dir / "audit.py"), tmpdir)
        assert result is None

        # Should NOT detect (same file)
        result = detect_filename_collision(str(lib_dir / "epistemology.py"), tmpdir)
        assert result is None

    print("✅ Filename collision detection passed")


def test_full_drift_check_catastrophic():
    """Test full drift check with catastrophic violations"""
    print("Testing full drift check (catastrophic)...")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create minimal structure
        (root / "scripts" / "ops").mkdir(parents=True)
        (root / ".claude" / "memory").mkdir(parents=True)

        # Test 1: Recursion (should block)
        allowed, errors, warnings = check_organizational_drift(
            "scripts/scripts/ops/test.py",
            tmpdir,
            is_sudo=False
        )
        assert not allowed
        assert len(errors) > 0
        assert "Recursive" in errors[0]

        # Test 2: Root pollution (should block)
        allowed, errors, warnings = check_organizational_drift(
            f"{tmpdir}/test.py",
            tmpdir,
            is_sudo=False
        )
        assert not allowed
        assert len(errors) > 0
        assert "Root pollution" in errors[0]

        # Test 3: Production pollution (should block)
        allowed, errors, warnings = check_organizational_drift(
            "scripts/ops/test_foo.py",
            tmpdir,
            is_sudo=False
        )
        assert not allowed
        assert len(errors) > 0
        assert "Production zone pollution" in errors[0]

        # Test 4: SUDO override (should allow)
        allowed, errors, warnings = check_organizational_drift(
            f"{tmpdir}/test.py",
            tmpdir,
            is_sudo=True
        )
        assert allowed
        assert len(errors) > 0  # Errors still detected
        # but allowed=True due to SUDO

    print("✅ Full drift check (catastrophic) passed")


def test_auto_tuning():
    """Test auto-tuning of thresholds based on false positives"""
    print("Testing auto-tuning...")

    # Create test state
    state = {
        "thresholds": {
            "max_hooks": 30,
            "max_scratch_files": 500,
            "max_memory_sessions": 100,
            "max_depth": 6,
        },
        "false_positives": {
            "hook_explosion": 20,  # High FP rate
            "scratch_bloat": 2,     # Low FP rate
        },
        "total_checks": {
            "hook_explosion": 100,  # 20% FP rate -> should loosen
            "scratch_bloat": 100,   # 2% FP rate -> should tighten
        },
        "turn_count": 100,
        "sudo_overrides": [],
    }

    original_hooks = state["thresholds"]["max_hooks"]
    original_scratch = state["thresholds"]["max_scratch_files"]

    # Run auto-tuning
    auto_tune_thresholds(state)

    # Hook threshold should increase (too many FPs)
    assert state["thresholds"]["max_hooks"] > original_hooks

    # Scratch threshold should decrease (very few FPs)
    assert state["thresholds"]["max_scratch_files"] < original_scratch

    print("✅ Auto-tuning passed")


def test_warnings_vs_errors():
    """Test that warnings don't block, but errors do"""
    print("Testing warnings vs errors...")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create structure
        (root / "scripts" / "ops").mkdir(parents=True)
        (root / ".claude" / "memory").mkdir(parents=True)
        (root / "scratch").mkdir(parents=True)

        # Create many hooks to trigger warning
        hooks_dir = root / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True)
        for i in range(35):
            (hooks_dir / f"hook_{i}.py").touch()

        # Test: Valid file in valid location (should allow with warnings)
        allowed, errors, warnings = check_organizational_drift(
            "scripts/ops/new_tool.py",
            tmpdir,
            is_sudo=False
        )
        assert allowed  # Should allow
        assert len(errors) == 0  # No errors
        assert len(warnings) > 0  # But has warnings about hook count

    print("✅ Warnings vs errors passed")


def test_exclusions_bypass_checks():
    """Test that excluded paths bypass all checks"""
    print("Testing exclusion bypass...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Even catastrophic violations should be allowed if excluded
        allowed, errors, warnings = check_organizational_drift(
            "node_modules/scripts/scripts/test.py",  # Recursive + excluded
            tmpdir,
            is_sudo=False
        )
        assert allowed
        assert len(errors) == 0
        assert len(warnings) == 0

        allowed, errors, warnings = check_organizational_drift(
            "projects/myapp/test_foo.py",  # Would be prod pollution + excluded
            tmpdir,
            is_sudo=False
        )
        assert allowed
        assert len(errors) == 0

    print("✅ Exclusion bypass passed")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("ORGANIZATIONAL DRIFT DETECTION - TEST SUITE")
    print("=" * 60)
    print()

    tests = [
        test_recursion_detection,
        test_root_pollution_detection,
        test_production_pollution_detection,
        test_depth_calculation,
        test_exclusion_patterns,
        test_filename_collision_detection,
        test_full_drift_check_catastrophic,
        test_auto_tuning,
        test_warnings_vs_errors,
        test_exclusions_bypass_checks,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {test.__name__} ERROR: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
