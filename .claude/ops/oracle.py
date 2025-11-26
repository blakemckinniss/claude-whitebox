#!/usr/bin/env python3
"""
Oracle: Generic OpenRouter LLM Consultation

Single-shot external reasoning via OpenRouter API.
Replaces: judge.py, critic.py, skeptic.py, consult.py

Usage:
  # Use predefined persona
  oracle.py --persona judge "Should we migrate to Rust?"
  oracle.py --persona critic "Rewrite backend in Go"
  oracle.py --persona skeptic "Use blockchain for auth"

  # Custom prompt
  oracle.py --custom-prompt "You are a security expert" "Review this code"

  # Direct consultation (no system prompt)
  oracle.py --consult "How does async/await work in Python?"

Personas:
  - judge: ROI/value assessment, prevents over-engineering
  - critic: Red team, attacks assumptions
  - skeptic: Risk analysis, failure modes
  - consult: General expert consultation (no persona)
"""
import sys
import os

# Add .claude/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
_current = _script_dir
while _current != '/':
    if os.path.exists(os.path.join(_current, '.claude', 'lib', 'core.py')):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with .claude/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, '.claude', 'lib'))
from core import setup_script, finalize, logger, handle_debug  # noqa: E402
from oracle import call_oracle_single, OracleAPIError  # noqa: E402

# ============================================================
# STANCE MODIFIERS
# ============================================================

STANCE_MODIFIERS = {
    "for": """You are advocating FOR this proposal.

Be supportive but HONEST. You MUST be direct and say "this is a bad idea" when it truly is.
Your job is not blind advocacy - it's to find the BEST case for this approach while acknowledging real flaws.

Focus on:
- Potential benefits and opportunities
- How to maximize success if pursued
- What conditions would make this work
- Honest assessment of feasibility""",

    "against": """You are arguing AGAINST this proposal.

Be critical but FAIR. You must acknowledge when ideas are fundamentally sound even while critiquing them.
Your job is not reflexive opposition - it's to find genuine risks and weaknesses.

Focus on:
- Real risks and failure modes
- What could go wrong in practice
- Alternative approaches that might be better
- Honest assessment of concerns vs paranoia""",

    "neutral": """You are providing BALANCED analysis.

True balance means ACCURATE representation, even when evidence strongly points in one direction.
Do not artificially manufacture "both sides" when one approach is clearly superior.

Focus on:
- Objective evaluation of tradeoffs
- Evidence-based assessment
- Clear statement when evidence favors one side
- Honest acknowledgment of uncertainty"""
}

# ============================================================
# PERSONA SYSTEM PROMPTS
# ============================================================

# Persona file loading
def load_persona_file(filename):
    """Load persona prompt from file"""
    from pathlib import Path
    persona_dir = Path(__file__).parent.parent / "config" / "personas"
    filepath = persona_dir / filename
    if filepath.exists():
        with open(filepath, 'r') as f:
            return f.read()
    return None


