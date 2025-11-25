#!/usr/bin/env python3
"""
Post-Tool Command Suggester Hook v2: Comprehensive pattern-based recommendations
Triggers on: PostToolUse
Purpose: Inject contextual guidance leveraging ALL ops tools and protocols

PHILOSOPHY:
- Every tool use is an opportunity to suggest the next best action
- Failures should immediately suggest alternatives
- Success should suggest quality gates and verification
- Patterns in behavior should trigger workflow guidance
"""
import sys
import json
import re
from pathlib import Path

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if not SCRIPT_DIR.exists():
    SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from lib.epistemology import load_session_state
except ImportError:
    import sys as _sys
    print("⚠️ post_tool_suggester: epistemology import failed, workflow triggers disabled", file=_sys.stderr)
    def load_session_state(sid):
        return {}

# =============================================================================
# TOOL FALLBACK CHAINS - When tool X fails, suggest Y
# =============================================================================
FALLBACK_CHAINS = {
    "WebFetch": {
        "triggers": ["failed", "error", "timeout", "blocked", "403", "404", "429", "rate limit", "empty", "redirect"],
        "suggestion": """🔄 WEB FETCH FAILED → FALLBACK CHAIN

1. **Firecrawl** (handles JS, anti-bot):
   firecrawl scrape "<url>"

2. **Playwright** (for complex sites):
   Use browser.py with get_browser_session()

3. **Research** (for search queries):
   research "<topic> documentation"

Why: Different tools handle different edge cases."""
    },
    "WebSearch": {
        "triggers": ["no results", "empty", "failed", "error", "rate limit"],
        "suggestion": """🔄 WEB SEARCH FAILED → ALTERNATIVES

1. **Research.py** (Tavily API):
   research "<refined query>"

2. **Firecrawl** (if you have specific URL):
   firecrawl scrape "https://docs.example.com"

3. **Probe** (for runtime API inspection):
   probe <module.Class>

Why: Search engines vary in coverage."""
    },
    "Grep": {
        "triggers": ["no matches", "0 matches", "not found"],
        "suggestion": """🔄 GREP FOUND NOTHING → ALTERNATIVES

1. **XRay** (AST-based, finds definitions):
   xray --type function --name <name>
   xray --type class --name <name>

2. **Glob** (find files by pattern):
   Glob with pattern "**/*<name>*"

3. **Broader search**:
   Grep with -i (case insensitive)

Why: Regex misses structural patterns."""
    },
    "Read": {
        "triggers": ["does not exist", "not found", "permission denied", "is a directory"],
        "suggestion": """🔄 READ FAILED → VERIFY PATH

1. **List directory first**:
   ls -la <parent_dir>

2. **Glob to find**:
   Glob with pattern "**/<filename>"

3. **Check if directory**:
   ls -F <path>

Why: Never guess paths - verify first (CLAUDE.md § Phantom Ban)."""
    },
}

# =============================================================================
# TOOL SUCCESS PATTERNS - When tool X succeeds, suggest next step
# =============================================================================
SUCCESS_PATTERNS = {
    "Write": {
        "production_paths": ["scripts/", "src/", "lib/", ".claude/hooks/"],
        "suggestion": """🛡️ PRODUCTION CODE WRITTEN → QUALITY GATES

Required before claiming done:
  audit <file>    - Security, complexity, secrets
  void <file>     - Completeness (stubs, missing ops)
  /drift          - Style consistency

Pattern: Write → Audit → Void → Verify → Commit"""
    },
    "Edit": {
        "production_paths": ["scripts/", "src/", "lib/", ".claude/hooks/"],
        "suggestion": """🛡️ PRODUCTION CODE EDITED → VERIFY INTEGRATION

1. **Reverse dependency check**:
   grep -r "<function_name>" . --include="*.py"

2. **Run tests**:
   pytest <related_tests>

3. **Quality gates**:
   audit <file> && void <file>

Why: Edits can break consumers (CLAUDE.md § Integration Blindness)."""
    },
    "Task": {
        "suggestion": """🤖 AGENT COMPLETED → REVIEW & INTEGRATE

1. **Review evidence**:
   /evidence review

2. **Check confidence boost**:
   /confidence status

3. **Verify agent claims**:
   Use /verify to confirm any "fixed" claims

Why: Trust but verify - agents can hallucinate too."""
    },
    "Bash": {
        "test_commands": ["pytest", "npm test", "cargo test", "go test", "make test"],
        "suggestion": """✅ TESTS RAN → VERIFY EXIT CODE

Don't trust output text alone:
  /verify command_success "<test_command>"

If tests failed:
  1. Read the failing test file
  2. Read the code being tested
  3. Use /think to decompose the fix

Why: Exit code is ground truth."""
    },
}

