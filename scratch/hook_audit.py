#!/usr/bin/env python3
"""
Hook Audit Script: Categorize hooks for prompt-based conversion
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# Hook categorization criteria
HOOK_ANALYSIS = {
    # KEEP AS COMMAND-BASED (Critical/Stateful)
    "confidence_init.py": {
        "category": "CRITICAL_STATE",
        "reason": "Initializes session state, modifies confidence.json",
        "convertible": False,
    },
    "command_tracker.py": {
        "category": "CRITICAL_STATE",
        "reason": "Tracks command execution for prerequisite enforcement",
        "convertible": False,
    },
    "evidence_tracker.py": {
        "category": "CRITICAL_STATE",
        "reason": "Records evidence gathering for confidence calculation",
        "convertible": False,
    },
    "detect_confidence_penalty.py": {
        "category": "CRITICAL_STATE",
        "reason": "Applies penalties to confidence state",
        "convertible": False,
    },
    "detect_confidence_reward.py": {
        "category": "CRITICAL_STATE",
        "reason": "Applies rewards to confidence state",
        "convertible": False,
    },
    "pre_advice.py": {
        "category": "CRITICAL_GATE",
        "reason": "Hard block for strategic advice without evidence",
        "convertible": False,
    },
    "tier_gate.py": {
        "category": "CRITICAL_GATE",
        "reason": "Hard block for tier violations",
        "convertible": False,
    },
    "confidence_gate.py": {
        "category": "CRITICAL_GATE",
        "reason": "Hard block for confidence violations",
        "convertible": False,
    },
    "command_prerequisite_gate.py": {
        "category": "CRITICAL_GATE",
        "reason": "Hard block for prerequisite violations",
        "convertible": False,
    },
    "risk_gate.py": {
        "category": "CRITICAL_GATE",
        "reason": "Hard block for risky operations",
        "convertible": False,
    },
    "pre_write_audit.py": {
        "category": "CRITICAL_GATE",
        "reason": "Security/stub detection with deterministic rules",
        "convertible": False,
    },
    "ban_stubs.py": {
        "category": "CRITICAL_GATE",
        "reason": "Prevents stub code with regex patterns",
        "convertible": False,
    },
    "block_mcp.py": {
        "category": "CRITICAL_GATE",
        "reason": "Whitebox enforcement (no MCP tools)",
        "convertible": False,
    },
    
    # COMPLEX LOGIC (Keep as scripts)
    "synapse_fire.py": {
        "category": "COMPLEX_LOGIC",
        "reason": "Pattern matching + file search + random constraints",
        "convertible": False,
    },
    "session_init.py": {
        "category": "COMPLEX_LOGIC",
        "reason": "Session initialization with file operations",
        "convertible": False,
    },
    "auto_commit_on_complete.py": {
        "category": "COMPLEX_LOGIC",
        "reason": "Git operations with state tracking",
        "convertible": False,
    },
    "auto_commit_on_end.py": {
        "category": "COMPLEX_LOGIC",
        "reason": "Git operations on session end",
        "convertible": False,
    },
    "auto_remember.py": {
        "category": "COMPLEX_LOGIC",
        "reason": "Memory extraction with file writes",
        "convertible": False,
    },
    "session_digest.py": {
        "category": "COMPLEX_LOGIC",
        "reason": "Digest generation with file operations",
        "convertible": False,
    },
    "token_tracker.py": {
        "category": "COMPLEX_LOGIC",
        "reason": "Token estimation with transcript parsing",
        "convertible": False,
    },
    "debt_tracker.py": {
        "category": "COMPLEX_LOGIC",
        "reason": "Technical debt tracking with file operations",
        "convertible": False,
    },
    "pattern_detector.py": {
        "category": "COMPLEX_LOGIC",
        "reason": "Multi-pattern detection with state updates",
        "convertible": False,
    },
    
    # ADVISORY (Convertible to prompt-based)
    "detect_batch.py": {
        "category": "ADVISORY_SIMPLE",
        "reason": "Simple keyword matching → LLM can understand batch intent",
        "convertible": True,
        "prompt_template": """Analyze if this describes a batch operation: $ARGUMENTS

Check for:
- Keywords: batch, bulk, mass, "all files", iterate, loop
- Patterns: "process files", "download all", "convert all"

If batch operation detected:
{
  "decision": "approve",
  "systemMessage": "⚠️ BATCH OPERATION DETECTED\\nUse scripts.lib.parallel for multi-threading\\nExample: run_parallel(func, items, max_workers=10)"
}

Otherwise: {"decision": "approve"}""",
    },
    "check_knowledge.py": {
        "category": "ADVISORY_SIMPLE",
        "reason": "Fast-moving tech detection → LLM can assess freshness needs",
        "convertible": True,
        "prompt_template": """Evaluate if this requires current documentation: $ARGUMENTS

Check for:
- Topics about new libraries, APIs, frameworks
- Error debugging that needs current solutions
- "Latest", "current", "how to" patterns

If research needed:
{
  "decision": "approve",
  "systemMessage": "⚠️ KNOWLEDGE CHECK: Run /research first\\nTraining data is from Jan 2025 - APIs may have changed"
}""",
    },
    "sanity_check.py": {
        "category": "ADVISORY_SIMPLE",
        "reason": "Library + code intent detection → LLM understands this naturally",
        "convertible": True,
        "prompt_template": """Check if user wants to write code for complex libraries: $ARGUMENTS

