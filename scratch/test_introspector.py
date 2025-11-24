#!/usr/bin/env python3
"""
Test the introspector hook with diverse prompts to verify semantic detection.
"""

import json
import subprocess
import sys
from pathlib import Path

# Test prompts covering different semantic signals
TEST_PROMPTS = [
    {
        "name": "Browser Automation Signal",
        "prompt": "How do I scrape product prices from Amazon's website?",
        "expected_signals": ["browser_automation", "xy_problem"],
    },
    {
        "name": "Research Signal",
        "prompt": "How does Playwright's auto-waiting feature work in 2025?",
        "expected_signals": ["research_needed"],
    },
    {
        "name": "API Uncertainty Signal",
        "prompt": "What methods are available on pandas.DataFrame?",
        "expected_signals": ["api_uncertainty"],
    },
    {
        "name": "Decision Complexity Signal",
        "prompt": "Should we migrate from REST to GraphQL for our API?",
        "expected_signals": ["decision_complexity"],
    },
    {
        "name": "Iteration Signal",
        "prompt": "Process all files in the src/ directory and update imports",
        "expected_signals": ["iteration_detected"],
    },
    {
        "name": "Verification Gap Signal",
        "prompt": "I've fixed the authentication bug and it should work now",
        "expected_signals": ["verification_gap"],
    },
    {
        "name": "Production Gate Signal",
        "prompt": "I'm ready to deploy scripts/ops/new_feature.py to production",
        "expected_signals": ["production_gate"],
    },
    {
        "name": "Complexity Smell Signal",
        "prompt": "This is really complicated - I need a custom workaround for nested loops",
        "expected_signals": ["complexity_smell"],
    },
    {
        "name": "Test Strategy Signal",
        "prompt": "Write unit tests for the authentication module with 100% coverage",
        "expected_signals": ["test_strategy"],
    },
    {
        "name": "Multiple Signals (Scraping + Research + XY)",
        "prompt": "How do I use requests to scrape a React SPA built with latest Next.js?",
        "expected_signals": ["browser_automation", "research_needed", "xy_problem"],
    },
]


def run_introspector(prompt: str, session_id: str = "test") -> dict:
    """Run introspector hook with given prompt"""
    hook_path = Path(__file__).parent.parent / ".claude" / "hooks" / "introspector.py"

    if not hook_path.exists():
        print(f"ERROR: Hook not found at {hook_path}")
        sys.exit(1)

    input_data = {"prompt": prompt, "session_id": session_id}

    try:
        result = subprocess.run(
            ["python3", str(hook_path)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            print(f"ERROR: Hook failed with code {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return {"error": result.stderr}

        output = json.loads(result.stdout)
        return output

    except subprocess.TimeoutExpired:
        return {"error": "Timeout"}
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON from hook: {result.stdout}")
        return {"error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"error": str(e)}


def extract_signals_from_context(context: str) -> list:
    """Extract signal names from context message"""
    signals = []
    if "🎭 PLAYWRIGHT SIGNAL" in context:
        signals.append("browser_automation")
    if "🔬 RESEARCH SIGNAL" in context:
        signals.append("research_needed")
    if "🎯 XY PROBLEM" in context:
        signals.append("xy_problem")
    if "⚖️ DECISION COMPLEXITY" in context:
        signals.append("decision_complexity")
    if "🔬 API UNCERTAINTY" in context:
        signals.append("api_uncertainty")
    if "🔁 ITERATION DETECTED" in context:
        signals.append("iteration_detected")
    if "⚠️ VERIFICATION GAP" in context:
        signals.append("verification_gap")
    if "🛡️ QUALITY GATE" in context:
        signals.append("production_gate")
    if "💡 COMPLEXITY SMELL" in context:
        signals.append("complexity_smell")
    if "🧪 TEST STRATEGY" in context:
        signals.append("test_strategy")
    return signals


def test_introspector():
    """Run all test cases"""
    print("🧪 TESTING INTROSPECTOR HOOK")
    print("=" * 80)

    passed = 0
    failed = 0

    for test in TEST_PROMPTS:
        print(f"\n📝 Test: {test['name']}")
        print(f"   Prompt: {test['prompt'][:60]}...")

        result = run_introspector(test["prompt"])

        if "error" in result:
            print(f"   ❌ ERROR: {result['error']}")
            failed += 1
            continue

        context = result.get("hookSpecificOutput", {}).get("additionalContext", "")

        if not context:
            print(f"   ⚠️  No context generated")
            detected_signals = []
        else:
            detected_signals = extract_signals_from_context(context)
            print(f"   🔍 Detected: {detected_signals}")

        # Check if expected signals were detected
        expected = set(test["expected_signals"])
        detected = set(detected_signals)

        # At least one expected signal should be detected
        if expected & detected:
            print(f"   ✅ PASS (found {expected & detected})")
            passed += 1

            # Show context preview (first 150 chars)
            if context:
                preview = context.replace("\n", " ")[:150]
                print(f"   💬 Context: {preview}...")
        else:
            print(f"   ❌ FAIL (expected {expected}, got {detected})")
            failed += 1

            # Debug: Show full context
            if context:
                print(f"   📄 Full context:\n{context}")

    print("\n" + "=" * 80)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")

    if failed == 0:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(test_introspector())
