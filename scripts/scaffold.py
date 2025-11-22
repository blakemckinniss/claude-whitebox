#!/usr/bin/env python3
"""
Script Scaffolder - Generates new scripts with Whitebox SDK standards built-in.

Usage:
    python3 scripts/scaffold.py scripts/<category>/<name>.py "Description of task"
    python3 scripts/scaffold.py scratch/tmp_test.py "Quick test script"
    python3 scripts/scaffold.py scratch/tmp_ui.py "Test UI" --template playwright
"""
import os
import argparse

TEMPLATE = '''#!/usr/bin/env python3
"""
{description}
"""
import sys
import os

# Add scripts/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
# Find project root by looking for 'scripts' directory
_current = _script_dir
while _current != '/':
    if os.path.exists(os.path.join(_current, 'scripts', 'lib', 'core.py')):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with scripts/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, 'scripts', 'lib'))
from core import setup_script, finalize, logger, handle_debug, check_dry_run


def main():
    parser = setup_script("{description}")

    # Add custom arguments here
    # parser.add_argument('--target', required=True, help="Target resource")
    # parser.add_argument('--count', type=int, default=10, help="Number of items")

    args = parser.parse_args()
    handle_debug(args)

    logger.info("Starting operation...")

    if args.dry_run:
        logger.warning("⚠️  DRY RUN MODE: No changes will be made")

    try:
        # ============================================================
        # YOUR LOGIC HERE
        # ============================================================

        # Example: Check before making changes
        # if check_dry_run(args, "delete all files"):
        #     return
        #
        # os.remove(file)

        result = "placeholder"
        logger.info(f"Result: {{result}}")

        # ============================================================

    except Exception as e:
        logger.error(f"Operation failed: {{e}}")
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
'''

PLAYWRIGHT_TEMPLATE = '''#!/usr/bin/env python3
"""
{description}
"""
import sys
import os

# Add scripts/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
# Find project root by looking for 'scripts' directory
_current = _script_dir
while _current != '/':
    if os.path.exists(os.path.join(_current, 'scripts', 'lib', 'core.py')):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with scripts/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, 'scripts', 'lib'))
from core import setup_script, finalize, logger, handle_debug
from browser import get_browser_session, smart_dump, take_screenshot


def main():
    parser = setup_script("{description}")

    # Add custom arguments here
    # parser.add_argument('--url', required=True, help="URL to navigate to")
    # parser.add_argument('--headless', action='store_true', help="Run in headless mode")

    args = parser.parse_args()
    handle_debug(args)

    logger.info("Starting browser automation...")

    if args.dry_run:
        logger.warning("⚠️  DRY RUN MODE: Would launch browser but not execute")
        finalize(success=True)

    try:
        with get_browser_session(headless=True) as (p, browser, page):
            # ============================================================
            # YOUR BROWSER AUTOMATION LOGIC HERE
            # ============================================================

            # Example: Navigate to a page
            # page.goto("https://example.com")

            # Example: Fill a form
            # page.fill("#username", "test")
            # page.fill("#password", "secret")
            # page.click("button[type=submit]")

            # Example: Wait for element
            # page.wait_for_selector(".dashboard", timeout=5000)

            # Example: Get page content
            # content = smart_dump(page)
            # logger.info(f"Page content: {{content[:200]}}...")

            # Example: Take screenshot
            # screenshot_path = take_screenshot(page, "result")
            # logger.info(f"Screenshot saved: {{screenshot_path}}")

            logger.info("Browser automation completed")

            # ============================================================

    except Exception as e:
        logger.error(f"Browser automation failed: {{e}}")
        # Screenshot is automatically taken by error handlers
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
'''


def main():
    parser = argparse.ArgumentParser(
        description="Script Scaffolder - Generates new scripts with Whitebox SDK standards",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/scaffold.py scripts/db/query.py "Query database"
  python3 scripts/scaffold.py scratch/tmp_test.py "Test something"
  python3 scripts/scaffold.py scratch/tmp_ui.py "Test login" --template playwright
        """,
    )

    parser.add_argument("path", help="Path to the new script file")
    parser.add_argument("description", nargs="+", help="Description of the script")
    parser.add_argument(
        "--template",
        choices=["standard", "playwright"],
        default="standard",
        help="Template to use (standard or playwright)",
    )

    args = parser.parse_args()

    path = args.path
    description = " ".join(args.description)
    template_type = args.template

    # Select template
    if template_type == "playwright":
        template = PLAYWRIGHT_TEMPLATE
        print("🎭 Using Playwright template")
    else:
        template = TEMPLATE

    # Ensure directory exists
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    # Generate content
    content = template.format(description=description)

    # Write file
    with open(path, "w") as f:
        f.write(content)

    # Make executable
    os.chmod(path, 0o755)

    print(f"✅ Scaffolded new script at: {path}")
    print(f"📝 Description: {description}")
    print()
    print("Next steps:")
    print(f"  1. Edit {path} and add your logic")
    print(f"  2. Run: python3 {path} --dry-run")
    print(f"  3. Run: python3 {path}")


if __name__ == "__main__":
    main()
