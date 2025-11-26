#!/usr/bin/env python3
"""
Browser Debugger CLI (bdg): Direct Chrome DevTools Protocol access for AI agents.

Inspired by https://github.com/szymdzum/browser-debugger-cli
Implemented in Python for the Whitebox toolkit.

Features:
- Complete CDP access (all 53 domains, 644+ methods)
- Self-discovery: --list, --search, --describe
- Token-efficient: selective queries instead of full dumps
- Unix composable: works with pipes and jq
"""
import sys
import os
import json
import asyncio
import subprocess
import signal
import time
from pathlib import Path
from typing import Optional
from urllib.request import urlopen
from urllib.error import URLError

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

# Constants
DEFAULT_CDP_PORT = 9222
STATE_FILE = Path("/tmp/bdg_state.json")
PID_FILE = Path("/tmp/bdg_chrome.pid")
CDP_DOMAINS_CACHE = Path("/tmp/bdg_domains.json")

# Chrome detection
CHROME_PATHS = [
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
]

# CDP Domain metadata (subset - full list has 53 domains)
CDP_DOMAINS = {
    "Accessibility": {"methods": ["disable", "enable", "getFullAXTree", "getPartialAXTree", "queryAXTree"]},
    "Browser": {"methods": ["close", "getVersion", "getWindowBounds", "setWindowBounds"]},
    "Console": {"methods": ["clearMessages", "disable", "enable"]},
    "DOM": {"methods": ["describeNode", "disable", "enable", "focus", "getAttributes", "getBoxModel",
                        "getDocument", "getNodeForLocation", "getOuterHTML", "querySelector",
                        "querySelectorAll", "removeNode", "setAttributeValue", "setNodeValue"]},
    "Emulation": {"methods": ["clearDeviceMetricsOverride", "setDeviceMetricsOverride",
                              "setGeolocationOverride", "setUserAgentOverride"]},
    "Fetch": {"methods": ["continueRequest", "disable", "enable", "failRequest", "fulfillRequest"]},
    "Input": {"methods": ["dispatchKeyEvent", "dispatchMouseEvent", "dispatchTouchEvent",
                          "insertText", "setIgnoreInputEvents"]},
    "Log": {"methods": ["clear", "disable", "enable", "startViolationsReport", "stopViolationsReport"]},
    "Network": {"methods": ["clearBrowserCache", "clearBrowserCookies", "deleteCookies", "disable",
                            "enable", "getAllCookies", "getCookies", "getResponseBody",
                            "setBlockedURLs", "setCacheDisabled", "setCookie", "setExtraHTTPHeaders"]},
    "Page": {"methods": ["addScriptToEvaluateOnNewDocument", "bringToFront", "captureScreenshot",
                         "close", "createIsolatedWorld", "disable", "enable", "getFrameTree",
                         "getLayoutMetrics", "getNavigationHistory", "navigate", "navigateToHistoryEntry",
                         "printToPDF", "reload", "setDocumentContent", "stopLoading"]},
    "Performance": {"methods": ["disable", "enable", "getMetrics", "setTimeDomain"]},
    "Profiler": {"methods": ["disable", "enable", "getBestEffortCoverage", "start", "stop"]},
    "Runtime": {"methods": ["awaitPromise", "callFunctionOn", "compileScript", "disable", "enable",
                            "evaluate", "getProperties", "globalLexicalScopeNames", "runScript"]},
    "Security": {"methods": ["disable", "enable", "setIgnoreCertificateErrors"]},
    "Storage": {"methods": ["clearCookies", "clearDataForOrigin", "getCookies", "getStorageKeyForFrame",
                            "getUsageAndQuota", "setCookies", "trackCacheStorageForOrigin"]},
    "Target": {"methods": ["activateTarget", "attachToTarget", "closeTarget", "createBrowserContext",
                           "createTarget", "detachFromTarget", "disposeBrowserContext", "getTargetInfo",
                           "getTargets", "setAutoAttach", "setDiscoverTargets"]},
}