# =============================================================================
# WORKFLOW TRIGGERS - Based on accumulated session patterns
# =============================================================================
WORKFLOW_TRIGGERS = {
    "multiple_reads": {
        "threshold": 5,
        "tool": "Read",
        "suggestion": """🔬 MANY FILES READ → USE STRUCTURAL SEARCH

XRay for code structure:
  xray --type class --name <Name>
  xray --type function --name <Name>
  xray --type import --name <module>

Why: AST search finds definitions, not just text matches."""
    },
    "multiple_writes": {
        "threshold": 3,
        "tool": "Write",
        "suggestion": """📐 MULTIPLE WRITES → CHECK CONSISTENCY

Run style drift check:
  /drift

Run upkeep before commit:
  /upkeep

Why: Multiple modifications can introduce inconsistencies."""
    },
    "multiple_greps": {
        "threshold": 4,
        "tool": "Grep",
        "suggestion": """📝 GREP ITERATION DETECTED → USE SCRIPT

Write a scratch script instead:
  scratch/search_analysis.py

Or use XRay for structural search:
  xray --type <type> --name <name>

Why: Manual iteration is inefficient (CLAUDE.md § Scratch-First)."""
    },
    "multiple_bash": {
        "threshold": 5,
        "tool": "Bash",
        "suggestion": """⚡ BASH ITERATION DETECTED → AUTOMATE

Write to scratch/ instead of manual commands:
  scratch/<task>_script.py

Use parallel.py for bulk operations:
  from parallel import parallel_execute

Why: Loops are banned, scripts are encouraged."""
    },
}

# =============================================================================
# ERROR TYPE HANDLERS - Specific error patterns
# =============================================================================
ERROR_HANDLERS = {
    r"ModuleNotFoundError|ImportError": """📦 IMPORT ERROR → CHECK ENVIRONMENT

1. **Check if installed**:
   pip show <package>

2. **MacGyver Protocol** (avoid installing):
   inventory  - Check what's available
   - Prefer stdlib over pip install

3. **If must install**:
   pip install <package> --user""",

    r"TypeError|AttributeError": """🔍 TYPE/ATTRIBUTE ERROR → PROBE RUNTIME

Don't guess - inspect:
  probe <module.object>

Example:
  probe pandas.DataFrame.merge

Why: Runtime truth > documentation.""",

    r"FileNotFoundError|No such file": """📁 FILE NOT FOUND → VERIFY PATH

1. **List parent directory**:
   ls -la <parent>

2. **Find the file**:
   Glob with "**/<filename>"

3. **Map before territory**:
   Never assume paths exist (CLAUDE.md § Map Before Territory).""",

    r"PermissionError|Permission denied": """🔒 PERMISSION ERROR → CHECK ACCESS

1. **Check permissions**:
   ls -la <file>

2. **Check ownership**:
   stat <file>

3. **If needed** (use sparingly):
   chmod/chown with SUDO""",

    r"TimeoutError|timed out|timeout": """⏱️ TIMEOUT → USE BACKGROUND EXECUTION

For slow operations:
  Bash with run_in_background=true

Check later:
  BashOutput(bash_id="<id>")

Why: Don't block session on slow ops.""",

    r"JSONDecodeError|Invalid JSON": """📋 JSON ERROR → VALIDATE FORMAT

1. **Check raw content**:
   cat <file> | head -20

2. **Validate JSON**:
   python3 -m json.tool <file>

3. **Common issues**:
   - Trailing commas
   - Unquoted keys
   - Single quotes (use double)""",

    r"ConnectionError|Connection refused": """🌐 CONNECTION ERROR → CHECK SERVICE

1. **Is service running?**
   verify port_open localhost:<port>

2. **Check URL**:
   curl -I <url>

3. **Firecrawl alternative** (for web):
   firecrawl scrape <url>""",
}

