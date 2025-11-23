#!/usr/bin/env python3
"""
LOGICAL FALLACY DETECTOR HOOK
==============================
Detects invalid reasoning patterns in Claude's responses.

TRIGGER: PostToolUse (analyzing Claude's output)
PATTERN: Logical fallacies (post hoc, circular, false dichotomy, etc.)
ENFORCEMENT: Exit 0 with WARNING + telemetry logging

Philosophy: LLMs optimize for linguistic coherence, not logical validity.
            Pattern detection catches common fallacies before they propagate.
"""

import re
import sys
import json
from pathlib import Path
from datetime import datetime


def find_project_root():
    """Find project root by looking for scripts/lib/core.py"""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "scripts" / "lib" / "core.py").exists():
            return current
        current = current.parent
    return Path.cwd()


PROJECT_ROOT = find_project_root()
TELEMETRY_FILE = PROJECT_ROOT / ".claude" / "memory" / "fallacy_telemetry.jsonl"


# Fallacy detection patterns: (name, pattern, severity, description)
FALLACY_PATTERNS = [
    # Post Hoc Ergo Propter Hoc (correlation → causation)
    (
        "post_hoc",
        r"(?:since|after|when).*(?:then|therefore|thus|so|consequently).*(?:cause|must be|obviously)",
        "HIGH",
        "Post Hoc: Temporal correlation does not imply causation. Need mechanism.",
    ),
    # Circular Reasoning (simple pattern: "X because X")
    (
        "circular_reasoning",
        r"\b(\w+)\s+(?:because|since|due to).*\b\1\b",
        "CRITICAL",
        "Circular Reasoning: Conclusion appears in premise. Need independent evidence.",
    ),
    # False Dichotomy ("either X or Y" without justification)
    (
        "false_dichotomy",
        r"(?:either|only\s+(?:two|2)).*(?:or|alternative|choice)(?!.*(?:also|additionally|another))",
        "MEDIUM",
        "False Dichotomy: May be oversimplifying to two options. Are there alternatives?",
    ),
    # Hasty Generalization (universal claims: "all", "always", "never")
    (
        "hasty_generalization",
        r"(?:all|every|always|never|none|no).*(?:based on|from|in this|in these)(?:.*(?:file|example|case|instance))",
        "HIGH",
        "Hasty Generalization: Universal claim from limited sample. Need N≥3 examples.",
    ),
    # Appeal to Authority (without verification)
    (
        "appeal_to_authority",
        r"(?:documentation|docs|expert|official|authority).*(?:says|states|claims).*(?:therefore|so|thus)",
        "MEDIUM",
        "Appeal to Authority: Documentation claims need verification (/verify or /probe).",
    ),
    # Slippery Slope (A → B → C without justification)
    (
        "slippery_slope",
        r"(?:if|when).*(?:then|will|would).*(?:then|will|would).*(?:then|will|would)",
        "MEDIUM",
        "Slippery Slope: Chain of implications without justifying each step.",
    ),
    # Sunk Cost Fallacy ("already spent X, must continue")
    (
        "sunk_cost",
        r"(?:already|spent|invested).*(?:continue|finish|complete|persist)",
        "HIGH",
        "Sunk Cost Fallacy: Past investment should not drive future decisions.",
    ),
    # Confirmation Bias indicators
    (
        "confirmation_bias",
        r"(?:as expected|confirms|validates|proves).*(?:hypothesis|theory|assumption)",
        "MEDIUM",
        "Confirmation Bias: Are you cherry-picking evidence? Check contradictory data.",
    ),
    # False Certainty (claiming certainty without verification)
    (
        "false_certainty",
        r"(?:definitely|certainly|must be|obviously|clearly)(?!.*(?:verify|test|check))",
        "HIGH",
        "False Certainty: Absolute claims without verification. Need probabilistic language.",
    ),
    # Strawman (misrepresenting to make easier to attack)
    (
        "strawman",
        r"(?:you(?:'re| are) saying|so you mean|in other words).*(?:wrong|incorrect|flawed)",
        "HIGH",
        "Possible Strawman: Are you misrepresenting the original position?",
    ),
]


