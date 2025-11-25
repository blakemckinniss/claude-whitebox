#!/usr/bin/env python3
"""
Prerequisite Checker Hook: Enforces prerequisite steps before major actions
Triggers on: UserPromptSubmit
Purpose: Warn about missing prerequisites before tool execution (early feedback)
"""
import sys
import json
from pathlib import Path

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

prompt = data.get("prompt", "").lower()
session_id = data.get("session_id", "unknown")

# Load session state to check confidence
try:
    memory_dir = Path.home() / ".claude" / "memory"
    state_file = memory_dir / f"session_{session_id}_state.json"

    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)
        confidence = state.get("confidence", 0)
        evidence_ledger = state.get("evidence_ledger", [])
        read_files = state.get("read_files", {})
    else:
        confidence = 0
        evidence_ledger = []
        read_files = {}
except Exception:
    confidence = 0
    evidence_ledger = []
    read_files = {}

# Check for prerequisite violations
warnings = []

# 1. WRITING CODE - Must have context (Read first) and sufficient confidence
code_writing_patterns = [
    "write a",
    "create a",
    "implement",
    "add a function",
    "add a class",
    "build a",
]
if any(p in prompt for p in code_writing_patterns):
    # Check if in production directory (not scratch)
    is_production = (
        "script" in prompt
        or "production" in prompt
        or "/ops/" in prompt
        or "/lib/" in prompt
    )

    if is_production and confidence < 71:
        warnings.append(f"""⚠️ PRE-WRITE PREREQUISITE FAILURE

You want to write PRODUCTION code but confidence is {confidence}% (need 71%+)

Required steps before writing production code:
  1. Read existing files in same module → +10% each
  2. Research APIs/patterns if needed → +20%
  3. Probe complex libraries → +15%
  4. Reach CERTAINTY tier (71%+)

Current tier: {'IGNORANCE' if confidence < 31 else 'HYPOTHESIS'} ({confidence}%)

To check what you've read:
  /evidence review

To boost confidence:
  Read relevant files, Research docs, Probe APIs, Verify assumptions

BLOCKED: tier_gate.py will block Write tool at execution time if <71%
""")

    elif not is_production and confidence < 31:
        warnings.append(f"""⚠️ PRE-WRITE PREREQUISITE WARNING

You want to write code but confidence is {confidence}% (need 31%+ for scratch/)

Recommendation: Read similar code first to understand patterns
  - Read tool → +10% per file
  - Grep tool → +5% for pattern searches

Current tier: IGNORANCE ({confidence}%)
Target: HYPOTHESIS (31%+) for scratch/ writes

To check current state:
  /confidence status
""")

    # Check if they've read ANY files
    if len(read_files) == 0:
        warnings.append("""⚠️ CONTEXT BLINDNESS WARNING

You haven't read any files yet in this session.

RULE: Always Read before Write (prevents context blindness)

Recommended workflow:
  1. Read existing code in same module
  2. Grep for similar patterns
  3. Understand existing architecture
  4. THEN write new code

Why: Writing without reading = high risk of inconsistency, duplication, breaking changes
""")

# 2. EDITING CODE - Must have Read the target file
edit_patterns = ["edit", "modify", "update", "change"]
file_mention_patterns = [
    ".py",
    ".js",
    ".ts",
    ".go",
    ".rs",
    ".java",
    ".cpp",
    ".c",
    "file",
]
if (
    any(p in prompt for p in edit_patterns)
    and any(p in prompt for p in file_mention_patterns)
    and confidence < 71
):
    warnings.append(f"""⚠️ PRE-EDIT PREREQUISITE FAILURE

You want to EDIT code but confidence is {confidence}% (need 71%+)

RULE: Edit requires CERTAINTY tier (71%+) always
Reason: Modifying existing code is higher risk than creating new

Required steps:
  1. Read the target file you want to edit → +10%
  2. Read related files (imports, callers) → +10% each
  3. Verify tests exist → +15%
  4. Reach 71%+ confidence

Current tier: {'IGNORANCE' if confidence < 31 else 'HYPOTHESIS'} ({confidence}%)

BLOCKED: tier_gate.py will hard-block Edit tool if <71%
""")

# 3. COMMITTING - Must run quality checks
commit_patterns = ["commit", "git commit", "push", "create pr"]
if any(p in prompt for p in commit_patterns):
    warnings.append("""⚠️ PRE-COMMIT PREREQUISITE CHECKLIST

Before committing, you MUST complete:

☐ Security scan:     python3 scripts/ops/audit.py <files>
☐ Completeness:      python3 scripts/ops/void.py <files>
☐ Style consistency: python3 scripts/ops/drift_check.py
☐ Tests passing:     /verify command_success "pytest tests/"

Then run:
  python3 scripts/ops/upkeep.py  (syncs requirements, updates index)

RULE: DO NOT skip these steps. Hooks will enforce them.

After all checks pass, then:
  git add <files>
  git commit -m "your message"

The commit hook will auto-format with Co-Authored-By: Claude
""")

# 4. DEPLOYING/PUSHING - Must have tests passing
deploy_patterns = ["deploy", "push to production", "ship", "release"]
if any(p in prompt for p in deploy_patterns):
    warnings.append("""⚠️ PRE-DEPLOY PREREQUISITE CHECKLIST

Before deploying, you MUST verify:

☐ All tests passing:
  /verify command_success "pytest tests/"

☐ No security issues:
  python3 scripts/ops/audit.py <files>

☐ No incomplete code:
  python3 scripts/ops/void.py <files>

☐ Environment check:
  - Secrets not committed (.env, credentials.json)
  - Config correct for target environment
  - Dependencies up to date

RULE: Never deploy without verification
Risk: Production outages, security breaches, data loss

If unsure, run:
  python3 scripts/ops/balanced_council.py "Deploy to production now"
""")

# 5. MAKING DECISIONS - Must gather context first
decision_patterns = ["should we", "which is better", "what's the best"]
if any(p in prompt for p in decision_patterns) and confidence < 40:
    warnings.append(f"""⚠️ PRE-DECISION PREREQUISITE WARNING

You're making a decision but confidence is {confidence}% (low context)

RULE: Don't decide at peak ignorance (Dunning-Kruger trap)

Before deciding:
  1. Research options → +20%
  2. Read existing implementations → +10%
  3. Probe APIs/libraries → +15%
  4. Consult documentation

Then use:
  python3 scripts/ops/balanced_council.py "<your proposal>"

Why: Decisions at low confidence = high risk of wrong choice
Target: 40%+ confidence before council consultation
""")

# Output warnings if any prerequisites missing
if warnings:
    # Join with double newline between warnings
    full_context = "\n\n".join(warnings)

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
    # No prerequisites missing, pass through
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
