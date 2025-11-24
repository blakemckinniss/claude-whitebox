#!/bin/bash
# Push all pending commits to GitHub

cd /home/jinx/workspace/claude-whitebox

# Keep pushing until we're in sync
for i in {1..10}; do
    # Commit any pending changes
    git add -A
    git commit -m "chore: Auto-commit session state" 2>/dev/null || true

    # Push
    git push origin master

    # Check if we're in sync
    behind=$(git rev-list --count origin/master..master)
    if [ "$behind" -eq 0 ]; then
        echo "✅ All commits pushed successfully"
        git status
        exit 0
    fi

    echo "Still $behind commits ahead, pushing again..."
    sleep 0.5
done

echo "⚠️  May still have commits pending"
git status
