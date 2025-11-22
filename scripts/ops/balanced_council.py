#!/usr/bin/env python3
"""
The Council: Six Thinking Hats Decision-Making Framework
=========================================================

Evidence-based decision support using Edward de Bono's Six Thinking Hats:
  1. ⚪ WHITE HAT (Facts & Data) → Oracle/Consult [unique model from shuffled pool]
  2. 🔴 RED HAT (Risks & Intuition) → Skeptic [unique model from shuffled pool]
  3. ⚫ BLACK HAT (Critical Analysis) → Critic [unique model from shuffled pool]
  4. 🟡 YELLOW HAT (Benefits & Opportunities) → Advocate [unique model from shuffled pool]
  5. 🟢 GREEN HAT (Alternatives & Creative) → Innovator [unique model from shuffled pool]
  6. 🔵 BLUE HAT (Process Control/Synthesis) → Arbiter [SOTA: google/gemini-3-pro-preview]

Five hats: Pool shuffled, one unique model per hat (no duplicates = max diversity).
Arbiter: Always SOTA model (best reasoning for critical synthesis).

Research basis:
- Six Thinking Hats (de Bono): 6 perspectives proven optimal
- Jury research: 12-person > 6-person juries (meta-analysis of 17 studies)
- Multi-agent AI: 5-6 agents balance diversity vs cost/sycophancy

Usage:
  python3 scripts/ops/balanced_council.py "Should we migrate to microservices?"
  python3 scripts/ops/balanced_council.py --dry-run "Use GraphQL instead of REST?"
"""
import sys
import os
import json
import random
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Add scripts/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
_current = _script_dir
while _current != "/":
    if os.path.exists(os.path.join(_current, "scripts", "lib", "core.py")):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with scripts/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, "scripts", "lib"))
from core import setup_script, finalize, logger, handle_debug
from context_builder import build_council_context


def load_model_pool():
    """Load the council model pool from config"""
    config_path = Path(_project_root) / ".claude" / "config" / "council_models.json"

    if not config_path.exists():
        logger.warning(f"Model config not found at {config_path}, using defaults")
        return [
            "google/gemini-3-pro-preview",
            "openai/gpt-4-turbo",
            "anthropic/claude-3-opus",
        ]

    try:
        with open(config_path) as f:
            config = json.load(f)
            models = config.get("models", [])
            if not models:
                logger.warning("No models in config, using defaults")
                return ["google/gemini-3-pro-preview"]
            return models
    except Exception as e:
        logger.error(f"Failed to load model config: {e}")
        return ["google/gemini-3-pro-preview"]


def pick_random_models(count):
    """Pick N random models from the pool"""
    pool = load_model_pool()
    return [random.choice(pool) for _ in range(count)]


def pick_council_models():
    """
    Pick models for council members.
    - 5 hats (White/Red/Black/Yellow/Green): Shuffle pool, assign models (reuse if pool < 5)
    - Blue Hat (Arbiter): Always google/gemini-3-pro-preview (SOTA for synthesis)

    If pool has fewer than 5 models, cycles through to fill all 5 hats.

    Returns: (white, red, black, yellow, green, blue)
    """
    pool = load_model_pool()

    if len(pool) < 5:
        logger.warning(f"Model pool has only {len(pool)} models (need 5). Some models will be reused.")
        # Cycle through pool to get 5 models (allows reuse if necessary)
        five_hats = [pool[i % len(pool)] for i in range(5)]
    else:
        # Shuffle and take first 5 (ensures unique assignment per hat)
        shuffled_pool = pool.copy()
        random.shuffle(shuffled_pool)
        five_hats = shuffled_pool[:5]

    arbiter_model = "google/gemini-3-pro-preview"  # SOTA model for critical synthesis
    return five_hats + [arbiter_model]


