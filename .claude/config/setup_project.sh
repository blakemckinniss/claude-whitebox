#!/usr/bin/env bash
# Quick Project Import - Creates empty folder or clones git repo into projects/
# Use this for importing EXISTING repos. For NEW projects with full structure,
# use setup_claude.sh --project <name> instead.
#
# Usage: .claude/config/setup_project.sh <name|git-url> [--ignore]

set -e

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROJECTS_DIR="$REPO_ROOT/projects"
GITIGNORE="$REPO_ROOT/.gitignore"

usage() {
    echo "Usage: $0 <name|git-url> [--ignore]"
    echo ""
    echo "Arguments:"
    echo "  name      Create empty project folder"
    echo "  git-url   Clone repository into projects/"
    echo ""
    echo "Options:"
    echo "  --ignore  Add project to .gitignore"
    echo ""
    echo "Examples:"
    echo "  $0 myapp"
    echo "  $0 https://github.com/user/repo.git"
    echo "  $0 myapp --ignore"
    exit 1
}

# Parse args
[[ $# -lt 1 ]] && usage

TARGET="$1"
ADD_IGNORE=false
[[ "${2:-}" == "--ignore" ]] && ADD_IGNORE=true

# Determine if git URL or plain name
if [[ "$TARGET" =~ ^(https?://|git@) ]]; then
    # Git URL - extract repo name
    PROJECT_NAME=$(basename "$TARGET" .git)
    PROJECT_DIR="$PROJECTS_DIR/$PROJECT_NAME"

    [[ -d "$PROJECT_DIR" ]] && { echo "Error: $PROJECT_DIR already exists"; exit 1; }

    echo "Cloning $TARGET..."
    git clone "$TARGET" "$PROJECT_DIR"
else
    # Plain name
    PROJECT_NAME="$TARGET"
    PROJECT_DIR="$PROJECTS_DIR/$PROJECT_NAME"

    [[ -d "$PROJECT_DIR" ]] && { echo "Error: $PROJECT_DIR already exists"; exit 1; }

    echo "Creating $PROJECT_DIR..."
    mkdir -p "$PROJECT_DIR"
    touch "$PROJECT_DIR/.gitkeep"
fi

# Add to .gitignore if requested
if $ADD_IGNORE; then
    if ! grep -qxF "projects/$PROJECT_NAME/" "$GITIGNORE" 2>/dev/null; then
        echo "projects/$PROJECT_NAME/" >> "$GITIGNORE"
        echo "Added projects/$PROJECT_NAME/ to .gitignore"
    fi
fi

echo "✓ Project ready: $PROJECT_DIR"
