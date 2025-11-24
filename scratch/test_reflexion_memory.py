#!/usr/bin/env python3
"""
Test script for Reflexion Memory auto-learning system
Creates intentional failures to verify auto-learning hooks
"""
import subprocess
import sys
from pathlib import Path

# Find project root
current = Path(__file__).resolve().parent
while current != current.parent:
    if (current / "scripts" / "lib" / "core.py").exists():
        PROJECT_ROOT = current
        break
    current = current.parent
else:
    print("ERROR: Could not find project root")
    sys.exit(1)

VERIFY_CMD = PROJECT_ROOT / "scripts" / "ops" / "verify.py"
LESSONS_FILE = PROJECT_ROOT / ".claude" / "memory" / "lessons.md"


def test_verify_failure():
    """Test 1: verify.py failure should auto-learn"""
    print("\n" + "=" * 70)
    print("TEST 1: Verify Failure Auto-Learning")
    print("=" * 70)

    # Get baseline lesson count
    with open(LESSONS_FILE, 'r') as f:
        before_content = f.read()
    before_count = before_content.count('[AUTO-LEARNED-FAILURE]')

    # Trigger failure (nonexistent file)
    print("\n🔧 Triggering verify failure...")
    result = subprocess.run(
        ["python3", str(VERIFY_CMD), "file_exists", "/tmp/nonexistent_test_file_reflexion_12345.txt"],
        capture_output=True
    )

    # Check if lesson was added
    with open(LESSONS_FILE, 'r') as f:
        after_content = f.read()
    after_count = after_content.count('[AUTO-LEARNED-FAILURE]')

    if after_count > before_count:
        print(f"✅ SUCCESS: Auto-learned failure (count: {before_count} → {after_count})")
        return True
    else:
        print(f"❌ FAIL: No auto-learning detected (count: {before_count} → {after_count})")
        return False


def test_multiple_failures_then_success():
    """Test 2: Multiple failures followed by success should auto-learn success"""
    print("\n" + "=" * 70)
    print("TEST 2: Success After Failures Auto-Learning")
    print("=" * 70)

    # Get baseline
    with open(LESSONS_FILE, 'r') as f:
        before_content = f.read()
    before_success_count = before_content.count('[AUTO-LEARNED-SUCCESS]')

    # Create test file for verification
    test_file = PROJECT_ROOT / "scratch" / "test_reflexion_target.txt"

    # Fail twice (file doesn't exist)
    print("\n🔧 Triggering 2 failures...")
    for i in range(2):
        subprocess.run(
            ["python3", str(VERIFY_CMD), "file_exists", str(test_file)],
            capture_output=True
        )
        print(f"   Failure {i+1}/2")

    # Succeed once (create file)
    print("\n🔧 Creating file and verifying (should succeed)...")
    test_file.write_text("test content")
    result = subprocess.run(
        ["python3", str(VERIFY_CMD), "file_exists", str(test_file)],
        capture_output=True
    )

    # Cleanup
    test_file.unlink()

    # Check if success was learned
    with open(LESSONS_FILE, 'r') as f:
        after_content = f.read()
    after_success_count = after_content.count('[AUTO-LEARNED-SUCCESS]')

    if after_success_count > before_success_count:
        print(f"✅ SUCCESS: Auto-learned success pattern (count: {before_success_count} → {after_success_count})")
        return True
    else:
        print(f"❌ FAIL: No success auto-learning detected (count: {before_success_count} → {after_success_count})")
        return False


def test_consolidation():
    """Test 3: Consolidation script should merge duplicates"""
    print("\n" + "=" * 70)
    print("TEST 3: Lesson Consolidation")
    print("=" * 70)

    consolidate_cmd = PROJECT_ROOT / "scripts" / "ops" / "consolidate_lessons.py"

    # Get before state
    with open(LESSONS_FILE, 'r') as f:
        before_content = f.read()
    before_auto_count = before_content.count('[AUTO-LEARNED-')

    # Run consolidation
    print("\n🔧 Running consolidation...")
    result = subprocess.run(
        ["python3", str(consolidate_cmd)],
        capture_output=True,
        text=True
    )

    print(f"   {result.stdout.strip()}")

    # Get after state
    with open(LESSONS_FILE, 'r') as f:
        after_content = f.read()
    after_auto_count = after_content.count('[AUTO-LEARNED-')

    if after_auto_count <= before_auto_count:
        print(f"✅ SUCCESS: Consolidation ran (auto-tags: {before_auto_count} → {after_auto_count})")
        return True
    else:
        print(f"❌ FAIL: Consolidation increased auto-tags (unexpected)")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🧠 REFLEXION MEMORY TEST SUITE")
    print("=" * 70)

    results = []

    # Test 1: Failure auto-learning
    results.append(("Failure Auto-Learning", test_verify_failure()))

    # Test 2: Success auto-learning
    results.append(("Success Auto-Learning", test_multiple_failures_then_success()))

    # Test 3: Consolidation
    results.append(("Lesson Consolidation", test_consolidation()))

    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")

    print(f"\n  Total: {passed}/{total} passed")

    if passed == total:
        print("\n  🎉 All tests passed! Reflexion Memory is operational.")
        return 0
    else:
        print(f"\n  ⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
