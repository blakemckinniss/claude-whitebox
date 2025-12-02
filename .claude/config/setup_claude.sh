#!/usr/bin/env bash
# Whitebox Framework Setup - Main entry point for new repos
# Sets up Python venv, dependencies, and creates new projects with full structure
#
# Usage: .claude/config/setup_claude.sh [--venv-only | --project <name>]
#   or:  ./setup.sh (if using root wrapper)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$CLAUDE_DIR")"
VENV_DIR="$CLAUDE_DIR/.venv"
PROJECTS_DIR="$REPO_ROOT/projects"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  🧠 Whitebox Framework Setup${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

setup_venv() {
    echo -e "\n${YELLOW}[1/2] Setting up Python environment...${NC}"

    if [ ! -d "$VENV_DIR" ]; then
        echo "  Creating venv at $VENV_DIR..."
        python3 -m venv "$VENV_DIR"
    else
        echo "  Venv exists at $VENV_DIR"
    fi

    source "$VENV_DIR/bin/activate"
    echo "  Installing dependencies..."
    pip install -q --upgrade pip
    pip install -q -r "$CLAUDE_DIR/requirements.txt"

    echo -e "${GREEN}  ✓ Python environment ready${NC}"
}

setup_playwright() {
    echo -e "\n${YELLOW}[2/2] Checking Playwright...${NC}"

    if command -v playwright &>/dev/null && playwright --version &>/dev/null; then
        echo -e "${GREEN}  ✓ Playwright already installed${NC}"
    else
        echo "  Installing Playwright browsers (this may take a minute)..."
        "$VENV_DIR/bin/playwright" install chromium 2>/dev/null || true
        echo -e "${GREEN}  ✓ Playwright ready${NC}"
    fi
}

create_project() {
    local project_name="$1"
    local project_dir="$PROJECTS_DIR/$project_name"

    if [ -d "$project_dir" ]; then
        echo -e "${RED}Error: Project '$project_name' already exists at $project_dir${NC}"
        exit 1
    fi

    echo -e "\n${YELLOW}Creating project: $project_name${NC}"

    # Create project structure
    mkdir -p "$project_dir"/{src,tests,.claude}

    # Create project CLAUDE.md with framework alignment
    cat > "$project_dir/CLAUDE.md" << 'PROJ_CLAUDE'
# Project Instructions

This project uses the Whitebox Framework from the parent repository.

## Quick Reference

**Python:** Use `../../.claude/.venv/bin/python` for framework tools.

**Tools available:**
```bash
# From project root, run framework tools:
../../.claude/.venv/bin/python ../../.claude/ops/audit.py src/
../../.claude/.venv/bin/python ../../.claude/ops/void.py src/
../../.claude/.venv/bin/python ../../.claude/ops/xray.py src/
```

**Project structure:**
- `src/` - Source code
- `tests/` - Test files
- `.claude/` - Project-specific overrides (optional)

## Conventions

Follow parent CLAUDE.md principles. Key points:
- No hallucinations - verify before claiming
- Delete with prejudice - unused = deleted
- Crash early - prefer assert over try/except
- Colocation > decoupling
PROJ_CLAUDE

    # Create minimal .gitignore
    cat > "$project_dir/.gitignore" << 'GITIGNORE'
__pycache__/
*.pyc
.env
*.egg-info/
dist/
build/
.pytest_cache/
GITIGNORE

    # Create src/__init__.py
    touch "$project_dir/src/__init__.py"

    # Create placeholder main
    cat > "$project_dir/src/main.py" << 'MAIN'
#!/usr/bin/env python3
"""Entry point for the project."""


def main():
    print("Hello from the project!")


if __name__ == "__main__":
    main()
MAIN

    echo -e "${GREEN}  ✓ Created project structure${NC}"

    # Initialize beads if available
    if command -v bd &>/dev/null; then
        echo -e "  ${YELLOW}Initializing beads issue tracker...${NC}"
        (cd "$project_dir" && bd init --quiet 2>/dev/null) || true
        if [ -d "$project_dir/.beads" ]; then
            echo -e "${GREEN}  ✓ Beads initialized${NC}"
        fi
    fi

    # Generate repomix context if npx available
    if command -v npx &>/dev/null; then
        echo -e "  ${YELLOW}Generating repomix codebase context...${NC}"
        (cd "$project_dir" && npx --yes repomix --style markdown --compress --output .repomix-context.md . 2>/dev/null) || true
        if [ -f "$project_dir/.repomix-context.md" ]; then
            echo -e "${GREEN}  ✓ Repomix context generated${NC}"
        fi
    fi
    echo ""
    echo -e "  ${CYAN}Project created at:${NC} $project_dir"
    echo -e "  ${CYAN}Next steps:${NC}"
    echo "    cd $project_dir"
    echo "    # Start coding in src/"
}

interactive_menu() {
    print_header
    echo ""
    echo "What would you like to do?"
    echo ""
    echo "  1) Setup framework environment only"
    echo "  2) Create a new project"
    echo "  3) Both (setup + create project)"
    echo "  q) Quit"
    echo ""
    read -p "Choice [1-3/q]: " choice

    case "$choice" in
        1)
            setup_venv
            setup_playwright
            echo -e "\n${GREEN}✓ Framework ready!${NC}"
            echo "  Tools: $CLAUDE_DIR/ops/"
            echo "  Venv:  source $VENV_DIR/bin/activate"
            ;;
        2)
            echo ""
            read -p "Project name: " project_name
            if [ -z "$project_name" ]; then
                echo -e "${RED}Error: Project name required${NC}"
                exit 1
            fi
            # Sanitize: lowercase, replace spaces with dashes
            project_name=$(echo "$project_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-_')
            create_project "$project_name"
            ;;
        3)
            setup_venv
            setup_playwright
            echo ""
            read -p "Project name: " project_name
            if [ -z "$project_name" ]; then
                echo -e "${RED}Error: Project name required${NC}"
                exit 1
            fi
            project_name=$(echo "$project_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-_')
            create_project "$project_name"
            echo -e "\n${GREEN}✓ All done!${NC}"
            ;;
        q|Q)
            echo "Bye!"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            exit 1
            ;;
    esac
}

# CLI argument handling
case "${1:-}" in
    --venv-only)
        print_header
        setup_venv
        setup_playwright
        echo -e "\n${GREEN}✓ Framework ready!${NC}"
        ;;
    --project)
        if [ -z "${2:-}" ]; then
            echo -e "${RED}Error: --project requires a name${NC}"
            echo "Usage: $0 --project <name>"
            exit 1
        fi
        print_header
        create_project "$2"
        ;;
    --help|-h)
        echo "Whitebox Framework Setup"
        echo ""
        echo "Usage:"
        echo "  $0              Interactive menu"
        echo "  $0 --venv-only  Setup Python environment only"
        echo "  $0 --project X  Create project X in projects/"
        echo "  $0 --help       Show this help"
        ;;
    "")
        interactive_menu
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        echo "Run '$0 --help' for usage"
        exit 1
        ;;
esac