def find_chrome() -> Optional[str]:
    """Find Chrome/Chromium binary"""
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    # Try which
    for name in ["google-chrome", "chromium", "chromium-browser"]:
        result = subprocess.run(["which", name], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    return None


def is_cdp_available(port: int = DEFAULT_CDP_PORT) -> bool:
    """Check if CDP endpoint is responding"""
    try:
        with urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as resp:
            return resp.status == 200
    except (URLError, OSError):
        return False


def get_cdp_targets(port: int = DEFAULT_CDP_PORT) -> list:
    """Get available CDP targets (tabs/pages)"""
    try:
        with urlopen(f"http://127.0.0.1:{port}/json", timeout=5) as resp:
            return json.loads(resp.read().decode())
    except (URLError, OSError, json.JSONDecodeError):
        return []


def get_cdp_version(port: int = DEFAULT_CDP_PORT) -> dict:
    """Get browser version info via CDP"""
    try:
        with urlopen(f"http://127.0.0.1:{port}/json/version", timeout=5) as resp:
            return json.loads(resp.read().decode())
    except (URLError, OSError, json.JSONDecodeError):
        return {}


def save_state(data: dict):
    """Persist daemon state"""
    STATE_FILE.write_text(json.dumps(data, indent=2))


def load_state() -> dict:
    """Load daemon state"""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {}


async def cdp_call(ws_url: str, method: str, params: dict = None, timeout: float = 30) -> dict:
    """Execute a CDP method via WebSocket"""
    try:
        import websockets
    except ImportError:
        logger.error("websockets library required: pip install websockets")
        return {"error": "websockets not installed"}

    msg_id = int(time.time() * 1000) % 100000
    message = {"id": msg_id, "method": method}
    if params:
        message["params"] = params

    try:
        async with websockets.connect(ws_url, close_timeout=5) as ws:
            await ws.send(json.dumps(message))

            # Wait for response with matching id
            start = time.time()
            while time.time() - start < timeout:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    data = json.loads(response)
                    if data.get("id") == msg_id:
                        if "error" in data:
                            return {"error": data["error"]}
                        return data.get("result", {})
                except asyncio.TimeoutError:
                    break
            return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}


def run_cdp(ws_url: str, method: str, params: dict = None) -> dict:
    """Synchronous wrapper for CDP calls"""
    return asyncio.run(cdp_call(ws_url, method, params))


# ============================================================================
# Commands
# ============================================================================

def cmd_start(args):
    """Start Chrome with CDP enabled"""
    chrome = find_chrome()
    if not chrome:
        logger.error("Chrome/Chromium not found")
        finalize(success=False)

    port = args.port or DEFAULT_CDP_PORT

    # Check if already running
    if is_cdp_available(port):
        version = get_cdp_version(port)
        logger.info(f"CDP already available on port {port}")
        print(json.dumps({
            "status": "already_running",
            "port": port,
            "browser": version.get("Browser", "unknown"),
        }))
        return

    # Launch Chrome
    chrome_args = [
        chrome,
        f"--remote-debugging-port={port}",
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-sync",
        "--disable-translate",
        "--mute-audio",
        f"--user-data-dir=/tmp/bdg-chrome-profile-{port}",
    ]

    if args.url:
        chrome_args.append(args.url)
    else:
        chrome_args.append("about:blank")

    logger.info(f"Starting Chrome on port {port}...")

    proc = subprocess.Popen(
        chrome_args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    # Save PID
    PID_FILE.write_text(str(proc.pid))

    # Wait for CDP to be available
    for _ in range(30):
        if is_cdp_available(port):
            version = get_cdp_version(port)
            save_state({"pid": proc.pid, "port": port, "started": time.time()})
            logger.info(f"✓ Chrome started (PID {proc.pid})")
            print(json.dumps({
                "status": "started",
                "pid": proc.pid,
                "port": port,
                "browser": version.get("Browser", "unknown"),
            }))
            return
        time.sleep(0.2)

    logger.error("Chrome failed to start CDP endpoint")
    proc.terminate()
    finalize(success=False)


def cmd_stop(args):
    """Stop the Chrome instance"""
    state = load_state()
    pid = state.get("pid")

    if not pid:
        # Try to find by PID file
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())

    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"✓ Stopped Chrome (PID {pid})")
            print(json.dumps({"status": "stopped", "pid": pid}))
        except ProcessLookupError:
            logger.warning(f"Process {pid} not found (already stopped?)")
            print(json.dumps({"status": "not_running"}))

        # Cleanup
        STATE_FILE.unlink(missing_ok=True)
        PID_FILE.unlink(missing_ok=True)
    else:
        logger.info("No Chrome instance to stop")
        print(json.dumps({"status": "not_running"}))


def cmd_status(args):
    """Check CDP status"""
    port = args.port or DEFAULT_CDP_PORT
    state = load_state()

    if is_cdp_available(port):
        version = get_cdp_version(port)
        targets = get_cdp_targets(port)

        result = {
            "status": "running",
            "port": port,
            "pid": state.get("pid"),
            "browser": version.get("Browser"),
            "protocol_version": version.get("Protocol-Version"),
            "targets": len(targets),
            "pages": [t.get("title", t.get("url", ""))[:50] for t in targets if t.get("type") == "page"],
        }
    else:
        result = {"status": "stopped", "port": port}

    print(json.dumps(result, indent=2))


