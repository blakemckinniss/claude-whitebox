#!/usr/bin/env python3
"""
The Timekeeper: Assesses proposal complexity and sets dynamic deliberation limits.
Prevents bikeshedding through parameter tuning, not LLM consultation.
"""
import sys
import os

# Add .claude/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
_current = _script_dir
while _current != "/":
    if os.path.exists(os.path.join(_current, ".claude", "lib", "core.py")):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with .claude/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, ".claude", "lib"))
from core import setup_script, finalize, logger  # noqa: E402


# Complexity assessment rules (heuristic-based, not LLM)
def assess_complexity(proposal_text):
    """
    Assess proposal complexity using heuristics.

    Returns: Dict with complexity, risk, reversibility, blast_radius, novelty
    """
    text_lower = proposal_text.lower()

    # Keywords for complexity tiers
    trivial_keywords = ["delete", "remove", "rename", "cosmetic", "comment", "typo", "fix typo"]
    simple_keywords = ["add", "feature", "update", "improve", "refactor", "extract"]
    complex_keywords = ["migrate", "migration", "framework", "replace", "rewrite", "integration"]
    strategic_keywords = ["architecture", "platform", "business", "direction", "strategy", "pivot"]

    # Risk keywords
    high_risk_keywords = ["production", "database", "auth", "security", "payment", "critical"]
    irreversible_keywords = ["delete", "drop", "remove", "migration", "rewrite"]

    # Blast radius keywords
    system_keywords = ["all", "every", "entire", "whole", "global", "platform"]
    module_keywords = ["package", "module", "component", "service"]

    # Novelty keywords
    novel_keywords = ["new", "novel", "unprecedented", "first time", "never done"]
    familiar_keywords = ["similar", "like before", "again", "repeat", "standard"]

    # Count matches
    def count_matches(keywords):
        return sum(1 for kw in keywords if kw in text_lower)

    # Assess complexity
    trivial_score = count_matches(trivial_keywords)
    simple_score = count_matches(simple_keywords)
    complex_score = count_matches(complex_keywords)
    strategic_score = count_matches(strategic_keywords)

    if strategic_score >= 2:
        complexity = "strategic"
    elif complex_score >= 2:
        complexity = "complex"
    elif simple_score >= 2 or (simple_score >= 1 and len(proposal_text) > 300):
        complexity = "simple"
    elif trivial_score >= 1:
        complexity = "trivial"
    else:
        # Default based on length
        if len(proposal_text) < 100:
            complexity = "trivial"
        elif len(proposal_text) < 300:
            complexity = "simple"
        elif len(proposal_text) < 800:
            complexity = "complex"
        else:
            complexity = "strategic"

    # Assess risk
    high_risk_score = count_matches(high_risk_keywords)
    if high_risk_score >= 3:
        risk = "critical"
    elif high_risk_score >= 2:
        risk = "high"
    elif high_risk_score >= 1:
        risk = "medium"
    else:
        risk = "low"

    # Assess reversibility
    irreversible_score = count_matches(irreversible_keywords)
    if irreversible_score >= 2:
        reversibility = "irreversible"
    elif irreversible_score >= 1:
        reversibility = "partially-reversible"
    else:
        reversibility = "reversible"

    # Assess blast radius
    system_score = count_matches(system_keywords)
    module_score = count_matches(module_keywords)
    if system_score >= 2:
        blast_radius = "platform"
    elif system_score >= 1:
        blast_radius = "system"
    elif module_score >= 1:
        blast_radius = "module"
    else:
        blast_radius = "isolated"

    # Assess novelty
    novel_score = count_matches(novel_keywords)
    familiar_score = count_matches(familiar_keywords)
    if novel_score >= 2:
        novelty = "unprecedented"
    elif novel_score >= 1:
        novelty = "novel"
    elif familiar_score >= 1:
        novelty = "familiar"
    else:
        novelty = "routine"

    return {
        "complexity": complexity,
        "risk": risk,
        "reversibility": reversibility,
        "blast_radius": blast_radius,
        "novelty": novelty
    }


