#!/usr/bin/env python3
"""Test scratch association accuracy"""
import subprocess
import json

test_cases = [
    {
        "query": "how to implement parallel hook testing with verification?",
        "expected_keywords": ["hook", "parallel", "test"]
    },
    {
        "query": "oracle consultation for architectural decisions",
        "expected_keywords": ["oracle", "decision", "architecture"]
    },
    {
        "query": "confidence tracking and epistemology enforcement",
        "expected_keywords": ["confidence", "epistemology", "enforcement"]
    },
    {
        "query": "batch file processing with parallel workers",
        "expected_keywords": ["parallel", "batch"]
    }
]

print("🧪 TESTING SCRATCH ASSOCIATION ACCURACY")
print("=" * 60)

total_tests = len(test_cases)
passed = 0

for i, test in enumerate(test_cases, 1):
    query = test['query']
    expected = set(test['expected_keywords'])
    
    # Call hook
    result = subprocess.run(
        ['python3', 'scratch/scratch_context_hook.py'],
        input=json.dumps({"prompt": query}),
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0 and result.stdout:
        try:
            response = json.loads(result.stdout)
            context = response.get('hookSpecificOutput', {}).get('additionalContext', '')
            
            # Check if expected keywords appear in context
            matched = sum(1 for kw in expected if kw in context.lower())
            accuracy = (matched / len(expected)) * 100
            
            status = "✅ PASS" if accuracy >= 50 else "❌ FAIL"
            print(f"\n{status} Test {i}: {query[:50]}...")
            print(f"   Accuracy: {accuracy:.0f}% ({matched}/{len(expected)} keywords matched)")
            print(f"   Context: {context[:150]}...")
            
            if accuracy >= 50:
                passed += 1
        except Exception as e:
            print(f"\n❌ FAIL Test {i}: Parse error - {e}")
    else:
        print(f"\n⚠️  SKIP Test {i}: No associations found (may be valid)")

print("\n" + "=" * 60)
print(f"📊 RESULTS: {passed}/{total_tests} tests passed ({(passed/total_tests)*100:.0f}%)")
print("=" * 60)