PERSONAS = {
    "judge": {
        "name": "The Judge",
        "title": "⚖️ THE JUDGE'S RULING",
        "tiers": {
            "exploration": "judge_exploration.txt",
            "production": "judge_production.txt",
            "critical": "judge_critical.txt",
        },
        "default_tier": "production",
        "prompt": """You are The Judge. You are a ruthless Minimalist Architect and grumpy Senior Staff Engineer.
Your goal is to STOP work. You hate code. You love existing solutions.
You have seen every framework fail, every "improvement" create technical debt, and every "refactor" introduce bugs.

Code is a LIABILITY, not an asset. The best code is NO code.

Analyze the user's proposal for:

1. **Bikeshedding:** Are they focusing on trivial details (colors, linting rules, folder names) while ignoring the core problem?
2. **YAGNI (You Ain't Gonna Need It):** Are they building for a future that hasn't happened? Are they solving problems they don't have?
3. **Reinventing the Wheel:** Does a standard library, shell command, or existing tool already do this?
4. **ROI (Return on Investment):** Is the effort worth the result? Will this move the needle on the actual business problem?
5. **The XY Problem:** Are they asking for Z to solve Y, when Y itself is the wrong solution to X?
6. **Premature Optimization:** Are they building a Ferrari when a bicycle would work?

Be BRUTAL. Be HONEST. Your job is to SAVE time, not validate feelings.

Output format:
## ⚖️ VERDICT: [PROCEED / STOP / SIMPLIFY]

## 📉 REASON:
[One brutal, honest sentence explaining why]

## ✂️ THE CUT:
[What can be removed from this plan? What's the MINIMUM VIABLE solution?]

## 💡 THE ALTERNATIVE:
[If there's a simpler way (stdlib, existing tool, shell command), name it]

If the verdict is PROCEED, still suggest what to cut to make it leaner."""
    },

    "critic": {
        "name": "The Critic",
        "title": "🥊 THE CRITIC'S REVIEW",
        "modes": {
            "editor": "critic_editor.txt",
            "legacy": None,  # Use old prompt
        },
        "default_mode": "editor",
        "prompt": """You are The Critic. You are not helpful. You are not nice. You are the Eternal Pessimist.
Your job is to find the fatal flaw in the user's thinking. You are the 10th Man.

You embody ruthless intellectual honesty. You say what polite coworkers would never say.

The user will present an idea, plan, or assumption. You must:

1. **Attack the Premise:** Why is the core assumption wrong? What are they taking for granted that might be false?
2. **Expose the Optimism:** Where are they hoping for the best? What uncomfortable truth are they avoiding?
3. **The Counter-Point:** What is the exact OPPOSITE approach, and why might it actually be better?
4. **The Brutal Truth:** Say what needs to be said, even if it's uncomfortable.

You are NOT trying to be mean for the sake of it. You are trying to prevent disasters by forcing examination of blind spots.

Output format:
## 🥊 THE ATTACK
[Why is the core assumption wrong? What are they taking for granted?]

## 🌑 THE BLIND SPOT
[What uncomfortable truth are they avoiding? Where is the optimism hiding?]

## 🔄 THE COUNTER-POINT
[What is the OPPOSITE approach? Why might it be better?]

## 🔥 THE BRUTAL TRUTH
[What needs to be said that nobody wants to hear?]

Be direct. Be harsh. Be honest. This is your ONLY job."""
    },

    "skeptic": {
        "name": "The Skeptic",
        "title": "🚨 THE SKEPTIC'S ANALYSIS",
        "modes": {
            "risk_analyst": "skeptic_risk_analyst.txt",
            "legacy": None,  # Use old prompt
        },
        "default_mode": "risk_analyst",
        "prompt": """You are a Hostile Architecture Reviewer and Senior Engineering Skeptic.
Your role is to find every possible flaw, fallacy, and failure mode in proposed technical plans.

You are NOT here to be encouraging. You are here to prevent disasters.

Analyze the proposed plan for:

1. **The XY Problem**
   - Is the user asking for a solution to a SYMPTOM rather than the ROOT CAUSE?
   - Are they trying to fix the wrong thing?
   - Example: "I want to cache everything" → Real problem: "One slow query"

2. **Sunk Cost Fallacy**
   - Are they patching bad code instead of rewriting it?
   - Are they adding complexity to preserve a flawed design?
   - Is this "technical debt on top of technical debt"?

3. **Premature Optimization**
   - Are they building a Ferrari to cross the street?
   - Is this optimization actually needed, or are they guessing?
   - Have they measured the actual bottleneck?

4. **Security & Data Loss Risks**
   - What happens if input is malicious?
   - What happens if the operation fails halfway through?
   - Are there race conditions, injection risks, or data integrity issues?

5. **Pre-Mortem Analysis**
   - Assume this implementation FAILED in production.
   - Write the post-mortem: "This failed because..."
   - What edge cases were not considered?

6. **Complexity Explosion**
   - Is this adding cognitive load for future maintainers?
   - Is there a simpler solution they're missing?
   - Are they reinventing the wheel?

Output Format:
## 🚨 CRITICAL ISSUES
[Any dealbreakers that MUST be addressed]

## ⚠️ LOGICAL FALLACIES DETECTED
[XY Problem, Sunk Cost, Premature Optimization, etc.]

## 🔥 PRE-MORTEM: How This Will Fail
[Assume it failed. Explain why.]

## 🛡️ SECURITY & DATA INTEGRITY
[What could go wrong? What's unprotected?]

## 💡 ALTERNATIVE APPROACHES
[Simpler/safer ways to solve the ACTUAL problem]

## ✅ IF YOU MUST PROCEED
[What mitigations are absolutely required?]

Be ruthless. Be specific. Cite line numbers or specifics from the plan."""
    }
}


