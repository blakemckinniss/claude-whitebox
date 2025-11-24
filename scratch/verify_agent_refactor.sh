#!/bin/bash
# Verification script for agent refactor

echo "======================================================================="
echo "AGENT REFACTOR VERIFICATION"
echo "======================================================================="
echo ""

echo "📊 AGENT COUNT:"
AGENT_COUNT=$(ls -1 .claude/agents/*.md 2>/dev/null | wc -l)
echo "  Total agents: $AGENT_COUNT (expected: 6)"
echo ""

echo "📝 REMAINING AGENTS:"
ls -1 .claude/agents/*.md | sed 's|.claude/agents/||' | sed 's|.md||' | while read agent; do
    echo "  ✅ $agent"
done
echo ""

echo "🔗 AUTO-INVOCATION HOOKS:"
if [ -f .claude/hooks/auto_researcher.py ]; then
    echo "  ✅ auto_researcher.py (PostToolUse - context firewall)"
else
    echo "  ❌ auto_researcher.py MISSING"
fi

if [ -f .claude/hooks/block_main_write.py ]; then
    echo "  ✅ block_main_write.py (PreToolUse - production code gate)"
else
    echo "  ❌ block_main_write.py MISSING"
fi

if [ -f .claude/hooks/detect_install.py ]; then
    echo "  ✅ detect_install.py (PreToolUse - anti-install)"
else
    echo "  ❌ detect_install.py MISSING"
fi
echo ""

echo "⚙️  HOOK REGISTRATION:"
REGISTERED=$(grep -c "auto_researcher\|block_main_write\|detect_install" .claude/settings.json)
echo "  Hooks in settings.json: $REGISTERED (expected: 3)"
echo ""

echo "🗑️  DELETED AGENTS:"
if [ ! -f .claude/agents/council-advisor.md ]; then
    echo "  ✅ council-advisor.md deleted"
else
    echo "  ❌ council-advisor.md still exists"
fi

if [ ! -f .claude/agents/critic.md ]; then
    echo "  ✅ critic.md deleted"
else
    echo "  ❌ critic.md still exists"
fi

if [ ! -f .claude/agents/runner.md ]; then
    echo "  ✅ runner.md deleted"
else
    echo "  ❌ runner.md still exists"
fi
echo ""

echo "📈 NEW AGENTS:"
if [ -f .claude/agents/tester.md ]; then
    echo "  ✅ tester.md created (TDD specialist)"
else
    echo "  ❌ tester.md MISSING"
fi

if [ -f .claude/agents/optimizer.md ]; then
    echo "  ✅ optimizer.md created (Performance specialist)"
else
    echo "  ❌ optimizer.md MISSING"
fi
echo ""

echo "📚 DOCUMENTATION UPDATED:"
if grep -q "AUTO-INVOKE" CLAUDE.md; then
    echo "  ✅ CLAUDE.md mentions AUTO-INVOKE"
else
    echo "  ❌ CLAUDE.md missing AUTO-INVOKE references"
fi

if grep -q "auto_researcher\|block_main_write\|detect_install" CLAUDE.md; then
    echo "  ✅ CLAUDE.md references new hooks"
else
    echo "  ❌ CLAUDE.md missing new hook references"
fi
echo ""

echo "🎯 EPISTEMOLOGY BONUSES:"
if grep -q "sherlock.*20" scripts/lib/epistemology.py && grep -q "macgyver.*15" scripts/lib/epistemology.py; then
    echo "  ✅ epistemology.py has sherlock/macgyver/tester/optimizer bonuses"
else
    echo "  ❌ epistemology.py missing agent bonuses"
fi
echo ""

echo "======================================================================="
echo "VERIFICATION COMPLETE"
echo "======================================================================="

# Summary
if [ "$AGENT_COUNT" -eq 6 ] && \
   [ -f .claude/hooks/auto_researcher.py ] && \
   [ -f .claude/hooks/block_main_write.py ] && \
   [ -f .claude/hooks/detect_install.py ] && \
   [ "$REGISTERED" -eq 3 ] && \
   [ ! -f .claude/agents/council-advisor.md ] && \
   [ ! -f .claude/agents/critic.md ] && \
   [ ! -f .claude/agents/runner.md ] && \
   [ -f .claude/agents/tester.md ] && \
   [ -f .claude/agents/optimizer.md ]; then
    echo ""
    echo "✅ ALL CHECKS PASSED - Refactor successful!"
    exit 0
else
    echo ""
    echo "⚠️  SOME CHECKS FAILED - Review above output"
    exit 1
fi
