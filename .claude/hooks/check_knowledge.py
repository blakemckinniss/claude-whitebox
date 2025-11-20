#!/usr/bin/env python3
"""
Knowledge Check Hook
Detects when user requests involve topics that require fresh, up-to-date information.
Triggers reminder to use The Researcher for current documentation.
"""
import sys
import json

try:
    data = json.load(sys.stdin)
except:
    sys.exit(0)

# Get user prompt
prompt = data.get("prompt", "").lower()

# Triggers indicating need for current information
freshness_triggers = [
    "latest", "current", "newest", "recent", "updated",
    "version", "docs", "documentation", "how do i", "how to",
    "error", "exception", "traceback", "fix", "debug",
    "best practice", "recommended way", "tutorial"
]

# Fast-moving libraries/technologies that frequently change
fast_moving_tech = [
    "next", "nextjs", "react", "vue", "angular", "svelte",
    "tailwind", "typescript", "node", "deno", "bun",
    "python", "rust", "go", "aws", "azure", "gcp",
    "kubernetes", "docker", "openai", "langchain",
    "pytorch", "tensorflow", "scikit"
]

# Check if prompt mentions fast-moving tech
tech_mentioned = any(tech in prompt for tech in fast_moving_tech)

# Check if prompt has freshness indicators
freshness_needed = any(trigger in prompt for trigger in freshness_triggers)

# Trigger if either condition is met
research_triggered = tech_mentioned or freshness_needed

if research_triggered:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                "⚠️ KNOWLEDGE CHECK: This topic may require current information.\n"
                "RESEARCH PROTOCOL: Consider running The Researcher before coding:\n"
                "  python3 scripts/ops/research.py \"<your search query>\"\n"
                "Your training data is from January 2025. Libraries/APIs may have changed."
            )
        }
    }))

sys.exit(0)
