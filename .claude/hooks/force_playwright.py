#!/usr/bin/env python3
"""
Force Playwright Hook: Prevents using requests/BS4 for UI tasks.

This hook detects when you're about to perform browser/UI automation
and ensures you use the Whitebox Browser SDK (Playwright) instead of
lazy text-based approaches (requests + BeautifulSoup).
"""
import sys
import json

# Load input
data = json.load(sys.stdin)
prompt = data.get("prompt", "").lower()

# Words implying UI interaction
ui_triggers = [
    "click",
    "login",
    "fill form",
    "screenshot",
    "render",
    "e2e",
    "selenium",
    "puppeteer",
    "test ui",
    "browser",
    "headless",
    "javascript",
    "react",
    "vue",
    "angular",
    "dynamic content",
]

# The lazy way (text-based scraping)
lazy_triggers = ["requests", "beautifulsoup", "bs4", "urllib", "httpx"]

wants_ui = any(t in prompt for t in ui_triggers)
wants_lazy = any(t in prompt for t in lazy_triggers)

if wants_ui and wants_lazy:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": (
                        "⚠️ PROTOCOL VIOLATION: Do not use requests/BS4 for UI tasks.\n"
                        "Dynamic sites require browser automation.\n\n"
                        "✅ REQUIRED ACTIONS:\n"
                        "1. Ensure Playwright is set up:\n"
                        "   python3 scripts/ops/playwright.py --check\n\n"
                        "2. Use the Whitebox Browser SDK:\n"
                        "   from browser import get_browser_session, smart_dump\n"
                        "   with get_browser_session() as (p, browser, page):\n"
                        "       page.goto('https://example.com')\n"
                        "       content = smart_dump(page)\n\n"
                        "3. Or scaffold a Playwright script:\n"
                        "   python3 scripts/scaffold.py scratch/browser_task.py 'Task' --template playwright\n\n"
                        "Why Playwright > requests:\n"
                        "- CSRF tokens require browser sessions\n"
                        "- JavaScript rendering needs real browser\n"
                        "- Login flows depend on cookies/localStorage\n"
                        "- requests.get() only works for static HTML\n\n"
                        "Confidence reward: +25% for using browser instead of requests"
                    ),
                }
            }
        )
    )
    sys.exit(0)

# No warning needed
print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit"}}))
sys.exit(0)
