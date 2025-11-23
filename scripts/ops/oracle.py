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
import json

# Add scripts/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
_current = _script_dir
while _current != '/':
    if os.path.exists(os.path.join(_current, 'scripts', 'lib', 'core.py')):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with scripts/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, 'scripts', 'lib'))
from core import setup_script, finalize, logger, handle_debug
from oracle import call_oracle_single, OracleAPIError

# ============================================================
# PERSONA SYSTEM PROMPTS
# ============================================================

PERSONAS = {
    "judge": {
        "name": "The Judge",
        "title": "⚖️ THE JUDGE'S RULING",
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
        "title": "🥊 THE CRITIC'S ASSAULT",
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
        "title": "🚨 THE SKEPTIC'S REVIEW",
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


def call_oracle(query, persona=None, custom_prompt=None, model="google/gemini-2.0-flash-thinking-exp"):
    """
    Call OpenRouter API with specified prompt.

    Args:
        query: User's question/proposal
        persona: Persona name (judge, critic, skeptic) or None
        custom_prompt: Custom system prompt or None
        model: OpenRouter model to use

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
        system_prompt = PERSONAS[persona]["prompt"]
        title = PERSONAS[persona]["title"]
    else:
        # No system prompt (consult mode)
        system_prompt = None
        title = "🧠 ORACLE CONSULTATION"

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

    # Query
    parser.add_argument(
        "query",
        nargs="?",  # Optional if --consult is used
        help="Question/proposal to send to oracle"
    )

    # Model selection
    parser.add_argument(
        "--model",
        default="google/gemini-2.0-flash-thinking-exp",
        help="OpenRouter model to use (default: gemini-2.0-flash-thinking-exp)"
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
        logger.info(f"Custom prompt: {args.custom_prompt or 'None'}")
        logger.info(f"Model: {args.model}")
        finalize(success=True)

    try:
        # Log invocation
        if args.persona:
            logger.info(f"Consulting {PERSONAS[args.persona]['name']} ({args.model})...")
        elif args.custom_prompt:
            logger.info(f"Consulting oracle with custom prompt ({args.model})...")
        else:
            logger.info(f"General consultation ({args.model})...")

        # Call oracle
        content, reasoning, title = call_oracle(
            query=query,
            persona=args.persona,
            custom_prompt=args.custom_prompt,
            model=args.model
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