def extract_confidence(content):
    """
    Extract confidence level from oracle response.

    Returns:
        str: One of ["exploring", "low", "medium", "high", "certain"] or None
    """
    import re
    content_lower = content.lower()

    # Look for explicit confidence statements
    confidence_match = re.search(
        r'confidence[:\s]+(exploring|low|medium|high|very high|certain)',
        content_lower
    )
    if confidence_match:
        conf = confidence_match.group(1)
        if conf == "very high":
            return "certain"
        return conf

    # Heuristic: check for uncertainty markers
    uncertainty_markers = ["unclear", "uncertain", "need more", "requires further", "unclear"]
    certainty_markers = ["definitely", "clearly", "certain", "conclusive", "obvious"]

    if any(marker in content_lower for marker in uncertainty_markers):
        return "low"
    if any(marker in content_lower for marker in certainty_markers):
        return "high"

    # Default to medium if unclear
    return "medium"


def consolidate_findings(findings):
    """
    Consolidate multi-step reasoning findings.

    Args:
        findings: List of (content, reasoning, confidence) tuples

    Returns:
        str: Consolidated findings
    """
    sections = []

    # Add step-by-step analysis
    for i, (content, reasoning, confidence) in enumerate(findings, 1):
        sections.append(f"### Step {i} (Confidence: {confidence})")
        if reasoning:
            sections.append(f"**Reasoning:** {reasoning}")
        sections.append(content)
        sections.append("")

    # Add synthesis
    sections.append("### Final Synthesis")
    final_content = findings[-1][0]  # Last step's content
    final_confidence = findings[-1][2]
    sections.append(f"**Final Confidence:** {final_confidence}")
    sections.append(final_content)

    return "\n".join(sections)


def call_oracle_multi_step(
    query,
    persona=None,
    custom_prompt=None,
    stance=None,
    max_steps=5,
    target_confidence="high",
    model="openai/gpt-5.1"
):
    """
    Multi-step reasoning with confidence gating.

    Args:
        query: User's question/proposal
        persona: Persona name or None
        custom_prompt: Custom system prompt or None
        stance: Stance modifier (for/against/neutral) or None
        max_steps: Maximum reasoning steps
        target_confidence: Stop when this confidence reached
        model: OpenRouter model to use

    Returns:
        tuple: (consolidated_content, reasoning, title, steps_taken)
    """
    # Confidence hierarchy
    confidence_levels = ["exploring", "low", "medium", "high", "certain"]
    target_idx = confidence_levels.index(target_confidence)

    findings = []

    logger.info(f"Starting multi-step reasoning (max {max_steps} steps, target: {target_confidence})")

    for step in range(1, max_steps + 1):
        # Build step prompt
        if step == 1:
            step_query = query
        else:
            # Include previous findings as context
            step_query = f"""Previous analysis:
{chr(10).join(f"Step {i}: {content[:200]}..." for i, (content, _, _) in enumerate(findings, 1))}

Continue deeper analysis:
{query}

State your confidence level explicitly (exploring/low/medium/high/certain).
"""

        # Call oracle for this step
        logger.info(f"  Step {step}/{max_steps}...")
        content, reasoning, title = call_oracle(
            query=step_query,
            persona=persona,
            custom_prompt=custom_prompt,
            stance=stance,
            model=model
        )

        # Extract confidence
        confidence = extract_confidence(content)
        findings.append((content, reasoning, confidence))

        logger.info(f"    Confidence: {confidence}")

        # Check if we've reached target confidence
        if confidence in confidence_levels:
            conf_idx = confidence_levels.index(confidence)
            if conf_idx >= target_idx:
                logger.info(f"  Target confidence '{target_confidence}' reached at step {step}")
                break

    # Consolidate findings
    consolidated = consolidate_findings(findings)

    return consolidated, findings[-1][1], title, len(findings)


