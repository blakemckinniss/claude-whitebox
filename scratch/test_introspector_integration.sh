#!/bin/bash
# Integration test: Verify introspector hook is registered and working

echo "🧪 INTROSPECTOR INTEGRATION TEST"
echo "================================="
echo ""

# Test 1: Check hook file exists
echo "📝 Test 1: Hook file exists"
if [ -f ".claude/hooks/introspector.py" ]; then
    echo "   ✅ PASS: .claude/hooks/introspector.py found"
else
    echo "   ❌ FAIL: Hook file missing"
    exit 1
fi

# Test 2: Check hook is executable
echo ""
echo "📝 Test 2: Hook is executable"
if [ -x ".claude/hooks/introspector.py" ]; then
    echo "   ✅ PASS: Hook is executable"
else
    echo "   ❌ FAIL: Hook not executable"
    exit 1
fi

# Test 3: Check pattern database exists
echo ""
echo "📝 Test 3: Pattern database exists"
if [ -f ".claude/memory/metacognition_patterns.json" ]; then
    echo "   ✅ PASS: metacognition_patterns.json found"
else
    echo "   ❌ FAIL: Pattern database missing"
    exit 1
fi

# Test 4: Validate pattern JSON
echo ""
echo "📝 Test 4: Pattern JSON is valid"
if python3 -m json.tool .claude/memory/metacognition_patterns.json > /dev/null 2>&1; then
    echo "   ✅ PASS: JSON is valid"
else
    echo "   ❌ FAIL: JSON is malformed"
    exit 1
fi

# Test 5: Check hook is registered in settings
echo ""
echo "📝 Test 5: Hook registered in settings.json"
if grep -q "introspector.py" .claude/settings.json; then
    echo "   ✅ PASS: Hook registered in settings.json"
else
    echo "   ❌ FAIL: Hook not registered"
    exit 1
fi

# Test 6: Run hook with test input (browser automation signal)
echo ""
echo "📝 Test 6: Hook executes without errors"
TEST_INPUT='{"prompt": "How do I scrape Amazon prices?", "session_id": "test"}'
RESULT=$(echo "$TEST_INPUT" | python3 .claude/hooks/introspector.py 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "   ✅ PASS: Hook executed successfully"
else
    echo "   ❌ FAIL: Hook failed with exit code $EXIT_CODE"
    echo "   Output: $RESULT"
    exit 1
fi

# Test 7: Verify output contains expected signal
echo ""
echo "📝 Test 7: Hook detects browser automation signal"
if echo "$RESULT" | grep -q "PLAYWRIGHT SIGNAL"; then
    echo "   ✅ PASS: Browser automation signal detected"
else
    echo "   ❌ FAIL: Signal not detected"
    echo "   Output: $RESULT"
    exit 1
fi

# Test 8: Run full test suite
echo ""
echo "📝 Test 8: Full test suite"
if python3 scratch/test_introspector.py > /dev/null 2>&1; then
    echo "   ✅ PASS: All 10 tests passing"
else
    echo "   ❌ FAIL: Test suite failed"
    python3 scratch/test_introspector.py
    exit 1
fi

echo ""
echo "================================="
echo "✅ ALL INTEGRATION TESTS PASSED"
echo ""
echo "📊 Summary:"
echo "   • Hook file: ✅ Present and executable"
echo "   • Pattern DB: ✅ Valid JSON"
echo "   • Registration: ✅ In settings.json"
echo "   • Execution: ✅ No errors"
echo "   • Detection: ✅ Signals working"
echo "   • Test Suite: ✅ 10/10 passing"
echo ""
echo "🚀 Introspector Protocol is OPERATIONAL"
