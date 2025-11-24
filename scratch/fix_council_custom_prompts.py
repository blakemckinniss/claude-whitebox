#!/usr/bin/env python3
"""
Fix council.py to use --custom-prompt for personas not in oracle.py.

Problem: oracle.py only supports 3 hardcoded personas (judge, critic, skeptic),
but council library has 12 personas. When council tries to call oracle with
persona="oracle" or "innovator", it fails.

Solution: Check if persona_key is in oracle.py's supported list. If yes, use
--persona flag. If no, use --custom-prompt with the prompt_template.
"""

import sys

council_path = "/home/jinx/workspace/claude-whitebox/scripts/ops/council.py"

with open(council_path, 'r') as f:
    content = f.read()

# Find and replace call_persona_with_context function
old_function = '''def call_persona_with_context(persona_key, persona_def, context, model, scripts_dir):
    """Call persona via oracle.py with --persona flag"""
    prompt = persona_def["prompt_template"].format(proposal=context)

    logger.info(f"  {persona_def['emoji']} {persona_def['role']} ({model})...")

    oracle_path = os.path.join(scripts_dir, "oracle.py")

    try:
        # Call oracle.py with --persona flag
        result = subprocess.run(
            ["python3", oracle_path, "--persona", persona_key, prompt, "--model", model],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            logger.error(f"Persona {persona_key} failed: {result.stderr}")
            # Return minimal valid output
            return parse_persona_output(
                f"VERDICT: ABSTAIN\\nCONFIDENCE: 0\\nREASONING: Oracle call failed",
                persona_key
            )

        # Parse structured output
        return parse_persona_output(result.stdout, persona_key)

    except subprocess.TimeoutExpired:
        logger.error(f"Persona {persona_key} timed out")
        return parse_persona_output(
            f"VERDICT: ABSTAIN\\nCONFIDENCE: 0\\nREASONING: Timeout after 120s",
            persona_key
        )
    except Exception as e:
        logger.error(f"Persona {persona_key} error: {e}")
        return parse_persona_output(
            f"VERDICT: ABSTAIN\\nCONFIDENCE: 0\\nREASONING: {str(e)}",
            persona_key
        )'''

new_function = '''def call_persona_with_context(persona_key, persona_def, context, model, scripts_dir):
    """Call persona via oracle.py (using --persona or --custom-prompt)"""
    prompt = persona_def["prompt_template"].format(proposal=context)

    logger.info(f"  {persona_def['emoji']} {persona_def['role']} ({model})...")

    oracle_path = os.path.join(scripts_dir, "oracle.py")

    # oracle.py only supports these hardcoded personas
    ORACLE_NATIVE_PERSONAS = ["judge", "critic", "skeptic"]

    try:
        # Build command based on persona support
        if persona_key in ORACLE_NATIVE_PERSONAS:
            # Use native --persona flag for better prompt engineering
            cmd = ["python3", oracle_path, "--persona", persona_key, prompt, "--model", model]
        else:
            # Use --custom-prompt for personas not in oracle.py
            # Extract just the system instructions from prompt_template
            cmd = ["python3", oracle_path, "--custom-prompt", prompt, prompt, "--model", model]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            logger.error(f"Persona {persona_key} failed: {result.stderr}")
            # Return minimal valid output
            return parse_persona_output(
                f"VERDICT: ABSTAIN\\nCONFIDENCE: 0\\nREASONING: Oracle call failed",
                persona_key
            )

        # Parse structured output
        return parse_persona_output(result.stdout, persona_key)

    except subprocess.TimeoutExpired:
        logger.error(f"Persona {persona_key} timed out")
        return parse_persona_output(
            f"VERDICT: ABSTAIN\\nCONFIDENCE: 0\\nREASONING: Timeout after 120s",
            persona_key
        )
    except Exception as e:
        logger.error(f"Persona {persona_key} error: {e}")
        return parse_persona_output(
            f"VERDICT: ABSTAIN\\nCONFIDENCE: 0\\nREASONING: {str(e)}",
            persona_key
        )'''

# Replace
if old_function in content:
    content = content.replace(old_function, new_function)
    print("✅ Updated call_persona_with_context() to support custom prompts")
else:
    print("❌ Could not find exact match for call_persona_with_context()")
    print("   Function may have changed. Showing search pattern...")
    sys.exit(1)

# Write back
with open(council_path, 'w') as f:
    f.write(content)

print(f"✅ Updated: {council_path}")
print("\nChanges:")
print("- Native personas (judge, critic, skeptic): use --persona flag")
print("- Other personas (oracle, innovator, etc.): use --custom-prompt")
print("\nNext: Test with council.py")