def determine_limits(assessment):
    """
    Determine deliberation limits based on assessment.

    Returns: Dict with max_rounds, convergence_threshold, token_budget, default_bias
    """
    complexity_limits = {
        "trivial": {
            "max_rounds": 2,
            "convergence_threshold": 0.80,
            "token_budget": 5000,
            "default_bias": "PROCEED"
        },
        "simple": {
            "max_rounds": 3,
            "convergence_threshold": 0.75,
            "token_budget": 10000,
            "default_bias": "NEUTRAL"
        },
        "complex": {
            "max_rounds": 5,
            "convergence_threshold": 0.70,
            "token_budget": 20000,
            "default_bias": "NEUTRAL"
        },
        "strategic": {
            "max_rounds": 7,
            "convergence_threshold": 0.65,
            "token_budget": 30000,
            "default_bias": "STOP"
        }
    }

    limits = complexity_limits[assessment["complexity"]].copy()

    # Adjust based on risk
    if assessment["risk"] == "critical":
        limits["default_bias"] = "STOP"
        limits["convergence_threshold"] += 0.05  # Require higher agreement
    elif assessment["risk"] == "high":
        if limits["default_bias"] == "PROCEED":
            limits["default_bias"] = "NEUTRAL"
    elif assessment["risk"] == "low":
        if limits["default_bias"] == "STOP":
            limits["default_bias"] = "NEUTRAL"
        limits["convergence_threshold"] -= 0.05  # Allow faster convergence

    # Adjust based on reversibility
    if assessment["reversibility"] == "irreversible":
        limits["max_rounds"] += 1  # More deliberation
        limits["default_bias"] = "STOP"
    elif assessment["reversibility"] == "reversible":
        limits["max_rounds"] = max(2, limits["max_rounds"] - 1)  # Less deliberation
        if limits["default_bias"] == "STOP":
            limits["default_bias"] = "NEUTRAL"

    # Clamp values
    limits["convergence_threshold"] = max(0.60, min(0.85, limits["convergence_threshold"]))
    limits["max_rounds"] = max(2, min(7, limits["max_rounds"]))

    return limits


def main():
    parser = setup_script(
        "The Timekeeper: Assesses proposal complexity and sets deliberation parameters."
    )

    parser.add_argument("proposal", help="The proposal to assess")
    parser.add_argument("--model", help="(Ignored - Timekeeper uses heuristics, not LLM)")

    args = parser.parse_args()

    # Assess complexity
    assessment = assess_complexity(args.proposal)
    limits = determine_limits(assessment)

    # Build reasoning
    reasoning_parts = [
        f"Complexity: {assessment['complexity']} (based on keywords and length)",
        f"Risk: {assessment['risk']} (based on domain keywords)",
        f"Reversibility: {assessment['reversibility']}",
        f"Blast Radius: {assessment['blast_radius']}",
        f"Novelty: {assessment['novelty']}"
    ]
    reasoning = "\n".join(reasoning_parts)

    # Output structured format (matching Timekeeper persona template from library.json)
    output = f"""COMPLEXITY: {assessment['complexity']}
RISK: {assessment['risk']}
REVERSIBILITY: {assessment['reversibility']}
BLAST_RADIUS: {assessment['blast_radius']}
NOVELTY: {assessment['novelty']}

RECOMMENDED_LIMITS:
  max_rounds: {limits['max_rounds']}
  convergence_threshold: {limits['convergence_threshold']:.2f}
  token_budget: {limits['token_budget']}
  default_bias: {limits['default_bias']}

REASONING: {reasoning}
"""

    print(output)

    logger.info(f"Complexity: {assessment['complexity']}, Risk: {assessment['risk']}")
    logger.info(f"Recommended: {limits['max_rounds']} rounds, {limits['convergence_threshold']*100:.0f}% threshold")

    finalize(success=True)


if __name__ == "__main__":
    main()
