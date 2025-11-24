#!/usr/bin/env python3
"""
Fix council.py to use oracle.py instead of individual persona scripts.

Problem: council.py calls persona scripts (judge.py, critic.py, etc.) via subprocess,
but those scripts were consolidated into oracle.py. Need to update call_persona_with_context()
to call: python3 oracle.py --persona <persona_key> "<prompt>"

Solution: Replace the subprocess call to individual scripts with oracle.py --persona calls.
"""

import sys
import os

# Read council.py
council_path = "/home/jinx/workspace/claude-whitebox/scripts/ops/council.py"

with open(council_path, 'r') as f:
    content = f.read()

# Find the call_persona_with_context function
# We need to replace the subprocess.run call that invokes individual scripts
# with a call to oracle.py --persona

# Original code (lines 185-224):
old_code = '''def call_persona_with_context(persona_key, persona_def, context, model, scripts_dir):
    """Call persona script with context"""
    script = persona_def["script"]
    prompt = persona_def["prompt_template"].format(proposal=context)

    logger.info(f"  {persona_def['emoji']} {persona_def['role']} ({model})...")

    script_path = os.path.join(scripts_dir, script)

    try:
        result = subprocess.run(
            ["python3", script_path, prompt, "--model", model],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            logger.error(f"Persona {persona_key} failed: {result.stderr}")
            # Return minimal valid output
            return parse_persona_output(
                f"VERDICT: ABSTAIN\\nCONFIDENCE: 0\\nREASONING: Script execution failed",
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

# New code that calls oracle.py instead
new_code = '''def call_persona_with_context(persona_key, persona_def, context, model, scripts_dir):
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

# Replace
if old_code in content:
    content = content.replace(old_code, new_code)
    print("✅ Successfully replaced call_persona_with_context() to use oracle.py")
else:
    print("❌ Could not find exact match for call_persona_with_context() function")
    print("   The function may have been modified. Manual fix required.")
    sys.exit(1)

# Write back
with open(council_path, 'w') as f:
    f.write(content)

print(f"✅ Updated: {council_path}")
print("\nChanges:")
print("- call_persona_with_context() now calls oracle.py --persona <key>")
print("- Removed dependency on individual persona scripts (judge.py, critic.py, etc.)")
print("\nNext: Test with: python3 scripts/ops/council.py 'test proposal'")