def cmd_cdp(args):
    """Execute raw CDP method"""
    port = args.port or DEFAULT_CDP_PORT

    if not is_cdp_available(port):
        logger.error(f"CDP not available on port {port}. Run: bdg start")
        finalize(success=False)

    # Get target
    targets = get_cdp_targets(port)
    pages = [t for t in targets if t.get("type") == "page"]

    if not pages:
        logger.error("No page targets available")
        finalize(success=False)

    ws_url = pages[0].get("webSocketDebuggerUrl")
    if not ws_url:
        logger.error("No WebSocket URL for target")
        finalize(success=False)

    # Parse params
    params = None
    if args.params:
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON params: {e}")
            finalize(success=False)

    # Execute
    result = run_cdp(ws_url, args.method, params)

    if "error" in result:
        logger.error(f"CDP error: {result['error']}")
        print(json.dumps(result, indent=2))
        finalize(success=False)

    print(json.dumps(result, indent=2))


def cmd_dom(args):
    """DOM operations"""
    port = args.port or DEFAULT_CDP_PORT

    if not is_cdp_available(port):
        logger.error(f"CDP not available on port {port}")
        finalize(success=False)

    targets = get_cdp_targets(port)
    pages = [t for t in targets if t.get("type") == "page"]
    if not pages:
        logger.error("No page targets")
        finalize(success=False)

    ws_url = pages[0].get("webSocketDebuggerUrl")

    if args.dom_cmd == "query":
        # Enable DOM first
        run_cdp(ws_url, "DOM.enable")

        # Get document
        doc = run_cdp(ws_url, "DOM.getDocument", {"depth": -1})
        root_id = doc.get("root", {}).get("nodeId")

        if not root_id:
            logger.error("Failed to get document root")
            finalize(success=False)

        # Query
        result = run_cdp(ws_url, "DOM.querySelectorAll", {
            "nodeId": root_id,
            "selector": args.selector,
        })

        node_ids = result.get("nodeIds", [])
        nodes = []

        for nid in node_ids[:args.limit]:
            html = run_cdp(ws_url, "DOM.getOuterHTML", {"nodeId": nid})
            nodes.append({
                "nodeId": nid,
                "html": html.get("outerHTML", "")[:500],  # Truncate for token efficiency
            })

        print(json.dumps({
            "selector": args.selector,
            "count": len(node_ids),
            "nodes": nodes,
        }, indent=2))

    elif args.dom_cmd == "html":
        run_cdp(ws_url, "DOM.enable")
        doc = run_cdp(ws_url, "DOM.getDocument", {"depth": -1})
        root_id = doc.get("root", {}).get("nodeId")

        if root_id:
            html = run_cdp(ws_url, "DOM.getOuterHTML", {"nodeId": root_id})
            # Token-efficient: truncate if needed
            content = html.get("outerHTML", "")
            if len(content) > 50000 and not args.full:
                content = content[:50000] + "\n... [truncated, use --full for complete]"
            print(content)
        else:
            logger.error("Failed to get document")
            finalize(success=False)


def cmd_network(args):
    """Network operations"""
    port = args.port or DEFAULT_CDP_PORT

    if not is_cdp_available(port):
        logger.error(f"CDP not available on port {port}")
        finalize(success=False)

    targets = get_cdp_targets(port)
    pages = [t for t in targets if t.get("type") == "page"]
    if not pages:
        logger.error("No page targets")
        finalize(success=False)

    ws_url = pages[0].get("webSocketDebuggerUrl")

    if args.net_cmd == "cookies":
        result = run_cdp(ws_url, "Network.getAllCookies")
        cookies = result.get("cookies", [])
        print(json.dumps({"count": len(cookies), "cookies": cookies}, indent=2))

    elif args.net_cmd == "clear-cache":
        run_cdp(ws_url, "Network.clearBrowserCache")
        print(json.dumps({"status": "cache_cleared"}))


