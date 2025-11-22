#!/usr/bin/env python3
"""
Command Prerequisite Gate Hook: Enforces workflow command prerequisites
Triggers on: PreToolUse (Bash, Write, Edit, Task)
Purpose: Hard-block actions until prerequisite commands are run
"""
import sys
import json
import re
from pathlib import Path

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import (
    load_session_state,
    initialize_session_state,
    check_command_prerequisite,
    get_confidence_tier,
    get_tier_privileges,
)

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    # Fail open on parse error (not a security issue)
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                }
            }
        )
    )
    sys.exit(0)

session_id = input_data.get("sessionId", "unknown")
tool_name = input_data.get("toolName", "")
tool_params = input_data.get("toolParams", {})

# Load session state
state = load_session_state(session_id)
if not state:
    state = initialize_session_state(session_id)

current_turn = state.get("turn_count", 0)
read_files = state.get("read_files", {})
current_confidence = state.get("confidence", 0)

# Get current tier and privileges
tier_name, tier_desc = get_confidence_tier(current_confidence)
privileges = get_tier_privileges(current_confidence)
enforcement_mode = privileges.get("prerequisite_mode", "enforce")

# ============================================================================
# EXPERT TIER (95-100%): Bypass all prerequisite checks
# ============================================================================
if enforcement_mode == "disabled":
    # Maximum freedom - no prerequisite enforcement
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": f"""✨ EXPERT TIER ({current_confidence}%) - Prerequisite checks bypassed

You have earned maximum autonomy through consistent evidence gathering.
Quality gates are your choice, not requirement.

Still recommended: /verify for claims, /upkeep before commits.""",
                }
            }
        )
    )
    sys.exit(0)

# ============================================================================
# RULE 1: Bash "git commit" requires /upkeep (last 20 turns)
# ============================================================================
if tool_name == "Bash":
    command = tool_params.get("command", "")

    if "git commit" in command:
        prereq_met, error_msg = check_command_prerequisite(
            session_id, "upkeep", current_turn, recency_window=20
        )
        if not prereq_met:
            # TRUSTED tier: Warning instead of block
            if enforcement_mode == "warn":
                warning_message = f"""⚠️ PREREQUISITE RECOMMENDATION (Trusted tier)

{error_msg}

RECOMMENDED: Run /upkeep before committing

Why:
  - Syncs requirements.txt with imports
  - Updates tool index
  - Checks scratch/ for orphaned scripts

At TRUSTED tier ({current_confidence}%), you can commit without upkeep.
However, upkeep is still recommended for project consistency.

Proceeding with commit (no block, but tracked)."""

                print(
                    json.dumps(
                        {
                            "hookSpecificOutput": {
                                "hookEventName": "PreToolUse",
                                "permissionDecision": "allow",
                                "additionalContext": warning_message,
                            }
                        }
                    )
                )
                sys.exit(0)

            # CERTAINTY tier: Hard block
            block_message = f"""🚫 PREREQUISITE VIOLATION: /upkeep Required Before Commit

{error_msg}

RULE: Run /upkeep before every commit

Why:
  - Syncs requirements.txt with imports
  - Updates tool index
  - Checks scratch/ for orphaned scripts
  - Ensures project consistency

Required action:
  /upkeep

After upkeep completes, then commit.

See CLAUDE.md § Upkeep Protocol"""

            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": block_message,
                        }
                    }
                )
            )
            sys.exit(0)

    # ========================================================================
    # RULE 2: Bash with "Fixed"/"Done"/"Working" in description
    #         requires /verify (last 3 turns)
    # NOTE: This rule is ALWAYS enforced, even at EXPERT tier (anti-gaslighting)
    # ========================================================================
    description = tool_params.get("description", "")
    completion_claims = ["fixed", "done", "working", "complete", "success"]

    if description and any(claim in description.lower() for claim in completion_claims):
        prereq_met, error_msg = check_command_prerequisite(
            session_id, "verify", current_turn, recency_window=3
        )
        if not prereq_met:
            # EXPERT tier gets softer message, but still blocked
            if enforcement_mode == "disabled":
                block_message = f"""⚠️ VERIFICATION RECOMMENDED (Even at Expert tier)

You claimed "{description}" but haven't run /verify recently.

{error_msg}

Even at EXPERT tier, verification is strongly recommended for claims.
LLMs hallucinate success - probability ≠ truth.

Recommended action:
  /verify command_success "<your command>"

You can proceed, but consider verifying first to avoid gaslighting loops."""

                print(
                    json.dumps(
                        {
                            "hookSpecificOutput": {
                                "hookEventName": "PreToolUse",
                                "permissionDecision": "allow",
                                "additionalContext": block_message,
                            }
                        }
                    )
                )
                sys.exit(0)

            # All other tiers: Hard block
            block_message = f"""🚫 PREREQUISITE VIOLATION: /verify Required

You claimed "{description}" but haven't run /verify recently.

{error_msg}

RULE: Never claim "Fixed" / "Done" without verification

Why:
  - LLMs hallucinate success
  - Probability ≠ Truth
  - Exit code is ground truth

Required action:
  /verify command_success "<your command>"

After verification passes, then make claims.

