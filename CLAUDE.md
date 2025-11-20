# Project Architecture & Commands

## 🧠 Core Philosophy: "Whitebox Engineering"
**WE DO NOT USE BLACKBOX MCP TOOLS.**
We rely on **transparent, executable code**. If you cannot read the code that performs an action, you do not run it.

## 🛠️ The Workflow Decision Matrix
Before taking action, categorize the task:

### 1. Is it a Primitive Operation? (Navigation, IO, Basic Shell)
✅ **Use Native Tools (`Read`, `Edit`, `Bash`, `Glob`, `Grep`)**
*   *Examples:* Checking if a file exists, reading a config, `ls -la`, `grep "TODO"`.
*   **Goal:** Speed and efficiency. Don't write a script just to `cat` a file.

### 2. Is it a Structural Question? (Definitions, Inheritance, Dependencies)
🔬 **Use The X-Ray (`scripts/ops/xray.py`)**
*   *Examples:* "Where is class `User` defined?", "Who imports `requests`?", "Find functions with `@tool` decorator."
*   **Why:** `grep` is blind to context. X-Ray sees the code structure via AST parsing.
*   **Goal:** Semantic understanding beyond text matching.

### 3. Is it a Logic or External Operation? (APIs, DBs, Data Munging)
📝 **Write a Script (`scratch/` or `scripts/`)**
*   *Examples:* Querying Snowflake, fetching GitHub issues, parsing complex JSON logs.
*   **Goal:** Transparency and Reusability. We want an artifact we can debug and version control.

---

## 🔮 The Oracle Protocol

**Before writing code for any complex task (architectural decisions, refactoring, system design):**

### When to Consult The Oracle
- Architecture decisions (database schema, API design)
- Large refactoring efforts (restructuring multiple components)
- Performance optimization strategies
- Security design patterns
- Complex algorithm selection
- Integration patterns for external systems

### The Consultation Flow
1.  **Identify Complexity:** Task requires significant design thinking or has multiple valid approaches
2.  **Consult:** Run `python3 scripts/ops/consult.py "Problem description and context"`
3.  **Review:** Read the `[🧠 ORACLE REASONING]` section for edge cases and considerations
4.  **Implement:** Use the `[💡 ORACLE ADVICE]` to guide your implementation
5.  **Validate:** Run tests to ensure the approach works

### Example Usage
```bash
# Consult on database design
python3 scripts/ops/consult.py "I need to design a schema for multi-tenant SaaS application. Each tenant has users, projects, and tasks. What's the best isolation strategy?"

# Consult on refactoring approach
python3 scripts/ops/consult.py "Current authentication uses JWT tokens stored in localStorage. Need to migrate to httpOnly cookies. What's the safest migration path?"

# Dry-run to preview prompt
python3 scripts/ops/consult.py "How should I structure microservices communication?" --dry-run
```

### Configuration
- Set `OPENROUTER_API_KEY` in your `.env` file
- Default model: `google/gemini-2.0-flash-thinking-exp:free`
- Override with: `--model google/deepseek-r1-distill-llama-70b:free`

### Philosophy
The Oracle is a **Whitebox reasoning augmentation**, not a blackbox. The script's code is transparent, the API call is visible, and all reasoning is printed to stdout for audit. You maintain full control and visibility.

---

## 🌐 The Research Protocol

**Your internal training data is STALE (Cutoff: January 2025).**

You **MUST** run `scripts/ops/research.py` BEFORE writing code if the task involves:

### When to Research
1. **New/Updated Libraries:** Any library updated in the last 18 months (Next.js, React, LangChain, AWS SDKs, Python packages)
2. **Error Messages:** If you encounter an error, search it verbatim before attempting fixes
3. **API Documentation:** Never guess API methods - search for current docs
4. **Best Practices:** When implementing patterns you're uncertain about
5. **Version-Specific Features:** When using specific versions of tools/frameworks
6. **Breaking Changes:** When upgrading dependencies or migrating code

### The Research Loop
1. **Identify:** Task requires current information beyond your training cutoff
2. **Search:** `python3 scripts/ops/research.py "current python openai library usage"`
3. **Analyze:** Read the direct answer and top sources carefully
4. **Implement:** Write code based **only** on search results, not stale memory
5. **Validate:** Verify implementation matches current documentation

