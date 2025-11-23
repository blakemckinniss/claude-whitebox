#!/usr/bin/env python3
"""
Best Practice Enforcer Hook: Strong assertions for common mistakes
Triggers on: UserPromptSubmit
Purpose: Use MANDATORY/RULE/BLOCKED language to prevent anti-patterns
"""
import sys
import json

try:
    data = json.load(sys.stdin)
except:
    sys.exit(0)

prompt = data.get("prompt", "").lower()

# Detect anti-patterns and enforce best practices
enforcements = []

# 1. REQUESTS ON DYNAMIC SITES - MANDATORY Playwright
dynamic_site_patterns = ["scrape", "crawl", "dynamic", "javascript", "spa", "react app"]
requests_patterns = ["requests.", "import requests", "use requests"]

if any(d in prompt for d in dynamic_site_patterns) and any(
    r in prompt for r in requests_patterns
):
    enforcements.append("""🚫 CRITICAL: HEADLESS PROTOCOL MANDATORY

You are attempting to use `requests` library for a dynamic website.

RULE: NO `requests` library for dynamic sites. PERIOD.

WHY:
  ❌ requests cannot execute JavaScript
  ❌ requests cannot wait for DOM to load
  ❌ requests cannot interact with SPA frameworks

  ✅ Playwright CAN do all of the above

MANDATORY ACTION:
  python3 scripts/scaffold.py scratch/scraper.py --template playwright

Example Playwright code:
  from playwright.sync_api import sync_playwright

  with sync_playwright() as p:
      browser = p.chromium.launch(headless=True)
      page = browser.new_page()
      page.goto("https://example.com")
      content = page.content()  # Full rendered HTML

This is NON-NEGOTIABLE per CLAUDE.md § Headless Protocol.

BLOCKED: If you try requests on dynamic site, it WILL fail. Use Playwright.
""")

# 2. GUESSING APIs - MANDATORY Probe
api_guess_patterns = [
    "should be",
    "probably has",
    "might have",
    "assume",
    "guess",
    "likely",
]
api_context = [
    "method",
    "function",
    "api",
    "library",
    "pandas",
    "numpy",
    "boto3",
    "fastapi",
    "django",
]

if any(g in prompt for g in api_guess_patterns) and any(a in prompt for a in api_context):
    enforcements.append("""🚫 CRITICAL: API GUESSING PROHIBITED

You are about to GUESS an API signature.

RULE: NO GUESSING. Probe runtime APIs. MANDATORY.

WHY:
  ❌ Training data is from Jan 2025 (stale)
  ❌ Libraries change frequently
  ❌ Hallucinated APIs cause runtime errors

  ✅ Probe shows ACTUAL runtime signatures

MANDATORY ACTION:
  python3 scripts/ops/probe.py <object_path>

Examples:
  probe.py pandas.DataFrame
  probe.py fastapi.FastAPI
  probe.py boto3.client

Output shows:
  - Real method signatures
  - Actual parameter names
  - Return types
  - Docstrings

CONSEQUENCE: If you guess wrong, code breaks. Probe is 2 seconds. Debugging is 20 minutes.

This is NON-NEGOTIABLE per CLAUDE.md § Probe Protocol (Runtime Truth).
""")

# 3. CLAIMING DONE WITHOUT TESTS - BLOCKED
done_patterns = ["done", "complete", "finished", "ready"]
test_patterns = ["test", "pytest", "verify"]

if any(d in prompt for d in done_patterns) and not any(t in prompt for t in test_patterns):
    enforcements.append("""🚫 CRITICAL: PREMATURE "DONE" CLAIM BLOCKED

You're claiming "done" without mentioning tests.

RULE: NO "DONE" WITHOUT VERIFICATION. MANDATORY.

Before claiming complete, you MUST:
  ☐ Tests written and passing
  ☐ /verify command_success "pytest tests/"
  ☐ /audit <files> (security scan)
  ☐ /void <files> (completeness check)

Pattern: Build → Test → Verify → THEN claim done

CONSEQUENCE: "Done" without tests = HALLUCINATION
  - Code may not work at all
  - Edge cases untested
  - Breaks in production

MANDATORY ACTION:
  /verify command_success "pytest tests/test_<module>.py"

Only after verification passes can you say "done".

This is NON-NEGOTIABLE per CLAUDE.md § Reality Check Protocol.
""")

# 4. MODIFYING WITHOUT READING - BLOCKED
modify_patterns = ["modify", "edit", "change", "update"]
# Check if it's a code modification request
code_extensions = [".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp"]

