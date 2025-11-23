#!/usr/bin/env python3
"""
Oracle Batch Mode: Parallel Multi-Persona Consultation

Consults multiple personas in parallel for fast multi-perspective analysis.
Replaces sequential oracle.py calls with 3-5× faster parallel execution.

Usage:
  oracle_batch.py --personas judge,critic,skeptic "proposal"
  oracle_batch.py --batch comprehensive "proposal"  # Uses preset
  oracle_batch.py --all "proposal"  # All available personas

Examples:
  # 3 personas in parallel (3s total vs 9s sequential)
  oracle_batch.py --personas judge,critic,skeptic "Should we refactor?"

  # Comprehensive batch (5 personas in 3s)
  oracle_batch.py --batch comprehensive "Migrate to microservices?"

  # All personas (10+ personas in 3s!)
  oracle_batch.py --all "New architecture proposal"
"""
import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    raise RuntimeError("Could not find project root")

sys.path.insert(0, os.path.join(_project_root, 'scripts', 'lib'))
from core import setup_script, finalize, logger, handle_debug
from oracle import call_openrouter, OracleAPIError

# Persona definitions
PERSONAS = {
    "judge": {
        "name": "The Judge",
        "prompt": "You are The Judge. Analyze ROI, YAGNI, and bikeshedding. Be brutal about unnecessary work. Return PROCEED/SIMPLIFY/STOP verdict with confidence (0-100).",
        "emoji": "⚖️"
    },
    "critic": {
        "name": "The Critic",
        "prompt": "You are The Critic (10th Man). Attack assumptions. Find the fatal flaw. Expose blind spots. Return verdict with confidence.",
        "emoji": "🤺"
    },
    "skeptic": {
        "name": "The Skeptic",
        "prompt": "You are The Skeptic. Find failure modes, security risks, and logical fallacies. Return verdict with confidence.",
        "emoji": "🔍"
    },
    "innovator": {
        "name": "The Innovator",
        "prompt": "You are The Innovator. Propose creative alternatives and novel approaches. Return verdict with confidence.",
        "emoji": "💡"
    },
    "advocate": {
        "name": "The Advocate",
        "prompt": "You are The Advocate. Champion user needs and stakeholder concerns. Return verdict with confidence.",
        "emoji": "🛡️"
    },
    "security": {
        "name": "The Security Expert",
        "prompt": "You are The Security Expert. Find vulnerabilities, injection points, and data integrity issues. Return verdict with confidence.",
        "emoji": "🔒"
    },
    "performance": {
        "name": "The Performance Expert",
        "prompt": "You are The Performance Expert. Identify bottlenecks, scalability issues, and optimization opportunities. Return verdict with confidence.",
        "emoji": "⚡"
    },
    "oracle": {
        "name": "The Oracle",
        "prompt": "You are The Oracle. Provide high-level strategic reasoning. Synthesize multiple perspectives. Return verdict with confidence.",
        "emoji": "🔮"
    },
}

# Preset combinations
PRESETS = {
    "quick": ["judge", "critic", "skeptic"],
    "comprehensive": ["judge", "critic", "skeptic", "innovator", "oracle"],
    "security": ["security", "skeptic", "critic"],
    "technical": ["performance", "security", "innovator"],
    "all": list(PERSONAS.keys())
}


def call_persona_parallel(persona_key, persona_def, query, model):
    """
    Call a single persona (worker function for parallel execution).

    Args:
        persona_key: Persona identifier
        persona_def: Persona definition dict
        query: User query
        model: OpenRouter model to use

    Returns:
        dict with persona, response, success
    """
    try:
        # Build prompt
        system_prompt = persona_def["prompt"]
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        # Call OpenRouter
        result = call_openrouter(messages, model=model, timeout=120)

        return {
            "persona": persona_key,
            "name": persona_def["name"],
            "emoji": persona_def["emoji"],
            "response": result["content"],
            "reasoning": result["reasoning"],
            "success": True,
            "error": None
        }

    except OracleAPIError as e:
        logger.error(f"{persona_key} failed: {e}")
        return {
            "persona": persona_key,
            "name": persona_def["name"],
            "emoji": persona_def["emoji"],
            "response": None,
            "reasoning": None,
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"{persona_key} unexpected error: {e}")
        return {
            "persona": persona_key,
            "name": persona_def["name"],
            "emoji": persona_def["emoji"],
            "response": None,
            "reasoning": None,
            "success": False,
            "error": str(e)
        }


