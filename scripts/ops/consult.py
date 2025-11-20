#!/usr/bin/env python3
"""
The Oracle: Consults a high-reasoning model via OpenRouter for architecture advice
"""
import sys
import os
import json
import requests

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
    parser = setup_script("The Oracle: Consults a high-reasoning model via OpenRouter for architecture advice")

    # Custom arguments
    parser.add_argument('prompt', help="The question or problem to analyze")
    parser.add_argument('--model', default="google/gemini-2.0-flash-thinking-exp:free",
                       help="OpenRouter model ID (default: Gemini 2.0 Flash Thinking)")

    args = parser.parse_args()
    handle_debug(args)

    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("Missing OPENROUTER_API_KEY environment variable")
        logger.error("Please add OPENROUTER_API_KEY to your .env file")
        finalize(success=False)

    logger.info(f"Consulting The Oracle ({args.model})...")

    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would send the following prompt to OpenRouter:")
        logger.info(f"Prompt: {args.prompt}")
        logger.info(f"Model: {args.model}")
        finalize(success=True)

    try:
        # Prepare OpenRouter API request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/claude-code/whitebox",
        }

        data = {
            "model": args.model,
            "messages": [{"role": "user", "content": args.prompt}],
            "extra_body": {"reasoning": {"enabled": True}}
        }

        logger.debug(f"Request payload: {json.dumps(data, indent=2)}")

        # Call OpenRouter API
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()

        logger.debug(f"Response: {json.dumps(result, indent=2)}")

        # Extract response content
        choice = result['choices'][0]['message']
        content = choice.get('content', '')

        # Try to extract reasoning (format varies by provider)
        reasoning = choice.get('reasoning', '') or result.get('reasoning', '')

        # Display results
        print("\n" + "=" * 70)
        print("🧠 ORACLE REASONING")
        print("=" * 70)
        if reasoning:
            print(reasoning)
        else:
            print("(No explicit reasoning trace provided by this model)")

        print("\n" + "=" * 70)
        print("💡 ORACLE ADVICE")
        print("=" * 70)
        print(content)
        print("\n")

        logger.info("Oracle consultation complete")

    except requests.exceptions.RequestException as e:
        logger.error(f"Oracle communication failed: {e}")
        if 'response' in locals():
            logger.error(f"Response text: {response.text}")
        finalize(success=False)
    except KeyError as e:
        logger.error(f"Unexpected response format: {e}")
        if 'result' in locals():
            logger.error(f"Response: {json.dumps(result, indent=2)}")
        finalize(success=False)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
