#!/usr/bin/env python3
"""
The Playwright Enforcer: Browser automation setup and verification tool

This script:
1. Checks if Playwright is installed
2. Auto-installs if missing (with user consent in non-autonomous mode)
3. Verifies browser binaries are available
4. Provides confidence boost when used appropriately
5. Can be triggered autonomously by hooks when browser tasks are detected
"""
import sys
import os
import subprocess

# Add .claude/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
_current = _script_dir
while _current != "/":
    if os.path.exists(os.path.join(_current, ".claude", "lib", "core.py")):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with .claude/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, ".claude", "lib"))

from core import setup_script, finalize, logger, handle_debug  # noqa: E402

# Check if playwright is available
try:
    from playwright.sync_api import sync_playwright  # noqa: F401
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def check_playwright_browsers():
    """Check if Playwright browsers are installed"""
    try:
        result = subprocess.run(
            ["playwright", "install", "--dry-run", "chromium"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # If dry-run shows no downloads needed, browsers are installed
        return "0 to download" in result.stdout or result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
        return False


def install_playwright_package():
    """Install playwright python package"""
    logger.info("Installing playwright python package...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "playwright"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error(f"Failed to install playwright: {result.stderr}")
            return False
        logger.info("✓ Playwright package installed successfully")
        return True
    except subprocess.TimeoutExpired:
        logger.error("Timeout during playwright installation")
        return False


def install_playwright_browsers():
    """Install Playwright browser binaries"""
    logger.info("Installing Playwright chromium browser...")
    try:
        result = subprocess.run(
            ["playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            logger.error(f"Failed to install chromium: {result.stderr}")
            return False
        logger.info("✓ Chromium browser installed successfully")
        return True
    except subprocess.TimeoutExpired:
        logger.error("Timeout during browser installation")
        return False


def check_playwright_python():
    """Check if playwright is installed as a Python package"""
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright is not installed")
        logger.error("Install with:")
        logger.error("  pip install playwright")
        logger.error("  playwright install chromium")
        return False
    return True


def verify_playwright_setup():
    """
    Verify complete Playwright setup

    Returns:
        tuple: (success: bool, message: str, status_code: int)
            status_code: 0=ready, 1=need_package, 2=need_browsers, 3=broken
    """
    # Check Python package
    if not PLAYWRIGHT_AVAILABLE:
        return (
            False,
            "Playwright Python package not installed",
            1,
        )

    # Check browsers
    if not check_playwright_browsers():
        return (
            False,
            "Playwright browsers not installed",
            2,
        )

    # All good
    return (
        True,
        "Playwright fully configured and ready",
        0,
    )


def auto_setup_playwright(autonomous=False):
    """
    Automatically set up Playwright if needed

    Args:
        autonomous: If True, install without prompts (for hook usage)

    Returns:
        bool: True if setup successful or already configured
    """
    success, message, status = verify_playwright_setup()

    if success:
        logger.info("✓ Playwright already configured")
        return True

    logger.warning(f"⚠️  {message}")

    # In autonomous mode, always install
    # In interactive mode, ask user
    if not autonomous:
        logger.info("\nPlaywright setup required for browser automation tasks.")
        logger.info("This will install:")
        if status == 1:
            logger.info("  • playwright Python package (~2 MB)")
            logger.info("  • Chromium browser binary (~150 MB)")
        elif status == 2:
            logger.info("  • Chromium browser binary (~150 MB)")

        response = input("\nProceed with installation? [Y/n]: ").strip().lower()
        if response and response != "y":
            logger.warning("Installation cancelled")
            return False

    # Install package if needed
    if status == 1:
        logger.info("\n📦 Installing Playwright package...")
        if not install_playwright_package():
            return False
        status = 2  # Now need browsers

    # Install browsers if needed
    if status == 2:
        logger.info("\n🌐 Installing browser binaries...")
        if not install_playwright_browsers():
            return False

    # Final verification
    success, message, status = verify_playwright_setup()
    if not success:
        logger.error(f"❌ Setup verification failed: {message}")
        return False

    logger.info("\n✅ Playwright setup complete!")
    return True


def main():
    parser = setup_script(
        "The Playwright Enforcer: Browser automation setup and verification"
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="Check status only (no installation)",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Auto-setup if needed (interactive)",
    )
    parser.add_argument(
        "--autonomous",
        action="store_true",
        help="Auto-setup without prompts (for hook usage)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify setup and exit with status code",
    )

    args = parser.parse_args()
    handle_debug(args)

    # Dry run mode
    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would check Playwright installation status")
        logger.info("Actions that would be performed:")
        logger.info("  1. Check if playwright Python package is installed")
        logger.info("  2. Check if chromium browser binaries are installed")
        if args.setup or args.autonomous:
            logger.info("  3. Install missing components if needed")
        finalize(success=True)

    # Check mode
    if args.check:
        success, message, status = verify_playwright_setup()
        print("\n" + "=" * 70)
        print("🎭 PLAYWRIGHT STATUS CHECK")
        print("=" * 70)

        if success:
            print("\n✅ Status: READY")
            print(f"   {message}")
            print("\n📚 Available via:")
            print("   from browser import get_browser_session, smart_dump")
            print("\n📖 Usage example:")
            print("   with get_browser_session() as (p, browser, page):")
            print("       page.goto('https://example.com')")
            print("       content = smart_dump(page)")
        else:
            print(f"\n❌ Status: {message}")
            if status == 1:
                print("\n🔧 To install:")
                print("   python3 .claude/ops/playwright.py --setup")
            elif status == 2:
                print("\n🔧 To complete setup:")
                print("   python3 .claude/ops/playwright.py --setup")

        print("=" * 70)
        sys.exit(status)

    # Verify mode (for automation)
    if args.verify:
        success, message, status = verify_playwright_setup()
        if success:
            logger.info(f"✓ {message}")
        else:
            logger.error(f"✗ {message}")
        sys.exit(status)

    # Setup modes
    if args.setup or args.autonomous:
        success = auto_setup_playwright(autonomous=args.autonomous)
        if success:
            logger.info("\n🎭 Playwright is ready for browser automation!")
            logger.info("\n📚 Import via:")
            logger.info("   from browser import get_browser_session, smart_dump")
        finalize(success=success)

    # Default: show status and suggest action
    success, message, status = verify_playwright_setup()

    print("\n" + "=" * 70)
    print("🎭 PLAYWRIGHT ENFORCER")
    print("=" * 70)

    if success:
        print(f"\n✅ {message}")
        print("\n📚 Ready to use browser automation via:")
        print("   from browser import get_browser_session, smart_dump")
        print("\n🔍 Check status anytime:")
        print("   python3 .claude/ops/playwright.py --check")
    else:
        print(f"\n⚠️  {message}")
        print("\n🔧 To auto-install:")
        print("   python3 .claude/ops/playwright.py --setup")
        print("\n🔍 To check status:")
        print("   python3 .claude/ops/playwright.py --check")

    print("=" * 70)
    sys.exit(status)


if __name__ == "__main__":
    main()