def run_batch_consultation(personas, query, model, max_workers=10):
    """
    Run parallel batch consultation.

    Args:
        personas: List of persona keys
        query: User query
        model: OpenRouter model
        max_workers: Maximum concurrent workers

    Returns:
        List of results
    """
    # Build persona list
    persona_defs = [
        (key, PERSONAS[key])
        for key in personas
        if key in PERSONAS
    ]

    if not persona_defs:
        logger.error("No valid personas selected")
        return []

    logger.info(f"Consulting {len(persona_defs)} personas in parallel...")

    results = []
    completed = 0
    total = len(persona_defs)

    # Execute in parallel
    with ThreadPoolExecutor(max_workers=min(max_workers, total)) as executor:
        futures = {
            executor.submit(call_persona_parallel, key, pdef, query, model): key
            for key, pdef in persona_defs
        }

        for future in as_completed(futures):
            persona_key = futures[future]
            result = future.result()
            results.append(result)
            completed += 1

            if result["success"]:
                print(f"✅ {result['emoji']} {result['name']} ({completed}/{total})")
            else:
                print(f"❌ {result['emoji']} {result['name']} failed ({completed}/{total})")

    return results


def display_results(results):
    """Display batch consultation results"""
    print("\n" + "="*70)
    print("BATCH ORACLE CONSULTATION")
    print("="*70)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"\nResults: {len(successful)} successful, {len(failed)} failed\n")

    # Display each persona's response
    for result in successful:
        print(f"\n{'─'*70}")
        print(f"{result['emoji']} {result['name'].upper()}")
        print(f"{'─'*70}")
        print(result["response"])

        if result["reasoning"]:
            print(f"\nReasoning:")
            print(result["reasoning"])

    # Display failures
    if failed:
        print(f"\n{'─'*70}")
        print("FAILED CONSULTATIONS")
        print(f"{'─'*70}")
        for result in failed:
            print(f"{result['emoji']} {result['name']}: {result['error']}")

    print("\n" + "="*70)


def main():
    parser = setup_script("Oracle Batch Mode: Parallel Multi-Persona Consultation")

    # Persona selection (mutually exclusive)
    selection_group = parser.add_mutually_exclusive_group(required=True)
    selection_group.add_argument(
        "--personas",
        help="Comma-separated persona list (e.g., judge,critic,skeptic)"
    )
    selection_group.add_argument(
        "--batch",
        choices=list(PRESETS.keys()),
        help="Preset batch combination"
    )
    selection_group.add_argument(
        "--all",
        action="store_true",
        help="Consult all available personas"
    )

    # Query
    parser.add_argument(
        "query",
        help="The proposal or question to evaluate"
    )

    # Options
    parser.add_argument(
        "--model",
        default="google/gemini-2.0-flash-thinking-exp",
        help="OpenRouter model to use (default: gemini-2.0-flash-thinking-exp)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum concurrent workers (default: 10)"
    )

    args = parser.parse_args()
    handle_debug(args)

    # Determine personas
    if args.personas:
        personas = [p.strip() for p in args.personas.split(",")]
    elif args.batch:
        personas = PRESETS[args.batch]
    elif args.all:
        personas = PRESETS["all"]
    else:
        parser.error("Must specify --personas, --batch, or --all")

    # Validate personas
    invalid = [p for p in personas if p not in PERSONAS]
    if invalid:
        logger.error(f"Invalid personas: {', '.join(invalid)}")
        logger.error(f"Available: {', '.join(PERSONAS.keys())}")
        finalize(success=False)

    # Dry run check
    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would consult personas in parallel")
        logger.info(f"Personas: {', '.join(personas)}")
        logger.info(f"Query: {args.query}")
        logger.info(f"Model: {args.model}")
        logger.info(f"Max workers: {args.max_workers}")
        finalize(success=True)

    try:
        # Run batch consultation
        print(f"\n🔮 Consulting {len(personas)} personas in parallel...")
        print(f"Personas: {', '.join(personas)}\n")

        results = run_batch_consultation(
            personas,
            args.query,
            args.model,
            args.max_workers
        )

        # Display results
        display_results(results)

        # Check success rate
        successful = sum(1 for r in results if r["success"])
        success_rate = successful / len(results) if results else 0

        if success_rate < 0.5:
            logger.warning("⚠️  Less than 50% of consultations succeeded")
            finalize(success=False)

        finalize(success=True)

    except KeyboardInterrupt:
        print("\n\n⚠️  Batch consultation interrupted by user")
        finalize(success=False)
    except Exception as e:
        logger.error(f"Batch consultation failed: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        finalize(success=False)


if __name__ == "__main__":
    main()
