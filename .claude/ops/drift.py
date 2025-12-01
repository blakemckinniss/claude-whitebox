#!/usr/bin/env python3
"""
The Court: Detects stylistic drift by comparing code against reference templates
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
        "The Court: Detects stylistic drift by comparing code against reference templates"
    )

    parser.add_argument("target", help="Python file to check for style drift")
    parser.add_argument(
        "--reference",
        help="Reference file to compare against (defaults to consult.py template)",
    )
    parser.add_argument(
        "--model",
        default="google/gemini-3-pro-preview",
        help="OpenRouter model ID (default: gemini-3-pro-preview)",
    )

    args = parser.parse_args()
    handle_debug(args)

    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("Missing OPENROUTER_API_KEY environment variable")
        logger.error("Please add OPENROUTER_API_KEY to your .env file")
        finalize(success=False)

    # Set default reference file
    if not args.reference:
        args.reference = os.path.join(_project_root, ".claude", "ops", "consult.py")
        logger.info(f"Using default reference: {args.reference}")

    target_path = os.path.abspath(args.target)
    reference_path = os.path.abspath(args.reference)

    # Validate files exist
    if not os.path.exists(target_path):
        logger.error(f"Target file not found: {target_path}")
        finalize(success=False)

    if not os.path.exists(reference_path):
        logger.error(f"Reference file not found: {reference_path}")
        finalize(success=False)

    if not target_path.endswith(".py"):
        logger.error("Target must be a Python file (.py)")
        finalize(success=False)

    if not reference_path.endswith(".py"):
        logger.error("Reference must be a Python file (.py)")
        finalize(success=False)

    logger.info(f"Analyzing drift in: {target_path}")
    logger.info(f"Against reference: {reference_path}")

    if args.dry_run:
        logger.warning("⚠️  DRY RUN MODE: Would compare files but not call API")
        with open(target_path, "r") as f:
            target_lines = len(f.readlines())
        with open(reference_path, "r") as f:
            ref_lines = len(f.readlines())
        logger.info(f"Target: {target_lines} lines")
        logger.info(f"Reference: {ref_lines} lines")
        finalize(success=True)

    try:
        # Read both files
        with open(target_path, "r") as f:
            target_content = f.read()

        with open(reference_path, "r") as f:
            reference_content = f.read()

        # Build comparison prompt
        prompt = f"""Compare the style, error handling, and import patterns of the Target file vs the Reference file.

REFERENCE FILE ({os.path.basename(reference_path)}):
```python
{reference_content}
```

TARGET FILE ({os.path.basename(target_path)}):
```python
{target_content}
```

**INSTRUCTIONS:**
- List ONLY the stylistic deviations (naming conventions, error handling patterns, import organization, logging style)
- IGNORE logic differences and implementation details
- Focus on SDK compliance: setup_script(), finalize(), logger usage, dry_run support
- Format as a bulleted list of specific deviations with line numbers
- If no deviations found, respond: "✅ No stylistic drift detected"
"""

        logger.info(f"Consulting The Oracle ({args.model}) for drift analysis...")

        # Prepare OpenRouter API request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/claude-code/whitebox",
        }

        data = {
            "model": args.model,
            "messages": [{"role": "user", "content": prompt}],
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
        print("⚖️  THE COURT: STYLE DRIFT ANALYSIS")
        print("=" * 70)
        print(f"  Target: {os.path.basename(target_path)}")
        print(f"  Reference: {os.path.basename(reference_path)}")
        print("=" * 70)
        print(content)
        print("\n")

        # Check if no drift detected
        if (
            "no stylistic drift" in content.lower()
            or "no deviations" in content.lower()
        ):
            logger.info("✅ No stylistic drift detected")
            finalize(success=True)
        else:
            logger.warning(
                "⚠️  Stylistic deviations found - consider aligning with reference"
            )
            finalize(success=True)  # Don't fail, just warn

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
        logger.error(f"Drift check failed: {e}")
        import traceback

        traceback.print_exc()
        finalize(success=False)


if __name__ == "__main__":
    main()
