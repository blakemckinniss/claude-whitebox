#!/usr/bin/env python3
"""
The Researcher: Performs deep web search using Tavily to retrieve up-to-date documentation and context
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
        "The Researcher: Performs deep web search using Tavily to retrieve up-to-date documentation and context"
    )

    # Custom arguments
    parser.add_argument("query", help="The search query")
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Use advanced search depth (more thorough, slower)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Maximum number of results to return (default: 5)",
    )

    args = parser.parse_args()
    handle_debug(args)

    search_depth = "advanced" if args.deep else "basic"
    logger.info(f"Researching: '{args.query}' (depth: {search_depth})...")

    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would send the following query to Tavily:")
        logger.info(f"Query: {args.query}")
        logger.info(f"Search Depth: {search_depth}")
        logger.info(f"Max Results: {args.max_results}")
        finalize(success=True)

    # Check for API key (after dry-run check)
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        logger.error("Missing TAVILY_API_KEY environment variable")
        logger.error("Please add TAVILY_API_KEY to your .env file")
        logger.error("Get your API key at: https://tavily.com/")
        finalize(success=False)

    try:
        # Prepare Tavily API request
        payload = {
            "api_key": api_key,
            "query": args.query,
            "search_depth": search_depth,
            "include_answer": True,
            "max_results": args.max_results,
        }

        logger.debug(
            f"Request payload: {json.dumps({**payload, 'api_key': '***'}, indent=2)}"
        )

        # Call Tavily API
        response = requests.post(
            "https://api.tavily.com/search",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()

        logger.debug(f"Response: {json.dumps(result, indent=2)}")

        # Display results
        print("\n" + "=" * 70)
        print("📚 RESEARCH RESULTS")
        print("=" * 70)
        print(f"Query: {args.query}")
        print(f"Search Depth: {search_depth}")
        print("=" * 70)

        # Show direct answer if available
        if result.get("answer"):
            print("\n" + "💡 DIRECT ANSWER")
            print("-" * 70)
            print(result["answer"])
            print()

        # Show search results
        results = result.get("results", [])
        if results:
            print(f"\n🔍 TOP {len(results)} SOURCES")
            print("=" * 70)

            for idx, item in enumerate(results, 1):
                title = item.get("title", "No title")
                url = item.get("url", "")
                content = item.get("content", "No content available")

                print(f"\n[{idx}] {title}")
                print(f"    URL: {url}")
                print(f"    {'-' * 66}")

                # Wrap content to fit nicely
                lines = content.split("\n")
                for line in lines:
                    if len(line) > 66:
                        # Simple word wrapping
                        words = line.split()
                        current_line = "    "
                        for word in words:
                            if len(current_line) + len(word) + 1 > 70:
                                print(current_line)
                                current_line = "    " + word
                            else:
                                current_line += (
                                    " " if current_line != "    " else ""
                                ) + word
                        if current_line.strip():
                            print(current_line)
                    else:
                        print(f"    {line}")

            print("\n" + "=" * 70)
        else:
            print("\n⚠️  No results found")

        logger.info(f"Research complete: {len(results)} sources retrieved")

    except requests.exceptions.RequestException as e:
        logger.error(f"Tavily API communication failed: {e}")
        if "response" in locals():
            logger.error(f"Response text: {response.text}")
        finalize(success=False)
    except KeyError as e:
        logger.error(f"Unexpected response format: {e}")
        if "result" in locals():
            logger.error(f"Response: {json.dumps(result, indent=2)}")
        finalize(success=False)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
