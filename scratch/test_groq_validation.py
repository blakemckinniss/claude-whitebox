#!/usr/bin/env python3
"""
Test input validation and error handling for groq.py
"""
import subprocess
import sys

def run_groq(*args):
    """Run groq.py with args and return result"""
    cmd = [sys.executable, "scripts/ops/groq.py"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10
    )
    return result.returncode, result.stdout, result.stderr

print("=" * 70)
print("GROQ.PY VALIDATION TESTS")
print("=" * 70)

# Test 1: Invalid temperature (too low)
print("\nTest 1: Temperature too low (-0.5)...")
code, stdout, stderr = run_groq("--temperature", "-0.5", "test")
assert code != 0, "Should reject negative temperature"
assert "Temperature must be between 0 and 2" in stderr, "Should show temperature error"
print("  ✅ Rejects negative temperature")

# Test 2: Invalid temperature (too high)
print("\nTest 2: Temperature too high (3.0)...")
code, stdout, stderr = run_groq("--temperature", "3.0", "test")
assert code != 0, "Should reject temperature > 2"
assert "Temperature must be between 0 and 2" in stderr, "Should show temperature error"
print("  ✅ Rejects temperature > 2")

# Test 3: Invalid max_tokens (negative)
print("\nTest 3: Negative max_tokens...")
code, stdout, stderr = run_groq("--max-tokens", "-100", "test")
assert code != 0, "Should reject negative max_tokens"
assert "Max tokens must be positive" in stderr, "Should show max_tokens error"
print("  ✅ Rejects negative max_tokens")

# Test 4: Invalid max_tokens (zero)
print("\nTest 4: Zero max_tokens...")
code, stdout, stderr = run_groq("--max-tokens", "0", "test")
assert code != 0, "Should reject zero max_tokens"
assert "Max tokens must be positive" in stderr, "Should show max_tokens error"
print("  ✅ Rejects zero max_tokens")

# Test 5: Valid temperature boundaries
print("\nTest 5: Valid temperature boundaries...")
code1, _, _ = run_groq("--dry-run", "--temperature", "0", "test")
code2, _, _ = run_groq("--dry-run", "--temperature", "2", "test")
assert code1 == 0, "Should accept temperature=0"
assert code2 == 0, "Should accept temperature=2"
print("  ✅ Accepts valid temperature range (0-2)")

# Test 6: Valid max_tokens
print("\nTest 6: Valid max_tokens...")
code, _, _ = run_groq("--dry-run", "--max-tokens", "1", "test")
assert code == 0, "Should accept max_tokens=1"
print("  ✅ Accepts positive max_tokens")

print("\n" + "=" * 70)
print("RESULTS: All validation tests passed ✅")
print("=" * 70)
