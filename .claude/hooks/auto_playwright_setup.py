#!/usr/bin/env python3
"""
Auto Playwright Setup Hook: Triggers playwright.py when browser tasks detected

Detects browser automation needs and ensures Playwright is set up autonomously.
Awards confidence for appropriate browser usage.
"""
import sys
import json
import subprocess
import os

# Load input
data = json.load(sys.stdin)
tool_name = data.get("tool_name", "")
tool_params = data.get("tool_input", {})

# Only trigger on Bash tool with browser-related commands
if tool_name != "Bash":
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
    sys.exit(0)

command = tool_params.get("command", "")

# Detect browser automation patterns
browser_patterns = [
    "from browser import",
    "get_browser_session",
    "playwright",
    "smart_dump",
    "take_screenshot",
]

needs_playwright = any(pattern in command for pattern in browser_patterns)

if not needs_playwright:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                }
            }
        )
    )
    sys.exit(0)

# Browser automation detected - verify Playwright is ready
try:
    # Find project root
    current = os.path.dirname(os.path.abspath(__file__))
    while current != "/":
        if os.path.exists(os.path.join(current, "scripts", "ops", "playwright.py")):
            project_root = current
            break
        current = os.path.dirname(current)
    else:
        # Can't find playwright.py, allow operation (will fail naturally)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                    }
                }
            )
        )
        sys.exit(0)

    playwright_script = os.path.join(project_root, "scripts", "ops", "playwright.py")

    # Check if Playwright is ready (--verify returns 0 if ready)
    result = subprocess.run(
        ["python3", playwright_script, "--verify"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    if result.returncode == 0:
        # Playwright ready, allow operation
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "additionalContext": (
                            "✅ Playwright ready for browser automation\n"
                            "Confidence boost: +15% (appropriate browser tool usage)"
                        ),
                    }
                }
            )
        )
        sys.exit(0)

    # Playwright not ready - auto-setup autonomously
    setup_result = subprocess.run(
        ["python3", playwright_script, "--autonomous"],
        capture_output=True,
        text=True,
        timeout=360,  # 6 minutes for browser download
    )

    if setup_result.returncode == 0:
        # Setup successful
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "additionalContext": (
                            "✅ Playwright auto-setup complete\n"
                            "Installed: Playwright package + Chromium browser\n"
                            "Browser automation now available\n"
                            "Confidence boost: +20% (proactive tool setup)"
                        ),
                    }
                }
            )
        )
        sys.exit(0)
    else:
        # Setup failed - warn but allow (will fail naturally with better error)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "additionalContext": (
                            "⚠️ Playwright auto-setup failed\n"
                            f"Error: {setup_result.stderr[:200]}\n\n"
                            "Manual setup required:\n"
                            "  python3 scripts/ops/playwright.py --setup"
                        ),
                    }
                }
            )
        )
        sys.exit(0)

except subprocess.TimeoutExpired:
    # Timeout during setup - warn but allow
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": (
                        "⚠️ Playwright setup timeout\n"
                        "Browser downloads can be slow on first install.\n"
                        "Try manual setup:\n"
                        "  python3 scripts/ops/playwright.py --setup"
                    ),
                }
            }
        )
    )
    sys.exit(0)

except Exception:
    # Unknown error - allow operation (fail naturally)
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                }
            }
        )
    )
    sys.exit(0)