if any(m in prompt for m in modify_patterns) and any(ext in prompt for ext in code_extensions):
    enforcements.append("""⚠️ CRITICAL: READ BEFORE MODIFY RULE

You're attempting to modify code.

RULE: ALWAYS Read file BEFORE modifying it. MANDATORY.

WHY:
  ❌ Context blindness = breaking changes
  ❌ Missing dependencies
  ❌ Inconsistent patterns
  ❌ Duplicate functionality

  ✅ Reading first = understanding context

WORKFLOW:
  1. Read target file → +10% confidence
  2. Read related files (imports, callers) → +10% each
  3. Understand existing patterns
  4. THEN modify with context

CONFIDENCE REQUIREMENT:
  Modifying code requires 71%+ (CERTAINTY tier)
  tier_gate.py will BLOCK Edit tool if <71%

CONSEQUENCE: Blind modification = high risk of bugs, inconsistency, breaking changes

Check what you've read:
  /evidence review

See CLAUDE.md § Epistemological Protocol (Read before Write).
""")

# 5. BATCH OPERATIONS WITHOUT PARALLEL - PERFORMANCE VIOLATION
batch_patterns = ["all files", "every file", "batch", "bulk", "mass", "100+", "1000+"]

if any(b in prompt for b in batch_patterns):
    enforcements.append("""⚠️ PERFORMANCE PROTOCOL VIOLATION

You're processing multiple items.

RULE: Batch operations MUST use parallel execution. MANDATORY.

WHY:
  ❌ Sequential = slow (1 file/sec = 1000 files = 16 minutes)
  ✅ Parallel = fast (10 workers = 1000 files = 2 minutes)

MANDATORY CODE PATTERN:
  from scripts.lib.parallel import run_parallel

  def process_item(item):
      # Your processing logic
      return result

  results = run_parallel(
      process_item,
      items,
      max_workers=50,
      desc="Processing items"
  )

Benefits:
  - ThreadPoolExecutor with progress bar
  - Error handling per item
  - 10x+ speedup on I/O operations

CONSEQUENCE: Sequential batch = user waits unnecessarily

See CLAUDE.md § Scripting Protocol (Performance).
""")

# 6. COMMITTING WITHOUT AUDIT - SECURITY VIOLATION
commit_without_audit = "commit" in prompt and "audit" not in prompt

if commit_without_audit:
    enforcements.append("""🛡️ SECURITY PROTOCOL VIOLATION

You're committing without security audit.

RULE: MANDATORY audit.py before ANY commit.

WHY:
  ❌ Secrets leaked (.env, API keys)
  ❌ SQL injection vulnerabilities
  ❌ XSS attacks possible
  ❌ High cyclomatic complexity

  ✅ audit.py catches these BEFORE commit

MANDATORY WORKFLOW:
  1. python3 scripts/ops/audit.py <files>
  2. Fix CRITICAL issues (BLOCKS commit)
  3. Fix HIGH/MEDIUM issues (best effort)
  4. python3 scripts/ops/void.py <files>
  5. python3 scripts/ops/drift_check.py
  6. THEN commit

CONSEQUENCE:
  - Committing secrets = security breach
  - Committing vulnerabilities = exploits in production
  - Committing complex code = unmaintainable

Hooks will enforce this, but you should run proactively.

See CLAUDE.md § Sentinel Protocol (Code Quality).
""")

# 7. USING ECHO/PRINT TO COMMUNICATE - ANTI-PATTERN
communication_antipattern = any(
    p in prompt for p in ["echo", "print to user", "tell user with print"]
)

if communication_antipattern:
    enforcements.append("""⚠️ COMMUNICATION ANTI-PATTERN DETECTED

You're using echo/print to communicate with user.

RULE: NEVER use bash echo or print statements to communicate.

WHY:
  ❌ echo is for SYSTEM OUTPUT, not user communication
  ✅ Text output is for user communication

CORRECT PATTERN:
  Don't: Bash tool with "echo 'The file was created'"
  Do:    Output text: "I created the file at path/to/file"

  Don't: Bash tool with "echo 'Process complete'"
  Do:    Output text: "The process completed successfully"

CONSEQUENCE:
  - echo appears in bash output (ugly formatting)
  - User sees command-line noise
  - Violates tool purpose separation

CORRECT USAGE OF ECHO:
  ✅ Generating file content: echo "data" > file.txt
  ✅ Piping to other commands: echo "$VAR" | grep pattern
  ❌ Talking to user: echo "I finished the task"

See system instructions § Tool Usage Policy.
""")

# Output enforcements if any violations detected
if enforcements:
    # Join with double newline between enforcements
    full_context = "\n\n".join(enforcements)

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
    # No violations detected, pass through
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
