#!/usr/bin/env python3
"""
The Skeptic: Analyzes a proposed plan for logical fallacies and failure modes
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
    parser = setup_script("The Skeptic: Analyzes a proposed plan for logical fallacies and failure modes")

    parser.add_argument('plan', help="The proposed plan or approach to critique")
    parser.add_argument('--model', default="google/gemini-3-pro-preview",
                       help="OpenRouter model ID (default: Gemini 2.0 Flash Thinking)")

    args = parser.parse_args()
    handle_debug(args)

    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("Missing OPENROUTER_API_KEY environment variable")
        logger.error("Please add OPENROUTER_API_KEY to your .env file")
        finalize(success=False)

    logger.info(f"Consulting The Skeptic ({args.model})...")

    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would send the following plan to The Skeptic:")
        logger.info(f"Plan: {args.plan}")
        logger.info(f"Model: {args.model}")
        finalize(success=True)

    try:
        # Prepare system prompt for hostile review
        system_prompt = """You are a Hostile Architecture Reviewer and Senior Engineering Skeptic.
Your role is to find every possible flaw, fallacy, and failure mode in proposed technical plans.

You are NOT here to be encouraging. You are here to prevent disasters.

Analyze the proposed plan for:

1. **The XY Problem**
   - Is the user asking for a solution to a SYMPTOM rather than the ROOT CAUSE?
   - Are they trying to fix the wrong thing?
   - Example: "I want to cache everything" → Real problem: "One slow query"

2. **Sunk Cost Fallacy**
   - Are they patching bad code instead of rewriting it?
   - Are they adding complexity to preserve a flawed design?
   - Is this "technical debt on top of technical debt"?

3. **Premature Optimization**
   - Are they building a Ferrari to cross the street?
   - Is this optimization actually needed, or are they guessing?
   - Have they measured the actual bottleneck?

4. **Security & Data Loss Risks**
   - What happens if input is malicious?
   - What happens if the operation fails halfway through?
   - Are there race conditions, injection risks, or data integrity issues?

5. **Pre-Mortem Analysis**
   - Assume this implementation FAILED in production.
   - Write the post-mortem: "This failed because..."
   - What edge cases were not considered?

6. **Complexity Explosion**
   - Is this adding cognitive load for future maintainers?
   - Is there a simpler solution they're missing?
   - Are they reinventing the wheel?

Output Format:
## 🚨 CRITICAL ISSUES
[Any dealbreakers that MUST be addressed]

## ⚠️ LOGICAL FALLACIES DETECTED
[XY Problem, Sunk Cost, Premature Optimization, etc.]

## 🔥 PRE-MORTEM: How This Will Fail
[Assume it failed. Explain why.]

## 🛡️ SECURITY & DATA INTEGRITY
[What could go wrong? What's unprotected?]

## 💡 ALTERNATIVE APPROACHES
[Simpler/safer ways to solve the ACTUAL problem]

## ✅ IF YOU MUST PROCEED
[What mitigations are absolutely required?]

Be ruthless. Be specific. Cite line numbers or specifics from the plan.
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
                {"role": "user", "content": f"Critique this plan:\n\n{args.plan}"}
            ]
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

        # Display results
        print("\n" + "=" * 70)
        print("🔍 THE SKEPTIC: HOSTILE ARCHITECTURE REVIEW")
        print("=" * 70)
        print(content)
        print("\n")

        # Check if critical issues were found
        if "CRITICAL ISSUES" in content and content.split("CRITICAL ISSUES")[1].split("\n\n")[0].strip() != "[None]":
            logger.warning("⚠️  CRITICAL ISSUES DETECTED - Review carefully before proceeding")
        else:
            logger.info("Skeptical review complete - no critical blockers")

    except requests.exceptions.RequestException as e:
        logger.error(f"API communication failed: {e}")
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
