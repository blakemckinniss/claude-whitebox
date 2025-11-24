#!/usr/bin/env python3
"""
Test script for new context injection hooks
Tests all 5 hooks with sample prompts to verify they work correctly
"""
import sys
import json
import subprocess
from pathlib import Path

# Test prompts and expected hooks to fire
test_cases = [
    {
        "prompt": "Should we migrate from REST to GraphQL?",
        "expected_hooks": ["intent_classifier (decision_making)", "command_suggester (decision)"],
        "description": "Architectural decision"
    },
    {
        "prompt": "Write a function to process user data",
        "expected_hooks": ["intent_classifier (code_writing)", "prerequisite_checker (write code)"],
        "description": "Code writing request"
    },
    {
        "prompt": "Fix this broken authentication error",
        "expected_hooks": ["intent_classifier (debugging)"],
        "description": "Debugging request"
    },
    {
        "prompt": "Check if my code is ready to commit",
        "expected_hooks": ["intent_classifier (quality_check, commit)", "prerequisite_checker (commit)", "ecosystem_mapper (pre-commit)"],
        "description": "Pre-commit quality check"
    },
    {
        "prompt": "How do I use the pandas DataFrame API?",
        "expected_hooks": ["intent_classifier (research)", "command_suggester (research)", "best_practice_enforcer (API guess)"],
        "description": "Research request"
    },
    {
        "prompt": "What's my current confidence level?",
        "expected_hooks": ["command_suggester (confidence)"],
        "description": "Confidence status check"
    },
    {
        "prompt": "Use requests to scrape this dynamic website",
        "expected_hooks": ["best_practice_enforcer (requests on dynamic)"],
        "description": "Anti-pattern: requests on dynamic site"
    },
    {
        "prompt": "Modify config.py to add new settings",
        "expected_hooks": ["prerequisite_checker (edit)", "best_practice_enforcer (modify without read)"],
        "description": "Edit request"
    },
    {
        "prompt": "Delegate this research to an agent",
        "expected_hooks": ["intent_classifier (delegation)", "command_suggester (agent)"],
        "description": "Agent delegation"
    },
    {
        "prompt": "Verify that the tests pass",
        "expected_hooks": ["intent_classifier (verification)", "command_suggester (verify)", "ecosystem_mapper (verification)"],
        "description": "Verification request"
    },
]

PROJECT_DIR = Path(__file__).resolve().parent.parent
HOOKS_DIR = PROJECT_DIR / ".claude" / "hooks"

# Test each hook with each prompt
def test_hook(hook_name, prompt):
    """Test a single hook with a prompt"""
    hook_path = HOOKS_DIR / f"{hook_name}.py"

    # Create input JSON
    input_data = json.dumps({
        "prompt": prompt,
        "sessionId": "test_session_context_injection"
    })

    try:
        result = subprocess.run(
            ["python3", str(hook_path)],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return None, f"Error: {result.stderr}"

        # Parse output
        try:
            output = json.loads(result.stdout)
            context = output.get("hookSpecificOutput", {}).get("additionalContext", "")
            return context, None
        except json.JSONDecodeError:
            return None, f"Invalid JSON output: {result.stdout}"

    except subprocess.TimeoutExpired:
        return None, "Timeout (>5s)"
    except Exception as e:
        return None, str(e)

def main():
    """Run all tests"""
    print("="*80)
    print("CONTEXT INJECTION HOOK TESTING")
    print("="*80)
    print()

    hooks = [
        "intent_classifier",
        "command_suggester",
        "prerequisite_checker",
        "best_practice_enforcer",
        "ecosystem_mapper"
    ]

    total_tests = 0
    passed_tests = 0

    for i, test_case in enumerate(test_cases, 1):
        prompt = test_case["prompt"]
        description = test_case["description"]
        expected = test_case["expected_hooks"]

        print(f"Test {i}: {description}")
        print(f"Prompt: \"{prompt}\"")
        print(f"Expected: {', '.join(expected)}")
        print()

        fired_hooks = []

        for hook in hooks:
            context, error = test_hook(hook, prompt)

            total_tests += 1

            if error:
                print(f"  ❌ {hook}: {error}")
            elif context and context.strip():
                fired_hooks.append(hook)
                passed_tests += 1
                print(f"  ✅ {hook}: Injected context ({len(context)} chars)")
                # Show first 100 chars of context
                preview = context.strip().split('\n')[0][:100]
                print(f"     Preview: {preview}...")
            else:
                # No context injected (expected for most hooks on most prompts)
                pass

        if fired_hooks:
            print(f"\n  Fired: {', '.join(fired_hooks)}")
        else:
            print(f"\n  No hooks fired (check if this is expected)")

        print()
        print("-"*80)
        print()

    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total hook executions: {total_tests}")
    print(f"Successful executions: {passed_tests}")
    print(f"Failed executions: {total_tests - passed_tests}")
    print()

    # Show sample output from one hook
    print("="*80)
    print("SAMPLE FULL OUTPUT (intent_classifier on decision prompt)")
    print("="*80)
    context, error = test_hook("intent_classifier", "Should we migrate from REST to GraphQL?")
    if context:
        print(context)
    else:
        print(f"Error: {error}")

if __name__ == "__main__":
    main()
