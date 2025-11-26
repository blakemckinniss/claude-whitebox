# Whitebox Slash Commands

This directory contains 18 custom slash commands that wrap the Whitebox SDK ops scripts.

## 🧠 Cognition (Decision Making)

| Command | Description | Usage |
|---------|-------------|-------|
| `/council` | 🏛️ The Council - Parallel multi-perspective analysis | `/council "Should we migrate to microservices?"` |
| `/judge` | ⚖️ The Judge - Value assurance, ROI, YAGNI | `/judge "Add GraphQL layer"` |
| `/critic` | 🥊 The Critic - The 10th Man, attacks assumptions | `/critic "Use serverless architecture"` |
| `/skeptic` | 🔍 The Skeptic - Hostile review, finds failure modes | `/skeptic "Deploy on Fridays"` |
| `/think` | 🧠 The Thinker - Decomposes complex problems | `/think "Implement OAuth flow"` |
| `/consult` | 🔮 The Oracle - High-level reasoning | `/consult "Best pattern for rate limiting"` |

## 🔎 Investigation (Information Gathering)

| Command | Description | Usage |
|---------|-------------|-------|
| `/research` | 🌐 The Researcher - Live web search | `/research "Playwright best practices 2025"` |
| `/probe` | 🔬 The Probe - Runtime API introspection | `/probe "pandas.DataFrame"` |
| `/xray` | 🔬 X-Ray - AST structural code search | `/xray --type class --name User` |
| `/spark` | ⚡ Synapse Fire - Associative memory retrieval | `/spark "database migration"` |

## ✅ Verification (Quality Assurance)

| Command | Description | Usage |
|---------|-------------|-------|
| `/verify` | 🤥 Reality Check - Anti-gaslighting verification | `/verify file_exists .env` |
| `/audit` | 🛡️ The Sheriff - Code quality audit | `/audit .claude/ops/council.py` |
| `/void` | 🕳️ The Void Hunter - Completeness checking | `/void .claude/ops/` |
| `/drift` | ⚖️ The Court - Style consistency check | `/drift` |

## 🛠️ Operations (Project Management)

| Command | Description | Usage |
|---------|-------------|-------|
| `/scope` | 🏁 The Finish Line - Definition of Done tracker | `/scope init "Refactor auth system"` |
| `/remember` | 🐘 The Elephant - Persistent memory | `/remember add lessons "Never deploy on Fridays"` |
| `/upkeep` | 🧹 The Janitor - Project maintenance | `/upkeep` |
| `/inventory` | 🖇️ MacGyver Scan - System tool scanner | `/inventory --compact` |

## 💡 Quick Examples

### Before making a big decision:
```
/council "Rewrite the backend in Rust"
```

### Before coding with a new library:
```
/research "FastAPI dependency injection patterns"
/probe "fastapi.Depends"
```

### Before claiming you fixed something:
```
/verify command_success "pytest tests/"
```

### To manage a complex task:
```
/scope init "Implement payment processing"
/scope check 1
/scope status
```

## 🔧 How It Works

- **Location**: `.claude/commands/*.md` (project-level commands)
- **Execution**: The `!` prefix executes bash commands immediately
- **Arguments**: `$ARGUMENTS` captures all args, `$1`, `$2`, etc. for positional args
- **Discovery**: Commands automatically appear in `/help`

## 📚 Related Documentation

- See `CLAUDE.md` for full protocol descriptions
- See `.claude/ops/` for the underlying Python scripts
- See Claude Code docs for slash command syntax: https://docs.claude.com/en/slash-commands
