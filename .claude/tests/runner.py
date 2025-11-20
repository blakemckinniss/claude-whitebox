#!/usr/bin/env python3
"""
Test Suite Runner
Executes all tests and reports results.

Usage:
    python3 .claude/tests/runner.py              # Run all tests
    python3 .claude/tests/runner.py unit         # Run only unit tests
    python3 .claude/tests/runner.py integration  # Run only integration tests
    python3 .claude/tests/runner.py alignment    # Run only alignment tests
    python3 .claude/tests/runner.py stability    # Run only stability tests
"""
import sys
import os
import subprocess
from pathlib import Path

# Test categories and their test files
TEST_SUITES = {
    "unit": [
        "unit/test_core.py",
    ],
    "integration": [
        "integration/test_scaffolder.py",
        "integration/test_indexer.py",
    ],
    "alignment": [
        "alignment/test_whitebox_principles.py",
    ],
    "stability": [
        "stability/test_path_resolution.py",
    ],
}

def run_test_file(test_file):
    """Run a single test file and return pass/fail status"""
    result = subprocess.run(
        ["python3", test_file],
        capture_output=True,
        text=True
    )

    # Print output
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    return result.returncode == 0

def main():
    tests_dir = Path(__file__).parent
    os.chdir(tests_dir)

    # Determine which suites to run
    if len(sys.argv) > 1:
        requested_suite = sys.argv[1]
        if requested_suite not in TEST_SUITES:
            print(f"Error: Unknown test suite '{requested_suite}'")
            print(f"Available suites: {', '.join(TEST_SUITES.keys())}")
            return 1
        suites_to_run = {requested_suite: TEST_SUITES[requested_suite]}
    else:
        suites_to_run = TEST_SUITES

    print("=" * 70)
    print("WHITEBOX SDK TEST SUITE")
    print("=" * 70)
    print()

    total_passed = 0
    total_failed = 0
    failed_tests = []

    # Run each suite
    for suite_name, test_files in suites_to_run.items():
        print(f"\n{'=' * 70}")
        print(f"SUITE: {suite_name.upper()}")
        print(f"{'=' * 70}\n")

        suite_passed = 0
        suite_failed = 0

        for test_file in test_files:
            test_path = tests_dir / test_file

            if not test_path.exists():
                print(f"⚠️  Test file not found: {test_file}")
                suite_failed += 1
                failed_tests.append(test_file)
                continue

            print(f"\n▶ Running {test_file}...")
            if run_test_file(test_path):
                suite_passed += 1
            else:
                suite_failed += 1
                failed_tests.append(test_file)

        print(f"\n{suite_name.upper()} Suite: {suite_passed} passed, {suite_failed} failed\n")

        total_passed += suite_passed
        total_failed += suite_failed

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"Total tests passed: {total_passed}")
    print(f"Total tests failed: {total_failed}")

    if failed_tests:
        print("\nFailed tests:")
        for test in failed_tests:
            print(f"  ❌ {test}")

    print("=" * 70)

    if total_failed == 0:
        print("\n✅ All tests passed! SDK is stable.")
        return 0
    else:
        print(f"\n❌ {total_failed} test(s) failed. Please review.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
