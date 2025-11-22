#!/usr/bin/env python3
"""
Intent Classifier Hook: Injects relevant CLAUDE.md protocol sections based on user intent
Triggers on: UserPromptSubmit
Purpose: Provide concrete guidance with actual commands, not just protocol names
"""
import sys
import json

try:
    data = json.load(sys.stdin)
except:
    sys.exit(0)

prompt = data.get("prompt", "").lower()

# Intent detection patterns
intents = []

# 1. DECISION MAKING - Council Protocol
decision_patterns = [
    "should we",
    "should i",
    "which is better",
    "what's the best",
    "migrate to",
    "switch to",
    "use x or y",
    "architecture",
    "design decision",
    "choose between",
    "pros and cons",
    "trade-off",
    "worth it",
]
if any(p in prompt for p in decision_patterns):
    intents.append("decision_making")

# 2. CODE WRITING - Pre-write checklist
code_patterns = [
    "write a",
    "create a",
    "implement",
    "add a function",
    "add a class",
    "build a",
    "make a script",
    "generate code",
]
if any(p in prompt for p in code_patterns):
    intents.append("code_writing")

# 3. DEBUGGING - Reality Check + Sherlock
debug_patterns = [
    "debug",
    "fix this",
    "not working",
    "broken",
    "error",
    "exception",
    "traceback",
    "why is",
    "why isn't",
    "doesn't work",
    "failing",
]
if any(p in prompt for p in debug_patterns):
    intents.append("debugging")

# 4. QUALITY CHECK - Sentinel Protocol
quality_patterns = [
    "check quality",
    "review code",
    "audit",
    "security",
    "vulnerabilities",
    "code quality",
    "before commit",
    "ready to commit",
]
if any(p in prompt for p in quality_patterns):
    intents.append("quality_check")

# 5. RESEARCH - Research Protocol
research_patterns = [
    "how does",
    "how do i",
    "how to",
    "research",
    "look up",
    "find out",
    "documentation",
    "api docs",
    "best practice",
]
if any(p in prompt for p in research_patterns):
    intents.append("research")

# 6. DELEGATION - Agent system
delegation_patterns = [
    "delegate",
    "use agent",
    "researcher agent",
    "script-smith",
    "sherlock",
    "have someone",
]
if any(p in prompt for p in delegation_patterns):
    intents.append("delegation")

# 7. COMMIT - Pre-commit workflow
commit_patterns = [
    "commit",
    "git commit",
    "ready to push",
    "push to",
    "create pr",
    "pull request",
]
if any(p in prompt for p in commit_patterns):
    intents.append("commit")

# 8. VERIFICATION - Verify protocol
verify_patterns = [
    "verify",
    "check if",
    "confirm that",
    "did it work",
    "is it working",
    "test that",
]
if any(p in prompt for p in verify_patterns):
    intents.append("verification")

# Build context based on detected intents
context_blocks = []

if "decision_making" in intents:
    context_blocks.append("""🏛️ ARCHITECTURAL DECISION DETECTED

For decisions with lasting impact, use the Council Protocol (Six Thinking Hats):

  python3 scripts/ops/balanced_council.py "<your proposal>"

This runs 6 perspectives in parallel (~45-90 sec):
  ⚪ White Hat  - Facts & Data (Oracle/Consult)
  🔴 Red Hat    - Risks & Intuition (Skeptic)
  ⚫ Black Hat  - Critical Analysis (Critic)
  🟡 Yellow Hat - Benefits & Opportunities (Advocate)
  🟢 Green Hat  - Alternatives & Creative (Innovator)
  🔵 Blue Hat   - Synthesis & Verdict (Arbiter)

Returns verdict: STRONG GO / CONDITIONAL GO / STOP / INVESTIGATE / ALTERNATIVE RECOMMENDED

Why: External LLMs prevent sycophancy, 6 perspectives balance diversity vs cost
See CLAUDE.md § Council Protocol (Six Thinking Hats Decision Framework)""")

if "code_writing" in intents:
    context_blocks.append("""⚠️ PRE-WRITE PROTOCOL CHECKLIST

RULE: You cannot write production code at low confidence.

Before writing code, you MUST:
  1. Read existing files in the same module (Read tool) → +10% each
  2. Search for similar implementations (Grep/Glob) → +5% each
  3. Probe runtime APIs if using complex libraries (Probe tool) → +15%

Confidence requirements:
  • scratch/ files: 31% minimum (HYPOTHESIS tier)
  • Production code: 71% minimum (CERTAINTY tier)
  • Edit existing: 71% minimum (always)

To check your current tier:
  /confidence status

To boost confidence:
  Read files (+10%), Research (+20%), Probe APIs (+15%), Verify state (+15%)

Why: Prevents Dunning-Kruger effect, ensures you understand context before modifying
See CLAUDE.md § Epistemological Protocol (Confidence Calibration)""")

if "debugging" in intents:
    context_blocks.append("""🔍 DEBUGGING PROTOCOL

RULE: Never claim "Fixed" without verification.

The Reality Check Protocol (Anti-Gaslighting):
  1. Reproduce the issue (verify it exists)
  2. Make your fix
  3. Verify the fix worked: /verify command_success "<test command>"
  4. Only then claim success

Example:
  /verify command_success "pytest tests/test_auth.py"
  /verify file_exists "config/settings.json"
  /verify grep_text "app.py" --expected "DEBUG = False"

If stuck in a loop (trying same thing repeatedly):
  Use the Sherlock agent (The Detective):
    - Read-only access (physically cannot modify)
    - Investigates objectively
    - Breaks gaslighting loops

Invocation:
  Use the Task tool with subagent_type='sherlock' prompt="Investigate why auth keeps failing"

Why: LLMs hallucinate success. Verification is objective truth.
See CLAUDE.md § Reality Check Protocol (Anti-Gaslighting)""")