# =============================================================================
# CONTEXT-AWARE SUGGESTIONS - Based on what was being done
# =============================================================================
CONTEXT_SUGGESTIONS = {
    "api_research": {
        "keywords": ["api", "documentation", "docs", "sdk", "library", "package"],
        "tools": ["WebFetch", "WebSearch", "Bash"],
        "suggestion": """🔬 API RESEARCH DETECTED → VERIFY AT RUNTIME

Don't trust docs alone:
  probe <module.Class>

Example workflow:
  1. research "pandas merge documentation 2024"
  2. probe pandas.DataFrame.merge
  3. Code with confidence

Why: Training cutoff is Jan 2025."""
    },
    "debugging": {
        "keywords": ["error", "bug", "fix", "broken", "fail", "issue"],
        "tools": ["Read", "Bash", "Edit"],
        "suggestion": """🐛 DEBUGGING DETECTED → STRUCTURED APPROACH

1. **Reproduce** (verify error exists):
   /verify command_success "<failing_command>"

2. **Decompose** (if complex):
   /think "<describe the problem>"

3. **Three-Strike Rule**:
   If 2 fixes failed, MUST run /think

Why: Systematic > random attempts."""
    },
    "refactoring": {
        "keywords": ["refactor", "rename", "move", "restructure", "clean"],
        "tools": ["Edit", "Write", "Bash"],
        "suggestion": """🔧 REFACTORING DETECTED → QUALITY PROTOCOL

1. **Before changing**:
   xray --type <type> --name <name>  # Find all usages

2. **After changing**:
   grep -r "<old_name>" .  # Verify no remnants
   /drift                   # Check consistency

3. **Separate commit**:
   Refactor BEFORE adding features

Why: CLAUDE.md § Preparatory Refactoring."""
    },
    "testing": {
        "keywords": ["test", "pytest", "spec", "coverage", "assert"],
        "tools": ["Bash", "Read", "Write"],
        "suggestion": """🧪 TESTING DETECTED → VERIFICATION PROTOCOL

1. **Verify tests pass**:
   /verify command_success "pytest <test_file>"

2. **If tests fail**:
   Read test file THEN implementation
   Use /think for complex failures

3. **Coverage check** (optional):
   pytest --cov=<module>

Why: Test critical paths only (CLAUDE.md § Pareto Testing)."""
    },
    "deployment": {
        "keywords": ["deploy", "release", "production", "build", "docker"],
        "tools": ["Bash", "Write"],
        "suggestion": """🚀 DEPLOYMENT DETECTED → GATE PROTOCOL

MANDATORY before deploy:
  /upkeep          # Sync requirements, clean
  audit <files>    # Security scan
  void <files>     # Completeness check

Verify build:
  /verify command_success "<build_command>"

Why: Production changes need gates."""
    },
}

# =============================================================================
# PROTOCOL REMINDERS - Based on tool + result patterns
# =============================================================================
PROTOCOL_REMINDERS = {
    "completion_claim": {
        "keywords": ["done", "complete", "finished", "fixed", "working", "100%", "success"],
        "suggestion": """⚠️ COMPLETION CLAIM → VERIFY BEFORE CLAIMING

REQUIRED (CLAUDE.md § Hard Block #3):
  /verify <check_type> <target>

Examples:
  /verify command_success "pytest tests/"
  /verify file_exists "<expected_output>"
  /verify grep_text "<file>" --expected "<text>"

Why: No "Fixed" claim without verify passing."""
    },
    "commit_intent": {
        "keywords": ["commit", "git add", "push", "merge"],
        "suggestion": """📝 COMMIT INTENT DETECTED → PREREQUISITES

MANDATORY (CLAUDE.md § Hard Block #2):
  /upkeep  # Must run in last 20 turns

Recommended:
  audit <changed_files>
  void <changed_files>
  /drift

Why: Commits require upkeep first."""
    },
}

# =============================================================================
# MAIN HOOK LOGIC
# =============================================================================
def extract_text(tool_result):
    """Extract text content from tool result (handles various formats)"""
    if isinstance(tool_result, str):
        return tool_result
    if isinstance(tool_result, dict):
        content = tool_result.get("content", "")
        if isinstance(content, list):
            return "\n".join(
                item.get("text", "") for item in content if isinstance(item, dict)
            )
        return str(content)
    return str(tool_result)


def check_fallbacks(tool_name, result_text):
    """Check if tool failed and suggest fallbacks"""
    if tool_name not in FALLBACK_CHAINS:
        return None

    chain = FALLBACK_CHAINS[tool_name]
    result_lower = result_text.lower()

    if any(trigger in result_lower for trigger in chain["triggers"]):
        return chain["suggestion"]
    return None


