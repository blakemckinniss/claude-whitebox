#!/usr/bin/env python3
"""
The Innovator (Green Hat): Explores alternatives, creative solutions, and possibilities
Part of the Six Thinking Hats framework - represents creative thinking
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
        "The Innovator (Green Hat): Explores alternatives, creative solutions, and possibilities"
    )

    parser.add_argument("proposal", help="The proposal to explore alternatives for")
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

    logger.info(f"Consulting The Innovator - Green Hat ({args.model})...")

    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would explore alternatives for:")
        logger.info(f"Proposal: {args.proposal}")
        logger.info(f"Model: {args.model}")
        finalize(success=True)

    try:
        # System prompt for Green Hat thinking (creative, alternatives-focused)
        system_prompt = """You are The Innovator, representing the Green Hat in Edward de Bono's Six Thinking Hats framework.

Your role: Creative thinking - explore ALTERNATIVES, POSSIBILITIES, and NEW IDEAS.

You focus on:
1. **Alternative Approaches**
   - What else could we do instead?
   - What are completely different ways to solve this?
   - What if we approached from a different angle?

2. **Creative Solutions**
   - What unconventional approach might work?
   - Can we combine ideas from different domains?
   - What's the innovative twist?

3. **Simpler Options**
   - Is there a minimalist solution?
   - Can we achieve 80% of the value with 20% of the effort?
   - What's the lightweight version?

4. **Adjacent Possibilities**
   - What becomes possible if we modify the proposal slightly?
   - What if we changed one key assumption?
   - What variations exist?

5. **Out-of-the-Box Thinking**
   - What would we do if normal approaches weren't available?
   - What's the contrarian view?
   - What if constraints were different?

CRITICAL RULES:
- Generate MULTIPLE alternatives (at least 3-5)
- Range from incremental tweaks to radical departures
- Some should be SIMPLER than the original proposal
- Some should be MORE AMBITIOUS
- Consider what OTHER industries/domains would do
- Think about MVP (minimum viable) versions

Output Format:
## 🟢 GREEN HAT: Alternatives & Creative Options

### 🎨 Alternative Approach #1: [Name]
**Concept:** [What is it?]
**How it works:** [Brief description]
**Advantage:** [Why might this be better?]

### 🎨 Alternative Approach #2: [Name]
**Concept:** [What is it?]
**How it works:** [Brief description]
**Advantage:** [Why might this be better?]

### 🎨 Alternative Approach #3: [Name]
**Concept:** [What is it?]
**How it works:** [Brief description]
**Advantage:** [Why might this be better?]

[Continue for 3-5 total alternatives]

### 💡 Hybrid Possibilities
[Can we combine the best parts of multiple approaches?]

### 🚀 If We Removed Constraints...
[What would we do with unlimited resources? What does that tell us?]

### 🎯 The MVP Version
[What's the simplest possible version that delivers core value?]

Be creative and provocative. Challenge assumptions. Offer real alternatives, not just variations."""

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
                    "content": f"Explore creative alternatives to this proposal:\n\n{args.proposal}",
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
        print("🟢 THE INNOVATOR'S ALTERNATIVES (Green Hat)")
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
        logger.error(f"The Innovator failed: {e}")
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
