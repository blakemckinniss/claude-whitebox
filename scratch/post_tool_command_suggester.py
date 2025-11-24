#!/usr/bin/env python3
"""
Post-Tool Command Suggester Hook: Pattern-based command suggestions after tool use
Triggers on: PostToolUse
Purpose: Inject relevant command guidance based on what just happened
"""
import sys
import json
from pathlib import Path

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import load_session_state

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

session_id = input_data.get("sessionId", "unknown")
tool_name = input_data.get("toolName", "")
tool_params = input_data.get("toolParams", {})
tool_result = input_data.get("toolResult", "")

if not tool_name:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

# Load session state for usage tracking
state = load_session_state(session_id)
evidence_ledger = state.get("evidence_ledger", []) if state else []

# Count tool usage in this session
write_count = sum(1 for e in evidence_ledger if e.get("tool") == "Write")
edit_count = sum(1 for e in evidence_ledger if e.get("tool") == "Edit")
bash_count = sum(1 for e in evidence_ledger if e.get("tool") == "Bash")

suggestions = []

# ============================================================================
# PATTERN 1: Write/Edit to Production Code → Quality Gates
# ============================================================================
if tool_name in ["Write", "Edit"]:
    file_path = tool_params.get("file_path", "")

    # Check if production code (not scratch/)
    if file_path and "scratch/" not in file_path:
        # Check if it's a Python file in scripts/ or source code
        path = Path(file_path)
        is_production = (
            path.suffix == ".py" and
            ("scripts/" in file_path or "src/" in file_path or "lib/" in file_path)
        )

        if is_production:
            suggestions.append("""🛡️ PRODUCTION CODE MODIFIED → QUALITY GATES REQUIRED

You just wrote/edited production code. Run quality checks before claiming done:

  /audit {file}   - Security scan, complexity check, secret detection
  /void {file}    - Completeness check (stubs, missing CRUD, error handling)
  /drift          - Style consistency check

Pattern: Write → Audit → Void → Drift → Verify → Commit

Why: Production code requires quality gates to prevent technical debt.
See CLAUDE.md § Sentinel Protocol""".format(file=path.name))

# ============================================================================
# PATTERN 2: Result Contains "Done" / "Complete" → Void Hunter
# ============================================================================
if tool_result and isinstance(tool_result, str):
    result_lower = tool_result.lower()
    completion_keywords = ["done", "complete", "finished", "100%", "successfully", "all tests pass"]

    if any(kw in result_lower for kw in completion_keywords):
        suggestions.append("""⚠️ COMPLETION CLAIM DETECTED → VERIFY COMPLETENESS

The tool result suggests completion. Before claiming "done", verify:

  /void <file_or_dir>     - Check for stubs, missing CRUD, gaps
  /verify command_success "pytest tests/"  - Verify tests pass
  /scope status           - Check Definition of Done percentage

Pattern: Result → Void → Verify → Scope → Only Then Claim Done

Why: LLMs suffer from "Happy Path Bias" - verify ecosystem completeness.
See CLAUDE.md § Void Hunter Protocol""")

# ============================================================================
# PATTERN 3: Bash Running Tests → Verify Exit Code
# ============================================================================
if tool_name == "Bash":
    command = tool_params.get("command", "")
    test_keywords = ["pytest", "npm test", "cargo test", "go test", "mvn test"]

    if any(kw in command for kw in test_keywords):
        suggestions.append("""✅ TEST COMMAND DETECTED → VERIFY EXIT CODE

You ran a test command. Don't trust output text - verify exit code:

  /verify command_success "{cmd}"

Example workflow:
  1. Run tests via Bash
  2. Use /verify to confirm exit code 0
  3. Only then claim tests pass

Why: LLMs can misinterpret test output. Exit code is ground truth.
See CLAUDE.md § Reality Check Protocol""".format(cmd=command[:60]))

