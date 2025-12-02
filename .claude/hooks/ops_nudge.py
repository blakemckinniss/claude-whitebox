#!/usr/bin/env python3
"""
Ops Tool Nudge Hook: Suggest appropriate .claude/ops/ tools based on prompt patterns.

Hook Type: UserPromptSubmit
Latency Target: <20ms (pattern matching only)

Maps user intent patterns to the best ops tool for the job.
"""

import sys
import json
import re

# =============================================================================
# TOOL CATALOG - Pattern → Tool mapping
# =============================================================================

TOOL_TRIGGERS = {
    # =========================================================================
    # INVESTIGATION / RESEARCH
    # =========================================================================
    "research": {
        "patterns": [
            r"(latest|current|new)\s+(docs?|documentation|api|version)",
            r"how\s+does\s+.+\s+work\s+in\s+(2024|2025)",
            r"\b(fastapi|pydantic|langchain|anthropic|openai)\b.*\b(docs?|how)\b",
            r"what('s| is)\s+the\s+(syntax|api|way)\s+to",
        ],
        "command": "python3 .claude/ops/research.py \"<query>\"",
        "reason": "Live web search for current documentation",
    },
    "firecrawl": {
        "patterns": [
            r"scrape\s+.*(page|site|url|docs?|documentation|http|www)",
            r"(extract|get)\s+(content|text|data)\s+from\s+(http|www)",
            r"crawl\s+(the\s+)?(docs?|site|pages?)",
            r"(fetch|grab|pull)\s+(the\s+)?(html|content|page)\s+from",
        ],
        "command": "python3 .claude/ops/firecrawl.py scrape <URL>",
        "reason": "Deep web scraping with clean markdown output",
    },
    "probe": {
        "patterns": [
            r"what\s+(methods?|attributes?|properties)\s+(does|are)",
            r"(inspect|introspect|examine)\s+(the\s+)?(api|object|class)",
            r"(dir|help)\s*\(",
            r"what\s+can\s+I\s+(call|do)\s+(on|with)",
            r"\.(methods|attrs|attributes)\b",
        ],
        "command": "python3 .claude/ops/probe.py \"<object_path>\"",
        "reason": "Runtime introspection - see actual API before coding",
    },
    "xray": {
        "patterns": [
            r"(find|list|show)\s+(all\s+)?(class|function|import)s?\s+in",
            r"(where|what)\s+(is|are)\s+(the\s+)?(class|function|def)\s+",
            r"(structure|anatomy|layout)\s+of\s+(the\s+)?(code|file|module)",
            r"ast\s+(analysis|search|parse)",
        ],
        "command": "python3 .claude/ops/xray.py --type <class|function> --name <Name>",
        "reason": "AST-based structural code search",
    },
    "docs": {
        "patterns": [
            r"(generate|create|write)\s+(docs?|documentation)",
            r"docstring\s+(for|format)",
        ],
        "command": "python3 .claude/ops/docs.py <file>",
        "reason": "Generate documentation from code",
    },

    # =========================================================================
    # DECISION / REASONING
    # =========================================================================
    "oracle_judge": {
        "patterns": [
            r"should\s+(we|i|you)\s+",
            r"(worth|worthwhile)\s+(it|doing|the\s+effort)",
            r"(roi|value|benefit)\s+of",
            r"is\s+it\s+(overkill|over-?engineer)",
            r"(yagni|premature)\s+",
        ],
        "command": "python3 .claude/ops/oracle.py --persona judge \"<question>\"",
        "reason": "ROI/value assessment - prevents over-engineering",
    },
    "oracle_critic": {
        "patterns": [
            r"(review|critique|roast)\s+(this|my|the)",
            r"what('s| is)\s+wrong\s+with",
            r"(holes?|flaws?|weaknesses?)\s+in",
            r"devil'?s?\s+advocate",
            r"(attack|break)\s+(this|the)\s+(design|code|plan)",
        ],
        "command": "python3 .claude/ops/oracle.py --persona critic \"<proposal>\"",
        "reason": "Adversarial review - finds blind spots",
    },
    "oracle_skeptic": {
        "patterns": [
            r"(risk|failure|fail)\s+(mode|scenario|case)s?",
            r"what\s+(could|might|can)\s+go\s+wrong",
            r"(dangerous|risky)\s+to",
            r"(edge|corner)\s+cases?",
        ],
        "command": "python3 .claude/ops/oracle.py --persona skeptic \"<proposal>\"",
        "reason": "Risk analysis - identifies failure modes",
    },
    "think": {
        "patterns": [
            r"(complex|complicated|tricky)\s+(problem|issue|bug)",
            r"(break\s+down|decompose|analyze)\s+(this|the)",
            r"(step\s+by\s+step|systematically)",
            r"(debug|troubleshoot|diagnose)\s+(this|the|a)",
            r"i('m| am)\s+(stuck|confused|lost)",
        ],
        "command": "python3 .claude/ops/think.py \"<problem>\"",
        "reason": "Structured problem decomposition",
    },
    "council": {
        "patterns": [
            r"(major|big|significant)\s+(decision|choice|change)",
            r"(architecture|design)\s+(decision|review)",
            r"(multiple|different)\s+(perspectives?|viewpoints?|opinions?)",
            r"(pros\s+and\s+cons|trade-?offs?)",
        ],
        "command": "python3 .claude/ops/council.py \"<proposal>\"",
        "reason": "Multi-perspective analysis (Judge+Critic+Skeptic)",
    },

    # =========================================================================
    # QUALITY / VERIFICATION
    # =========================================================================
    "audit": {
        "patterns": [
            r"(security|vulnerability|injection)\s+(check|scan|audit)",
            r"(code\s+)?(quality|smell|issue)s?\s+(check|review)",
            r"(safe|secure)\s+to\s+(deploy|ship|commit)",
        ],
        "command": "python3 .claude/ops/audit.py <file>",
        "reason": "Security and code quality audit",
    },
    "void": {
        "patterns": [
            r"(stub|todo|fixme|xxx|incomplete)",
            r"(missing|forgot)\s+(implementation|handler|case)",
            r"(complete|finish|done)\s*\?",
            r"anything\s+(missing|left|incomplete)",
        ],
        "command": "python3 .claude/ops/void.py <file>",
        "reason": "Completeness check - finds stubs and gaps",
    },
    "verify": {
        "patterns": [
            r"(verify|check|confirm)\s+(that|if|whether)",
            r"(does|is)\s+(the\s+)?(file|port|service)\s+(exist|open|running)",
            r"(assertion|sanity)\s+check",
        ],
        "command": "python3 .claude/ops/verify.py <check_type> <target>",
        "reason": "Reality verification (file_exists, grep_text, port_open)",
    },
    "drift_check": {
        "patterns": [
            r"(style|convention|consistency)\s+(check|drift|violation)",
            r"(code\s+)?style\s+(guide|standard)",
            r"(lint|format)\s+(check|issues?)",
        ],
        "command": "python3 .claude/ops/drift_check.py",
        "reason": "Style consistency and drift detection",
    },

    # =========================================================================
    # MEMORY / CONTEXT
    # =========================================================================
    "remember": {
        "patterns": [
            r"(remember|save|store)\s+(this|that|the)\s+(lesson|decision|learning)",
            r"(learned|discovered)\s+(that|something)",
            r"(note|record)\s+(for|to)\s+(future|later|myself)",
            r"don'?t\s+forget",
        ],
        "command": "python3 .claude/ops/remember.py add lessons \"<text>\"",
        "reason": "Persist lessons/decisions across sessions",
    },
    "spark": {
        "patterns": [
            r"(recall|retrieve|what\s+did\s+we)\s+(learn|decide|know)",
            r"(previous|past|earlier)\s+(session|conversation|decision)",
            r"(remind|refresh)\s+(me|my\s+memory)",
            r"(related|similar)\s+(to|issue|problem)\s+before",
        ],
        "command": "python3 .claude/ops/spark.py \"<topic>\"",
        "reason": "Retrieve associative memories",
    },
    "scope": {
        "patterns": [
            r"(define|set|track)\s+(the\s+)?(scope|dod|done)",
            r"(task|feature)\s+(complete|done|finished)\s*\?",
            r"(checkpoint|rollback|save\s+point)",
        ],
        "command": "python3 .claude/ops/scope.py init \"<task>\"",
        "reason": "Definition of Done tracking with checkpoints",
    },
    "evidence": {
        "patterns": [
            r"(evidence|proof|verification)\s+(log|trail|history)",
            r"(show|list)\s+(what\s+)?(verified|checked|confirmed)",
        ],
        "command": "python3 .claude/ops/evidence.py review",
        "reason": "Evidence ledger - review gathered proof",
    },

    # =========================================================================
    # EXECUTION / ORCHESTRATION
    # =========================================================================
    "orchestrate": {
        "patterns": [
            r"(process|analyze|scan)\s+(all|many|multiple|every)\s+files?",
            r"(batch|bulk|aggregate)\s+(process|operation|task)",
            r"(summarize|consolidate|combine)\s+(the\s+)?(results?|outputs?|findings?)",
            r"(count|list|extract)\s+.+\s+(from|across)\s+(all|many|multiple)",
            r"(reduce|minimize)\s+(context|tokens?|output)",
            r"return\s+(only|just)\s+(the\s+)?(summary|important|critical)",
            r"(3|three|several)\+?\s+(dependent\s+)?(operations?|steps?|tasks?)",
        ],
        "command": "python3 .claude/ops/orchestrate.py \"<task description>\"",
        "reason": "Claude API code_execution - 37% token reduction for batch/aggregate tasks",
    },
    "swarm": {
        "patterns": [
            r"(parallel|concurrent|batch)\s+(generation|tasks?|agents?)",
            r"(multiple|many)\s+(files?|outputs?)\s+at\s+once",
            r"(fan-?out|distribute)\s+(the\s+)?(work|task)",
        ],
        "command": "python3 .claude/ops/swarm.py --mode <mode> \"<task>\"",
        "reason": "Parallel agent dispatch for bulk operations",
    },
    "playwright": {
        "patterns": [
            r"(browser|headless|selenium|puppeteer)",
            r"(automate|scrape|test)\s+(the\s+)?(web|page|site|ui)",
            r"(click|fill|submit)\s+(the\s+)?(form|button|input)",
            r"(screenshot|capture)\s+(the\s+)?(page|screen)",
        ],
        "command": "python3 .claude/ops/playwright.py <action>",
        "reason": "Browser automation for web interaction",
    },
    "groq": {
        "patterns": [
            r"(fast|quick|instant)\s+(llm|model|inference)",
            r"groq\s+(api|model)",
        ],
        "command": "python3 .claude/ops/groq.py \"<prompt>\"",
        "reason": "Fast LLM inference via Groq",
    },

    # =========================================================================
    # META / UPKEEP
    # =========================================================================
    "upkeep": {
        "patterns": [
            r"(pre-?commit|before\s+commit)",
            r"(clean|tidy|maintenance)\s+(up|check)",
            r"(ready\s+to\s+)?(commit|push)",
        ],
        "command": "python3 .claude/ops/upkeep.py",
        "reason": "Pre-commit checks and project maintenance",
    },
    "confidence": {
        "patterns": [
            r"(confidence|certainty)\s+(level|score|status)",
            r"(epistemolog|tier)\s+(check|status)",
            r"how\s+(confident|certain|sure)",
        ],
        "command": "python3 .claude/ops/confidence.py status",
        "reason": "Epistemological confidence tracking",
    },
    "inventory": {
        "patterns": [
            r"(available|installed)\s+(tools?|binaries|commands?)",
            r"what('s| is)\s+(installed|available)\s+on\s+(this|the)\s+(system|machine)",
            r"(system|tool)\s+inventory",
        ],
        "command": "python3 .claude/ops/inventory.py",
        "reason": "Scan available system tools and binaries",
    },
}


def find_matching_tools(prompt: str) -> list[tuple[str, dict]]:
    """Find all tools that match the prompt patterns."""
    prompt_lower = prompt.lower()
    matches = []

    for tool_name, config in TOOL_TRIGGERS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, prompt_lower):
                matches.append((tool_name, config))
                break  # One match per tool is enough

    return matches[:3]  # Max 3 suggestions


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

    matches = find_matching_tools(user_prompt)

    if not matches:
        print(json.dumps({}))
        sys.exit(0)

    suggestions = []
    for tool_name, config in matches:
        # Clean tool name for display
        display_name = tool_name.replace("_", " ").replace("oracle ", "oracle --persona ")
        suggestions.append(
            f"🛠️ {display_name.upper()}: {config['reason']}\n"
            f"   → {config['command']}"
        )

    output = {
        "additionalContext": "OPS TOOLS AVAILABLE:\n" + "\n\n".join(suggestions)
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