def detect_fallacies(text):
    """Check text for logical fallacy patterns"""
    text_lower = text.lower()
    detected = []

    for name, pattern, severity, description in FALLACY_PATTERNS:
        matches = list(re.finditer(pattern, text_lower, re.DOTALL | re.MULTILINE))
        if matches:
            for match in matches:
                # Extract context (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].replace("\n", " ")

                detected.append(
                    {
                        "fallacy": name,
                        "severity": severity,
                        "description": description,
                        "matched_text": match.group(0),
                        "context": context,
                        "position": match.start(),
                    }
                )

    return detected


def log_telemetry(fallacies, turn_number):
    """Log detected fallacies to telemetry file"""
    TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "turn": turn_number,
        "fallacy_count": len(fallacies),
        "fallacies": fallacies,
    }

    with open(TELEMETRY_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def get_turn_number():
    """Estimate turn number from session state"""
    try:
        session_file = PROJECT_ROOT / ".claude" / "memory" / "session_unknown_state.json"
        if session_file.exists():
            with open(session_file) as f:
                data = json.load(f)
                return data.get("turn_count", 0)
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass
    return 0


def build_warning_message(fallacies):
    """Build formatted warning message from detected fallacies"""
    warning_lines = ["\n⚠️ LOGICAL FALLACY DETECTION", "=" * 60, ""]

    # Group by severity
    critical = [f for f in fallacies if f["severity"] == "CRITICAL"]
    high = [f for f in fallacies if f["severity"] == "HIGH"]
    medium = [f for f in fallacies if f["severity"] == "MEDIUM"]

    if critical:
        warning_lines.append("🚨 CRITICAL:")
        for f in critical:
            warning_lines.append(f"  • {f['description']}")
            warning_lines.append(f"    Context: ...{f['context']}...")
        warning_lines.append("")

    if high:
        warning_lines.append("⚠️ HIGH:")
        for f in high:
            warning_lines.append(f"  • {f['description']}")
        warning_lines.append("")

    if medium:
        warning_lines.append("💡 MEDIUM:")
        for f in medium:
            warning_lines.append(f"  • {f['description']}")
        warning_lines.append("")

    warning_lines.extend(
        [
            "🧠 METACOGNITIVE QUESTIONS:",
            "  1. What evidence would DISPROVE this hypothesis?",
            "  2. What alternative explanations exist?",
            "  3. What assumptions am I making?",
            "  4. How confident am I really? (0-100%)",
            "",
            "💡 RECOMMENDED:",
            "  • Run /verify to check claims",
            "  • Consult oracle.py --persona skeptic for adversarial review",
            "  • Use probabilistic language (likely, possibly) not certainty",
            "",
            f"📊 Telemetry logged to: {TELEMETRY_FILE.relative_to(PROJECT_ROOT)}",
        ]
    )

    return "\n".join(warning_lines)


def main():
    # Read tool use data from stdin
    try:
        data = json.load(sys.stdin)
        tool_name = data.get("toolName", "")
        tool_output = data.get("toolOutput", "")

        # Only analyze tools that produce text output (not file operations)
        if tool_name not in ["Bash", "Read", "Grep", "WebFetch", "WebSearch"]:
            # Not a tool that produces reasoning output
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

    except (json.JSONDecodeError, KeyError, ValueError):
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

    # Detect fallacies
    fallacies = detect_fallacies(str(tool_output))

    if not fallacies:
        # No fallacies detected
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

    # Log to telemetry
    turn_number = get_turn_number()
    log_telemetry(fallacies, turn_number)

    # Build warning message
    warning = build_warning_message(fallacies)

    # Return warning (soft - does not block)
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": warning,
                }
            }
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
