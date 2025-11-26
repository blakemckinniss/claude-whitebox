#!/usr/bin/env python3
"""
The Firecrawler: Scrape and crawl websites using Firecrawl API
Returns clean markdown/HTML/JSON from any webpage.
"""
import sys
import os
import json
import requests

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

BASE_URL = "https://api.firecrawl.dev/v2"


def scrape_url(api_key: str, url: str, formats: list = None, only_main: bool = True,
               wait_for: int = 0, timeout: int = 30000) -> dict:
    """Scrape a single URL and return content."""
    payload = {
        "url": url,
        "onlyMainContent": only_main,
        "waitFor": wait_for,
        "timeout": timeout,
    }
    if formats:
        payload["formats"] = formats

    response = requests.post(
        f"{BASE_URL}/scrape",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout // 1000 + 10,  # Convert ms to s, add buffer
    )
    response.raise_for_status()
    return response.json()


def start_crawl(api_key: str, url: str, limit: int = 10, include_paths: list = None,
                exclude_paths: list = None, max_depth: int = None) -> dict:
    """Start an async crawl job."""
    payload = {
        "url": url,
        "limit": limit,
    }
    if include_paths:
        payload["includePaths"] = include_paths
    if exclude_paths:
        payload["excludePaths"] = exclude_paths
    if max_depth:
        payload["maxDiscoveryDepth"] = max_depth

    response = requests.post(
        f"{BASE_URL}/crawl",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_crawl_status(api_key: str, crawl_id: str) -> dict:
    """Check status of a crawl job."""
    response = requests.get(
        f"{BASE_URL}/crawl/{crawl_id}",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main():
    parser = setup_script(
        "The Firecrawler: Scrape and crawl websites using Firecrawl API"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Scrape subcommand
    scrape_parser = subparsers.add_parser("scrape", help="Scrape a single URL")
    scrape_parser.add_argument("url", help="URL to scrape")
    scrape_parser.add_argument(
        "--format", "-f",
        action="append",
        dest="formats",
        choices=["markdown", "html", "rawHtml", "links", "screenshot"],
        help="Output format(s) (can specify multiple)",
    )
    scrape_parser.add_argument(
        "--full-page",
        action="store_true",
        help="Include headers, footers, nav (default: main content only)",
    )
    scrape_parser.add_argument(
        "--wait",
        type=int,
        default=0,
        help="Wait time in ms for JS to load (default: 0)",
    )
    scrape_parser.add_argument(
        "--timeout",
        type=int,
        default=30000,
        help="Timeout in ms (default: 30000)",
    )
    scrape_parser.add_argument(
        "--output", "-o",
        help="Save output to file (JSON format)",
    )

    # Crawl subcommand
    crawl_parser = subparsers.add_parser("crawl", help="Crawl a website")
    crawl_parser.add_argument("url", help="Base URL to crawl")
    crawl_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Maximum pages to crawl (default: 10)",
    )
    crawl_parser.add_argument(
        "--depth",
        type=int,
        help="Maximum crawl depth",
    )
    crawl_parser.add_argument(
        "--include",
        action="append",
        dest="include_paths",
        help="URL patterns to include (regex)",
    )
    crawl_parser.add_argument(
        "--exclude",
        action="append",
        dest="exclude_paths",
        help="URL patterns to exclude (regex)",
    )

    # Status subcommand
    status_parser = subparsers.add_parser("status", help="Check crawl job status")
    status_parser.add_argument("crawl_id", help="Crawl job ID")

    args = parser.parse_args()
    handle_debug(args)

    if not args.command:
        parser.print_help()
        finalize(success=False, message="No command specified")
        return

    # Dry-run handling
    if args.dry_run:
        logger.warning(f"DRY RUN: Would execute '{args.command}' command")
        if args.command == "scrape":
            logger.info(f"  URL: {args.url}")
            logger.info(f"  Formats: {args.formats or ['markdown']}")
        elif args.command == "crawl":
            logger.info(f"  URL: {args.url}")
            logger.info(f"  Limit: {args.limit}")
        elif args.command == "status":
            logger.info(f"  Crawl ID: {args.crawl_id}")
        finalize(success=True)
        return

    # Get API key
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        logger.error("Missing FIRECRAWL_API_KEY environment variable")
        logger.error("Get your API key at: https://firecrawl.dev")
        finalize(success=False)
        return

    try:
        if args.command == "scrape":
            logger.info(f"Scraping: {args.url}")
            formats = args.formats or ["markdown"]

            result = scrape_url(
                api_key=api_key,
                url=args.url,
                formats=formats,
                only_main=not args.full_page,
                wait_for=args.wait,
                timeout=args.timeout,
            )

            if not result.get("success"):
                logger.error(f"Scrape failed: {result.get('error', 'Unknown error')}")
                finalize(success=False)
                return

            data = result.get("data", {})

            # Output handling
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(data, f, indent=2)
                logger.info(f"Saved to: {args.output}")
            else:
                # Print to stdout
                print("\n" + "=" * 70)
                print("FIRECRAWL SCRAPE RESULT")
                print("=" * 70)

                if "metadata" in data:
                    meta = data["metadata"]
                    print(f"Title: {meta.get('title', 'N/A')}")
                    print(f"Source: {meta.get('sourceURL', args.url)}")
                    print("-" * 70)

                if "markdown" in data:
                    print("\n[MARKDOWN]\n")
                    print(data["markdown"][:5000])  # Truncate for display
                    if len(data.get("markdown", "")) > 5000:
                        print(f"\n... (truncated, {len(data['markdown'])} chars total)")

                if "links" in data:
                    print(f"\n[LINKS] ({len(data['links'])} found)")
                    for link in data["links"][:10]:
                        print(f"  - {link}")
                    if len(data["links"]) > 10:
                        print(f"  ... and {len(data['links']) - 10} more")

                print("\n" + "=" * 70)

            logger.info("Scrape complete")

        elif args.command == "crawl":
            logger.info(f"Starting crawl: {args.url}")

            result = start_crawl(
                api_key=api_key,
                url=args.url,
                limit=args.limit,
                include_paths=args.include_paths,
                exclude_paths=args.exclude_paths,
                max_depth=args.depth,
            )

            if not result.get("success"):
                logger.error(f"Crawl failed: {result.get('error', 'Unknown error')}")
                finalize(success=False)

            crawl_id = result.get("id")
            print("\n" + "=" * 70)
            print("CRAWL JOB STARTED")
            print("=" * 70)
            print(f"Job ID: {crawl_id}")
            print(f"Status URL: {result.get('url')}")
            print("\nCheck status with:")
            print(f"  python3 .claude/ops/firecrawl.py status {crawl_id}")
            print("=" * 70)

            logger.info(f"Crawl started: {crawl_id}")

        elif args.command == "status":
            logger.info(f"Checking crawl status: {args.crawl_id}")

            result = get_crawl_status(api_key, args.crawl_id)

            print("\n" + "=" * 70)
            print("CRAWL STATUS")
            print("=" * 70)
            print(f"Status: {result.get('status', 'unknown')}")
            print(f"Total: {result.get('total', 0)} pages")
            print(f"Completed: {result.get('completed', 0)} pages")

            if result.get("data"):
                print(f"\nResults available: {len(result['data'])} pages")
                for page in result["data"][:5]:
                    print(f"  - {page.get('metadata', {}).get('sourceURL', 'N/A')}")
                if len(result["data"]) > 5:
                    print(f"  ... and {len(result['data']) - 5} more")

            print("=" * 70)

            logger.info(f"Status: {result.get('status')}")

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                logger.error(f"API error: {error_data.get('error', e.response.text)}")
            except Exception:
                logger.error(f"Response: {e.response.text[:500]}")
        finalize(success=False)
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        finalize(success=False)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