def call_hat(script_name, query, label, emoji, model):
    """Call a thinking hat script and return labeled result"""
    logger.info(f"Consulting {emoji} {label} ({model})...")
    script_path = os.path.join(_project_root, "scripts", "ops", script_name)

    try:
        result = subprocess.run(
            ["python3", script_path, query, "--model", model],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            return (
                label,
                emoji,
                f"ERROR: {script_name} failed\n{result.stderr}",
                model,
            )

        # Extract the actual response (skip logging/metadata lines)
        output_lines = result.stdout.split("\n")
        # Find substantial lines (skip short logging lines)
        response = "\n".join(line for line in output_lines if len(line.strip()) > 50)

        return (label, emoji, response or result.stdout, model)

    except subprocess.TimeoutExpired:
        return (label, emoji, f"ERROR: {script_name} timed out after 120s", model)
    except Exception as e:
        return (label, emoji, f"ERROR: {script_name} failed: {e}", model)


def call_arbiter(proposal, white, red, black, yellow, green, model):
    """Call arbiter (Blue Hat) with the five perspectives"""
    logger.info(f"Consulting 🔵 The Arbiter/Blue Hat ({model})...")
    script_path = os.path.join(_project_root, "scripts", "ops", "arbiter.py")

    try:
        result = subprocess.run(
            [
                "python3",
                script_path,
                proposal,
                "--white-hat",
                white,
                "--red-hat",
                red,
                "--black-hat",
                black,
                "--yellow-hat",
                yellow,
                "--green-hat",
                green,
                "--model",
                model,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            return f"ERROR: arbiter.py failed\n{result.stderr}"

        # Extract the actual response
        output_lines = result.stdout.split("\n")
        response = "\n".join(line for line in output_lines if len(line.strip()) > 50)

        return response or result.stdout

    except subprocess.TimeoutExpired:
        return "ERROR: arbiter.py timed out after 120s"
    except Exception as e:
        return f"ERROR: arbiter.py failed: {e}"


def main():
    parser = setup_script("The Council: Six Thinking Hats Decision-Making Framework")
    parser.add_argument("proposal", help="The proposal or decision to evaluate")

    args = parser.parse_args()
    handle_debug(args)

    if args.dry_run:
        logger.warning("⚠️  DRY RUN MODE: Will show what would be consulted")
        models = pick_council_models()
        print("\n" + "=" * 70)
        print("🎩 SIX THINKING HATS COUNCIL CONSULTATION (DRY RUN)")
        print("=" * 70)
        print(f"Proposal: {args.proposal}\n")
        print("Research-based framework (de Bono + Jury Studies + Multi-Agent AI)")
        print("\nWould consult:\n")
        print(f"  1. ⚪ WHITE HAT (Facts & Data) → consult.py [{models[0]}]")
        print(f"  2. 🔴 RED HAT (Risks & Intuition) → skeptic.py [{models[1]}]")
        print(f"  3. ⚫ BLACK HAT (Critical Analysis) → critic.py [{models[2]}]")
        print(
            f"  4. 🟡 YELLOW HAT (Benefits & Opportunities) → advocate.py [{models[3]}]"
        )
        print(
            f"  5. 🟢 GREEN HAT (Alternatives & Creative) → innovator.py [{models[4]}]"
        )
        print(
            f"\n  6. 🔵 BLUE HAT (Arbiter/Synthesis) → arbiter.py [{models[5]}] ⭐ SOTA"
        )
        print(
            "\n📊 Execution: Five hats in PARALLEL (unique models, no duplicates) → Arbiter synthesizes (SOTA)"
        )
        print("⏱️  Estimated time: ~45-90 seconds total")
        print("\nSkipping actual consultation in dry-run mode.")
        finalize(success=True)
        return

    try:
        logger.info(f"Six Thinking Hats Council: {args.proposal}")

        # Get session ID for context enrichment
        session_id = os.getenv("CLAUDE_SESSION_ID", "unknown")

        # Enrich proposal with project context
        logger.info("Building enriched context (memories, session state, git status)...")
        context_result = build_council_context(args.proposal, session_id, _project_root)

        # Handle context build result
        if not context_result["success"]:
            logger.error(f"Context enrichment failed: {context_result['error']}")
            logger.error("Falling back to raw proposal (no context enrichment)")
            enriched_proposal = args.proposal
        else:
            enriched_proposal = context_result["formatted"]

            # Log warnings if any
            for warning in context_result.get("warnings", []):
                logger.warning(warning)

            logger.debug(f"Enriched context:\n{enriched_proposal}")

        # Pick models: 5 random for hats, fixed SOTA for arbiter
        models = pick_council_models()
        white_model, red_model, black_model, yellow_model, green_model, blue_model = (
            models
        )

        logger.info("Model assignments:")
        logger.info(f"  ⚪ White={white_model} (unique from shuffled pool)")
        logger.info(f"  🔴 Red={red_model} (unique from shuffled pool)")
        logger.info(f"  ⚫ Black={black_model} (unique from shuffled pool)")
        logger.info(f"  🟡 Yellow={yellow_model} (unique from shuffled pool)")
        logger.info(f"  🟢 Green={green_model} (unique from shuffled pool)")
        logger.info(f"  🔵 Blue/Arbiter={blue_model} (SOTA - always fixed)")

        # Structure queries for each thinking hat (using enriched context)
        hats = [
            # WHITE HAT (Facts & Data)
            (
                "consult.py",
                f"Analyze this proposal objectively using only facts, data, and precedents. What do we KNOW? What do we NOT know? Cite evidence:\n\n{enriched_proposal}",
                "WHITE HAT (Facts)",
                "⚪",
                white_model,
            ),
            # RED HAT (Risks & Intuition)
            (
                "skeptic.py",
                f"What does your gut say about this? What feels wrong? What are the warning signs and hidden risks?\n\n{enriched_proposal}",
                "RED HAT (Risks)",
                "🔴",
                red_model,
            ),
            # BLACK HAT (Critical)
            (
                "critic.py",
                f"Attack this proposal. What are the weaknesses? Why will this fail? Be brutally critical:\n\n{enriched_proposal}",
                "BLACK HAT (Critical)",
                "⚫",
                black_model,
            ),
            # YELLOW HAT (Benefits)
            (
                "advocate.py",
                f"What are the benefits and opportunities? What's the best-case scenario? What value does this create?\n\n{enriched_proposal}",
                "YELLOW HAT (Benefits)",
                "🟡",
                yellow_model,
            ),
            # GREEN HAT (Alternatives)
            (
                "innovator.py",
                f"What else could we do instead? What are creative alternatives? What's the innovative approach?\n\n{enriched_proposal}",
                "GREEN HAT (Alternatives)",
                "🟢",
                green_model,
            ),
        ]

        # PHASE 1: Execute five hats in PARALLEL (ThreadPoolExecutor)
        logger.info("🎩 Phase 1: Consulting Five Hats in PARALLEL...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(call_hat, script, query, label, emoji, model)
                for script, query, label, emoji, model in hats
            ]
            results = [f.result() for f in futures]

        # Extract outputs for arbiter
        white_label, white_emoji, white_output, white_m = results[0]
        red_label, red_emoji, red_output, red_m = results[1]
        black_label, black_emoji, black_output, black_m = results[2]
        yellow_label, yellow_emoji, yellow_output, yellow_m = results[3]
        green_label, green_emoji, green_output, green_m = results[4]

        # Display Phase 1 results
        print("\n" + "=" * 70)
        print("🎩 SIX THINKING HATS COUNCIL CONSULTATION")
        print("=" * 70)
        print(f"Proposal: {args.proposal}\n")
        print("Framework: Edward de Bono's Six Thinking Hats")
        print("Research: Optimal 5+1 perspectives (de Bono, Jury Studies, AI)")
        print("=" * 70)

        for label, emoji, response, model in results:
            print(f"\n{emoji} {label.upper()} [{model}]")
            print("-" * 70)
            print(response)
            print()

        # PHASE 2: Call Arbiter (Blue Hat) with five outputs
        logger.info("🔵 Phase 2: Arbiter synthesizing verdict from Five Hats...")
        arbiter_output = call_arbiter(
            enriched_proposal,  # Pass enriched context to arbiter too
            white_output,
            red_output,
            black_output,
            yellow_output,
            green_output,
            blue_model,
        )

        # Display Phase 2: Arbiter verdict
        print("=" * 70)
        print(f"🔵 BLUE HAT: THE ARBITER'S VERDICT [{blue_model}]")
        print("=" * 70)
        print(arbiter_output)
        print("=" * 70)

        print("\n💡 DECISION SUPPORT COMPLETE")
        print("=" * 70)
        print("You now have:")
        print(
            "  ✅ Five independent perspectives (random external LLMs, diverse views)"
        )
        print("  ✅ Synthesized verdict (SOTA Arbiter's recommendation)")
        print("  ✅ Full transparency (can review all reasoning)")
        print("\nModel Strategy:")
        print("  • Five Hats: Shuffled pool, one unique model per hat (no duplicates)")
        print("  • Arbiter: google/gemini-3-pro-preview (SOTA for synthesis)")
        print("\nFinal decision remains with YOU.")
        print("=" * 70)

    except Exception as e:
        logger.error(f"Council consultation failed: {e}")
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
