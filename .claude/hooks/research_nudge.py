#!/usr/bin/env python3
"""
Research Nudge Hook v3: Suggest web search for topics needing current info.

Hook Type: UserPromptSubmit
Latency Target: <15ms (pattern matching only)

Problem: Claude doesn't use WebSearch for current documentation/libraries
Solution: Detect topics that benefit from live search, suggest it proactively
"""

import sys
import json
import re

# =============================================================================
# TOPICS THAT NEED CURRENT INFO
# =============================================================================

# Libraries/frameworks that change frequently (suggest docs lookup)
FAST_MOVING_TECH = [
    # Python
    r"\b(fastapi|pydantic|langchain|llamaindex|anthropic|openai)\b",
    r"\b(polars|duckdb|streamlit|gradio)\b",
    # JavaScript/Node
    r"\b(next\.?js|nuxt|remix|astro|svelte|solid)\b",
    r"\b(bun|deno|vite|turbopack)\b",
    # AI/ML
    r"\b(transformers|diffusers|torch|tensorflow)\b",
    r"\b(ollama|groq|together|replicate)\b",
    # Cloud
    r"\b(gcloud|aws|azure|vercel|cloudflare)\b",
    # Rust
    r"\b(tokio|axum|actix|leptos|tauri)\b",
]

# Patterns suggesting user wants current info
CURRENT_INFO_PATTERNS = [
    r"latest\s+(version|docs|api|syntax)",
    r"new\s+(feature|api|release)",
    r"(2024|2025)\s+",  # Year references
    r"how\s+to\s+.*(setup|install|configure|deploy)",
    r"what.*changed\s+in",
    r"breaking\s+changes?",
    r"migration\s+(guide|path)",
    r"best\s+practice.*\d{4}",  # Best practices with year
    r"current\s+(state|status|recommendation)",
]

# Topics Claude's training might be outdated on
KNOWLEDGE_CUTOFF_TOPICS = [
    r"\b(claude\s*3|gpt-?4|gemini|llama\s*3)\b",
    r"\b(cursor|windsurf|continue\.dev)\b",
    r"mcp\s+(server|tool|protocol)",
    r"(anthropic|openai)\s+api",
]

# Patterns suggesting need for external reasoning (oracle.py)
DECISION_PATTERNS = [
    r"should\s+(we|i|you)\s+",
    r"(pros|cons|trade-?offs?|tradeoffs?)\b",
    r"(better|worse|prefer)\s+(to|approach|option)",
    r"(compare|comparison|versus|vs\.?)\s+",
    r"(architecture|design)\s+(decision|choice)",
    r"(worth|worthwhile)\s+(it|doing|the)",
    r"which\s+(approach|method|way|option)",
    r"(risky|risk|dangerous)\s+to",
    r"(migrate|migration|rewrite|refactor)\s+(to|from|the)",
]

# Patterns for hostile review (oracle --persona critic/skeptic)
REVIEW_PATTERNS = [
    r"(review|critique|analyze)\s+(this|my|the)",
    r"what.*wrong\s+with",
    r"(holes?|flaws?|weaknesses?)\s+in",
    r"(attack|stress.?test|break)\s+(this|the)",
    r"devil'?s?\s+advocate",
]

# =============================================================================
# DETECTION LOGIC
# =============================================================================

def needs_web_search(prompt: str) -> tuple[bool, str]:
    """Check if prompt would benefit from web search."""
    prompt_lower = prompt.lower()

    # Check fast-moving tech
    for pattern in FAST_MOVING_TECH:
        if re.search(pattern, prompt_lower):
            match = re.search(pattern, prompt_lower)
            tech = match.group(0) if match else "this technology"
            return True, f"`{tech}` changes frequently - docs may be outdated"

    # Check current info patterns
    for pattern in CURRENT_INFO_PATTERNS:
        if re.search(pattern, prompt_lower):
            return True, "This topic likely needs current information"

    # Check knowledge cutoff topics
    for pattern in KNOWLEDGE_CUTOFF_TOPICS:
        if re.search(pattern, prompt_lower):
            match = re.search(pattern, prompt_lower)
            topic = match.group(0) if match else "this topic"
            return True, f"`{topic}` is post-training-cutoff - search recommended"

    return False, ""


def needs_oracle(prompt: str) -> tuple[bool, str, str]:
    """Check if prompt would benefit from oracle consultation.
    Returns: (needs_oracle, reason, suggested_persona)
    """
    prompt_lower = prompt.lower()

    # Check decision patterns → judge persona
    for pattern in DECISION_PATTERNS:
        if re.search(pattern, prompt_lower):
            return True, "Decision/tradeoff detected - external reasoning recommended", "judge"

    # Check review patterns → critic/skeptic persona
    for pattern in REVIEW_PATTERNS:
        if re.search(pattern, prompt_lower):
            return True, "Review/critique requested - adversarial analysis recommended", "critic"

    return False, "", ""


def main():
    """UserPromptSubmit hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({}))
        sys.exit(0)

    user_prompt = input_data.get("user_prompt", "")
    if not user_prompt or len(user_prompt) < 5:
        print(json.dumps({}))
        sys.exit(0)

    suggestions = []

    # Check for web search need
    needs_search, search_reason = needs_web_search(user_prompt)
    if needs_search:
        suggestions.append(
            f"🌐 WEB SEARCH: {search_reason}\n"
            f"   Run: python3 .claude/ops/research.py \"<query>\""
        )

    # Check for oracle need
    needs_ext, oracle_reason, persona = needs_oracle(user_prompt)
    if needs_ext:
        suggestions.append(
            f"🔮 ORACLE CONSULTATION: {oracle_reason}\n"
            f"   Run: python3 .claude/ops/oracle.py --persona {persona} \"<question>\""
        )

    if suggestions:
        output = {"additionalContext": "\n\n".join(suggestions)}
    else:
        output = {}

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
