#!/usr/bin/env python3
"""
Ecosystem Mapper Hook: Shows complete toolchains for task categories
Triggers on: UserPromptSubmit
Purpose: Provide full workflow sequences, not just individual tools
"""
import sys
import json

try:
    data = json.load(sys.stdin)
except:
    sys.exit(0)

prompt = data.get("prompt", "").lower()

# Detect task categories and show complete toolchains
toolchains = []

# 1. PRE-COMMIT WORKFLOW
precommit_patterns = [
    "before commit",
    "pre-commit",
    "ready to commit",
    "commit checklist",
]
if any(p in prompt for p in precommit_patterns):
    toolchains.append("""📦 PRE-COMMIT TOOLCHAIN (Complete Workflow)

The full quality assurance pipeline before ANY commit:

┌─ STEP 1: Security & Complexity Scan ─────────────────┐
│ python3 scripts/ops/audit.py <files>                 │
│                                                       │
│ Checks:                                              │
│   • Secret detection (.env, API keys, passwords)    │
│   • SQL injection vulnerabilities                    │
│   • XSS attack vectors                              │
│   • Cyclomatic complexity                           │
│   • Unsafe eval/exec usage                          │
│                                                       │
│ BLOCKS: CRITICAL issues must be fixed               │
└───────────────────────────────────────────────────────┘

┌─ STEP 2: Completeness Check ─────────────────────────┐
│ python3 scripts/ops/void.py <file_or_dir>           │
│                                                       │
│ Finds:                                               │
│   • Stubs (pass, TODO, NotImplementedError)         │
│   • Missing error handling                           │
│   • Incomplete CRUD operations                       │
│   • Missing docstrings (if project requires them)   │
│                                                       │
│ BLOCKS: Stubs banned by ban_stubs.py hook           │
└───────────────────────────────────────────────────────┘

┌─ STEP 3: Style Consistency ──────────────────────────┐
│ python3 scripts/ops/drift_check.py                   │
│                                                       │
│ Validates:                                           │
│   • Matches project patterns                         │
│   • Consistent naming conventions                    │
│   • No style drift from codebase                    │
└───────────────────────────────────────────────────────┘

┌─ STEP 4: Test Verification ──────────────────────────┐
│ /verify command_success "pytest tests/"              │
│                                                       │
│ Confirms:                                            │
│   • All tests pass                                   │
│   • No regressions                                   │
│   • New code is tested                              │
│                                                       │
│ BLOCKS: Cannot claim "done" without passing tests   │
└───────────────────────────────────────────────────────┘

┌─ STEP 5: Project Upkeep ─────────────────────────────┐
│ python3 scripts/ops/upkeep.py                        │
│                                                       │
│ Syncs:                                               │
│   • requirements.txt with imports                    │
│   • Tool index (.claude/skills/tool_index.md)       │
│   • Cleans scratch/ directory                       │
└───────────────────────────────────────────────────────┘

┌─ STEP 6: Commit ──────────────────────────────────────┐
│ git add <files>                                       │
│ git commit -m "your message"                          │
│                                                       │
│ Auto-formatted with:                                 │
│   • Co-Authored-By: Claude                          │
│   • Link to Claude Code                             │
└───────────────────────────────────────────────────────┘

Complete sequence:
  audit.py → void.py → drift_check.py → verify tests → upkeep.py → commit

See CLAUDE.md § Sentinel Protocol + Upkeep Protocol""")

# 2. RESEARCH/INVESTIGATION WORKFLOW
research_workflow_patterns = ["research workflow", "how to research", "investigation"]
if any(p in prompt for p in research_workflow_patterns):
    toolchains.append("""🔬 RESEARCH & INVESTIGATION TOOLCHAIN

Complete workflow for gathering information:

┌─ PHASE 1: External Documentation ────────────────────┐
│ python3 scripts/ops/research.py "<query>"            │
│                                                       │
│ Use when:                                            │
│   • New libraries (post-2023)                        │
│   • Current API documentation                        │
│   • Best practices (2025)                            │
│   • Error messages / stack traces                   │
│                                                       │
│ Returns: Live web search results (not stale training)│
│ Boost: +20% confidence                               │
└───────────────────────────────────────────────────────┘

┌─ PHASE 2: Runtime API Introspection ─────────────────┐
│ python3 scripts/ops/probe.py <object_path>           │
│                                                       │
│ Use when:                                            │
│   • Complex libraries (pandas, boto3, FastAPI)      │
│   • Need actual method signatures                   │
│   • Checking parameter names/types                  │
│                                                       │
│ Returns: Real runtime API (not guesses)             │
│ Boost: +15% confidence                               │
└───────────────────────────────────────────────────────┘

┌─ PHASE 3: Code Structure Analysis ───────────────────┐
│ python3 scripts/ops/xray.py --type <type> --name <N> │
│                                                       │
│ Types: class, function, import                       │
│                                                       │
│ Use when:                                            │
│   • Finding class definitions                        │
│   • Tracing dependencies                             │
│   • Understanding inheritance                        │
│                                                       │
│ Returns: AST-based structural search                │
│ Boost: +5% confidence                                │
└───────────────────────────────────────────────────────┘

┌─ PHASE 4: File Pattern Search ───────────────────────┐
│ Glob: "**/*.py" or "src/models/*.ts"                 │
│ Grep: pattern in code, -i for case-insensitive      │
│                                                       │
│ Use when:                                            │
│   • Finding all files of a type                      │
│   • Searching for keywords in code                  │
│                                                       │
│ Boost: +5% confidence per search                    │
└───────────────────────────────────────────────────────┘

BETTER: Delegate to researcher agent for context isolation
  "Use the researcher agent to investigate <topic>"
  - Absorbs 500-line outputs → returns 50-word summary
  - Prevents main context pollution
  - Boost: +25% confidence

Complete sequence:
  research.py (external) → probe.py (runtime) → xray.py (structure) → Glob/Grep (patterns)

See CLAUDE.md § Research Protocol + Probe Protocol""")

