"""
Browser automation utilities using Playwright.

This module provides a simplified interface for browser automation tasks,
making Playwright the path of least resistance for UI interactions.
"""

import os
from contextlib import contextmanager

# Check if playwright is available
try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from .core import logger


def check_playwright():
    """Check if playwright is installed and provide installation instructions."""
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright is not installed")
        logger.error("Install with:")
        logger.error("  pip install playwright")
        logger.error("  playwright install chromium")
        logger.error("")
        logger.error("Or if using system-managed Python:")
        logger.error("  apt-get install python3-playwright")
        logger.error("  playwright install chromium")
        return False
    return True


@contextmanager
def get_browser_session(headless=True, viewport=None, user_agent=None):
    """
    Context manager that yields (playwright, browser, page).

    Args:
        headless: Whether to run browser in headless mode (default: True)
        viewport: Dict with 'width' and 'height' (default: 1280x720)
        user_agent: Custom user agent string (default: Whitebox Agent)

    Yields:
        tuple: (playwright, browser, page)

    Example:
        with get_browser_session() as (p, browser, page):
            page.goto("https://example.com")
            print(smart_dump(page))
    """
    if not check_playwright():
        raise ImportError("Playwright is not installed")

    viewport = viewport or {"width": 1280, "height": 720}
    user_agent = user_agent or "Mozilla/5.0 (Whitebox Agent)"

    p = sync_playwright().start()
    browser = None
    page = None

    try:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport=viewport, user_agent=user_agent)
        page = context.new_page()

        logger.info(f"🎭 Browser session started (headless={headless})")
        yield p, browser, page

    finally:
        if page:
            page.close()
        if browser:
            browser.close()
        p.stop()
        logger.info("🎭 Browser session closed")


def smart_dump(page, max_length=5000):
    """
    Converts page content to a clean LLM-readable format.

    This function:
    1. Waits for network idle to ensure page is fully loaded
    2. Extracts visible text only (no HTML tags)
    3. Truncates to reasonable length for token efficiency

    Args:
        page: Playwright page object
        max_length: Maximum characters to return (default: 5000)

    Returns:
        str: Clean text representation of the page

    Example:
        with get_browser_session() as (p, browser, page):
            page.goto("https://example.com")
            content = smart_dump(page)
            print(content)
    """
    # Wait for network idle to ensure hydration/dynamic content
    try:
        page.wait_for_load_state("networkidle", timeout=3000)
    except Exception as e:
        logger.debug(f"Network idle timeout: {e}")
        # Proceed anyway if timeout

    title = page.title()
    url = page.url

    # Get visible text only (no HTML)
    text = page.evaluate("document.body.innerText")

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "..."

    output = f"--- PAGE: {title} ---\n"
    output += f"URL: {url}\n\n"
    output += text

    return output


def take_screenshot(page, name="state", directory="scratch"):
    """
    Take a screenshot of the current page state.

    Args:
        page: Playwright page object
        name: Filename without extension (default: "state")
        directory: Directory to save screenshot (default: "scratch")

    Returns:
        str: Path to saved screenshot

    Example:
        with get_browser_session() as (p, browser, page):
            page.goto("https://example.com")
            screenshot_path = take_screenshot(page, "homepage")
            print(f"Screenshot saved to {screenshot_path}")
    """
    # Ensure directory exists
    os.makedirs(directory, exist_ok=True)

    path = os.path.join(directory, f"{name}.png")
    page.screenshot(path=path, full_page=True)
    logger.info(f"📸 Screenshot saved to {path}")

    return path


def snapshot_on_error(func):
    """
    Decorator that takes a screenshot if the wrapped function fails.

    Usage:
        @snapshot_on_error
        def test_login(page):
            page.fill("#username", "test")
            page.fill("#password", "secret")
            page.click("button[type=submit]")

    If the function raises an exception, a screenshot will be saved
    to scratch/error.png before re-raising the exception.
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Try to find page object in args
            page = None
            for arg in args:
                if hasattr(arg, "screenshot"):
                    page = arg
                    break

            if page:
                try:
                    take_screenshot(page, "error")
                    logger.error(
                        "❌ Error occurred - screenshot saved to scratch/error.png"
                    )
                except Exception as screenshot_error:
                    logger.debug(f"Could not save error screenshot: {screenshot_error}")

            raise e

    return wrapper


def wait_for_selector(page, selector, timeout=5000, state="visible"):
    """
    Wait for a selector with better error messages.

    Args:
        page: Playwright page object
        selector: CSS selector to wait for
        timeout: Timeout in milliseconds (default: 5000)
        state: Element state to wait for (default: "visible")

    Returns:
        ElementHandle: The found element

    Raises:
        TimeoutError: If element not found within timeout
    """
    try:
        return page.wait_for_selector(selector, timeout=timeout, state=state)
    except Exception as e:
        logger.error(f"Could not find selector: {selector}")
        logger.error(f"Current URL: {page.url}")
        take_screenshot(page, "selector_not_found")
        raise TimeoutError(f"Selector '{selector}' not found after {timeout}ms") from e


def safe_fill(page, selector, value, timeout=5000):
    """
    Fill an input field with better error handling.

    Args:
        page: Playwright page object
        selector: CSS selector for the input field
        value: Value to fill
        timeout: Timeout in milliseconds (default: 5000)
    """
    try:
        wait_for_selector(page, selector, timeout=timeout)
        page.fill(selector, value)
        logger.debug(f"Filled {selector} with value")
    except Exception:
        logger.error(f"Could not fill {selector}")
        take_screenshot(page, "fill_error")
        raise


def safe_click(page, selector, timeout=5000):
    """
    Click an element with better error handling.

    Args:
        page: Playwright page object
        selector: CSS selector for the element
        timeout: Timeout in milliseconds (default: 5000)
    """
    try:
        wait_for_selector(page, selector, timeout=timeout)
        page.click(selector)
        logger.debug(f"Clicked {selector}")
    except Exception:
        logger.error(f"Could not click {selector}")
        take_screenshot(page, "click_error")
        raise
