#!/usr/bin/env python3
"""
CONSTITUTIONAL GUARD HOOK
=========================
Blocks unauthorized writes to CLAUDE.md (the system constitution).

TRIGGER: PreToolUse (Write/Edit tools)
PATTERN: Any attempt to modify CLAUDE.md
ENFORCEMENT: Hard block with explanation + recommendation mechanism

Philosophy:
-----------
CLAUDE.md is the system constitution - it reflects CURRENT REALITY, not future plans.
AI should not self-modify its own instruction set without explicit human authorization.

However, Claude CAN and SHOULD recommend changes via:
  scratch/claude_md_proposals.md

Workflow:
---------
1. Claude wants to update CLAUDE.md
2. Hook blocks the Write/Edit
3. Claude writes proposal to scratch/claude_md_proposals.md instead
4. User reviews proposal
5. User either:
   - Approves: Manually applies change + uses "SUDO" keyword to allow commit
   - Rejects: Deletes proposal, provides feedback

Bypass:
-------
Include "SUDO CONSTITUTIONAL" in prompt to allow CLAUDE.md modification.
Use this ONLY after reviewing Claude's proposal.
"""

import sys
import json
from pathlib import Path

def validate_file_path(file_path: str) -> bool:
    """
    Validate file path to prevent path traversal attacks.
    Per official docs: "Block path traversal - Check for .. in file paths"
    """
    if not file_path:
        return True

    # Normalize path to resolve any . or .. components
    normalized = str(Path(file_path).resolve())

    # Check for path traversal attempts
    if '..' in file_path:
        return False

    return True


def find_project_root():
    """Find project root by looking for scripts/lib/"""
    current = Path.cwd()
    for _ in range(10):
        if (current / "scripts" / "lib").exists():
            return current
        current = current.parent
    return Path.cwd()

PROJECT_ROOT = find_project_root()
PROPOSALS_FILE = PROJECT_ROOT / "scratch" / "claude_md_proposals.md"

def main():
    """Block unauthorized CLAUDE.md modifications"""
    try:
        data = json.load(sys.stdin)
    except Exception:
        # Can't read input, allow (fail open)
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    tool_name = data.get("toolName", "")
    tool_params = data.get("toolParams", {})
    prompt = data.get("prompt", "")

    # Only intercept Write and Edit tools
    if tool_name not in ["Write", "Edit"]:
        sys.exit(0)

    file_path = tool_params.get("file_path", "")

    # Check if targeting CLAUDE.md
    if not file_path:
        sys.exit(0)

    target = Path(file_path).resolve()
    claude_md = PROJECT_ROOT / "CLAUDE.md"

    if target != claude_md.resolve():
        sys.exit(0)

    # Check for bypass keyword
    if "SUDO CONSTITUTIONAL" in prompt:
        # Allow with warning
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": """
✅ CONSTITUTIONAL OVERRIDE GRANTED

User has authorized CLAUDE.md modification with "SUDO CONSTITUTIONAL".
Proceeding with constitutional change.

⚠️  Reminder: CLAUDE.md should reflect CURRENT REALITY only.
   Do not add roadmaps, future plans, or unimplemented features.
"""
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # BLOCK: Unauthorized constitutional modification
    block_message = """
🛡️ CONSTITUTIONAL GUARD TRIGGERED

BLOCKED: Unauthorized modification of CLAUDE.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📜 RATIONALE:
   CLAUDE.md is the system constitution. It defines CURRENT REALITY,
   not future plans or unimplemented features.

   AI self-modification of the instruction set requires human review
   to prevent:
   • Hallucinated features being added as "implemented"
   • Roadmaps/plans polluting the system prompt
   • Constitutional drift without accountability

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ RECOMMENDED WORKFLOW:

Instead of editing CLAUDE.md directly, you should:

1. Write your proposal to:
   scratch/claude_md_proposals.md

2. Include in your proposal:
   • SECTION: Which part of CLAUDE.md to modify
   • RATIONALE: Why this change is needed
   • CURRENT: The existing text (if editing)
   • PROPOSED: The new text
   • IMPACT: How this changes system behavior

3. User will review your proposal and either:
   • APPROVE: User manually applies change, then uses "SUDO CONSTITUTIONAL"
   • REJECT: User provides feedback on why change isn't needed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Example Proposal Format:
```markdown
# CLAUDE.md Change Proposal

## Section
Manifesto - Rule 19 (new rule)

## Rationale
Need explicit rule preventing AI from editing CLAUDE.md without authorization.

## Current State
No explicit rule about CLAUDE.md immutability.

## Proposed Addition
19. **Constitutional Immutability:** CLAUDE.md is READ-ONLY to AI.
    Propose changes via scratch/claude_md_proposals.md for user review.

## Impact
• Prevents accidental self-modification
• Maintains constitutional integrity
• Creates explicit approval workflow
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BYPASS (User Only):
If you are the user and want to authorize this change, re-run with:
   "SUDO CONSTITUTIONAL <your instruction>"

"""

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": block_message,
        }
    }
    print(json.dumps(output))
    sys.exit(0)

if __name__ == "__main__":
    main()
