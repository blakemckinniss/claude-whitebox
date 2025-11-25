#!/usr/bin/env python3
"""
Command Suggester Hook: Suggests related commands based on keywords
Triggers on: UserPromptSubmit
Purpose: Improve command discoverability and ecosystem awareness
"""
import sys
import json

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

prompt = data.get("prompt", "").lower()

# Command ecosystem mappings
suggestions = []

# 1. CONFIDENCE/EVIDENCE ECOSYSTEM
confidence_keywords = ["confidence", "evidence", "tier", "epistemolog"]
if any(kw in prompt for kw in confidence_keywords):
    suggestions.append("""📊 CONFIDENCE & EVIDENCE COMMANDS

Check your epistemic state:
  /confidence status        - Show current session (confidence/risk/tokens)
  /confidence list          - List all sessions with stats
  /evidence review          - Review evidence ledger by tool type

Boost confidence:
  Read files (+10% first, +2% repeat)
  Research (+20%): python3 scripts/ops/research.py "<query>"
  Probe APIs (+15%): python3 scripts/ops/probe.py <object>
  Verify state (+15%): /verify command_success "<cmd>"

Confidence tiers:
  0-30% (IGNORANCE)  → Can only Read/Research/Probe
  31-70% (HYPOTHESIS) → Can write to scratch/
  71-100% (CERTAINTY) → Can write production code

See CLAUDE.md § Epistemological Protocol""")

# 2. QUALITY/AUDIT ECOSYSTEM
quality_keywords = ["quality", "audit", "security", "void", "drift", "completeness"]
if any(kw in prompt for kw in quality_keywords):
    suggestions.append("""🛡️ CODE QUALITY COMMANDS

Pre-commit quality checks:
  /audit <file>     - Security scan, complexity check, secret detection
  /void <file>      - Completeness check (stubs, missing error handling)
  /drift            - Style consistency check across project

Verification:
  /verify command_success "pytest tests/"  - Test verification
  /verify file_exists "path/to/file"       - File check
  /verify grep_text "file" --expected "text" - Content check

Complete workflow:
  audit.py → void.py → drift_check.py → verify tests → commit

See CLAUDE.md § Sentinel Protocol (Code Quality)""")

# 3. DECISION/COUNCIL ECOSYSTEM
decision_keywords = ["decision", "choice", "should", "council", "judge", "critic", "skeptic"]
if any(kw in prompt for kw in decision_keywords):
    suggestions.append("""🏛️ DECISION-MAKING COMMANDS

For major decisions (architecture, migrations, library choices):
  python3 scripts/ops/balanced_council.py "<proposal>"
  - Runs 6 perspectives (Six Thinking Hats)
  - Time: ~45-90 seconds
  - Returns verdict: STRONG GO / CONDITIONAL GO / STOP / INVESTIGATE / ALTERNATIVE

Single-perspective advisors (quick checks):
  /judge "<proposal>"    - Value/ROI assessment
  /critic "<idea>"       - Red team / attack assumptions
  /skeptic "<proposal>"  - Risk analysis, failure modes
  /think "<problem>"     - Decompose into sequential steps

For objective facts:
  /consult "<question>"  - High-reasoning model advice

RULE: For strategic decisions, use balanced_council.py (not single advisors)
See CLAUDE.md § Council Protocol (Six Thinking Hats)""")

# 4. RESEARCH/INVESTIGATION ECOSYSTEM
research_keywords = ["research", "docs", "documentation", "api", "how to", "probe", "xray"]
if any(kw in prompt for kw in research_keywords):
    suggestions.append("""🔬 RESEARCH & INVESTIGATION COMMANDS

For external docs (live, not stale training data):
  /research "<query>"                      - Web search via Tavily API
  python3 scripts/ops/research.py "<query>"

For runtime APIs (don't guess):
  /probe <object_path>                     - Introspect object at runtime
  python3 scripts/ops/probe.py pandas.DataFrame

For code structure:
  /xray --type <class|function|import> --name <Name>  - AST search
  python3 scripts/ops/xray.py --type class --name User

For file patterns:
  Glob: Glob tool with pattern "**/*.py"
  Grep: Grep tool with pattern "class.*User"

Agent delegation (context firewall):
  "Use the researcher agent to investigate FastAPI dependency injection"
  - Absorbs 500 lines → returns 50-word summary

See CLAUDE.md § Research Protocol (Live Data)""")

