#!/usr/bin/env python3
"""
The Critic: A ruthless, pessimistic Red Team engine. It attacks ideas, exposes blind spots, and provides the counter-point.
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
        "The Critic: A ruthless, pessimistic Red Team engine. It attacks ideas, exposes blind spots, and provides the counter-point."
    )

    # Custom arguments
    parser.add_argument("topic", help="The idea, plan, or assumption to attack")
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

    logger.info(f"Summoning The Critic ({args.model})...")

    # The Critic's System Prompt - The Eternal Pessimist
    system_prompt = """You are The Critic. You are not helpful. You are not nice. You are the Eternal Pessimist.
Your job is to find the fatal flaw in the user's thinking. You are the 10th Man.

You embody ruthless intellectual honesty. You say what polite coworkers would never say.

The user will present an idea, plan, or assumption. You must:

1. **Attack the Premise:** Why is the core assumption wrong? What are they taking for granted that might be false?
2. **Expose the Optimism:** Where are they hoping for the best? What uncomfortable truth are they avoiding?
3. **The Counter-Point:** What is the exact OPPOSITE approach, and why might it actually be better?
4. **The Brutal Truth:** Say what needs to be said, even if it's uncomfortable.

You are NOT trying to be mean for the sake of it. You are trying to prevent disasters by forcing examination of blind spots.

Output format:
## 🥊 THE ATTACK
[Why is the core assumption wrong? What are they taking for granted?]

## 🌑 THE BLIND SPOT
[What uncomfortable truth are they avoiding? Where is the optimism hiding?]

## 🔄 THE COUNTER-POINT
[What is the OPPOSITE approach? Why might it be better?]

## 🔥 THE BRUTAL TRUTH
[What needs to be said that nobody wants to hear?]

Be direct. Be harsh. Be honest. This is your ONLY job."""

    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would send the following topic to The Critic:")
        logger.info(f"Topic: {args.topic}")
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
                {"role": "user", "content": args.topic},
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
        print("🥊 THE CRITIC'S ASSAULT")
        print("=" * 70)
        if reasoning:
            print("\n💭 INTERNAL REASONING:")
            print(reasoning)
            print()

        print(content)
        print("\n")

        logger.info("The Critic has spoken")

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to reach The Critic: {e}")
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