See CLAUDE.md § Reality Check Protocol (Anti-Gaslighting)"""

            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": block_message,
                        }
                    }
                )
            )
            sys.exit(0)

# ============================================================================
# RULE 3: Edit requires file in read_files (Read before Edit)
# NOTE: This is now handled by tier_gate.py with graduated enforcement
# ============================================================================
# Removed - tier_gate.py handles read-before-edit with graduated tiers

# ============================================================================
# RULE 4: Write to production code requires /audit AND /void (last 10 turns)
# ============================================================================
if tool_name == "Write":
    file_path = tool_params.get("file_path", "")

    # Check if production code (not scratch/)
    if file_path and "scratch/" not in file_path:
        path = Path(file_path)
        is_production = path.suffix == ".py" and (
            "scripts/" in file_path or "src/" in file_path or "lib/" in file_path
        )

        if is_production:
            # Check both audit and void
            audit_met, audit_msg = check_command_prerequisite(
                session_id, "audit", current_turn, recency_window=10
            )
            void_met, void_msg = check_command_prerequisite(
                session_id, "void", current_turn, recency_window=10
            )

            if not (audit_met and void_met):
                missing = []
                if not audit_met:
                    missing.append(f"/audit - {audit_msg}")
                if not void_met:
                    missing.append(f"/void - {void_msg}")

                # TRUSTED tier: Warning instead of block
                if enforcement_mode == "warn":
                    warning_message = f"""⚠️ QUALITY GATES RECOMMENDED (Trusted tier)

You're writing production code to {path.name} without quality checks.

Missing prerequisites:
{chr(10).join(f"  • {m}" for m in missing)}

RECOMMENDED: Run /audit AND /void before production writes

Why:
  - /audit: Catches security issues, secrets, high complexity
  - /void: Catches stubs, missing CRUD, incomplete error handling

At TRUSTED tier ({current_confidence}%), you can write without quality gates.
However, running them is still recommended for safety.

Proceeding with write (no block, but tracked)."""

                    print(
                        json.dumps(
                            {
                                "hookSpecificOutput": {
                                    "hookEventName": "PreToolUse",
                                    "permissionDecision": "allow",
                                    "additionalContext": warning_message,
                                }
                            }
                        )
                    )
                    sys.exit(0)

                # CERTAINTY tier: Hard block
                block_message = f"""🚫 PREREQUISITE VIOLATION: Quality Gates Required

You're writing production code to {path.name} without quality checks.

Missing prerequisites:
{chr(10).join(f"  • {m}" for m in missing)}

RULE: Production code requires /audit AND /void

Why:
  - /audit: Prevents security issues, secrets, high complexity
  - /void: Prevents stubs, missing CRUD, incomplete error handling

Required actions:
  /audit <file>
  /void <file>

After both pass, then write production code.

See CLAUDE.md § Sentinel Protocol (Code Quality)"""

                print(
                    json.dumps(
                        {
                            "hookSpecificOutput": {
                                "hookEventName": "PreToolUse",
                                "permissionDecision": "deny",
                                "permissionDecisionReason": block_message,
                            }
                        }
                    )
                )
                sys.exit(0)

# ============================================================================
# RULE 5: Task (script-smith) with complex prompt requires /think (last 10 turns)
# ============================================================================
if tool_name == "Task":
    subagent_type = tool_params.get("subagent_type", "")
    prompt = tool_params.get("prompt", "")

    # Check if delegating to script-smith with complex task
    if subagent_type == "script-smith" and len(prompt) > 200:
        prereq_met, error_msg = check_command_prerequisite(
            session_id, "think", current_turn, recency_window=10
        )

        if not prereq_met:
            # TRUSTED tier: Warning instead of block
            if enforcement_mode == "warn":
                warning_message = f"""⚠️ DECOMPOSITION RECOMMENDED (Trusted tier)

You're delegating a complex task to script-smith ({len(prompt)} chars) without decomposition.

{error_msg}

RECOMMENDED: Run /think for complex delegations

Why:
  - Decomposes problem into clear steps
  - Prevents missing requirements
  - Agent works better with structured instructions

At TRUSTED tier ({current_confidence}%), you can delegate without /think.
However, decomposition is still recommended for complex tasks.

Proceeding with delegation (no block, but tracked)."""

                print(
                    json.dumps(
                        {
                            "hookSpecificOutput": {
                                "hookEventName": "PreToolUse",
                                "permissionDecision": "allow",
                                "additionalContext": warning_message,
                            }
                        }
                    )
                )
                sys.exit(0)

            # CERTAINTY tier: Hard block
            block_message = f"""🚫 PREREQUISITE VIOLATION: /think Required for Complex Delegation

You're delegating a complex task to script-smith ({len(prompt)} chars) without decomposition.

{error_msg}

RULE: Complex tasks (>200 chars) require /think first

Why:
  - /think decomposes problem into steps
  - Prevents missing requirements
  - Ensures comprehensive solution
  - Agent works better with clear steps

Required action:
  /think "<your problem description>"

After decomposition, then delegate with clear steps.

See CLAUDE.md § Cartesian Protocol (Meta-Cognition)"""

            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": block_message,
                        }
                    }
                )
            )
            sys.exit(0)

# ============================================================================
# All checks passed - allow action
# ============================================================================
print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }
    )
)
sys.exit(0)
