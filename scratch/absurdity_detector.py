#!/usr/bin/env python3
"""
ABSURDITY DETECTOR HOOK
=======================
Flags obviously contradictory or nonsensical requests.

TRIGGER: UserPromptSubmit
PATTERN: Technology mismatches, anti-patterns, contradictions
ENFORCEMENT: Exit 0 with WARNING (let user decide, but flag it)

Examples:
- "Install Rust in JavaScript web project"
- "Add microservices for a todo app with 10 users"
- "Use blockchain for user authentication"
- "Optimize for speed and add heavy ORM with 50 relations"

Philosophy: LLMs are sycophantic and will justify anything. Absurdity detector
            provides pushback without hard blocking (user may have good reason).
"""

import re
import sys
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


# Absurdity patterns: (pattern, warning message)
ABSURDITIES = [
    # Technology mismatches
    (
        r'\b(?:install|add|use)\s+(?:rust|go|java|php|ruby)\b.*?\b(?:javascript|js|node\.?js)\b',
        "⚠️  TECHNOLOGY MISMATCH: Adding {tech1} to JavaScript project (are you sure?)"
    ),
    (
        r'\b(?:install|add|use)\s+(?:javascript|js|typescript)\b.*?\b(?:python|django|flask)\b',
        "⚠️  TECHNOLOGY MISMATCH: Adding JavaScript runtime to Python project (are you sure?)"
    ),
    (
        r'\b(?:install|add|use)\s+(?:python|pip)\b.*?\b(?:ruby|rails|gem)\b',
        "⚠️  TECHNOLOGY MISMATCH: Mixing Python and Ruby toolchains (are you sure?)"
    ),

    # Over-engineering patterns
    (
        r'\bmicroservices?\b.*?\b(?:todo|simple|small|prototype)\b',
        "⚠️  OVER-ENGINEERING: Microservices for simple app (YAGNI violation)"
    ),
    (
        r'\bkubernetes\b.*?\b(?:10|dozen|few)\s+users?\b',
        "⚠️  OVER-ENGINEERING: Kubernetes for tiny user base (premature optimization)"
    ),
    (
        r'\bblockchain\b.*?\b(?:auth|login|user|todo|simple)\b',
        "⚠️  ABSURD TECH CHOICE: Blockchain for {use_case} (massive overkill)"
    ),
    (
        r'\bgraphql\b.*?\b(?:crud|simple|basic)\b',
        "⚠️  POSSIBLE OVER-ENGINEERING: GraphQL for basic CRUD (REST might suffice)"
    ),

    # Contradictory goals
    (
        r'\boptimize\b.*?(?:speed|performance).*?\b(?:orm|heavy|large framework)\b',
        "⚠️  CONTRADICTORY GOALS: Optimize for speed + add heavy abstractions"
    ),
    (
        r'\bsimple\b.*?\b(?:add|use).*?\b(?:kafka|rabbitmq|redis cluster)\b',
        "⚠️  CONTRADICTORY GOALS: Keep it simple + add distributed systems"
    ),
    (
        r'\bminimal\b.*?\b(?:add|install).*?\b(?:dependencies|packages|libraries)\b.*?\b(?:10|20|30|many)\b',
        "⚠️  CONTRADICTORY GOALS: Minimal dependencies + installing many packages"
    ),

    # Anti-patterns
    (
        r'\b(?:no|skip|avoid)\s+(?:tests?|testing)\b',
        "⚠️  ANTI-PATTERN DETECTED: Skipping tests (tech debt accumulation)"
    ),
    (
        r'\bproduction\b.*?\b(?:no|without|skip).*?\b(?:backup|monitoring|logging)\b',
        "⚠️  DANGER: Production deployment without {missing} (recipe for disaster)"
    ),
    (
        r'\bstore\b.*?\b(?:password|secret|key)\b.*?\b(?:plain|clear|unencrypted)\b',
        "🚨 SECURITY VIOLATION: Storing credentials in plaintext (NEVER do this)"
    ),
]


def detect_absurdity(prompt):
    """Check if prompt contains absurd requests"""
    prompt_lower = prompt.lower()
    warnings = []

    for pattern, warning_template in ABSURDITIES:
        match = re.search(pattern, prompt_lower, re.DOTALL)
        if match:
            # Try to extract relevant terms for template
            warning = warning_template
            if '{tech1}' in warning or '{use_case}' in warning or '{missing}' in warning:
                # Simple extraction - just use first captured group or matched text
                warning = warning.replace('{tech1}', 'foreign technology')
                warning = warning.replace('{use_case}', 'this use case')
                warning = warning.replace('{missing}', 'critical feature')
            warnings.append(warning)

    return warnings


def main():
    # Read user prompt from stdin
    try:
        user_input = sys.stdin.read().strip()
    except:
        sys.exit(0)  # Can't read input, allow

    if not user_input:
        sys.exit(0)  # Empty input, allow

    # Detect absurdities
    warnings = detect_absurdity(user_input)

    if warnings:
        print("""
🥊 ABSURDITY DETECTOR TRIGGERED
================================
Your request contains patterns that often indicate:
  • Technology mismatches (wrong tool for the job)
  • Over-engineering (premature optimization)
  • Contradictory goals (fast + heavy)
  • Anti-patterns (no tests, plaintext secrets)

""", file=sys.stderr)

        for i, warning in enumerate(warnings, 1):
            print(f"{i}. {warning}", file=sys.stderr)

        print("""
🤔 QUESTIONS TO ASK YOURSELF:
  • Do I actually need this?
  • Is there a simpler solution?
  • Am I solving a problem I don't have yet?
  • Would this pass code review?

💡 RECOMMENDED: Consult The Judge or Critic before proceeding
   python3 scripts/ops/judge.py "<your proposal>"
   python3 scripts/ops/critic.py "<your proposal>"

This is a WARNING, not a block. Proceed if you have good reason.
""", file=sys.stderr)

    # Always exit 0 (allow) - this is advisory, not blocking
    sys.exit(0)


if __name__ == "__main__":
    main()
