#!/usr/bin/env python3
"""
The Arbiter (Blue Hat): Synthesizes Five Hats into a final verdict
===================================================================

Part of the Six Thinking Hats framework - represents process control and synthesis.

Receives five external perspectives (White, Red, Black, Yellow, Green Hats) and
provides an unbiased synthesis with a clear verdict.

Usage:
  python3 scripts/ops/arbiter.py "<proposal>" \
    --white-hat "<facts_output>" \
    --red-hat "<risks_output>" \
    --black-hat "<critical_output>" \
    --yellow-hat "<benefits_output>" \
    --green-hat "<alternatives_output>"
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
    parser = setup_script("The Arbiter (Blue Hat): Synthesizes Five Hats into verdict")

    parser.add_argument("proposal", help="The proposal being evaluated")
    parser.add_argument(
        "--white-hat",
        required=True,
        dest="white_hat",
        help="White Hat perspective (Facts & Data)",
    )
    parser.add_argument(
        "--red-hat",
        required=True,
        dest="red_hat",
        help="Red Hat perspective (Risks & Intuition)",
    )
    parser.add_argument(
        "--black-hat",
        required=True,
        dest="black_hat",
        help="Black Hat perspective (Critical Analysis)",
    )
    parser.add_argument(
        "--yellow-hat",
        required=True,
        dest="yellow_hat",
        help="Yellow Hat perspective (Benefits & Opportunities)",
    )
    parser.add_argument(
        "--green-hat",
        required=True,
        dest="green_hat",
        help="Green Hat perspective (Alternatives & Creative)",
    )
    parser.add_argument(
        "--model", default="google/gemini-3-pro-preview", help="OpenRouter model to use"
    )

    args = parser.parse_args()
    handle_debug(args)

    # Get API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("Missing OPENROUTER_API_KEY environment variable")
        logger.error("Please add OPENROUTER_API_KEY to your .env file")
        finalize(success=False)

    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would synthesize the following perspectives:")
        logger.info(f"Proposal: {args.proposal}")
        logger.info(f"WHITE HAT (Facts): {args.white_hat[:100]}...")
        logger.info(f"RED HAT (Risks): {args.red_hat[:100]}...")
        logger.info(f"BLACK HAT (Critical): {args.black_hat[:100]}...")
        logger.info(f"YELLOW HAT (Benefits): {args.yellow_hat[:100]}...")
        logger.info(f"GREEN HAT (Alternatives): {args.green_hat[:100]}...")
        logger.info(f"Model: {args.model}")
        finalize(success=True)

    logger.info(f"Consulting The Arbiter ({args.model})...")

    # The Arbiter's System Prompt (Blue Hat)
    system_prompt = """You are The Arbiter (Blue Hat), representing process control in Edward de Bono's Six Thinking Hats framework.

Your role: Synthesize FIVE perspectives into a clear, actionable verdict.

You will receive (Six Thinking Hats framework):
1. ⚪ WHITE HAT (Facts): Objective data, precedents, research
2. 🔴 RED HAT (Risks): Gut instincts, warning signs, intuition
3. ⚫ BLACK HAT (Critical): Weaknesses, flaws, why it will fail
4. 🟡 YELLOW HAT (Benefits): Opportunities, ROI, best-case scenario
5. 🟢 GREEN HAT (Alternatives): Creative options, other approaches

Your task:
1. Weigh all FIVE perspectives fairly
2. Identify areas of agreement and conflict across all hats
3. Assess the strength of each perspective
4. Consider whether alternatives (Green) are better than the original proposal
5. Provide a clear verdict based on the balance of evidence

CRITICAL RULES:
- Do NOT inject your own opinions beyond what the five perspectives provide
- Do NOT introduce new arguments not present in the inputs
- Do NOT be swayed by eloquence - focus on substance
- Base your verdict ONLY on the evidence presented
- If GREEN HAT alternatives are superior, recommend those instead

Output format (MUST follow this structure):

## ⚖️ VERDICT: [STRONG GO / CONDITIONAL GO / STOP / INVESTIGATE / ALTERNATIVE RECOMMENDED]

**Verdict Definitions:**
- STRONG GO: Proceed with confidence (Yellow strong, Black/Red addressable, White supports, no better alternatives)
- CONDITIONAL GO: Proceed with caution (mixed signals, must address conditions first)
- STOP: Do not proceed (Black/Red critical flaws, White opposes, or alternatives clearly better)
- INVESTIGATE: Gather more information (conflicting signals, White lacks data)
- ALTERNATIVE RECOMMENDED: One of Green's alternatives is superior to the original proposal

## 📊 FIVE HATS SUMMARY:

**⚪ WHITE (Facts):** [Strong / Moderate / Weak]
[One sentence: What do the facts say?]

**🔴 RED (Risks):** [High Risk / Medium Risk / Low Risk]
[One sentence: What's the gut feeling/warning?]

**⚫ BLACK (Critical):** [Critical Flaws / Concerns / Minor Issues]
[One sentence: What's the strongest critique?]

**🟡 YELLOW (Benefits):** [High Value / Medium Value / Low Value]
[One sentence: What's the strongest benefit?]

**🟢 GREEN (Alternatives):** [Better Options Exist / Comparable / None Better]
[One sentence: Are alternatives superior?]

## 🎯 SYNTHESIS:

[2-3 sentences explaining your verdict based on the balance of evidence from all three perspectives]

## ⚠️ CONDITIONS (if CONDITIONAL GO):

[Bulleted list of what must be addressed before proceeding. Omit if verdict is STRONG GO, STOP, or INVESTIGATE]

## 🔍 NEXT STEPS:

[Specific, actionable next steps based on the verdict]

## 📈 CONFIDENCE:

[High / Medium / Low] - [One sentence explaining your confidence level in this verdict]

Remember: You are synthesizing external perspectives, not creating new arguments."""

    try:
        # Build the user message with all five perspectives (Six Thinking Hats)
        user_message = f"""Proposal: {args.proposal}

===============================================
⚪ WHITE HAT (Facts & Data)
===============================================
{args.white_hat}

===============================================
🔴 RED HAT (Risks & Intuition)
===============================================
{args.red_hat}

===============================================
⚫ BLACK HAT (Critical Analysis)
===============================================
{args.black_hat}

===============================================
🟡 YELLOW HAT (Benefits & Opportunities)
===============================================
{args.yellow_hat}

===============================================
🟢 GREEN HAT (Alternatives & Creative Options)
===============================================
{args.green_hat}

===============================================

Based on these FIVE perspectives (Six Thinking Hats framework), provide your synthesized verdict."""

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
                {"role": "user", "content": user_message},
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
        print("⚖️  THE ARBITER'S VERDICT")
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
        logger.error(f"The Arbiter failed: {e}")
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