def check_success_patterns(tool_name, tool_params, result_text):
    """Check for success patterns that need follow-up"""
    if tool_name not in SUCCESS_PATTERNS:
        return None

    pattern = SUCCESS_PATTERNS[tool_name]
    file_path = tool_params.get("file_path", "")
    command = tool_params.get("command", "")

    # Check production paths for Write/Edit
    if tool_name in ["Write", "Edit"]:
        prod_paths = pattern.get("production_paths", [])
        if any(p in file_path for p in prod_paths) and "scratch/" not in file_path:
            return pattern["suggestion"]

    # Check test commands for Bash
    if tool_name == "Bash":
        test_cmds = pattern.get("test_commands", [])
        if any(cmd in command for cmd in test_cmds):
            return pattern["suggestion"]

    # Task always gets suggestion
    if tool_name == "Task":
        return pattern["suggestion"]

    return None


def check_error_patterns(result_text):
    """Check for specific error types"""
    for pattern, suggestion in ERROR_HANDLERS.items():
        try:
            if re.search(pattern, result_text, re.IGNORECASE):
                return suggestion
        except re.error:
            # Invalid regex pattern in config - skip it
            continue
    return None


def check_workflow_triggers(session_state, tool_name):
    """Check for workflow patterns based on session history"""
    evidence = session_state.get("evidence_ledger", [])

    for trigger_name, config in WORKFLOW_TRIGGERS.items():
        target_tool = config["tool"]
        threshold = config["threshold"]

        count = sum(1 for e in evidence if e.get("tool") == target_tool)

        if tool_name == target_tool and count >= threshold:
            # Only suggest once per session
            already_suggested = any(
                trigger_name in str(e.get("reason", ""))
                for e in evidence
            )
            if not already_suggested:
                return config["suggestion"]

    return None


def check_context_suggestions(tool_name, tool_params, result_text):
    """Check for context-aware suggestions"""
    combined_text = f"{tool_params} {result_text}".lower()

    for context_name, config in CONTEXT_SUGGESTIONS.items():
        if tool_name not in config["tools"]:
            continue

        keywords = config["keywords"]
        if any(kw in combined_text for kw in keywords):
            return config["suggestion"]

    return None


def check_protocol_reminders(result_text):
    """Check if protocol reminders are needed"""
    result_lower = result_text.lower()

    for reminder_name, config in PROTOCOL_REMINDERS.items():
        keywords = config["keywords"]
        if any(kw in result_lower for kw in keywords):
            return config["suggestion"]

    return None


def main():
    # Load input
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "",
            }
        }))
        sys.exit(0)

    try:
        tool_name = input_data.get("tool_name", "")
        # Handle null tool_input: JSON null becomes None, not {}
        tool_params = input_data.get("tool_input") or {}
        tool_result = input_data.get("tool_response") or input_data.get("toolResult", "")
        session_id = input_data.get("session_id", "unknown")

        if not tool_name:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }))
            sys.exit(0)

        # Extract text from result
        result_text = extract_text(tool_result)

        # Load session state
        session_state = load_session_state(session_id) or {}

        # Collect suggestions (priority order)
        suggestions = []

        # 1. Check for tool failures → fallbacks (highest priority)
        fallback = check_fallbacks(tool_name, result_text)
        if fallback:
            suggestions.append(fallback)

        # 2. Check for specific error patterns
        error_suggestion = check_error_patterns(result_text)
        if error_suggestion:
            suggestions.append(error_suggestion)

        # 3. Check for success patterns needing follow-up
        success_suggestion = check_success_patterns(tool_name, tool_params, result_text)
        if success_suggestion:
            suggestions.append(success_suggestion)

        # 4. Check workflow triggers (iteration detection)
        workflow_suggestion = check_workflow_triggers(session_state, tool_name)
        if workflow_suggestion:
            suggestions.append(workflow_suggestion)

        # 5. Check context-aware suggestions
        context_suggestion = check_context_suggestions(tool_name, tool_params, result_text)
        if context_suggestion:
            suggestions.append(context_suggestion)

        # 6. Check protocol reminders
        protocol_suggestion = check_protocol_reminders(result_text)
        if protocol_suggestion:
            suggestions.append(protocol_suggestion)

        # Output (limit to 2 most relevant)
        if suggestions:
            output = "\n\n".join(suggestions[:2])
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": output,
                }
            }))
        else:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }))

    except Exception as e:
        # Global crash handler - graceful degradation
        print(f"⚠️ post_tool_suggester error: {type(e).__name__}", file=sys.stderr)
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "",
            }
        }))

    sys.exit(0)


if __name__ == "__main__":
    main()
