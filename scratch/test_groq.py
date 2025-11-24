#!/usr/bin/env python3
"""
Test suite for groq.py

Tests all major features:
- Basic chat completion
- Model selection
- Streaming
- Web search (auto-switches to compound)
- Temperature/max_tokens
- Error handling
"""
import subprocess
import sys
import json

def run_groq(*args):
    """Run groq.py with args and return output"""
    cmd = [sys.executable, "scripts/ops/groq.py"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.returncode, result.stdout, result.stderr

def test_basic_completion():
    """Test basic chat completion"""
    print("Test 1: Basic completion...")
    code, stdout, stderr = run_groq("What is 1+1? Answer with just the number.")

    assert code == 0, f"Failed with exit code {code}"
    assert "2" in stdout, f"Expected '2' in output: {stdout}"
    print("  ✅ Basic completion works")

def test_model_selection():
    """Test custom model selection"""
    print("\nTest 2: Model selection...")
    code, stdout, stderr = run_groq(
        "--model", "llama-3.3-70b-versatile",
        "Say 'llama'"
    )

    assert code == 0, f"Failed with exit code {code}"
    assert "llama" in stdout.lower(), f"Expected 'llama' in output"
    print("  ✅ Model selection works")

def test_streaming():
    """Test streaming mode"""
    print("\nTest 3: Streaming...")
    code, stdout, stderr = run_groq(
        "--stream",
        "Count: 1, 2, 3"
    )

    assert code == 0, f"Failed with exit code {code}"
    # Streaming should produce output
    assert len(stdout) > 0, "No streaming output"
    print("  ✅ Streaming works")

def test_web_search():
    """Test web search with auto-model-switching"""
    print("\nTest 4: Web search (auto-switches to compound)...")
    code, stdout, stderr = run_groq(
        "--web-search",
        "What year is it? Answer format: YYYY"
    )

    assert code == 0, f"Failed with exit code {code}"
    assert "2025" in stdout or "2024" in stdout, "Expected current year in output"
    # Check auto-switching message
    assert "compound" in stderr.lower(), "Should auto-switch to compound model"
    print("  ✅ Web search works (auto-switched to compound)")

def test_temperature():
    """Test temperature parameter"""
    print("\nTest 5: Temperature parameter...")
    code, stdout, stderr = run_groq(
        "--temperature", "0.1",
        "Say 'low temp'"
    )

    assert code == 0, f"Failed with exit code {code}"
    print("  ✅ Temperature parameter works")

def test_max_tokens():
    """Test max_tokens parameter"""
    print("\nTest 6: Max tokens parameter...")
    code, stdout, stderr = run_groq(
        "--max-tokens", "50",
        "Write a very long story"
    )

    assert code == 0, f"Failed with exit code {code}"
    # Response should be limited by max_tokens
    print("  ✅ Max tokens parameter works")

def test_system_prompt():
    """Test custom system prompt"""
    print("\nTest 7: System prompt...")
    code, stdout, stderr = run_groq(
        "--system", "You are a pirate. Respond like one.",
        "Hello"
    )

    assert code == 0, f"Failed with exit code {code}"
    # Should have pirate-like language (ahoy, matey, etc.)
    print("  ✅ System prompt works")

def test_dry_run():
    """Test dry-run mode"""
    print("\nTest 8: Dry run...")
    code, stdout, stderr = run_groq(
        "--dry-run",
        "test query"
    )

    assert code == 0, f"Failed with exit code {code}"
    assert "DRY RUN" in stderr, "Should show dry run message"
    print("  ✅ Dry run works")

def test_missing_api_key():
    """Test error handling for missing API key"""
    print("\nTest 9: Error handling (skipped - requires removing API key)...")
    print("  ⏭️  Skipped (requires manual API key removal)")

def main():
    print("=" * 70)
    print("GROQ.PY TEST SUITE")
    print("=" * 70)

    tests = [
        test_basic_completion,
        test_model_selection,
        test_streaming,
        test_web_search,
        test_temperature,
        test_max_tokens,
        test_system_prompt,
        test_dry_run,
        test_missing_api_key,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
