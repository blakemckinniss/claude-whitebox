#!/usr/bin/env python3
"""
Hook Conversion Script: Generate prompt-based hook configuration

This script generates a new .claude/settings.json segment with prompt-based hooks
replacing the convertible advisory hooks.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# Load templates
templates_path = PROJECT_ROOT / "scratch" / "prompt_templates.json"
with open(templates_path) as f:
    TEMPLATES = json.load(f)

def generate_prompt_hooks_config():
    """Generate prompt-based hooks configuration"""
    
    config = {
        "UserPromptSubmit": [
            {
                "hooks": []
            }
        ],
        "PreToolUse": []
    }
    
    # Add UserPromptSubmit prompt-based hooks
    user_prompt_hooks = []
    
    # Meta-enforcement (runs first - most important)
    user_prompt_hooks.append({
        "type": "prompt",
        "prompt": TEMPLATES["meta_enforcement_templates"]["protocol_enforcer"]["prompt"],
        "timeout": TEMPLATES["meta_enforcement_templates"]["protocol_enforcer"]["timeout"]
    })
    
    user_prompt_hooks.append({
        "type": "prompt",
        "prompt": TEMPLATES["meta_enforcement_templates"]["intent_router"]["prompt"],
        "timeout": TEMPLATES["meta_enforcement_templates"]["intent_router"]["timeout"]
    })
    
    # Simple advisory (specific checks)
    for name, template in TEMPLATES["simple_advisory_templates"].items():
        user_prompt_hooks.append({
            "type": "prompt",
            "prompt": template["prompt"],
            "timeout": template["timeout"]
        })
    
    config["UserPromptSubmit"][0]["hooks"] = user_prompt_hooks
    
    # Add PreToolUse prompt-based hooks
    config["PreToolUse"].append({
        "matcher": "Task",
        "hooks": [{
            "type": "prompt",
            "prompt": TEMPLATES["meta_enforcement_templates"]["shortcut_detector"]["prompt"],
            "timeout": TEMPLATES["meta_enforcement_templates"]["shortcut_detector"]["timeout"]
        }]
    })
    
    config["PreToolUse"].append({
        "matcher": "Write|Edit",
        "hooks": [{
            "type": "prompt",
            "prompt": TEMPLATES["meta_enforcement_templates"]["code_intent_validator"]["prompt"],
            "timeout": TEMPLATES["meta_enforcement_templates"]["code_intent_validator"]["timeout"]
        }]
    })
    
    return config

def generate_hybrid_config():
    """
    Generate HYBRID configuration showing:
    1. Which hooks to REMOVE (converted to prompt-based)
    2. Which hooks to KEEP (critical/stateful)
    3. New prompt-based hooks to ADD
    """
    
    # Hooks to remove (being replaced by prompt-based)
    REMOVE_HOOKS = [
        "detect_batch.py",
        "check_knowledge.py", 
        "sanity_check.py",
        "force_playwright.py",
        "intervention.py",
    ]
    
    # Hooks to keep (critical/stateful/complex)
    KEEP_HOOKS = [
        "confidence_init.py",  # Critical state
        "command_tracker.py",  # Critical state
        "evidence_tracker.py",  # Critical state
        "detect_confidence_penalty.py",  # Critical state
        "detect_confidence_reward.py",  # Critical state
        "pre_advice.py",  # Critical gate
        "detect_low_confidence.py",  # State-dependent
        "prerequisite_checker.py",  # Complex logic
        "synapse_fire.py",  # Complex logic
        "anti_sycophant.py",  # Keep for now (uses state)
        "detect_gaslight.py",  # Keep for now (uses state)
        "enforce_workflow.py",  # Keep for now
        "command_suggester.py",  # Keep for now
        "post_tool_command_suggester.py",  # PostToolUse
        "intent_classifier.py",  # Keep for now (complex)
        "best_practice_enforcer.py",  # Keep for now
        "ecosystem_mapper.py",  # Keep for now
    ]
    
    return {
        "analysis": {
            "total_hooks": 40,
            "convertible": 13,
            "phase_1_conversions": len(REMOVE_HOOKS),
            "hooks_to_remove": REMOVE_HOOKS,
            "hooks_to_keep": KEEP_HOOKS,
        },
        "prompt_based_hooks": generate_prompt_hooks_config(),
        "migration_steps": [
            "1. Backup current .claude/settings.json",
            "2. Remove hooks listed in 'hooks_to_remove' from UserPromptSubmit",
            "3. Add prompt-based hooks from 'prompt_based_hooks' section",
            "4. Test latency impact",
            "5. Monitor token usage",
            "6. Iterate on prompt templates based on effectiveness"
        ]
    }

def main():
    print("🔄 GENERATING PROMPT-BASED HOOK CONFIGURATION\n")
    print("=" * 80)
    
    hybrid_config = generate_hybrid_config()
    
    print("\n📊 CONVERSION PLAN")
    print("-" * 80)
    print(f"Total hooks analyzed: {hybrid_config['analysis']['total_hooks']}")
    print(f"Phase 1 conversions: {hybrid_config['analysis']['phase_1_conversions']}")
    print(f"\nRemoving (→ prompt-based):")
    for hook in hybrid_config['analysis']['hooks_to_remove']:
        print(f"  ❌ {hook}")
    
    print(f"\nKeeping (command-based):")
    print(f"  {len(hybrid_config['analysis']['hooks_to_keep'])} hooks (critical/stateful)")
    
    print("\n📝 NEW PROMPT-BASED HOOKS")
    print("-" * 80)
    
    user_prompt_count = len(hybrid_config['prompt_based_hooks']['UserPromptSubmit'][0]['hooks'])
    pre_tool_count = len(hybrid_config['prompt_based_hooks']['PreToolUse'])
    
    print(f"UserPromptSubmit: {user_prompt_count} prompt-based hooks")
    print("  1. Protocol Enforcer (meta-enforcement)")
    print("  2. Intent Router (tool recommendations)")
    print("  3. Batch Detection")
    print("  4. Knowledge Freshness")
    print("  5. API Guessing Prevention")
    print("  6. Browser Automation")
    print("  7. Bikeshedding Detection")
    
    print(f"\nPreToolUse: {pre_tool_count} prompt-based hooks")
    print("  1. Shortcut Detector (Task delegation)")
    print("  2. Code Intent Validator (Write/Edit)")
    
    # Save full configuration
    output_path = PROJECT_ROOT / "scratch" / "prompt_hooks_config.json"
    with open(output_path, "w") as f:
        json.dump(hybrid_config, f, indent=2)
    
    print(f"\n💾 Full configuration saved to: {output_path}")
    
    # Generate settings.json snippet
    snippet_path = PROJECT_ROOT / "scratch" / "settings_snippet.json"
    with open(snippet_path, "w") as f:
        json.dump(hybrid_config['prompt_based_hooks'], f, indent=2)
    
    print(f"💾 Settings snippet saved to: {snippet_path}")
    
    print("\n" + "=" * 80)
    print("\n⚠️ NEXT STEPS:")
    for step in hybrid_config['migration_steps']:
        print(f"  {step}")
    
    print("\n⚡ ESTIMATED IMPACT:")
    print("  Latency: +1-2 seconds per UserPromptSubmit (7 LLM calls in parallel)")
    print("  Token cost: ~500-1000 tokens per prompt hook")
    print("  Benefit: Semantic understanding > keyword matching")
    print("  Maintenance: 5 Python scripts → 9 prompt templates")

if __name__ == "__main__":
    main()