if "quality_check" in intents:
    context_blocks.append("""🛡️ CODE QUALITY PROTOCOL (The Sentinel)

MANDATORY checks before commit:

1. Security & Complexity:
   python3 scripts/ops/audit.py <file>
   - Scans for secrets, SQL injection, XSS, etc.
   - Checks cyclomatic complexity
   - BLOCKS on critical issues

2. Completeness Check:
   python3 scripts/ops/void.py <file_or_dir>
   - Finds stubs (pass, TODO, NotImplementedError)
   - Checks for missing error handling
   - Finds incomplete CRUD operations

3. Style Consistency:
   python3 scripts/ops/drift_check.py
   - Matches project patterns
   - Prevents style drift

4. Test Verification:
   /verify command_success "pytest tests/"

Complete workflow:
  audit.py → void.py → drift_check.py → verify tests → THEN commit

Why: Prevents shipping incomplete, insecure, or inconsistent code
See CLAUDE.md § Sentinel Protocol (Code Quality)""")

if "research" in intents:
    context_blocks.append("""🌐 RESEARCH PROTOCOL

RULE: Training data is stale (Jan 2025). For new libs/APIs, research first.

For external documentation:
  python3 scripts/ops/research.py "<query>"
  - Live web search via Tavily API
  - Returns current docs (not 2025 training data)
  - Example: "Playwright auto-waiting feature 2025"

For runtime APIs (don't guess):
  python3 scripts/ops/probe.py <object_path>
  - Introspects actual object at runtime
  - Shows real method signatures
  - Example: probe.py pandas.DataFrame

For code structure:
  python3 scripts/ops/xray.py --type <class|function|import> --name <Name>
  - AST-based structural search
  - Finds definitions, dependencies, inheritance

BETTER: Use the researcher agent (context firewall):
  - Absorbs 500-line docs → returns 50-word summary
  - Prevents context pollution
  - Invocation: "Use the researcher agent to investigate FastAPI dependency injection"

Why: Prevents hallucinating outdated APIs
See CLAUDE.md § Research Protocol (Live Data)""")

if "delegation" in intents:
    context_blocks.append("""🤖 AGENT DELEGATION (The Specialists)

Use specialized agents for context isolation and tool scoping:

| Agent          | Use For                    | Benefit                        |
|----------------|----------------------------|--------------------------------|
| researcher     | Deep doc searches          | Context firewall (500→50 lines)|
| script-smith   | Write/refactor code        | Quality gates (audit/void)     |
| sherlock       | Debug/investigate          | Read-only (cannot modify)      |
| critic         | Red team / attack plan     | Mandatory dissent              |
| council-advisor| Major decisions            | Runs 5 advisors in parallel    |
| macgyver       | Tool failures/restrictions | Living off the Land            |

Invocation patterns:
  Implicit: "Researcher, investigate Playwright best practices"
  Explicit: Use Task tool with subagent_type='researcher' prompt="..."

When to delegate:
  • Context isolation: Prevents large outputs from polluting main conversation
  • Tool scoping: Safety constraints (read-only for debugging)
  • Async work: Delegate research while planning next steps
  • Specialized expertise: Agents have domain-specific prompts

See CLAUDE.md § Agent Delegation (The Specialists)""")

if "commit" in intents:
    context_blocks.append("""📦 PRE-COMMIT WORKFLOW

MANDATORY steps before git commit:

1. Code Quality (BLOCKING):
   python3 scripts/ops/audit.py <files>
   python3 scripts/ops/void.py <files>
   python3 scripts/ops/drift_check.py

2. Test Verification (BLOCKING):
   /verify command_success "pytest tests/"
   All tests must pass. No exceptions.

3. Project Upkeep:
   python3 scripts/ops/upkeep.py
   - Syncs requirements.txt
   - Updates tool index
   - Checks scratch/ for debris

4. Then commit:
   The commit hook will auto-format message with:
   - Change summary
   - Co-Authored-By: Claude
   - Link to Claude Code

DO NOT:
  • Skip verification (--no-verify)
  • Commit secrets (.env, credentials.json)
  • Commit incomplete code (stubs, TODOs)
  • Force push to main/master

Why: Prevents shipping broken, incomplete, or insecure code
See CLAUDE.md § Sentinel Protocol""")

if "verification" in intents:
    context_blocks.append("""✅ VERIFICATION PROTOCOL

RULE: Probability ≠ Truth. Verify objectively.

The verify.py tool provides objective state checks:

1. File existence:
   /verify file_exists "path/to/file.py"

2. Text in file:
   /verify grep_text "config.py" --expected "DEBUG = False"

3. Port listening:
   /verify port_open 5432

4. Command success:
   /verify command_success "pytest tests/"

Pattern: Edit → Verify (True) → Claim Success

Never say:
  • "The tests should pass"
  • "This should work"
  • "The file was created"

Always verify:
  • /verify command_success "pytest tests/test_auth.py"
  • /verify file_exists "output/report.json"
  • /verify grep_text "app.py" --expected "version = '2.0'"

Why: LLMs hallucinate. Verification is reality.
See CLAUDE.md § Reality Check Protocol (Anti-Gaslighting)""")

# Output context if any intents detected
if context_blocks:
    # Join with double newline between blocks
    full_context = "\n\n".join(context_blocks)

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
    # No intents detected, pass through
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
