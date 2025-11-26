#!/usr/bin/env python3
"""
The Documentation Hunter: Retrieves latest documentation using Context7 REST API
Proactively triggered when library/framework documentation is needed
"""
import sys
import os
import json
import requests

# Add .claude/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
# Find project root by looking for '.claude' directory
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


def main():
    parser = setup_script(
        "The Documentation Hunter: Retrieves latest documentation using Context7 REST API"
    )

    # Custom arguments
    parser.add_argument("library", help="Library name (e.g., 'react', 'next.js', 'fastapi', 'pandas')")
    parser.add_argument(
        "--topic",
        help="Specific topic to search for (e.g., 'ssr', 'dependency injection', 'filtering')",
    )
    parser.add_argument(
        "--tokens",
        type=int,
        default=5000,
        help="Maximum tokens to return (default: 5000)",
    )
    parser.add_argument(
        "--format",
        choices=["txt", "json"],
        default="txt",
        help="Response format: txt (markdown), json (structured data)",
    )
    parser.add_argument(
        "--output",
        help="Save output to file instead of stdout",
    )

    args = parser.parse_args()
    handle_debug(args)

    # Library path is used as-is (e.g., vercel/next.js)
    library_path = args.library

    logger.info(f"Fetching documentation for '{args.library}'" +
                (f" (topic: {args.topic})" if args.topic else ""))

    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would send the following request to Context7:")
        logger.info(f"Library: {args.library}")
        logger.info(f"Topic: {args.topic or 'all'}")
        logger.info(f"Tokens: {args.tokens}")
        logger.info(f"Format: {args.format}")
        finalize(success=True)

    # Check for API key (after dry-run check)
    api_key = os.getenv("CONTEXT7_API_KEY")
    if not api_key:
        logger.error("Missing CONTEXT7_API_KEY environment variable")
        logger.error("Please add CONTEXT7_API_KEY to your .env file")
        logger.error("Get your API key at: https://context7.com/")
        finalize(success=False)

    try:
        # Build URL with query parameters
        url = f"https://context7.com/api/v1/{library_path}"
        params = {
            "type": args.format,
            "tokens": args.tokens,
        }
        if args.topic:
            params["topic"] = args.topic

        logger.debug(f"Request URL: {url}")
        logger.debug(f"Parameters: {json.dumps(params, indent=2)}")

        # Call Context7 API
        response = requests.get(
            url,
            params=params,
            headers={
                "Authorization": f"Bearer {api_key}",
            },
            timeout=30,
        )
        response.raise_for_status()

        # Parse and format response
        if args.format == "json":
            try:
                result = response.json()
                content = json.dumps(result, indent=2)
            except json.JSONDecodeError as e:
                logger.error(f"API returned invalid JSON: {e}")
                logger.error(f"Response: {response.text[:500]}")
                finalize(success=False)
        else:
            # Text format - already formatted by Context7
            content = response.text

        # Validate content
        if not content or len(content) == 0:
            logger.warning("⚠️ API returned empty response (0 tokens)")

        # Output to file or stdout
        if args.output:
            # Create parent directories if needed
            output_dir = os.path.dirname(args.output)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            # Write with explicit UTF-8 encoding
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Documentation saved to {args.output} ({len(content)} chars)")
        else:
            print(content)
            logger.info(f"Documentation retrieved successfully ({len(content)} chars)")

    except requests.exceptions.HTTPError as e:
        # Differentiate user errors from API errors
        if "response" in locals():
            status = response.status_code
            if status == 404:
                logger.error(f"Library not found: {args.library}")
                logger.error("Add it at: https://context7.com/add-library")
            elif status == 400:
                logger.error(f"Invalid request: {response.text}")
                logger.error("Expected format: username/library (e.g., vercel/next.js)")
            elif status == 429:
                logger.error("Rate limit exceeded - too many requests")
                logger.error("Check your quota at: https://context7.com/dashboard")
            else:
                logger.error(f"API error ({status}): {e}")
                logger.error(f"Response: {response.text[:500]}")
        finalize(success=False)
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error: {e}")
        finalize(success=False)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