# ============================================================================
# PATTERN 4: WebSearch/WebFetch → Probe Runtime APIs
# ============================================================================
if tool_name in ["WebSearch", "WebFetch"]:
    query = tool_params.get("query", "") or tool_params.get("url", "")

    # Check if searching for library/API docs
    api_keywords = ["api", "documentation", "docs", "how to use", "method", "function"]
    if any(kw in query.lower() for kw in api_keywords):
        suggestions.append("""🔬 API RESEARCH DETECTED → PROBE RUNTIME TRUTH

You searched for API documentation. Before coding, verify at runtime:

  /probe <object_path>     - Introspect actual API signatures
  python3 scripts/ops/probe.py pandas.DataFrame

Pattern: Research → Probe → Code (don't guess from stale docs)

Why: Training data is from Jan 2025. Runtime introspection is truth.
See CLAUDE.md § Probe Protocol""")

# ============================================================================
# PATTERN 5: Error/Failure in Result → Verification Loop
# ============================================================================
if tool_result and isinstance(tool_result, str):
    error_keywords = ["error", "failed", "failure", "exception", "traceback", "not found"]

    if any(kw in tool_result.lower() for kw in error_keywords):
        suggestions.append("""🚨 ERROR DETECTED → ENTER VERIFICATION LOOP

The tool result shows an error. Use verification to debug:

  /verify file_exists "<path>"              - Check file exists
  /verify grep_text "<file>" --expected "<text>"  - Verify content
  /verify command_success "<cmd>"           - Test command

If stuck in gaslighting loop:
  Use the Sherlock agent (read-only debugger)

Pattern: Error → Verify State → Fix → Verify Again

Why: LLMs can hallucinate fixes. Verification provides ground truth.
See CLAUDE.md § Reality Check Protocol""")

# ============================================================================
# PATTERN 6: Multiple Write/Edit → Drift Check
# ============================================================================
if write_count + edit_count >= 3:
    # Only suggest drift check once per session
    drift_suggested = any(
        "/drift" in e.get("reason", "")
        for e in evidence_ledger
    )

    if not drift_suggested:
        suggestions.append("""📐 MULTIPLE MODIFICATIONS DETECTED → CHECK STYLE CONSISTENCY

You've made {count} write/edit operations. Check for style drift:

  /drift    - Analyze style consistency across project

Example issues detected:
  - Inconsistent import order
  - Mixed naming conventions (snake_case vs camelCase)
  - Inconsistent error handling patterns

Why: Multiple modifications can introduce style inconsistencies.
See CLAUDE.md § Sentinel Protocol""".format(count=write_count + edit_count))

# ============================================================================
# PATTERN 7: Task Delegation → Evidence Review
# ============================================================================
if tool_name == "Task":
    subagent_type = tool_params.get("subagent_type", "")

    suggestions.append("""🤖 AGENT DELEGATION COMPLETED → REVIEW EVIDENCE

You delegated to the '{agent}' agent. Review what was learned:

  /evidence review          - See evidence gathered by tools
  /confidence status        - Check confidence boost from delegation

Agent confidence boosts:
  - Researcher: +25% (better than manual research +20%)
  - Script-smith: +15% (with quality gates)
  - Others: +20% (delegation credit)

Why: Agents gather evidence - review it to understand what changed.
See CLAUDE.md § Epistemological Protocol""".format(agent=subagent_type))

# ============================================================================
# PATTERN 8: Read 5+ Files → Suggest XRay Structural Search
# ============================================================================
read_count = sum(1 for e in evidence_ledger if e.get("tool") == "Read")

if read_count >= 5:
    # Only suggest once per session
    xray_suggested = any(
        "/xray" in e.get("reason", "")
        for e in evidence_ledger
    )

    if not xray_suggested:
        suggestions.append("""🔬 MANY FILES READ → USE STRUCTURAL SEARCH

You've read {count} files. For code structure exploration, use XRay:

  /xray --type class --name User        - Find class definitions
  /xray --type function --name validate - Find function definitions
  /xray --type import --name pandas     - Find import usage

Why: XRay uses AST (not regex), finds exact definitions + inheritance.
See CLAUDE.md § X-Ray Protocol""".format(count=read_count))

# ============================================================================
# Output Suggestions (max 2 to avoid spam)
# ============================================================================
if suggestions:
    # Limit to 2 most relevant suggestions
    output = "\n\n".join(suggestions[:2])

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": output,
                }
            }
        )
    )
else:
    # No patterns matched
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }
        )
    )

sys.exit(0)
