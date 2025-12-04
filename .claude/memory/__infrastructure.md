# Infrastructure Index

**CRITICAL: Read this BEFORE making any "create X" or "add Y" recommendations.**

## Setup Scripts (ALREADY EXIST)
- `.claude/config/setup_claude.sh` - Venv, deps, Playwright, project scaffolding
- `.claude/config/setup_project.sh` - Import existing repos, gitignore management

## Key Directories
| Path | Purpose | Count |
|------|---------|-------|
| `.claude/ops/` | Operational tools | 34 Python scripts |
| `.claude/hooks/` | Hook scripts | 53 Python scripts |
| `.claude/commands/` | Slash commands | 57 markdown files |
| `.claude/config/` | Configuration | personas, enforcement, setup |
| `.claude/memory/` | Persistent state | session, lessons, decisions |
| `.claude/lib/` | Shared code | core.py |
| `.claude/reminders/` | Dynamic context | YAML-triggered reminders |
| `.claude/agents/` | Agent configs | subagent definitions |

## API Dependencies
| Key | Used By | Required? |
|-----|---------|-----------|
| `OPENROUTER_API_KEY` | oracle, council, think, void, drift | Yes for AI features |
| `TAVILY_API_KEY` | research.py | Yes for web search |
| `CONTEXT7_API_KEY` | docs.py | Yes for doc lookup |
| `GROQ_API_KEY` | counterfactual_check, assumption_ledger | Optional (fast inference) |

## Core Infrastructure Files
- `.claude/lib/core.py` - Shared utilities (get_project_root, setup_script, finalize)
- `.claude/hooks/py` - Python environment shim (venv detection)
- `.claude/settings.json` - Hook wiring configuration
- `.claude/requirements.txt` - Python dependencies

## Before Recommending "Create X"
1. Check if X exists in this index
2. Search: `ls .claude/*/` or `grep -r "X" .claude/`
3. If similar exists, suggest modification not creation