### Example Usage
```bash
# Search for current API usage
python3 scripts/ops/research.py "python openai library chat completion example 2025"

# Deep search for complex topics
python3 scripts/ops/research.py "nextjs 15 app router best practices" --deep

# Debug error messages
python3 scripts/ops/research.py "TypeError: 'NoneType' object is not subscriptable python fix"

# Check version-specific features
python3 scripts/ops/research.py "react 19 new hooks useOptimistic" --max-results 10

# Dry-run to preview query
python3 scripts/ops/research.py "tailwind css 4 features" --dry-run
```

### Configuration
- Set `TAVILY_API_KEY` in your `.env` file
- Get API key at: https://tavily.com/
- Default: 5 results, basic search depth
- Use `--deep` for thorough research (slower, more comprehensive)
- Use `--max-results N` to control result count

### Philosophy
The Researcher is **Whitebox real-time intelligence**. The script's code is transparent, API calls are visible, and all sources are printed to stdout with URLs for verification. You can audit every piece of information and trace it back to its source.

---

## 🔬 The Probe Protocol (Anti-Hallucination)

**The Core Problem:** LLMs work on probability, not truth. When you write `client.get_user(id)`, it's not because you *know* that function exists; it's because that sequence of tokens is statistically likely.

**The Solution:** You must **interrogate the runtime environment** before claiming to know it.

### The "No-Guess" Rule

You are **FORBIDDEN** from assuming an API method exists, especially for:
- Libraries you haven't used in this session
- Objects returned by complex API calls (HTTP responses, database cursors, API clients)
- "Standard" libraries that change often (pandas, requests, boto3, pydantic, openai, etc.)
- Any library method where you're uncertain about the signature

### The Inspection Loop

Before writing implementation logic:

1. **Probe:** Run `python3 scripts/ops/probe.py <library_or_object>`
2. **Verify:** Check if the method you *thought* existed is actually in the list
3. **Confirm Signature:** If it exists, inspect the exact signature
4. **Code:** Only use methods that appeared in the Probe output

### Example Usage

```bash
# Inspect a module
python3 scripts/ops/probe.py json

# Inspect a nested object
python3 scripts/ops/probe.py os.path

# Filter by method name
python3 scripts/ops/probe.py pandas.DataFrame --grep to_dict

# Inspect a specific method's signature
python3 scripts/ops/probe.py json.loads

# Include dunder methods
python3 scripts/ops/probe.py requests.Response --show-dunder
```

### The Right Way vs The Wrong Way

❌ **Wrong:**
```
"I'll use `df.to_dict(orient='records')` because I think that's right."
*Writes code. It breaks. Asks user for help.*
```

✅ **Right:**
```
1. Run: `python3 scripts/ops/probe.py pandas.DataFrame --grep to_dict`
2. Verify: "I see `to_dict` in the output."
3. Run: `python3 scripts/ops/probe.py pandas.DataFrame.to_dict`
4. Confirm: "The signature shows `orient` is a valid arg."
5. NOW write the code with confidence.
```

### The Knowledge Pyramid

You now have three layers solving "Unknown Unknowns":

1. **"I don't know the concept"** → **The Oracle** (OpenRouter) handles architecture
2. **"I don't know the facts"** → **The Researcher** (Tavily) fetches current docs
3. **"I don't know the syntax"** → **The Probe** (Runtime Inspector) verifies code

This eliminates hallucinations because the system forces you to traverse this pyramid before writing production code.

### Philosophy

The Probe is **Whitebox runtime verification**. The script's code is transparent, imports are explicit, and all introspection happens via Python's standard `inspect` module. You're not guessing—you're reading the actual runtime state.

---

## 🔬 The X-Ray Protocol (Structural Code Search)

**The Core Problem:** `grep` finds text, not structure. When you search for "class User", grep returns every line containing that string: definitions, imports, comments, docstrings. You wanted the definition, not 50 usages.

**The Solution:** AST-based semantic search that understands Python code structure.

### Text Search vs Structure Search

**Text Search (`grep`):**
- Finds strings like "User" anywhere in text
- Cannot distinguish between definition, usage, or comment
- Returns overwhelming results (definitions mixed with usages)
- Blind to code relationships (inheritance, decorators, call chains)

**Structure Search (`xray.py`):**
- Parses Python AST (Abstract Syntax Tree)
- Finds definitions, not mentions
- Understands classes, functions, imports, calls, decorators
- Shows inheritance hierarchies and function signatures

### When to Use X-Ray

Use X-Ray for **structural questions**:
- "Where is class `X` defined?" → Find class definitions
- "What does class `Y` inherit from?" → See base classes
- "Which functions have the `@retry` decorator?" → Find decorators
- "Who imports `requests`?" → Track import dependencies
- "Where is function `foo` called?" → Find call sites
- "List all functions in module X" → Catalog API surface

