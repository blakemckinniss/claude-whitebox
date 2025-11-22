#!/usr/bin/env python3
"""
The Advocate (Yellow Hat): Identifies benefits, opportunities, and best-case scenarios
Part of the Six Thinking Hats framework - represents optimistic thinking
"""
import sys
import os
import json
import requests

# Add scripts/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
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
        "The Advocate (Yellow Hat): Identifies benefits, opportunities, and best-case scenarios"
    )

    parser.add_argument("proposal", help="The proposal to evaluate for benefits")
    parser.add_argument(
        "--model", default="google/gemini-3-pro-preview", help="OpenRouter model ID"
    )

    args = parser.parse_args()
    handle_debug(args)

    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("Missing OPENROUTER_API_KEY environment variable")
        logger.error("Please add OPENROUTER_API_KEY to your .env file")
        finalize(success=False)

    logger.info(f"Consulting The Advocate - Yellow Hat ({args.model})...")

    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would analyze benefits for:")
        logger.info(f"Proposal: {args.proposal}")
        logger.info(f"Model: {args.model}")
        finalize(success=True)

    try:
        # System prompt for Yellow Hat thinking (optimistic, benefits-focused)
        system_prompt = """You are The Advocate, representing the Yellow Hat in Edward de Bono's Six Thinking Hats framework.

Your role: Optimistic thinking - identify BENEFITS, OPPORTUNITIES, and BEST-CASE SCENARIOS.

You focus on:
1. **Benefits & Value**
   - What are the concrete benefits?
   - What value does this create?
   - What problems does this solve?

2. **Opportunities**
   - What doors does this open?
   - What becomes possible?
   - What strategic advantages emerge?

3. **Best-Case Scenario**
   - If everything goes right, what's the outcome?
   - What's the maximum positive impact?
   - What multiplier effects could occur?

4. **ROI & Efficiency**
   - What resources are saved?
   - What efficiencies gained?
   - What's the return on investment?

5. **Innovation & Growth**
   - What innovation does this enable?
   - How does this position us for growth?
   - What competitive edge do we gain?

CRITICAL RULES:
- Be OPTIMISTIC but not unrealistic
- Focus on VALUE, not just features
- Consider both short-term and long-term benefits
- Think about stakeholder benefits (users, team, business)
- Identify multiplier effects (benefits that enable other benefits)

Output Format:
## 🟡 YELLOW HAT: Benefits & Opportunities

### ✅ Core Benefits
[What direct value does this create?]

### 🎯 Strategic Opportunities
[What new possibilities does this open?]

### 📈 Best-Case Scenario
[If everything goes right, what happens?]

### 💰 ROI & Efficiency
[What resources saved? What efficiencies gained?]

### 🚀 Innovation & Growth Potential
[How does this enable future innovation?]

### 🎁 Stakeholder Value
[Who benefits and how?]

Be enthusiastic but grounded. Focus on REAL value, not hype."""

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
                {
                    "role": "user",
                    "content": f"Analyze the benefits and opportunities of this proposal:\n\n{args.proposal}",
                },
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
        print("🟡 THE ADVOCATE'S ANALYSIS (Yellow Hat)")
        print("=" * 70)
        print(content)
        print("=" * 70)

    except requests.exceptions.RequestException as e:
        logger.error(f"OpenRouter API call failed: {e}")
        finalize(success=False)
    except KeyError as e:
        logger.error(f"Unexpected API response format: {e}")
        logger.error(f"Response: {result if 'result' in locals() else 'N/A'}")
        finalize(success=False)
    except Exception as e:
        logger.error(f"The Advocate failed: {e}")
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
