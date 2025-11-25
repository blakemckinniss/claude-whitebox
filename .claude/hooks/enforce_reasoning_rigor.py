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


# Reasoning requirement patterns - SUDO
# Expanded false positive list - common patterns that aren't claims
FALSE_POSITIVE_PHRASES = [
    # Git/file operations
    "stage all", "all changes", "all files", "all checks", "all tests",
    "all hooks", "for all", "install all", "remove all", "delete all",
    "read all", "write all", "allow all", "deny all", "pass all",
    "fail all", "run all", "skip all", "list all",
    # Iteration (not claims)
    "every turn", "every file", "every module", "every time",
    "for every", "in every", "on every",
    # Recommendations (not claims about state)
    "always use", "never use", "always prefer", "never commit",
    # Negations
    "none of", "not all", "never mind",
    # Code patterns (docstrings, function names)
    "all registered", "all protocols", "all rules", "all features",
    "all matches", "all results", "all items", "all entries",
    "evaluate all", "process all", "handle all", "return all",
    # Common method names
    "get_all", "list_all", "find_all", "fetch_all", "load_all",
    "_all_", "all_", "_all",
    # Programming context
    "for all x", "all elements", "all keys", "all values",
]

# IMPROVED: Focus on CLAIMS about verification, not any use of "all"
# The problem was "all registered protocols" in docstrings triggering
RIGOR_VIOLATIONS = [
    # Universal quantifier IN CLAIMS about verification/checking
    (
        "universal_claim_without_evidence",
        r"\b(?:i |we |i've |we've )?(?:verified|checked|fixed|updated|tested|confirmed|ensured|reviewed|audited)\s+(?:all|every|each)\b",
        "BLOCKED: Universal verification claim without evidence",
        "Universal verification claims require EXHAUSTIVE EVIDENCE.\n"
        "  Fix: Either verify with grep/xray count, or qualify:\n"
        "    X 'I checked all error handlers'\n"
        "    V 'Checked error handlers in auth/, api/ (N=12, grep count)'\n"
        "    V 'Checked sampled error handlers (N=5 of ~50)'",
    ),
    # "All X work/pass/succeed" without evidence (but allow "All 47 tests pass")
    (
        "universal_success_claim",
        r"\ball\s+(?![\d,]+\s)(?:\w+\s+)?(?:tests?\s+)?(?:work|pass|succeed|complete|fixed|done|running|operational)\b",
        "BLOCKED: Universal success claim without evidence",
        "Claims that 'all X work' require verification.\n"
        "  Fix: Run actual tests or qualify:\n"
        "    X 'All tests pass'\n"
        "    V 'All 47 tests pass (pytest output)'\n"
        "    V '23/25 tests pass (2 skipped)'",
    ),
    # Causal claim without mechanism (keep - reasonable)
    (
        "causation_without_mechanism",
        r"(?:cause[sd]?|lead[s]? to|result[s]? in|trigger[s]?).*(?:because|due to|owing to)(?!.{0,200}(?:via|through|by|mechanism))",
        "BLOCKED: Causal claim without mechanism",
        "Causal claims require MECHANISM explanation.\n"
        "  Fix: Explain the causal pathway:\n"
        "    X 'X causes Y'\n"
        "    V 'X causes Y via [specific mechanism Z]'",
    ),
    # False certainty - specific phrases only
    (
        "certainty_without_verification",
        r"\b(?:this will definitely|must be working|certainly works|obviously fixed|clearly resolved)\b",
        "BLOCKED: False certainty without verification",
        "Absolute certainty requires VERIFICATION.\n"
        "  Fix: Run /verify or use probabilistic language:\n"
        "    X 'This will definitely work'\n"
        "    V 'This should work (80% confident)'\n"
        "    V 'Verified working via pytest'",
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
                
                # Check for false positive phrases
                matched_text = match.group(0).lower()
                is_false_positive = False
                for fp_phrase in FALSE_POSITIVE_PHRASES:
                    if fp_phrase in matched_text or fp_phrase in context.lower():
                        is_false_positive = True
                        break
                
                if is_false_positive:
                    continue  # Skip this match

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
        tool_name = data.get("tool_name", "")
        tool_params = data.get("tool_input", {})

        # Only enforce for production writes
        if tool_name not in ["Write", "Edit"]:
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

        # Check if production path
        file_path = tool_params.get("file_path", "")
        if not is_production_path(file_path):
            # Scratch zone - allow (experimentation is OK)
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

        # Check for "SUDO" override via transcript (PreToolUse doesn't get recentPrompts)
        transcript_path = data.get("transcript_path", "")
        sudo_found = False
        if transcript_path:
            try:
                import os
                if os.path.exists(transcript_path):
                    with open(transcript_path, 'r') as tf:
                        transcript = tf.read()
                        last_chunk = transcript[-5000:] if len(transcript) > 5000 else transcript
                        sudo_found = "SUDO" in last_chunk
            except Exception:
                pass

        if sudo_found:
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "allow",
                            "additionalContext": "⚠️ SUDO bypass - reasoning rigor check skipped"
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
                        "permissionDecision": "allow",
                    }
                }
            )
        )
        sys.exit(0)

    # Get recent conversation context from transcript (where reasoning happens)
    # IMPORTANT: Only check assistant reasoning, NOT tool outputs or tool parameters
    context_text = ""
    transcript_path = data.get("transcript_path", "")
    if transcript_path:
        try:
            import os
            if os.path.exists(transcript_path):
                with open(transcript_path, 'r') as tf:
                    transcript = tf.read()
                    # Use last 10000 chars for reasoning context
                    raw_context = transcript[-10000:] if len(transcript) > 10000 else transcript

                    # Filter out tool results - they contain code with comments like
                    # "# Evaluate all rules" which triggers false positives
                    # Only keep assistant reasoning text, not <function_results> blocks
                    import re
                    # Remove function_results blocks (tool output)
                    context_text = re.sub(
                        r'<function_results>.*?</function_results>',
                        '[TOOL_OUTPUT_REMOVED]',
                        raw_context,
                        flags=re.DOTALL
                    )
                    # Remove result blocks
                    context_text = re.sub(
                        r'<result>.*?</result>',
                        '[RESULT_REMOVED]',
                        context_text,
                        flags=re.DOTALL
                    )
                    # Remove output blocks (from Read tool)
                    context_text = re.sub(
                        r'<output>.*?</output>',
                        '[OUTPUT_REMOVED]',
                        context_text,
                        flags=re.DOTALL
                    )
                    # Remove antml invoke blocks (tool parameters - contain code)
                    context_text = re.sub(
                        r'<invoke.*?</invoke>',
                        '[TOOL_PARAMS_REMOVED]',
                        context_text,
                        flags=re.DOTALL
                    )
                    # Remove function_calls blocks (tool call wrappers)
                    context_text = re.sub(
                        r'<function_calls>.*?</function_calls>',
                        '[FUNCTION_CALLS_REMOVED]',
                        context_text,
                        flags=re.DOTALL
                    )
        except Exception:
            pass

    # Check for reasoning violations
    violations = check_reasoning_rigor(context_text)

    if not violations:
        # No violations - allow
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
                    "permissionDecision": "deny",
                    "permissionDecisionReason": block_message,
                }
            }
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
