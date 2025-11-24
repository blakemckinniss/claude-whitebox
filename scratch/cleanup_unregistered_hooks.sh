#!/bin/bash
# Cleanup Unregistered Hooks
# Removes obsolete/redundant hooks from .claude/hooks/

set -e

HOOKS_DIR=".claude/hooks"
ARCHIVE_DIR="scratch/archive/hooks"

echo "🧹 Cleaning up unregistered hooks..."
echo

# Create archive directory
mkdir -p "$ARCHIVE_DIR"

# 1. Delete redundant parallel_agent_reminder.py
if [ -f "$HOOKS_DIR/parallel_agent_reminder.py" ]; then
    echo "❌ Deleting: parallel_agent_reminder.py (redundant with meta_cognition_performance.py)"
    rm "$HOOKS_DIR/parallel_agent_reminder.py"
else
    echo "⚠️  Already deleted: parallel_agent_reminder.py"
fi

# 2. Delete experimental parallel_hook_executor.py
if [ -f "$HOOKS_DIR/parallel_hook_executor.py" ]; then
    echo "❌ Deleting: parallel_hook_executor.py (experimental, not integrated)"
    rm "$HOOKS_DIR/parallel_hook_executor.py"
else
    echo "⚠️  Already deleted: parallel_hook_executor.py"
fi

# 3. Delete obsolete performance_gate_temp.py
if [ -f "$HOOKS_DIR/performance_gate_temp.py" ]; then
    echo "❌ Deleting: performance_gate_temp.py (obsolete backup)"
    rm "$HOOKS_DIR/performance_gate_temp.py"
else
    echo "⚠️  Already deleted: performance_gate_temp.py"
fi

# 4. Archive hook_timing_wrapper.py (optional future use)
if [ -f "$HOOKS_DIR/hook_timing_wrapper.py" ]; then
    echo "📦 Archiving: hook_timing_wrapper.py → $ARCHIVE_DIR/"
    mv "$HOOKS_DIR/hook_timing_wrapper.py" "$ARCHIVE_DIR/"
else
    echo "⚠️  Already archived: hook_timing_wrapper.py"
fi

echo
echo "✅ Cleanup complete!"
echo
echo "Summary:"
echo "  • 3 files deleted (redundant/obsolete)"
echo "  • 1 file archived (potential future use)"
echo "  • absurdity_detector.py ready for registration"
echo

# Count remaining hooks
TOTAL_HOOKS=$(find "$HOOKS_DIR" -name "*.py" -type f | wc -l)
echo "📊 Remaining hooks in $HOOKS_DIR: $TOTAL_HOOKS"