# 5. DEFINITION OF DONE ECOSYSTEM
dod_keywords = ["scope", "progress", "checklist", "definition of done", "punch list"]
if any(kw in prompt for kw in dod_keywords):
    suggestions.append("""🏁 DEFINITION OF DONE COMMANDS

For tasks >5 minutes, track completion:
  /scope init "<task description>"  - Initialize DoD tracker
  /scope check <N>                  - Mark item N as complete
  /scope status                     - Check completion percentage

Example workflow:
  1. /scope init "Add user authentication system"
     Creates punch list: [setup, implement, test, document]

  2. After each step: /scope check 1, /scope check 2, ...

  3. /scope status → Shows 75% complete

RULE: Don't claim "Done" until /scope status shows 100%

Include in DoD:
  - All features implemented
  - Tests passing (/verify command_success "pytest")
  - Code audited (/audit, /void, /drift)
  - Documentation updated

See CLAUDE.md § Finish Line Protocol (Definition of Done)""")

# 6. MEMORY/LESSONS ECOSYSTEM
memory_keywords = ["remember", "memory", "lessons", "spark", "past", "learned"]
if any(kw in prompt for kw in memory_keywords):
    suggestions.append("""🐘 MEMORY & LESSONS COMMANDS

Add to persistent memory:
  /remember add lessons "<lesson>"      - Document bugs, failures, gotchas
  /remember add decisions "<decision>"  - Record architectural choices
  /remember add context "<context>"     - Store session context

View memories:
  /remember view lessons    - See past mistakes
  /remember view decisions  - See past choices
  /remember view context    - See recent session summaries

Associative recall:
  /spark "<topic>"  - Retrieve related protocols, tools, past lessons
  - Auto-runs on every prompt via synapse_fire.py hook

Example lessons to record:
  - "research.py must check --dry-run before checking API key"
  - "Playwright required for dynamic sites, requests fails"
  - "Always Read file before Edit to avoid context blindness"

See CLAUDE.md § Elephant Protocol (Memory)""")

# 7. AGENT/DELEGATION ECOSYSTEM
agent_keywords = ["agent", "delegate", "researcher", "script-smith", "sherlock", "macgyver"]
if any(kw in prompt for kw in agent_keywords):
    suggestions.append("""🤖 AGENT DELEGATION COMMANDS

Available specialist agents:
  researcher     - Deep doc searches (context firewall: 500→50 lines)
  script-smith   - Write/refactor code (quality gates: audit/void)
  sherlock       - Debug/investigate (read-only, cannot modify)
  critic         - Red team review (mandatory dissent)
  council-advisor- Major decisions (runs 5 advisors in parallel)
  macgyver       - Tool failures (Living off the Land)

Invocation patterns:
  Implicit: "Researcher, investigate Playwright auto-waiting"
  Explicit: Use Task tool with subagent_type='researcher' prompt="..."

When to delegate:
  - Large outputs (research) → context pollution prevention
  - Quality gates (code writing) → automatic audit/void checks
  - Debugging loops → read-only access prevents modification
  - Major decisions → multi-perspective analysis

Agent tool scopes:
  researcher: Bash, Read, Glob, Grep (read-only)
  script-smith: Bash, Read, Write, Edit, Glob, Grep (+ quality gates)
  sherlock: Bash, Read, Glob, Grep (read-only, cannot modify files)

See CLAUDE.md § Agent Delegation (The Specialists)""")

# 8. VERIFICATION ECOSYSTEM
verify_keywords = ["verify", "check if", "confirm", "did it work", "is it"]
if any(kw in prompt for kw in verify_keywords):
    suggestions.append("""✅ VERIFICATION COMMANDS

Objective state checks (anti-gaslighting):
  /verify file_exists "<path>"                      - Check file exists
  /verify grep_text "<file>" --expected "<text>"    - Verify content
  /verify port_open <port>                          - Check port listening
  /verify command_success "<cmd>"                   - Run and verify exit code

Common verification patterns:
  After code change:
    /verify command_success "pytest tests/test_auth.py"

  After file creation:
    /verify file_exists "output/report.json"

  After config change:
    /verify grep_text "config.py" --expected "DEBUG = False"

  After service start:
    /verify port_open 8000

RULE: Never claim "Fixed" or "Done" without verification
Pattern: Edit → Verify → Claim Success

If stuck in loop, use Sherlock agent (read-only debugger)

See CLAUDE.md § Reality Check Protocol (Anti-Gaslighting)""")

# Output suggestions if any keywords matched
if suggestions:
    # Join with double newline between suggestions
    full_context = "\n\n".join(suggestions)

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
    # No keywords matched, pass through
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
