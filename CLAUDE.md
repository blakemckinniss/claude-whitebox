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

### 2. Is it a Logic or External Operation? (APIs, DBs, Data Munging)
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