Use `grep` for **content questions**:
- "Which files mention 'TODO'?" → Text search
- "Find error messages containing 'failed'" → Text search
- "Where is this exact code snippet?" → Text search

### Example Usage

```bash
# Find class definitions
python3 scripts/ops/xray.py scripts/ --type class --name User

# Find what a class inherits from (with details)
python3 scripts/ops/xray.py . --type class --name Model --details

# Find functions with specific decorator
python3 scripts/ops/xray.py . --type decorator --name tool

# Find all imports of a module
python3 scripts/ops/xray.py . --type import --name requests

# Find where a function is called
python3 scripts/ops/xray.py . --type call --name setup_script

# Find functions matching a pattern (regex)
python3 scripts/ops/xray.py . --type function --name "^test_"

# Scan specific file
python3 scripts/ops/xray.py scripts/lib/core.py --type function

# Find all structures (functions, classes, imports)
python3 scripts/ops/xray.py scripts/ --type all
```

### Output Format

**Function Definitions:**
```
🔹 DEF: setup_script(description) @deprecated
   📍 scripts/lib/core.py:21
   📄 Creates argument parser with standard flags
```

**Class Definitions:**
```
📦 CLASS: CodeVisitor (inherits: ast.NodeVisitor) @dataclass
   📍 scripts/ops/xray.py:28
   📄 AST visitor that finds and reports code structures
```

**Imports:**
```
📥 IMPORT: from core import setup_script
   📍 scripts/ops/probe.py:25
```

**Function Calls:**
```
📞 CALL: logger.info()
   📍 scripts/ops/upkeep.py:318
```

### The Right Way vs The Wrong Way

❌ **Wrong (grep):**
```
User: "Where is the Process class defined?"
Claude: *Runs grep -r "class Process"*
Result: 15 matches (definitions, imports, comments, docstrings)
Claude: *Reads through all 15 to find the actual definition*
```

✅ **Right (X-Ray):**
```
User: "Where is the Process class defined?"
Claude: *Runs xray.py --type class --name Process*
Result: 📦 CLASS: Process (inherits: Base, Runnable)
        📍 scripts/lib/process.py:42
Claude: "It's defined at scripts/lib/process.py:42 and inherits from Base and Runnable."
```

### Technical Implementation

X-Ray uses Python's built-in `ast` module to:
1. Parse Python files into Abstract Syntax Trees
2. Walk the AST nodes (FunctionDef, ClassDef, Import, Call, etc.)
3. Match nodes against search criteria (type + name pattern)
4. Extract semantic information (args, bases, decorators, docstrings)
5. Report results grouped by file

No external dependencies. No AI inference. Pure structural analysis.

### Philosophy

The X-Ray is **Whitebox semantic search**. The script's code is transparent, uses only Python stdlib (`ast`), and all analysis is deterministic. You're not text-matching—you're understanding code structure.

---

## 🐘 The Elephant Protocol (Memory Management)

**Context Window ≠ Memory.** You suffer from amnesia. To survive, externalize your memory.

### The Problem
- Context windows fill up → architectural decisions forgotten
- Regression loops: fixing the same bug multiple times
- Session amnesia: no memory of what was being worked on
- Lost lessons: repeating the same mistakes

### The Solution: Three Layers of Memory

**1. Active Context (`.claude/memory/active_context.md`) - Short Term**
- What are we working on *right now*?
- Current sprint, status, next steps, blockers
- Updated frequently during active work

**2. Decisions (`.claude/memory/decisions.md`) - Medium Term**
- Why did we choose this library/pattern/structure?
- Architectural Decision Records (ADRs)
- Prevents architectural drift

**3. Lessons (`.claude/memory/lessons.md`) - Long Term**
- What tried to kill us? What failed?
- Bug patterns, wrong assumptions, gotchas
- Prevents repeating mistakes

### Usage

**Read Memory:**
```bash
# Read all memory
python3 scripts/ops/remember.py

# Read specific category
python3 scripts/ops/remember.py read context
python3 scripts/ops/remember.py read decisions
python3 scripts/ops/remember.py read lessons
```

**Add to Memory:**
```bash
# Record a lesson (CRITICAL - do this immediately after bugs/failures)
python3 scripts/ops/remember.py add lessons "Tried to use X, failed because Y. Use Z instead."

# Record a decision
python3 scripts/ops/remember.py add decisions "Selected Tqdm because built-in logging was too verbose."

# Update context
python3 scripts/ops/remember.py add context "Finished setup. Next step: Implement login."
```