def call_oracle(query, persona=None, custom_prompt=None, stance=None, model="openai/gpt-5.1", tier=None, mode=None):
    """
    Call OpenRouter API with specified prompt.

    Args:
        query: User's question/proposal
        persona: Persona name (judge, critic, skeptic) or None
        custom_prompt: Custom system prompt or None
        stance: Stance modifier (for/against/neutral) or None
        model: OpenRouter model to use
        tier: Persona tier (exploration/production/critical) for judge
        mode: Persona mode (editor/legacy) for critic/skeptic

    Returns:
        tuple: (content, reasoning, title)
    """
    # Determine system prompt and title
    if custom_prompt:
        system_prompt = custom_prompt
        title = "🔮 ORACLE RESPONSE"
    elif persona:
        # Map persona to system prompt
        if persona not in PERSONAS:
            raise ValueError(f"Unknown persona: {persona}. Choose from: {', '.join(PERSONAS.keys())}")

        persona_config = PERSONAS[persona]
        title = persona_config["title"]

        # Check for tiered personas (judge)
        if "tiers" in persona_config:
            tier = tier or persona_config.get("default_tier", "production")
            if tier not in persona_config["tiers"]:
                raise ValueError(f"Unknown tier '{tier}' for {persona}. Choose from: {', '.join(persona_config['tiers'].keys())}")

            # Try to load from file
            tier_file = persona_config["tiers"][tier]
            loaded_prompt = load_persona_file(tier_file)
            if loaded_prompt:
                system_prompt = loaded_prompt
                title = f"{title} ({tier.upper()} TIER)"
            else:
                # Fallback to hardcoded
                system_prompt = persona_config["prompt"]
                logger.warning(f"Could not load {tier_file}, using legacy prompt")

        # Check for mode-based personas (critic, skeptic)
        elif "modes" in persona_config:
            mode = mode or persona_config.get("default_mode", "legacy")
            if mode not in persona_config["modes"]:
                raise ValueError(f"Unknown mode '{mode}' for {persona}. Choose from: {', '.join(persona_config['modes'].keys())}")

            mode_file = persona_config["modes"][mode]
            if mode_file:
                # Try to load from file
                loaded_prompt = load_persona_file(mode_file)
                if loaded_prompt:
                    system_prompt = loaded_prompt
                    title = f"{title} ({mode.upper()} MODE)"
                else:
                    # Fallback to hardcoded
                    system_prompt = persona_config["prompt"]
                    logger.warning(f"Could not load {mode_file}, using legacy prompt")
            else:
                # Legacy mode (use hardcoded)
                system_prompt = persona_config["prompt"]

        else:
            # No tiers or modes, use default prompt
            system_prompt = persona_config["prompt"]
    else:
        # No system prompt (consult mode)
        system_prompt = None
        title = "🧠 ORACLE CONSULTATION"

    # Apply stance modifier if provided
    if stance:
        if stance not in STANCE_MODIFIERS:
            raise ValueError(f"Unknown stance: {stance}. Choose from: {', '.join(STANCE_MODIFIERS.keys())}")

        stance_text = STANCE_MODIFIERS[stance]

        if system_prompt:
            # Prepend stance to existing prompt
            system_prompt = f"{stance_text}\n\n{system_prompt}"
        else:
            # Use stance as the only system prompt
            system_prompt = stance_text

        # Update title to reflect stance
        stance_emoji = {"for": "👍", "against": "👎", "neutral": "⚖️"}
        title = f"{stance_emoji.get(stance, '🔮')} {title}"

    # Call shared library function
    logger.debug(f"Calling OpenRouter with model: {model}")
    content, reasoning, _ = call_oracle_single(
        query=query,
        custom_prompt=system_prompt,
        model=model
    )

    return content, reasoning, title


