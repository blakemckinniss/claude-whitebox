#!/usr/bin/env python3
"""
The Judge: Evaluates the VALUE and NECESSITY of a task. Prevents over-engineering.
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
while _current != "/":
    if os.path.exists(os.path.join(_current, "scripts", "lib", "core.py")):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with scripts/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, "scripts", "lib"))
from core import setup_script, finalize, logger, handle_debug


def main():
    parser = setup_script(
        "The Judge: Evaluates the VALUE and NECESSITY of a task. Prevents over-engineering."
    )

    # Custom arguments
    parser.add_argument("proposal", help="The proposed task or feature to evaluate")
    parser.add_argument(
        "--model",
        default="google/gemini-3-pro-preview",
        help="OpenRouter model to use (default: gemini-2.0-flash-thinking)",
    )

    args = parser.parse_args()
    handle_debug(args)

    # Get API key from environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("Missing OPENROUTER_API_KEY environment variable")
        logger.error("Please add OPENROUTER_API_KEY to your .env file")
        finalize(success=False)

    logger.info(f"Bringing proposal before The Judge ({args.model})...")

    # The Judge's System Prompt - Ruthless Pragmatism
    system_prompt = """You are The Judge. You are a ruthless Minimalist Architect and grumpy Senior Staff Engineer.
Your goal is to STOP work. You hate code. You love existing solutions.
You have seen every framework fail, every "improvement" create technical debt, and every "refactor" introduce bugs.

Code is a LIABILITY, not an asset. The best code is NO code.

Analyze the user's proposal for:

1. **Bikeshedding:** Are they focusing on trivial details (colors, linting rules, folder names) while ignoring the core problem?
2. **YAGNI (You Ain't Gonna Need It):** Are they building for a future that hasn't happened? Are they solving problems they don't have?
3. **Reinventing the Wheel:** Does a standard library, shell command, or existing tool already do this?
4. **ROI (Return on Investment):** Is the effort worth the result? Will this move the needle on the actual business problem?
5. **The XY Problem:** Are they asking for Z to solve Y, when Y itself is the wrong solution to X?
6. **Premature Optimization:** Are they building a Ferrari when a bicycle would work?

Be BRUTAL. Be HONEST. Your job is to SAVE time, not validate feelings.

Output format:
## ⚖️ VERDICT: [PROCEED / STOP / SIMPLIFY]

## 📉 REASON:
[One brutal, honest sentence explaining why]

## ✂️ THE CUT:
[What can be removed from this plan? What's the MINIMUM VIABLE solution?]

## 💡 THE ALTERNATIVE:
[If there's a simpler way (stdlib, existing tool, shell command), name it]

If the verdict is PROCEED, still suggest what to cut to make it leaner."""

    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would send the following proposal to The Judge:")
        logger.info(f"Proposal: {args.proposal}")
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
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": args.proposal},
            ],
            "extra_body": {"reasoning": {"enabled": True}},
        }

        logger.debug(f"Request payload: {json.dumps(data, indent=2)}")

        # Call OpenRouter API
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=120,
        )
        response.raise_for_status()
        result = response.json()

        logger.debug(f"Response: {json.dumps(result, indent=2)}")

        # Extract response content
        choice = result["choices"][0]["message"]
        content = choice.get("content", "")

        # Try to extract reasoning (format varies by provider)
        reasoning = choice.get("reasoning", "") or result.get("reasoning", "")

        # Display results
        print("\n" + "=" * 70)
        print("⚖️ THE JUDGE'S RULING")
        print("=" * 70)
        if reasoning:
            print("\n🧠 REASONING:")
            print(reasoning)
            print()

        print(content)
        print("\n")

        logger.info("Judgment rendered")

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to reach The Judge: {e}")
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
