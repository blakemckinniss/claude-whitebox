#!/usr/bin/env python3
"""
The Thinker: Decomposes complex problems into atomic steps using Chain of Thought
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
        "The Thinker: Decomposes complex problems into atomic steps using Chain of Thought"
    )

    parser.add_argument(
        "problem", help="The problem to decompose into sequential steps"
    )
    parser.add_argument(
        "--model",
        default="google/gemini-3-pro-preview",
        help="OpenRouter model ID (default: Gemini 2.0 Flash Thinking)",
    )

    args = parser.parse_args()
    handle_debug(args)

    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("Missing OPENROUTER_API_KEY environment variable")
        logger.error("Please add OPENROUTER_API_KEY to your .env file")
        finalize(success=False)

    logger.info(f"Consulting The Thinker ({args.model})...")

    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would send the following problem to The Thinker:")
        logger.info(f"Problem: {args.problem}")
        logger.info(f"Model: {args.model}")
        finalize(success=True)

    try:
        # Prepare system prompt for sequential decomposition
        system_prompt = """You are a Sequential Logic Engine.
Your role is to decompose complex problems into atomic, executable steps.

Rules:
1. Identify the ROOT CAUSE first (what is the actual problem, not the symptom?)
2. List any UNKNOWN VARIABLES that need investigation before proceeding
3. Create a LINEAR PLAN with numbered steps (Step 1, Step 2, Step 3...)
4. For each step, specify WHAT to do and HOW to verify it worked
5. Do NOT write the code - only write the plan
6. Include a "Definition of Done" at the end

Output Format:
## 🎯 Core Objective
[What are we actually trying to achieve?]

## 🚧 Constraints
[What are the limitations, requirements, or boundaries?]

## ❓ Unknown Variables
[What do we need to investigate/probe/research first?]

## 📋 Sequential Steps
1. [Step description] → Verify: [how to check success]
2. [Step description] → Verify: [how to check success]
...

## ✅ Definition of Done
[What does "success" look like?]
"""

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
                {"role": "user", "content": args.problem},
            ],
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

        # Display results
        print("\n" + "=" * 70)
        print("🧠 THE THINKER: SEQUENTIAL DECOMPOSITION")
        print("=" * 70)
        print(content)
        print("\n")

        logger.info("Sequential decomposition complete")

    except requests.exceptions.RequestException as e:
        logger.error(f"API communication failed: {e}")
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