# 3. DECISION-MAKING WORKFLOW
decision_workflow_patterns = [
    "decision workflow",
    "how to decide",
    "decision process",
]
if any(p in prompt for p in decision_workflow_patterns):
    toolchains.append("""🏛️ DECISION-MAKING TOOLCHAIN (Six Thinking Hats)

Complete workflow for architectural/strategic decisions:

┌─ PHASE 1: Context Gathering (PREREQUISITE) ──────────┐
│ RULE: Don't decide at peak ignorance (Dunning-Kruger)│
│                                                       │
│ Required confidence: 40%+ before council             │
│                                                       │
│ Gather context via:                                  │
│   • Read existing code → +10% per file               │
│   • Research alternatives → +20%                     │
│   • Probe APIs if relevant → +15%                   │
│                                                       │
│ Check: /confidence status                            │
└───────────────────────────────────────────────────────┘

┌─ PHASE 2: Council Consultation (MANDATORY) ──────────┐
│ python3 scripts/ops/balanced_council.py "<proposal>" │
│                                                       │
│ The Six Thinking Hats (parallel execution):         │
│   ⚪ White Hat  - Facts & Data (Oracle)              │
│   🔴 Red Hat    - Risks & Intuition (Skeptic)        │
│   ⚫ Black Hat  - Critical Analysis (Critic)          │
│   🟡 Yellow Hat - Benefits & Opportunities (Advocate) │
│   🟢 Green Hat  - Alternatives & Creative (Innovator)│
│   🔵 Blue Hat   - Synthesis & Verdict (Arbiter)      │
│                                                       │
│ Time: ~45-90 seconds                                 │
│ Output: Verdict (STRONG GO / CONDITIONAL GO / STOP / │
│         INVESTIGATE / ALTERNATIVE RECOMMENDED)       │
└───────────────────────────────────────────────────────┘

┌─ PHASE 3: Decision Logging ──────────────────────────┐
│ /remember add decisions "<decision made>"            │
│                                                       │
│ Why: Persistent memory for future reference         │
│ Example: "Decided to use GraphQL over REST because..." │
└───────────────────────────────────────────────────────┘

Quick checks (NOT for strategic decisions):
  /judge "<proposal>"   - ROI/value assessment
  /critic "<idea>"      - Red team only
  /skeptic "<proposal>" - Risk analysis only
  /think "<problem>"    - Problem decomposition

RULE: For strategic/architectural decisions, ALWAYS use balanced_council.py
      Single advisors = confirmation bias risk

Complete sequence:
  Gather context (40%+ confidence) → balanced_council.py → log decision

See CLAUDE.md § Council Protocol (Six Thinking Hats)""")