def cmd_page(args):
    """Page operations"""
    port = args.port or DEFAULT_CDP_PORT

    if not is_cdp_available(port):
        logger.error(f"CDP not available on port {port}")
        finalize(success=False)

    targets = get_cdp_targets(port)
    pages = [t for t in targets if t.get("type") == "page"]
    if not pages:
        logger.error("No page targets")
        finalize(success=False)

    ws_url = pages[0].get("webSocketDebuggerUrl")

    if args.page_cmd == "navigate":
        result = run_cdp(ws_url, "Page.navigate", {"url": args.url})
        print(json.dumps(result, indent=2))

    elif args.page_cmd == "screenshot":
        result = run_cdp(ws_url, "Page.captureScreenshot", {
            "format": args.format or "png",
            "quality": args.quality or 80,
        })

        if "data" in result:
            import base64
            img_data = base64.b64decode(result["data"])
            output = args.output or f"screenshot.{args.format or 'png'}"
            Path(output).write_bytes(img_data)
            print(json.dumps({"status": "saved", "file": output, "size": len(img_data)}))
        else:
            logger.error("Screenshot failed")
            print(json.dumps(result))
            finalize(success=False)

    elif args.page_cmd == "pdf":
        result = run_cdp(ws_url, "Page.printToPDF", {
            "printBackground": True,
            "preferCSSPageSize": True,
        })

        if "data" in result:
            import base64
            pdf_data = base64.b64decode(result["data"])
            output = args.output or "page.pdf"
            Path(output).write_bytes(pdf_data)
            print(json.dumps({"status": "saved", "file": output, "size": len(pdf_data)}))
        else:
            logger.error("PDF generation failed")
            finalize(success=False)

    elif args.page_cmd == "reload":
        result = run_cdp(ws_url, "Page.reload")
        print(json.dumps({"status": "reloaded"}))


def cmd_eval(args):
    """Evaluate JavaScript"""
    port = args.port or DEFAULT_CDP_PORT

    if not is_cdp_available(port):
        logger.error(f"CDP not available on port {port}")
        finalize(success=False)

    targets = get_cdp_targets(port)
    pages = [t for t in targets if t.get("type") == "page"]
    if not pages:
        logger.error("No page targets")
        finalize(success=False)

    ws_url = pages[0].get("webSocketDebuggerUrl")

    result = run_cdp(ws_url, "Runtime.evaluate", {
        "expression": args.expression,
        "returnByValue": True,
        "awaitPromise": args.await_promise,
    })

    if "exceptionDetails" in result:
        logger.error("Evaluation error")
        print(json.dumps(result["exceptionDetails"], indent=2))
        finalize(success=False)

    print(json.dumps(result.get("result", {}), indent=2))


def cmd_list(args):
    """List CDP domains and methods"""
    if args.domain:
        domain = args.domain
        if domain not in CDP_DOMAINS:
            # Fuzzy match
            matches = [d for d in CDP_DOMAINS if d.lower().startswith(domain.lower())]
            if matches:
                domain = matches[0]
            else:
                logger.error(f"Unknown domain: {args.domain}")
                logger.info(f"Available: {', '.join(sorted(CDP_DOMAINS.keys()))}")
                finalize(success=False)

        methods = CDP_DOMAINS[domain]["methods"]
        print(f"\n{domain} ({len(methods)} methods):")
        for m in sorted(methods):
            print(f"  • {domain}.{m}")
    else:
        print(f"\nCDP Domains ({len(CDP_DOMAINS)} available):\n")
        for domain in sorted(CDP_DOMAINS.keys()):
            count = len(CDP_DOMAINS[domain]["methods"])
            print(f"  {domain:<20} ({count} methods)")
        print("\nUse: bdg --list <domain> for method details")


def cmd_search(args):
    """Search CDP methods"""
    pattern = args.pattern.lower()
    matches = []

    for domain, info in CDP_DOMAINS.items():
        for method in info["methods"]:
            full_name = f"{domain}.{method}"
            if pattern in full_name.lower():
                matches.append(full_name)

    if matches:
        print(f"\nMethods matching '{args.pattern}':\n")
        for m in sorted(matches):
            print(f"  • {m}")
        print(f"\n({len(matches)} matches)")
    else:
        logger.warning(f"No methods matching '{args.pattern}'")


def cmd_describe(args):
    """Describe a CDP method (basic info)"""
    method = args.method

    if "." not in method:
        logger.error("Method must be in format: Domain.method")
        finalize(success=False)

    domain, method_name = method.split(".", 1)

    if domain not in CDP_DOMAINS:
        logger.error(f"Unknown domain: {domain}")
        finalize(success=False)

    if method_name not in CDP_DOMAINS[domain]["methods"]:
        logger.error(f"Unknown method: {method}")
        logger.info(f"Available in {domain}: {', '.join(CDP_DOMAINS[domain]['methods'])}")
        finalize(success=False)

    # Basic description (full schema would require fetching CDP protocol.json)
    print(f"\n{method}")
    print("=" * len(method))
    print(f"Domain: {domain}")
    print("\nUsage:")
    print(f"  bdg cdp {method} --params '{{...}}'")
    print("\nFor full parameters, see:")
    print(f"  https://chromedevtools.github.io/devtools-protocol/tot/{domain}/#method-{method_name}")


