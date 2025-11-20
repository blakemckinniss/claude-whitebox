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
- **Run Tmp:** `python3 scratch/tmp_<name>.py`
- **Run Tool (Dry):** `python3 scripts/<cat>/<name>.py --dry-run`
- **Run Tool (Real):** `python3 scripts/<cat>/<name>.py`
- **List Agents:** `/agents`