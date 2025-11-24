#!/usr/bin/env python3
"""
Test Playwright Integration

Verifies:
1. playwright.py script works
2. Hook registration is correct
3. Confidence rewards are defined
4. CLAUDE.md alias is present
"""
import json
import subprocess
import sys
from pathlib import Path

def test_playwright_script():
    """Test that playwright.py script exists and runs"""
    script = Path("scripts/ops/playwright.py")
    assert script.exists(), "playwright.py script not found"
    assert script.stat().st_mode & 0o111, "playwright.py not executable"

    # Test --dry-run --check
    result = subprocess.run(
        ["python3", str(script), "--dry-run", "--check"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Dry run failed: {result.stderr}"
    # Check stderr since logger outputs to stderr
    combined = result.stdout + result.stderr
    assert "DRY RUN" in combined, f"Dry run output missing. Got: {combined[:200]}"

    print("✓ playwright.py script working")


def test_hook_registration():
    """Test that auto_playwright_setup hook is registered"""
    settings_file = Path(".claude/settings.json")
    with open(settings_file) as f:
        settings = json.load(f)

    # Check PreToolUse hooks for Bash
    pre_tool_use = settings.get("hooks", {}).get("PreToolUse", [])
    bash_matchers = [m for m in pre_tool_use if m.get("matcher") == "Bash"]

    assert bash_matchers, "No Bash matcher in PreToolUse hooks"

    bash_hooks = bash_matchers[0].get("hooks", [])
    hook_commands = [h.get("command", "") for h in bash_hooks]

    playwright_hook = any("auto_playwright_setup.py" in cmd for cmd in hook_commands)
    assert playwright_hook, "auto_playwright_setup.py hook not registered"

    print("✓ auto_playwright_setup hook registered")


def test_confidence_rewards():
    """Test that playwright confidence rewards are defined"""
    sys.path.insert(0, "scripts/lib")
    from epistemology import CONFIDENCE_GAINS

    assert "use_playwright" in CONFIDENCE_GAINS, "use_playwright reward missing"
    assert "setup_playwright" in CONFIDENCE_GAINS, "setup_playwright reward missing"
    assert "browser_instead_requests" in CONFIDENCE_GAINS, "browser_instead_requests reward missing"

    assert CONFIDENCE_GAINS["use_playwright"] == 15, "Wrong use_playwright reward"
    assert CONFIDENCE_GAINS["setup_playwright"] == 20, "Wrong setup_playwright reward"
    assert CONFIDENCE_GAINS["browser_instead_requests"] == 25, "Wrong browser_instead_requests reward"

    print("✓ Confidence rewards defined correctly")


def test_claude_md_alias():
    """Test that CLAUDE.md has playwright alias"""
    claude_md = Path("CLAUDE.md")
    content = claude_md.read_text()

    assert 'playwright: "python3 scripts/ops/playwright.py"' in content, \
        "playwright alias missing from CLAUDE.md"

    print("✓ CLAUDE.md alias present")


def test_force_playwright_hook():
    """Test that force_playwright hook has updated messaging"""
    hook_file = Path(".claude/hooks/force_playwright.py")
    content = hook_file.read_text()

    assert "python3 scripts/ops/playwright.py --check" in content, \
        "force_playwright hook doesn't reference new script"
    assert "Confidence reward: +25%" in content, \
        "force_playwright hook missing confidence messaging"

    print("✓ force_playwright hook updated")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Testing Playwright Integration")
    print("=" * 60 + "\n")

    try:
        test_playwright_script()
        test_hook_registration()
        test_confidence_rewards()
        test_claude_md_alias()
        test_force_playwright_hook()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print("\nPlaywright integration complete:")
        print("  • playwright.py ops script ✓")
        print("  • auto_playwright_setup.py hook ✓")
        print("  • force_playwright.py hook updated ✓")
        print("  • Confidence rewards (+15/+20/+25) ✓")
        print("  • CLAUDE.md alias ✓")
        print("\nUsage:")
        print("  python3 scripts/ops/playwright.py --check")
        print("  python3 scripts/ops/playwright.py --setup")
        print("=" * 60 + "\n")

        sys.exit(0)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
