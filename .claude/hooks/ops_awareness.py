#!/usr/bin/env python3
"""
Ops Awareness Hook v3: Remind Claude to use existing ops scripts.

Hook Type: UserPromptSubmit
Latency Target: <20ms (no API calls, pure pattern matching)

Problem: Claude often reinvents the wheel instead of using scripts/ops/*.py
Solution: Pattern match user prompts against ops script capabilities
"""

import sys
import json
import re

# =============================================================================
# OPS SCRIPT CATALOG - What each script does
# =============================================================================

OPS_SCRIPTS = {
    # Research & Documentation
    "research": {
        "triggers": ["look up", "find docs", "documentation", "how does.*work",
                     "what is.*api", "latest version", "library.*usage"],
        "description": "Web search via Tavily API for docs/libraries"
    },
    "probe": {
        "triggers": ["inspect.*object", "what methods", "api.*signature",
                     "runtime.*introspect", "pandas.*api", "boto3.*api"],
        "description": "Runtime introspection - inspect objects before coding"
    },

    # Code Analysis
    "xray": {
        "triggers": ["find.*class", "find.*function", "where is.*defined",
                     "ast.*search", "code structure", "list.*functions"],
        "description": "AST-based structural code search"
    },
    "audit": {
        "triggers": ["security.*check", "code.*review", "check.*injection",
                     "vulnerability", "secrets.*code"],
        "description": "Security audit (OWASP, secrets, injection)"
    },
    "void": {
        "triggers": ["find.*stubs", "todo.*code", "incomplete.*implementation",
                     "notimplemented", "missing.*crud"],
        "description": "Find stubs, TODOs, incomplete code"
    },

    # Reasoning & Decision
    "think": {
        "triggers": ["break.*down", "decompose", "step.*by.*step",
                     "complex.*problem", "analyze.*approach"],
        "description": "Problem decomposition into sequential steps"
    },
    "oracle": {
        "triggers": ["should i", "which.*approach", "trade.*off",
                     "architecture.*decision", "library.*choice", "roi"],
        "description": "External reasoning via OpenRouter (judge/critic/skeptic)"
    },
    "council": {
        "triggers": ["major.*decision", "architectural", "multi.*perspective",
                     "pros.*cons", "comprehensive.*analysis"],
        "description": "6-perspective parallel analysis"
    },

    # Verification
    "verify": {
        "triggers": ["check.*exists", "verify.*file", "test.*command",
                     "confirm.*works", "port.*open"],
        "description": "Reality checks (file_exists, grep_text, command_success)"
    },

    # Memory & Context
    "remember": {
        "triggers": ["save.*lesson", "remember.*this", "store.*decision",
                     "add.*context", "lessons.*learned"],
        "description": "Persistent memory (lessons, decisions, context)"
    },
    "spark": {
        "triggers": ["recall.*about", "what.*learned", "previous.*experience",
                     "memory.*of", "associative"],
        "description": "Retrieve associative memories for a topic"
    },

    # Project Management
    "scope": {
        "triggers": ["definition.*done", "track.*progress", "acceptance.*criteria",
                     "dod", "scope.*check"],
        "description": "Manage Definition of Done (init, check, status)"
    },
    "upkeep": {
        "triggers": ["pre.*commit", "sync.*requirements", "project.*health",
                     "maintenance"],
        "description": "Project maintenance before commits"
    },

    # External Tools
    "swarm": {
        "triggers": ["parallel.*generation", "multiple.*variants", "bulk.*create",
                     "mass.*generate"],
        "description": "Parallel generation via external agents"
    }
}

# =============================================================================
# DETECTION LOGIC
# =============================================================================

def find_relevant_scripts(user_prompt: str) -> list:
    """Find ops scripts relevant to the user's prompt."""
    prompt_lower = user_prompt.lower()
    matches = []

    for script, config in OPS_SCRIPTS.items():
        for trigger in config["triggers"]:
            if re.search(trigger, prompt_lower):
                matches.append({
                    "script": script,
                    "command": f"python3 scripts/ops/{script}.py",
                    "description": config["description"]
                })
                break  # One match per script is enough

    return matches[:3]  # Top 3 most relevant

def main():
    """UserPromptSubmit hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({}))
        sys.exit(0)

    user_prompt = input_data.get("user_prompt", "")
    if not user_prompt or len(user_prompt) < 10:
        print(json.dumps({}))
        sys.exit(0)

    matches = find_relevant_scripts(user_prompt)

    if matches:
        suggestions = "\n".join([
            f"   - `{m['script']}`: {m['description']}"
            for m in matches
        ])
        context = f"🔧 OPS SCRIPTS AVAILABLE:\n{suggestions}"

        output = {
            "additionalContext": context
        }
    else:
        output = {}

    print(json.dumps(output))
    sys.exit(0)

if __name__ == "__main__":
    main()