def main():
    parser = setup_script(
        "Browser Debugger CLI: Direct Chrome DevTools Protocol access"
    )

    # Global options
    parser.add_argument("--port", "-p", type=int, help=f"CDP port (default: {DEFAULT_CDP_PORT})")
    parser.add_argument("--json", action="store_true", help="Force JSON output")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # start
    p_start = subparsers.add_parser("start", help="Start Chrome with CDP")
    p_start.add_argument("--url", help="Initial URL to load")

    # stop
    subparsers.add_parser("stop", help="Stop Chrome instance")

    # status
    subparsers.add_parser("status", help="Check CDP status")

    # cdp (raw)
    p_cdp = subparsers.add_parser("cdp", help="Execute raw CDP method")
    p_cdp.add_argument("method", help="CDP method (e.g., Page.navigate)")
    p_cdp.add_argument("--params", help="JSON parameters")

    # dom
    p_dom = subparsers.add_parser("dom", help="DOM operations")
    dom_sub = p_dom.add_subparsers(dest="dom_cmd")

    p_dom_query = dom_sub.add_parser("query", help="Query DOM with selector")
    p_dom_query.add_argument("selector", help="CSS selector")
    p_dom_query.add_argument("--limit", type=int, default=10, help="Max results")

    p_dom_html = dom_sub.add_parser("html", help="Get page HTML")
    p_dom_html.add_argument("--full", action="store_true", help="Don't truncate")

    # network
    p_net = subparsers.add_parser("network", help="Network operations")
    net_sub = p_net.add_subparsers(dest="net_cmd")
    net_sub.add_parser("cookies", help="Get all cookies")
    net_sub.add_parser("clear-cache", help="Clear browser cache")

    # page
    p_page = subparsers.add_parser("page", help="Page operations")
    page_sub = p_page.add_subparsers(dest="page_cmd")

    p_nav = page_sub.add_parser("navigate", help="Navigate to URL")
    p_nav.add_argument("url", help="URL to navigate to")

    p_ss = page_sub.add_parser("screenshot", help="Capture screenshot")
    p_ss.add_argument("--output", "-o", help="Output file")
    p_ss.add_argument("--format", choices=["png", "jpeg", "webp"], default="png")
    p_ss.add_argument("--quality", type=int, default=80, help="JPEG/WebP quality")

    p_pdf = page_sub.add_parser("pdf", help="Generate PDF")
    p_pdf.add_argument("--output", "-o", help="Output file")

    page_sub.add_parser("reload", help="Reload page")

    # eval
    p_eval = subparsers.add_parser("eval", help="Evaluate JavaScript")
    p_eval.add_argument("expression", help="JavaScript expression")
    p_eval.add_argument("--await", dest="await_promise", action="store_true", help="Await promise")

    # Discovery commands
    p_list = subparsers.add_parser("list", help="List CDP domains/methods")
    p_list.add_argument("domain", nargs="?", help="Domain to list methods for")

    p_search = subparsers.add_parser("search", help="Search CDP methods")
    p_search.add_argument("pattern", help="Search pattern")

    p_desc = subparsers.add_parser("describe", help="Describe CDP method")
    p_desc.add_argument("method", help="Method name (Domain.method)")

    args = parser.parse_args()
    handle_debug(args)

    # Route commands
    if args.command == "start":
        cmd_start(args)
    elif args.command == "stop":
        cmd_stop(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "cdp":
        cmd_cdp(args)
    elif args.command == "dom":
        if not args.dom_cmd:
            parser.parse_args(["dom", "--help"])
        cmd_dom(args)
    elif args.command == "network":
        if not args.net_cmd:
            parser.parse_args(["network", "--help"])
        cmd_network(args)
    elif args.command == "page":
        if not args.page_cmd:
            parser.parse_args(["page", "--help"])
        cmd_page(args)
    elif args.command == "eval":
        cmd_eval(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "describe":
        cmd_describe(args)
    else:
        parser.print_help()
        print("\nQuick start:")
        print("  bdg start                    # Start Chrome with CDP")
        print("  bdg page navigate https://example.com")
        print("  bdg dom query 'h1'           # Query DOM")
        print("  bdg eval 'document.title'    # Run JavaScript")
        print("  bdg stop                     # Stop Chrome")

    finalize(success=True)


if __name__ == "__main__":
    main()