If coding with pandas/boto3/fastapi/etc without probing:
{
  "decision": "approve",
  "systemMessage": "⚠️ SANITY CHECK: Run /probe and /research before coding\\nDo not guess API signatures"
}""",
    },
    "force_playwright.py": {
        "category": "ADVISORY_SIMPLE",
        "reason": "UI automation detection → LLM can recognize browser needs",
        "convertible": True,
        "prompt_template": """Check if this requires browser automation: $ARGUMENTS

UI triggers: click, login, screenshot, dynamic content, JavaScript
Lazy triggers: requests, BeautifulSoup

If UI task + lazy approach:
{
  "decision": "approve",
  "systemMessage": "⚠️ Use Playwright for browser automation\\nrequests/BS4 fails on dynamic sites"
}""",
    },
    "intervention.py": {
        "category": "ADVISORY_SIMPLE",
        "reason": "Bikeshedding detection → LLM can assess value/ROI",
        "convertible": True,
        "prompt_template": """Detect bikeshedding/YAGNI/NIH syndrome: $ARGUMENTS

Bikeshedding: prettier config, linting, color schemes
NIH: "build our own", "custom framework"
YAGNI: "might need", "future proof"

If detected:
{
  "decision": "approve",
  "systemMessage": "⚖️ JUDGE WARNING: Run /judge before proceeding\\nDoes this ship to production TODAY?"
}""",
    },
    
    # ADVISORY COMPLEX (Maybe convertible, but loses structure)
    "anti_sycophant.py": {
        "category": "ADVISORY_COMPLEX",
        "reason": "Opinion request detection + assumption extraction",
        "convertible": True,  # Could work but loses structured checks
    },
    "detect_gaslight.py": {
        "category": "ADVISORY_COMPLEX",
        "reason": "Frustration detection + sherlock invocation",
        "convertible": True,
    },
    "detect_low_confidence.py": {
        "category": "ADVISORY_COMPLEX",
        "reason": "Confidence threshold checks",
        "convertible": False,  # Needs precise state access
    },
    "enforce_workflow.py": {
        "category": "ADVISORY_COMPLEX",
        "reason": "Workflow enforcement reminders",
        "convertible": True,
    },
    "prerequisite_checker.py": {
        "category": "ADVISORY_COMPLEX",
        "reason": "Multi-condition prerequisite checks",
        "convertible": False,  # Complex state dependencies
    },
    "best_practice_enforcer.py": {
        "category": "ADVISORY_COMPLEX",
        "reason": "Best practice reminders",
        "convertible": True,
    },
    "ecosystem_mapper.py": {
        "category": "ADVISORY_COMPLEX",
        "reason": "Ecosystem thinking reminders",
        "convertible": True,
    },
    "intent_classifier.py": {
        "category": "ADVISORY_COMPLEX",
        "reason": "Intent classification for routing",
        "convertible": True,
    },
    "command_suggester.py": {
        "category": "ADVISORY_COMPLEX",
        "reason": "Suggests next commands based on context",
        "convertible": True,
    },
    "post_tool_command_suggester.py": {
        "category": "ADVISORY_COMPLEX",
        "reason": "Post-tool command suggestions",
        "convertible": True,
    },
    
    # DEPRECATED / UNUSED
    "trigger_skeptic.py": {
        "category": "DEPRECATED",
        "reason": "PreToolUse skeptic trigger (likely unused now)",
        "convertible": False,
    },
    "absurdity_detector.py": {
        "category": "DEPRECATED",
        "reason": "Possibly experimental",
        "convertible": False,
    },
    "pre_delegation.py": {
        "category": "GATE",
        "reason": "Agent delegation checks",
        "convertible": False,
    },
}

def main():
    print("🔍 HOOK AUDIT REPORT\n")
    print("=" * 80)
    
    # Group by category
    categories = {}
    for hook, info in HOOK_ANALYSIS.items():
        cat = info["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((hook, info))
    
    # Print by category
    for category in sorted(categories.keys()):
        hooks = categories[category]
        print(f"\n## {category} ({len(hooks)} hooks)")
        print("-" * 80)
        
        for hook_name, info in sorted(hooks):
            convertible = "✅ CONVERTIBLE" if info["convertible"] else "❌ KEEP AS SCRIPT"
            print(f"\n{hook_name}")
            print(f"  {convertible}")
            print(f"  Reason: {info['reason']}")
            if info.get("prompt_template"):
                print(f"  Has prompt template: Yes")
    
    # Summary stats
    total = len(HOOK_ANALYSIS)
    convertible = sum(1 for h in HOOK_ANALYSIS.values() if h["convertible"])
    
    print("\n" + "=" * 80)
    print(f"\n📊 SUMMARY")
    print(f"  Total hooks analyzed: {total}")
    print(f"  Convertible to prompt-based: {convertible}")
    print(f"  Must remain command-based: {total - convertible}")
    print(f"  Conversion ratio: {convertible/total*100:.1f}%")
    
    # Save categorization to JSON
    output_file = PROJECT_ROOT / "scratch" / "hook_categorization.json"
    with open(output_file, "w") as f:
        json.dump(HOOK_ANALYSIS, f, indent=2)
    
    print(f"\n💾 Detailed categorization saved to: {output_file}")

if __name__ == "__main__":
    main()
