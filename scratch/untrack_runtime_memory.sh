#!/bin/bash
# Untrack runtime state from git while preserving SDK configuration

cd /home/jinx/workspace/claude-whitebox

# Files to KEEP (SDK configuration/knowledge)
KEEP_FILES=(
  ".claude/memory/anti_patterns.md"
  ".claude/memory/automation_config.json"
  ".claude/memory/circuit_breaker_config.json"
  ".claude/memory/decisions.md"
  ".claude/memory/hook_registry.json"
  ".claude/memory/lessons.md"
  ".claude/memory/metacognition_patterns.json"
  ".claude/memory/scratch_index.json"
  ".claude/memory/settings_baseline.json"
  ".claude/memory/synapses.json"
)

# Get all currently tracked files in memory/
ALL_TRACKED=$(git ls-files .claude/memory/)

# Remove from tracking (but keep files locally)
echo "Untracking runtime state files..."
for file in $ALL_TRACKED; do
  # Check if file should be kept
  SHOULD_KEEP=false
  for keep in "${KEEP_FILES[@]}"; do
    if [[ "$file" == "$keep" ]]; then
      SHOULD_KEEP=true
      break
    fi
  done
  
  if [[ "$SHOULD_KEEP" == false ]]; then
    echo "  Untracking: $file"
    git rm --cached "$file" 2>/dev/null || true
  else
    echo "  Keeping: $file"
  fi
done

echo ""
echo "Done. Runtime state untracked but preserved locally."
echo "SDK configuration files remain committed."
