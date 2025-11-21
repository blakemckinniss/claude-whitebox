# 🧠 Whitebox Engineering Constitution

## 📜 Core Philosophy
1.  **NO BLACKBOX TOOLS:** We rely on transparent, executable code (Scripts).
2.  **NO HALLUCINATIONS:** We verify reality (Probe/Reality Check) before claiming facts.
3.  **NO LAZINESS:** We use rigorous definitions of done (Finish Line).
4.  **NO SYCOPHANCY:** We challenge assumptions (Council/Critic).

---

## 🛠️ The Workflow Decision Matrix (Start Here)

### 1. Need to make a Decision?
🏛️ **The Council Protocol:** `python3 scripts/ops/council.py "<proposal>"`
*   *Use for:* Architecture changes, new libraries, refactors, complex trade-offs.

### 2. Need Information?
*   **External (Docs/Libs):** 🌐 `python3 scripts/ops/research.py "<query>"`
*   **Internal (Code Structure):** 🔬 `python3 scripts/ops/xray.py ...`
*   **Runtime (API/Objects):** 🔬 `python3 scripts/ops/probe.py ...`

### 3. Need to Act?
*   **Simple IO:** ✅ Use Native Tools (`Read`, `Bash`).
*   **Logic/Data:** 📝 Write a Script (`scripts/scaffold.py`).
*   **Browser/UI:** 🎭 Use Playwright (`--template playwright`).
*   **Blocked?** 🖇️ Use MacGyver (`/use macgyver`).

### 4. Need to Verify?
*   **Did it work?** 🤥 `python3 scripts/ops/verify.py ...`
*   **Is it safe?** 🛡️ `python3 scripts/ops/audit.py ...`
*   **Is it complete?** 🕳️ `python3 scripts/ops/void.py ...`

---

## 🧠 Cognition Protocols (Thinking)

### 🏛️ The Council Protocol (Decision Making)
Before major decisions, assemble the experts:
*   **The Judge:** "Is this worth doing?" (ROI/YAGNI).
*   **The Critic:** "Are the assumptions wrong?" (10th Man).
*   **The Skeptic:** "How will this fail?" (Risk).
*   **The Thinker:** "How to decompose this?" (Planning).
*   **The Oracle:** "What are the implications?" (Architecture).

### 🧠 The Synapse Protocol (Associative Memory)
*   **Automatic:** Context is injected into your prompt based on keywords.
*   **Function:** Connects current tasks to past Lessons (`lessons.md`) and Protocols.
*   **Spark:** Lateral thinking constraints (e.g., "What if you couldn't use Python?") appear here.

### 🏁 The Finish Line Protocol (Definition of Done)
For tasks > 5 minutes:
1.  **Init:** `python3 scripts/ops/scope.py init "Task Description"`
2.  **Execute:** Mark items done (`scope.py check <N>`) only after verification.
3.  **Finish:** You are **FORBIDDEN** from saying "Done" until status is 100%.
4.  **Report:** Must provide stats (Files changed, Tests passed).

---

## 🔎 Investigation Protocols (Eyes)

### 🌐 The Research Protocol (Live Data)
**Training Data is Stale.**
*   **Mandatory:** For new libraries (>2023), debugging errors, or API docs.
*   **Action:** Run `research.py`. Read output. Code based on *output*, not memory.

### 🔬 The Probe Protocol (Runtime Truth)
**No Guessing APIs.**
*   **Mandatory:** Before using complex libraries (pandas, boto3).
*   **Action:** `python3 scripts/ops/probe.py <object>`. Check signature. Code matches runtime.

### 🔬 The X-Ray Protocol (Structural Search)
**Grep is Blind.**
*   **Use for:** Finding definitions, dependencies, and inheritance.
*   **Action:** `python3 scripts/ops/xray.py --type class --name User`.

---

## ⚙️ Action Protocols (Hands)

### 🔄 The Scripting Protocol
*   **Phase A (Draft):** `scratch/tmp_*.py`. Fast, throwaway.
*   **Phase B (Production):** `scripts/ops/name.py`.
    *   **MUST** use `scaffold.py`.
    *   **MUST** import `scripts.lib.core`.
    *   **MUST** support `--dry-run`.

### 🎭 The Headless Protocol (Browser)
*   **Rule:** No `requests` for dynamic sites.
*   **Action:** `python3 scripts/scaffold.py scratch/ui.py --template playwright`.
*   **Debug:** Check `scratch/error.png` on failure.

### 🖇️ The MacGyver Protocol (Improvisation)
*   **Trigger:** `/use macgyver` or when tools are blocked.
*   **Philosophy:** Living off the Land. Use installed binaries (`curl`, `awk`, `bash`).
*   **Scan:** `python3 scripts/ops/inventory.py`.

---

## 🛡️ Quality Assurance Protocols (Guardrails)

### 🛡️ The Sentinel Protocol (Code Quality)
*   **The Law:** Check `.claude/memory/anti_patterns.md`.
*   **The Sheriff:** Run `python3 scripts/ops/audit.py <file>`.
    *   **Critical:** Security/Keys (Blocked by hook).
    *   **Warning:** Complexity/Debt (Fix before commit).
*   **The Court:** Run `scripts/ops/drift_check.py` to match project style.

### 🕳️ The Void Hunter Protocol (Completeness)
**Happy Path is a Trap.**
*   **Rule:** No Stubs (`pass`, `TODO`). Blocked by hook.
*   **Check:** Run `scripts/ops/void.py` to find missing CRUD methods, error handling, or config.

### 🤥 The Reality Check Protocol (Anti-Gaslighting)
**Probability ≠ Truth.**
*   **Rule:** Never claim "Fixed" without `scripts/ops/verify.py`.
*   **Loop:** Edit -> Verify (True) -> Claim Success.
*   **Sherlock:** Use `/use sherlock` if you are stuck in a gaslighting loop.

---

## 🧹 Maintenance Protocols

### 🐘 The Elephant Protocol (Memory)
*   **Pain Log:** Bug/Failure? -> `remember.py add lessons "..."`
*   **Decisions:** Architecture Choice? -> `remember.py add decisions "..."`
*   **Context:** End of Session? -> `remember.py add context "..."`

### 🧹 The Upkeep Protocol
*   **Session End:** Runs automatically.
*   **Manual:** `python3 scripts/ops/upkeep.py`.
*   **Rule:** Requirements and Tool Index must match reality.

---

## 📡 Response Protocol: The "Engineer's Footer"
At the end of every significant response, append:

### 🚦 Status & Direction
*   **Next Steps:** [Bullet points]
*   **Areas of Concern:** [Specific risks/edge cases]
*   **Priority Gauge:** [1-100] (0=Low, 100=Critical)

---

## ⚡ Commands
- **Scaffold:** `python3 scripts/scaffold.py scripts/<cat>/<name>.py "<desc>"`
- **Research:** `python3 scripts/ops/research.py "<query>"`
- **Consult:** `python3 scripts/ops/consult.py "<topic>"`
- **Council:** `python3 scripts/ops/council.py "<proposal>"`
- **Audit:** `python3 scripts/ops/audit.py <file>`
- **Verify:** `python3 scripts/ops/verify.py <check> <target>`
- **Punch List:** `python3 scripts/ops/scope.py status`
- **Refresh Index:** `python3 scripts/index.py`
- **🆘 EMERGENCY:** `python3 scripts/ops/council.py "We are stuck. Analyze situation."`