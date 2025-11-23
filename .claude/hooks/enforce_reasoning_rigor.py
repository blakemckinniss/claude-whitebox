#!/usr/bin/env python3
"""
REASONING RIGOR ENFORCEMENT HOOK
=================================
Hard blocks production actions with invalid reasoning patterns.

TRIGGER: PreToolUse (Write, Edit, Task for production code)
PATTERN: Universal claims without evidence, causal claims without mechanism
ENFORCEMENT: Exit 1 HARD BLOCK (must fix reasoning first)

Philosophy: Detection is advisory. Enforcement is mandatory.
            No production code from fallacious reasoning.
"""

import re
import sys
import json
from pathlib import Path


def find_project_root():
    """Find project root by looking for scripts/lib/core.py"""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "scripts" / "lib" / "core.py").exists():
            return current
        current = current.parent
    return Path.cwd()


PROJECT_ROOT = find_project_root()


# Reasoning requirement patterns
RIGOR_VIOLATIONS = [
    # Universal quantifier without evidence
    (
        "universal_without_evidence",
        r"\b(?:all|every|always|never|none)\s+\w+",
        "BLOCKED: Universal claim without evidence",
        "Universal quantifiers (all/every/always/never) require EXHAUSTIVE VERIFICATION.\n"
        "  Fix: Either verify ALL instances, or use qualified language:\n"
        "    ❌ 'All error handlers follow pattern X'\n"
        "    ✅ '73% of 156 error handlers follow pattern X (verified via grep)'\n"
        "    ✅ 'Error handlers in auth/ follow pattern X (N=12)'\n"
        "    ✅ 'Most error handlers likely follow pattern X (sample N=5)'",
    ),
    # Causal claim without mechanism
    (
        "causation_without_mechanism",
        r"(?:cause[sd]?|lead[s]? to|result[s]? in|trigger[s]?).*(?:because|due to|owing to)(?!.{0,200}(?:via|through|by|mechanism))",
        "BLOCKED: Causal claim without mechanism",
        "Causal claims require MECHANISM explanation.\n"
        "  Fix: Explain the causal pathway:\n"
        "    ❌ 'X causes Y'\n"
        "    ✅ 'X causes Y via [specific mechanism Z]'\n"
        "    ✅ 'X increases likelihood of Y by [pathway]'\n"
        "  Example: 'Race condition causes crash via unsynchronized access to shared state'",
    ),
    # Certainty without verification
    (
        "certainty_without_verification",
        r"\b(?:will definitely|must be|certainly|obviously|clearly|undoubtedly)(?!.{0,100}(?:verify|test|check|probe))",
        "BLOCKED: False certainty without verification",
        "Absolute certainty requires VERIFICATION.\n"
        "  Fix: Use probabilistic language OR run verification:\n"
        "    ❌ 'This will definitely work'\n"
        "    ✅ 'This will likely work (80% confident based on [evidence])'\n"
        "    ✅ 'This will work (verified via /verify command_success)'\n"
        "  Remember: Code is reality. Claims are hypotheses until verified.",
    ),
    # Generalization from single example
    (
        "single_example_generalization",
        r"(?:in this|from this|based on this).*(?:file|example|case).*(?:all|always|typical|standard|pattern)",
        "BLOCKED: Generalization from single example",
        "Pattern claims require MULTIPLE EXAMPLES (N≥3).\n"
        "  Fix: Verify pattern across sufficient sample:\n"
        "    ❌ 'Based on auth.py, all modules use pattern X'\n"
        "    ✅ 'Pattern X found in 8/12 modules (auth, api, db, ...)'\n"
        "    ✅ 'Pattern X observed in auth.py, api.py, db.py (N=3)'\n"
        "  Use: grep or xray to find pattern occurrences",
    ),
]


def is_production_path(file_path):
    """Check if file path is in production zone"""
    if not file_path:
        return False

    path = Path(file_path)

    # Production zones: scripts/ops/, scripts/lib/, .claude/hooks/
    production_dirs = ["scripts/ops", "scripts/lib", ".claude/hooks"]

    try:
        for prod_dir in production_dirs:
            if prod_dir in str(path):
                return True
    except (TypeError, AttributeError):
        pass

    return False


def check_reasoning_rigor(text):
    """Check for reasoning rigor violations"""
    text_lower = text.lower()
    violations = []

    for name, pattern, error, fix in RIGOR_VIOLATIONS:
        matches = list(re.finditer(pattern, text_lower, re.DOTALL | re.MULTILINE))
        if matches:
            for match in matches:
                # Extract context
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].replace("\n", " ")

                violations.append(
                    {
                        "violation": name,
                        "error": error,
                        "fix": fix,
                        "matched_text": match.group(0),
                        "context": context,
                    }
                )

    return violations


def main():
    # Read tool use data from stdin
    try:
        data = json.load(sys.stdin)
        tool_name = data.get("toolName", "")
        tool_params = data.get("toolParams", {})

        # Only enforce for production writes
        if tool_name not in ["Write", "Edit"]:
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "action": "allow",
                        }
                    }
                )
            )
            sys.exit(0)

        # Check if production path
        file_path = tool_params.get("file_path", "")
        if not is_production_path(file_path):
            # Scratch zone - allow (experimentation is OK)
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "action": "allow",
                        }
                    }
                )
            )
            sys.exit(0)

        # Check for "SUDO" override
        recent_prompts = data.get("recentPrompts", [])
        for prompt in recent_prompts[-3:]:  # Last 3 turns
            if "SUDO" in prompt.upper():
                print(
                    json.dumps(
                        {
                            "hookSpecificOutput": {
                                "hookEventName": "PreToolUse",
                                "action": "allow",
                            }
                        }
                    )
                )
                sys.exit(0)

    except (json.JSONDecodeError, KeyError, ValueError, AttributeError):
        # Cannot parse input - allow
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "action": "allow",
                    }
                }
            )
        )
        sys.exit(0)

    # Get recent conversation context (where reasoning happens)
    context_text = " ".join(recent_prompts[-5:]) if recent_prompts else ""

    # Check for reasoning violations
    violations = check_reasoning_rigor(context_text)

    if not violations:
        # No violations - allow
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "action": "allow",
                    }
                }
            )
        )
        sys.exit(0)

    # Build block message
    block_lines = [
        "\n🚫 REASONING RIGOR VIOLATION - HARD BLOCK",
        "=" * 60,
        "",
        "Production code requires rigorous reasoning.",
        f"Target: {file_path}",
        "",
        "VIOLATIONS DETECTED:",
    ]

    for i, v in enumerate(violations, 1):
        block_lines.extend(
            [
                "",
                f"{i}. {v['error']}",
                f"   Matched: ...{v['context']}...",
                "",
                v["fix"],
            ]
        )

    block_lines.extend(
        [
            "",
            "=" * 60,
            "📋 REQUIREMENTS FOR PRODUCTION CODE:",
            "  1. Universal claims (all/always) → Exhaustive verification",
            "  2. Causal claims (X causes Y) → Mechanism explanation",
            "  3. Certainty claims (definitely/must) → Verification or probability",
            "  4. Pattern claims → Multiple examples (N≥3)",
            "",
            "🛠️ TOOLS TO FIX:",
            "  • /verify command_success - Test claims",
            "  • grep/xray - Find pattern occurrences",
            "  • oracle --persona skeptic - Review reasoning",
            "",
            "🚪 OVERRIDE: Include 'SUDO' in prompt to bypass (use sparingly)",
        ]
    )

    block_message = "\n".join(block_lines)

    # HARD BLOCK - deny action
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "action": "deny",
                    "reason": block_message,
                }
            }
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