# 4. QUALITY ASSURANCE WORKFLOW
qa_workflow_patterns = ["quality workflow", "qa process", "quality assurance"]
if any(p in prompt for p in qa_workflow_patterns):
    toolchains.append("""🛡️ QUALITY ASSURANCE TOOLCHAIN

Complete workflow for code quality verification:

┌─ PHASE 1: Static Analysis ───────────────────────────┐
│ python3 scripts/ops/audit.py <file>                  │
│                                                       │
│ Scans for:                                           │
│   🔴 CRITICAL: Secrets, SQL injection, XSS           │
│   🟡 HIGH: Unsafe eval, complexity >15               │
│   🟢 MEDIUM: Code smells, style issues               │
│                                                       │
│ Tools used: bandit, radon, ruff                      │
│ BLOCKS: Critical issues prevent commit              │
└───────────────────────────────────────────────────────┘

┌─ PHASE 2: Completeness Analysis ─────────────────────┐
│ python3 scripts/ops/void.py <file_or_dir>           │
│                                                       │
│ Finds gaps:                                          │
│   • Stubs (pass, TODO, NotImplementedError)         │
│   • Missing error handling (no try/except)          │
│   • Incomplete CRUD (only Create, no Read/Update)   │
│   • Happy path only (no edge cases)                 │
│                                                       │
│ BLOCKS: ban_stubs.py hook prevents stub commits     │
└───────────────────────────────────────────────────────┘

┌─ PHASE 3: Consistency Check ─────────────────────────┐
│ python3 scripts/ops/drift_check.py                   │
│                                                       │
│ Validates:                                           │
│   • Naming conventions match project                 │
│   • Import patterns consistent                       │
│   • File structure aligned                           │
│                                                       │
│ Prevents: Style drift over time                     │
└───────────────────────────────────────────────────────┘

┌─ PHASE 4: Runtime Verification ──────────────────────┐
│ /verify command_success "pytest tests/"              │
│ /verify command_success "black --check ."            │
│ /verify command_success "mypy src/"                  │
│                                                       │
│ Confirms:                                            │
│   • Tests pass (functionality)                       │
│   • Formatting correct (style)                       │
│   • Type hints valid (static typing)                │
└───────────────────────────────────────────────────────┘

┌─ PHASE 5: Manual Review (if needed) ─────────────────┐
│ Use critic agent for adversarial review:            │
│   Use Task tool, subagent_type='critic'             │
│   prompt="Review <file> for security issues"        │
│                                                       │
│ Or use sherlock agent for investigation:            │
│   Use Task tool, subagent_type='sherlock'           │
│   prompt="Investigate why tests are failing"        │
└───────────────────────────────────────────────────────┘

Complete sequence:
  audit.py → void.py → drift_check.py → verify tests → (optional: critic/sherlock)

See CLAUDE.md § Sentinel Protocol + Void Hunter Protocol""")

# 5. VERIFICATION WORKFLOW
verification_workflow_patterns = [
    "verification workflow",
    "how to verify",
    "verification process",
]
if any(p in prompt for p in verification_workflow_patterns):
    toolchains.append("""✅ VERIFICATION TOOLCHAIN (Anti-Gaslighting)

Complete workflow for objective state verification:

┌─ RULE: Probability ≠ Truth ──────────────────────────┐
│ Never claim success without objective verification   │
│                                                       │
│ Pattern: Edit → Verify (True) → Claim Success       │
└───────────────────────────────────────────────────────┘

┌─ PHASE 1: File Operations ───────────────────────────┐
│ After creating/deleting files:                       │
│   /verify file_exists "path/to/file"                 │
│                                                       │
│ After writing content:                               │
│   /verify grep_text "file" --expected "content"      │
│                                                       │
│ Examples:                                            │
│   /verify file_exists "output/report.json"           │
│   /verify grep_text "config.py" --expected "DEBUG=False" │
└───────────────────────────────────────────────────────┘

┌─ PHASE 2: Service Operations ────────────────────────┐
│ After starting service:                              │
│   /verify port_open <port>                           │
│                                                       │
│ Examples:                                            │
│   /verify port_open 8000  (web server)              │
│   /verify port_open 5432  (PostgreSQL)              │
└───────────────────────────────────────────────────────┘

┌─ PHASE 3: Command Execution ─────────────────────────┐
│ After making changes:                                │
│   /verify command_success "<command>"                │
│                                                       │
│ Examples:                                            │
│   /verify command_success "pytest tests/"            │
│   /verify command_success "black --check ."          │
│   /verify command_success "mypy src/"                │
│   /verify command_success "npm run build"            │
└───────────────────────────────────────────────────────┘

┌─ PHASE 4: Integration Verification ──────────────────┐
│ For complex changes, verify end-to-end:             │
│   1. Unit tests pass                                 │
│   2. Integration tests pass                          │
│   3. Manual smoke test                              │
│                                                       │
│ Example:                                             │
│   /verify command_success "pytest tests/unit/"       │
│   /verify command_success "pytest tests/integration/" │
│   /verify port_open 8000 && curl http://localhost:8000/health │
└───────────────────────────────────────────────────────┘

If stuck verifying (loop):
  Use sherlock agent (read-only debugger):
    Use Task tool, subagent_type='sherlock'
    prompt="Investigate why tests keep failing despite fixes"

Complete sequence:
  Make change → verify file → verify tests → verify service → claim success

See CLAUDE.md § Reality Check Protocol (Anti-Gaslighting)""")

# Output toolchains if any task categories detected
if toolchains:
    # Join with double newline between toolchains
    full_context = "\n\n".join(toolchains)

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": full_context,
                }
            }
        )
    )
else:
    # No task categories detected, pass through
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "",
                }
            }
        )
    )

sys.exit(0)
