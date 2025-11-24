#!/bin/bash
# Debug enforcement hook

echo "Test 1: Scratch path (should allow once)"
echo '{"toolName": "Write", "toolParams": {"file_path": "scratch/test.py"}, "recentPrompts": ["All error"]}' | python3 scratch/enforce_reasoning_rigor.py

echo -e "\n\nTest 2: Production path with violation (should deny once)"
echo '{"toolName": "Write", "toolParams": {"file_path": "scripts/ops/test.py"}, "recentPrompts": ["All error handlers"]}' | python3 scratch/enforce_reasoning_rigor.py

echo -e "\n\nTest 3: SUDO override (should allow once)"
echo '{"toolName": "Write", "toolParams": {"file_path": "scripts/ops/test.py"}, "recentPrompts": ["SUDO All error handlers"]}' | python3 scratch/enforce_reasoning_rigor.py