**Search Memory:**
```bash
# Search across all memory
python3 scripts/ops/remember.py search all "pytest"

# Search specific category
python3 scripts/ops/remember.py search decisions "database"
```

### When to Use (Critical)

**The "Pain Log" (Highest Priority):**
- ⚠️ Immediately after encountering a bug → record the lesson
- ⚠️ After a failed approach → document why it failed
- ⚠️ After discovering a gotcha → prevent future pain

**The "Decision Record":**
- When making architectural choices (library selection, pattern adoption)
- When establishing constraints or standards
- When rejecting an alternative approach (document why)

**The "Context Handoff":**
- End of work session → update current status
- Before context clear/compact → preserve state
- When switching tasks → document transition

### Philosophy

Memory is stored in **plain markdown files** (not vector databases, not MCP servers). This means:
- ✅ Human-readable and auditable
- ✅ Version-controlled with git
- ✅ Searchable with standard tools
- ✅ No external dependencies

The Elephant Protocol turns ephemeral token context into **persistent file storage**. Memory injected automatically at `SessionStart` ensures continuity across sessions.

---

## 🧹 The Upkeep Protocol (Definition of Done)

**The Problem:** Documentation, indexes, and requirements drift away from actual code. This is called "bitrot" - where project artifacts become stale and unreliable.

**The Solution:** Automation and gatekeeping. You cannot rely on LLMs to "remember" to update documentation. The system must enforce it.

### The "Clean Exit" Rule

You are **not finished** with a task until the environment is consistent. Before ending a major task or session, you **MUST** run:

```bash
python3 scripts/ops/upkeep.py
```

This script automatically:
1. **Updates the tool registry** (runs `index.py`)
2. **Verifies dependencies** (scans imports vs `requirements.txt`)
3. **Checks scratch hygiene** (warns about old files >24h)
4. **Logs maintenance** (timestamps in `.claude/memory/upkeep_log.md`)

### File Synchronization Rules

**When you add a dependency:**
```bash
# Add to requirements.txt immediately
echo "requests>=2.31.0" >> requirements.txt
```

**When you add a script:**
```bash
# Run the indexer immediately
python3 scripts/index.py
```

**When you change architecture:**
```bash
# Document the decision immediately
python3 scripts/ops/remember.py add decisions "Switched from X to Y because Z"
```

### Scratchpad Hygiene

The `scratch/` folder is for **temporary** work:
- ✅ **Promote useful scripts** to `scripts/` if they prove valuable
- ✅ **Delete garbage** when experiments fail
- ❌ **Do not accumulate zombie files** that are never used

The Upkeep Protocol warns when files exceed 24 hours old.

### The Gatekeeper (Pre-Commit Check)

To prevent committing code with stale indexes, run the gatekeeper before commits:

```bash
# Verify project state before committing
python3 scripts/ops/pre_commit.py
```

This script:
1. Runs the indexer
2. Checks if `tool_index.md` changed
3. **Blocks the commit** if the index was stale
4. Tells you to stage the updated file and retry

**Integration with git hooks (optional):**
```bash
# Add to .git/hooks/pre-commit (if you want automatic enforcement)
#!/bin/bash
python3 scripts/ops/pre_commit.py || exit 1
```

### Automatic Maintenance

The Upkeep Protocol runs automatically at `SessionEnd` (when you type `/exit` or session times out).

**What happens:**
```
> Session Ending...
> [Janitor] Updating Tool Registry... ✅ Done
> [Janitor] Checking dependencies... ✅ All documented
> [Janitor] Checking scratch/... ⚠️  3 files older than 24h
> [Janitor] Cleanup suggestions logged
```

### Philosophy

The Upkeep Protocol enforces **continuous synchronization** between code and documentation. This prevents:
- ❌ Stale tool indexes that mislead you
- ❌ Undocumented dependencies that break installation
- ❌ Forgotten scratch files that clutter the workspace
- ❌ Lost architectural context from missing decision logs

**Whitebox Principle:** All maintenance is transparent, auditable Python code. No blackbox "auto-formatters" or opaque build systems.

---

## 🔄 The Scripting Protocol

### Phase A: The Scratchpad (Exploration)
For one-off tasks or experimenting with logic:
1.  **Draft:** Write to `scratch/tmp_<descriptive_name>.py`.
2.  **Run:** `python3 scratch/...`
3.  **Debug:** Read traceback -> Edit -> Retry.