def main():
    parser = setup_script("Oracle: Generic OpenRouter LLM consultation")

    # Persona selection (mutually exclusive)
    persona_group = parser.add_mutually_exclusive_group()
    persona_group.add_argument(
        "--persona",
        choices=PERSONAS.keys(),
        help=f"Predefined persona: {', '.join(PERSONAS.keys())}"
    )
    persona_group.add_argument(
        "--custom-prompt",
        help="Custom system prompt (instead of persona)"
    )
    persona_group.add_argument(
        "--consult",
        action="store_true",
        help="General consultation (no system prompt)"
    )

    # Stance modifier
    parser.add_argument(
        "--stance",
        choices=STANCE_MODIFIERS.keys(),
        help=f"Stance modifier: {', '.join(STANCE_MODIFIERS.keys())} (applies to persona)"
    )

    # Tier selection (for judge)
    parser.add_argument(
        "--tier",
        choices=["exploration", "production", "critical"],
        help="Judge tier: exploration (low-stakes), production (medium-stakes), critical (high-stakes)"
    )

    # Mode selection (for critic/skeptic)
    parser.add_argument(
        "--mode",
        choices=["editor", "risk_analyst", "legacy"],
        help="Persona mode: editor/risk_analyst (constructive) or legacy (pessimistic)"
    )

    # Multi-step reasoning
    parser.add_argument(
        "--steps",
        type=int,
        metavar="N",
        help="Enable multi-step reasoning (max N steps)"
    )
    parser.add_argument(
        "--target-confidence",
        choices=["exploring", "low", "medium", "high", "certain"],
        default="high",
        help="Stop when this confidence level reached (default: high)"
    )

    # Query
    parser.add_argument(
        "query",
        nargs="?",  # Optional if --consult is used
        help="Question/proposal to send to oracle"
    )

    # Model selection
    parser.add_argument(
        "--model",
        default="openai/gpt-5.1",
        help="OpenRouter model to use (default: gpt-5.1)"
    )

    args = parser.parse_args()
    handle_debug(args)

    # Validate arguments
    if not args.query and not args.consult:
        parser.error("Query required unless using --consult mode")

    # Handle consult mode
    if args.consult and not args.query:
        # Read from stdin for consultation
        logger.info("Consultation mode: enter your question (Ctrl+D to finish)")
        query = sys.stdin.read().strip()
    else:
        query = args.query

    # Dry run check
    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would send the following to OpenRouter:")
        logger.info(f"Query: {query}")
        logger.info(f"Persona: {args.persona or 'None (custom or consult)'}")
        logger.info(f"Stance: {args.stance or 'None'}")
        logger.info(f"Custom prompt: {args.custom_prompt or 'None'}")
        logger.info(f"Multi-step: {args.steps or 'No (single-shot)'}")
        if args.steps:
            logger.info(f"Target confidence: {args.target_confidence}")
        logger.info(f"Model: {args.model}")
        finalize(success=True)

    try:
        # Log invocation
        if args.persona:
            persona_name = PERSONAS[args.persona]['name']
            stance_label = f" ({args.stance})" if args.stance else ""
            logger.info(f"Consulting {persona_name}{stance_label} ({args.model})...")
        elif args.custom_prompt:
            logger.info(f"Consulting oracle with custom prompt ({args.model})...")
        else:
            logger.info(f"General consultation ({args.model})...")

        # Determine if multi-step or single-shot
        if args.steps:
            # Multi-step reasoning
            content, reasoning, title, steps_taken = call_oracle_multi_step(
                query=query,
                persona=args.persona,
                custom_prompt=args.custom_prompt,
                stance=args.stance,
                max_steps=args.steps,
                target_confidence=args.target_confidence,
                model=args.model
            )

            # Add step count to title
            title = f"{title} (Multi-Step: {steps_taken} steps)"

        else:
            # Single-shot
            content, reasoning, title = call_oracle(
                query=query,
                persona=args.persona,
                custom_prompt=args.custom_prompt,
                stance=args.stance,
                model=args.model,
                tier=args.tier,
                mode=args.mode
            )

        # Display results
        print("\n" + "=" * 70)
        print(title)
        print("=" * 70)

        if reasoning:
            print("\n🧠 REASONING:")
            print("-" * 70)
            print(reasoning)
            print("-" * 70)

        print("\n" + content)
        print("=" * 70 + "\n")

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        finalize(success=False)
    except OracleAPIError as e:
        logger.error(f"API call failed: {e}")
        finalize(success=False)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