### Phase B: Production Tooling (The SDK)
For repeatable tools or promoting a scratch script:
1.  **Scaffold:** NEVER start from a blank file. Use the factory:
    *   `python3 scripts/scaffold.py scripts/<category>/<name>.py "Description"`
2.  **Implement:** Add logic inside the generated `try/except` block.
3.  **Verify:** Run with `--dry-run` first.
4.  **Index:** Run `python3 scripts/index.py` to update the registry.

---

## 🏗️ Engineering Standards
All scripts in `scripts/` must adhere to the Whitebox SDK:

1.  **The Core Library**: Must import `scripts.lib.core`.
    *   Use `setup_script()` to handle args and env vars.
    *   Use `logger.info()` instead of `print()` for operational logs.
    *   Use `finalize(success=True/False)` to exit.
2.  **Safety First**:
    *   All mutating scripts **MUST** support `--dry-run`.
    *   No hardcoded credentials (use `.env` loaded via Core Lib).
3.  **Discovery**:
    *   Run the indexer after creating a new tool.
    *   Check `.claude/skills/tool_index.md` to see what tools exist.
4.  **Performance Standards**:
    *   **Parallel by Default:** If a script processes more than 3 items (files, API calls, URLs), you **MUST** use `scripts.lib.parallel`.
    *   **Visual Feedback:** Batch operations must use progress bars (via `tqdm` or fallback).
    *   **Resilience:** Batch scripts must not crash on single failures. Log the error and continue.

## 📂 Directory Roles
- **`scratch/`**: The Workshop. Ephemeral scripts. (Git ignored)
- **`scripts/`**: The Arsenal. Production tools. (Committed)
- **`scripts/lib/`**: The SDK. Shared logic (logging, config).
- **`.claude/skills/`**: The Manuals. Docs for your scripts.
- **`.claude/agents/`**: The Crew. Specialized subagents.

## 🤖 Agent Roles
- **Default (You)**: The Coordinator. You plan, delegate, and oversee.
- **`script-smith`**: The Builder. Uses `scaffold.py` to build robust tools.
- **`runner`**: The Operator. Executes tools safely using `--dry-run`.

## 🚫 Strict Prohibitions
- **NO MCP**: Do not use external tool servers.
- **NO "Imaginary" APIs**: Do not guess how a library works. Write a script to inspect `dir(lib)` if unsure.
- **NO Silent Failures**: Scripts must exit with non-zero codes on failure.

## 🧪 Testing & Validation

### Test Suite Location
All tests are in `.claude/tests/` organized by category:
- **`unit/`** - Core library function tests
- **`integration/`** - Scaffolder, indexer workflow tests
- **alignment/`** - Whitebox principle enforcement tests
- **`stability/`** - Path resolution and edge case tests

### Running Tests
```bash
# Run all tests
python3 .claude/tests/runner.py

# Run specific suite
python3 .claude/tests/runner.py unit
python3 .claude/tests/runner.py integration
python3 .claude/tests/runner.py alignment
python3 .claude/tests/runner.py stability
```

### When to Run Tests
- **Before committing SDK changes** - Ensure stability
- **After modifying core library** - Validate dependents still work
- **When adding new tools** - Confirm integration
- **Periodically** - Catch regressions early

### Test Philosophy
Tests embody the Whitebox principle: "If you can't test it transparently, don't build it."
Every test is readable Python validating expected behavior without external dependencies.

## 📡 Response Protocol: The "Engineer's Footer"
At the end of every significant response (especially after writing or running code), you **MUST** append this block:

### 🚦 Status & Direction
*   **Next Steps:** [Bullet points of immediate next actions]
*   **Areas of Concern:** [Specific risks: unhandled edge cases, scalability issues, security gaps, or technical debt in the current artifact]
*   **Priority Gauge:** [1-100]
    *   *0-30 (Low):* Housekeeping, optimization, or "nice to have".
    *   *31-70 (Med):* Standard workflow, feature implementation.
    *   *71-100 (High):* Critical error, security risk, or blocking dependency.

## ⚡ Commands
- **Scaffold Tool:** `python3 scripts/scaffold.py scripts/<cat>/<name>.py "<desc>"`
- **Refresh Index:** `python3 scripts/index.py`
- **Run Tests:** `python3 .claude/tests/runner.py`
- **Run Tmp:** `python3 scratch/tmp_<name>.py`
- **Run Tool (Dry):** `python3 scripts/<cat>/<name>.py --dry-run`
- **Run Tool (Real):** `python3 scripts/<cat>/<name>.py`
- **List Agents:** `/agents`