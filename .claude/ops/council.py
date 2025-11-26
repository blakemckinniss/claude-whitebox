#!/usr/bin/env python3
"""
Deliberative Council: Multi-Round Decision Framework with Convergence
======================================================================

Complete implementation of adaptive multi-round council deliberation.

Features:
- N personas + 1 Arbiter (always)
- Multi-round deliberation with convergence detection
- Information gathering (auto + user interaction)
- Dynamic persona recruitment
- Context sharing across rounds
- Structured output parsing

Usage:
  council_deliberative.py "Should we migrate to microservices?"
  council_deliberative.py --preset comprehensive "Architecture decision"
  council_deliberative.py --recruit "Deploy on Kubernetes?"
"""
import sys
import os
import json
import re
import random
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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
from core import setup_script, finalize, logger, handle_debug  # noqa: E402
from context_builder import build_council_context  # noqa: E402
from oracle import call_arbiter, OracleAPIError  # noqa: E402

# Import council components from lib
from persona_parser import parse_persona_output  # noqa: E402
from council_engine import (  # noqa: E402
    ConvergenceDetector,
    InformationGatherer,
    UserInteraction,
    build_round_context
)

# Import recruiter if available
try:
    sys.path.insert(0, os.path.join(_project_root, ".claude", "ops"))
    from recruiter import recruit_council
except ImportError:
    recruit_council = None


def load_persona_library():
    """Load persona library (v2 with structured output)"""
    # Try v2 first (in scratch), fall back to production
    v2_path = Path(_project_root) / "scratch" / "library_v2.json"
    prod_path = Path(_project_root) / ".claude" / "config" / "personas" / "library.json"

    library_path = v2_path if v2_path.exists() else prod_path

    logger.debug(f"Loading persona library from: {library_path}")

    try:
        with open(library_path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Malformed JSON in {library_path}: {e}")
        raise RuntimeError(f"Failed to parse persona library: {e}")
    except FileNotFoundError:
        logger.error(f"Persona library not found at {library_path}")
        raise RuntimeError("Persona library not found")


def load_presets():
    """Load preset combinations"""
    presets_path = Path(_project_root) / ".claude" / "config" / "personas" / "presets.json"

    if not presets_path.exists():
        return {}

    try:
        with open(presets_path) as f:
            return json.load(f).get("presets", {})
    except json.JSONDecodeError as e:
        logger.error(f"Malformed JSON in {presets_path}: {e}")
        return {}


def load_model_pool():
    """Load model pool for diversity"""
    pool_path = Path(_project_root) / ".claude" / "config" / "council_models.json"

    default_models = ["google/gemini-3-pro-preview", "openai/gpt-4-turbo", "anthropic/claude-3-opus"]

    if not pool_path.exists():
        return default_models

    try:
        with open(pool_path) as f:
            models = json.load(f).get("models", [])
            return models if models else default_models
    except json.JSONDecodeError as e:
        logger.error(f"Malformed JSON in {pool_path}: {e}")
        return default_models


def assign_models(num_personas, pool):
    """Assign unique models to personas"""
    if not pool:
        logger.error("Model pool is empty, using default model")
        return ["anthropic/claude-3-opus"] * num_personas

    if len(pool) < num_personas:
        return [pool[i % len(pool)] for i in range(num_personas)]

    shuffled = pool.copy()
    random.shuffle(shuffled)
    return shuffled[:num_personas]


def call_timekeeper(proposal, scripts_dir):
    """
    Call Timekeeper to assess complexity and get dynamic limits.

    Returns: Dict with complexity assessment and recommended limits
    """
    script_path = os.path.join(scripts_dir, "timekeeper.py")

    try:
        result = subprocess.run(
            ["python3", script_path, proposal],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            logger.error(f"Timekeeper failed: {result.stderr}")
            return None

        # Parse Timekeeper output
        output = result.stdout

        # Extract fields
        complexity_match = re.search(r'^COMPLEXITY:\s*(\w+)', output, re.MULTILINE)
        risk_match = re.search(r'^RISK:\s*(\w+)', output, re.MULTILINE)
        max_rounds_match = re.search(r'max_rounds:\s*(\d+)', output)
        threshold_match = re.search(r'convergence_threshold:\s*([\d.]+)', output)
        bias_match = re.search(r'default_bias:\s*(\w+)', output)

        if not all([complexity_match, risk_match, max_rounds_match, threshold_match, bias_match]):
            logger.error("Could not parse Timekeeper output")
            return None

        assessment = {
            "complexity": complexity_match.group(1),
            "risk": risk_match.group(1),
            "max_rounds": int(max_rounds_match.group(1)),
            "convergence_threshold": float(threshold_match.group(1)),
            "default_bias": bias_match.group(1)
        }

        logger.info("⏱️  Timekeeper Assessment:")
        logger.info(f"   Complexity: {assessment['complexity']}, Risk: {assessment['risk']}")
        logger.info(f"   Recommended: {assessment['max_rounds']} rounds, {assessment['convergence_threshold']*100:.0f}% threshold")

        return assessment

    except Exception as e:
        logger.error(f"Timekeeper error: {e}")
        return None


def call_persona_with_context(persona_key, persona_def, context, model, scripts_dir):
    """Call persona via oracle.py (using --persona or --custom-prompt)"""
    logger.info(f"  {persona_def['emoji']} {persona_def['role']} ({model})...")

    oracle_path = os.path.join(scripts_dir, "oracle.py")

    # oracle.py only supports these hardcoded personas
    ORACLE_NATIVE_PERSONAS = ["judge", "critic", "skeptic"]

    try:
        # Build command based on persona support
        if persona_key in ORACLE_NATIVE_PERSONAS:
            # Use native --persona flag (context gets passed as query)
            cmd = ["python3", oracle_path, "--persona", persona_key, context, "--model", model]
        else:
            # Use --custom-prompt for other personas
            # Extract system prompt by removing {proposal} placeholder
            system_prompt = persona_def["prompt_template"].replace("{proposal}", "CONTEXT PROVIDED BELOW")
            cmd = ["python3", oracle_path, "--custom-prompt", system_prompt, context, "--model", model]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            logger.error(f"Persona {persona_key} failed: {result.stderr}")
            # Return minimal valid output
            return parse_persona_output(
                "VERDICT: ABSTAIN\nCONFIDENCE: 0\nREASONING: Oracle call failed",
                persona_key
            )

        # Parse structured output
        return parse_persona_output(result.stdout, persona_key)

    except subprocess.TimeoutExpired:
        logger.error(f"Persona {persona_key} timed out")
        return parse_persona_output(
            "VERDICT: ABSTAIN\nCONFIDENCE: 0\nREASONING: Timeout after 120s",
            persona_key
        )
    except Exception as e:
        logger.error(f"Persona {persona_key} error: {e}")
        return parse_persona_output(
            f"VERDICT: ABSTAIN\nCONFIDENCE: 0\nREASONING: {str(e)}",
            persona_key
        )


def run_deliberation(
    proposal,
    personas,
    enriched_context,
    max_rounds=5,
    convergence_threshold=0.7
):
    """
    Multi-round deliberation with convergence.

    Returns:
        Dict with rounds, convergence info, recruited personas
    """
    project_root = Path(_project_root)
    scripts_dir = os.path.join(_project_root, ".claude", "ops")
    model_pool = load_model_pool()

    detector = ConvergenceDetector(threshold=convergence_threshold)
    gatherer = InformationGatherer(project_root)

    round_history = []
    all_personas = personas.copy()  # Track all personas (may grow via recruitment)

    for round_num in range(1, max_rounds + 1):
        print(f"\n{'='*70}")
        print(f"🎩 ROUND {round_num}")
        print(f"{'='*70}\n")

        # Assign models for this round
        persona_models = assign_models(len(all_personas), model_pool)

        # Build context for this round
        if round_num == 1:
            round_context = enriched_context
        else:
            # Subsequent rounds: personas see full deliberation history
            round_context = enriched_context  # Base context shared by all

        # Consult all personas in parallel
        logger.info(f"Consulting {len(all_personas)} personas in parallel...")

        with ThreadPoolExecutor(max_workers=len(all_personas)) as executor:
            futures = []
            for (persona_key, persona_def), model in zip(all_personas, persona_models):
                # Build persona-specific context (includes deliberation history)
                persona_context = build_round_context(
                    proposal,
                    round_history,
                    persona_key,
                    round_context
                )

                future = executor.submit(
                    call_persona_with_context,
                    persona_key,
                    persona_def,
                    persona_context,
                    model,
                    scripts_dir
                )
                futures.append((persona_key, future))

            # Collect results
            round_outputs = {}
            for persona_key, future in futures:
                output = future.result()
                round_outputs[persona_key] = output

                # Display verdict
                verdict = output.get("verdict") or "UNKNOWN"
                confidence = output.get("confidence") or 0
                print(f"  {verdict:15s} ({confidence:3d}%) - {persona_key}")

        # Store round data
        round_data = {
            "round": round_num,
            "outputs": round_outputs,
            "info_gathered": []
        }
        round_history.append(round_data)

        # Check convergence
        output_list = list(round_outputs.values())
        convergence = detector.check_convergence(output_list)

        print(f"\nConvergence: {convergence['agreement_ratio']*100:.0f}% agree on {convergence['dominant_verdict']}")
        print(f"Status: {convergence['reason']}")

        if convergence["converged"]:
            print(f"\n✅ CONVERGED after {round_num} rounds")
            break

        # Detect bikeshedding and force decision if detected
        if convergence.get("has_low_conviction_stalemate"):
            print("\n⚠️  BIKESHEDDING DETECTED (low conviction, low agreement)")
            print(f"   Avg conviction: {convergence.get('avg_conviction', 0):.0f}%")
            print(f"   Forcing convergence with current dominant verdict: {convergence['dominant_verdict']}")
            # Force convergence by marking as converged
            convergence["converged"] = True
            break

        # Gather information requests
        print("\n📋 Information Gathering Phase...")
        gathered, missing = gatherer.gather_all_requests(output_list)

        if gathered:
            print(f"  ✅ Auto-gathered {len(gathered)} items")
            for item in gathered:
                print(f"     - {item['request']['description'][:60]}...")

        # Handle recruitment requests
        recruitment_requests = [
            p for p in output_list if p.get("recruits") is not None
        ]

        if recruitment_requests:
            print(f"\n🎯 Recruitment Requests: {len(recruitment_requests)}")
            library = load_persona_library()

            for req in recruitment_requests:
                recruit_info = req["recruits"]
                persona_to_add = recruit_info["persona"]
                reason = recruit_info["reason"]

                if persona_to_add in [p[0] for p in all_personas]:
                    print(f"  ⚠️  {persona_to_add} already in council")
                    continue

                if persona_to_add not in library["personas"]:
                    print(f"  ❌ Unknown persona: {persona_to_add}")
                    continue

                print(f"  ➕ Adding {persona_to_add} - {reason}")
                all_personas.append((persona_to_add, library["personas"][persona_to_add]))

        # Ask user for missing critical information
        if missing:
            critical_missing = [m for m in missing if m["priority"] == "critical"]

            if critical_missing and sys.stdout.isatty():
                try:
                    user_responses = UserInteraction.ask_for_information(critical_missing)

                    # Add user responses to gathered info
                    for req_id, response in user_responses.items():
                        req = next((m for m in critical_missing if m["id"] == req_id), None)
                        if req:
                            gathered.append({
                                "request": req,
                                "data": response,
                                "source": "user"
                            })
                except KeyboardInterrupt:
                    print("\n\n⚠️  User interrupted. Skipping user interaction, continuing with available info...")
                    logger.warning("User interrupted information gathering")
            elif critical_missing:
                logger.warning(f"Critical information needed but running in non-interactive mode. Skipping {len(critical_missing)} requests.")

        round_data["info_gathered"] = gathered

        # Check if we've hit max rounds
        if round_num == max_rounds:
            print(f"\n⚠️  Max rounds ({max_rounds}) reached without full convergence")
            break

    return {
        "rounds": round_history,
        "convergence": convergence,
        "final_personas": all_personas,
        "total_rounds": len(round_history)
    }


def call_arbiter_synthesis(proposal, deliberation_result, model):
    """Call arbiter with full deliberation history"""
    logger.info(f"\n🔵 Arbiter synthesizing {deliberation_result['total_rounds']} rounds...")

    # Build synthesis context
    rounds_summary = []
    for round_data in deliberation_result["rounds"]:
        r_num = round_data["round"]
        outputs = round_data["outputs"]

        rounds_summary.append(f"=== ROUND {r_num} ===")
        for persona_key, output in outputs.items():
            verdict = output.get("verdict", "UNKNOWN")
            confidence = output.get("confidence", 0)
            reasoning = output.get("reasoning", "")[:200]

            rounds_summary.append(f"{persona_key}: {verdict} ({confidence}%) - {reasoning}...")

        if round_data.get("info_gathered"):
            rounds_summary.append(f"Info gathered: {len(round_data['info_gathered'])} items")

        rounds_summary.append("")

    # Check if bikeshedding was detected
    bikeshedding_note = ""
    if deliberation_result['convergence'].get('has_low_conviction_stalemate'):
        bikeshedding_note = """
⚠️  BIKESHEDDING DETECTED: Low conviction + low agreement suggests personas are debating
low-stakes details. Council was forced to converge using conviction-weighted voting.
"""

    deliberation_context = f"""ORIGINAL PROPOSAL:
{proposal}

DELIBERATION HISTORY ({deliberation_result['total_rounds']} rounds):

{chr(10).join(rounds_summary)}

CONVERGENCE STATUS:
- Agreement: {deliberation_result['convergence']['agreement_ratio']*100:.0f}%
- Dominant Verdict: {deliberation_result['convergence']['dominant_verdict']}
- Final Council Size: {len(deliberation_result['final_personas'])} personas
{bikeshedding_note}

Synthesize the multi-round deliberation into a final verdict."""

    # Call arbiter via shared library
    print("\n" + "=" * 70)
    print("🔵 ARBITER SYNTHESIS")
    print("=" * 70)

    try:
        result = call_arbiter(
            proposal=proposal,
            deliberation_context=deliberation_context,
            model=model,
            timeout=60
        )

        arbiter_verdict = result["parsed_verdict"]

        print(f"\nFinal Verdict: {arbiter_verdict.get('verdict', 'UNKNOWN')}")
        print(f"Confidence: {arbiter_verdict.get('confidence', 0)}%")
        print("\nReasoning:")
        print(arbiter_verdict.get('reasoning', 'No reasoning provided'))

        return {
            **deliberation_result['convergence'],
            "arbiter_verdict": arbiter_verdict.get('verdict'),
            "arbiter_confidence": arbiter_verdict.get('confidence'),
            "arbiter_reasoning": arbiter_verdict.get('reasoning')
        }

    except OracleAPIError as e:
        logger.warning(f"Arbiter API call failed: {e}, using convergence stats")
        print(f"\nDominant Verdict: {deliberation_result['convergence']['dominant_verdict']}")
        print(f"Agreement Level: {deliberation_result['convergence']['agreement_ratio']*100:.0f}%")
        print(f"Rounds: {deliberation_result['total_rounds']}")
        print(f"Final Council Size: {len(deliberation_result['final_personas'])} personas")

        return deliberation_result['convergence']


def main():
    parser = setup_script("Deliberative Council: Multi-Round Decision Framework")
    parser.add_argument("proposal", help="The proposal to evaluate")
    parser.add_argument(
        "--preset",
        help="Preset persona combination"
    )
    parser.add_argument(
        "--personas",
        help="Comma-separated persona list"
    )
    parser.add_argument(
        "--recruit",
        action="store_true",
        help="Use Recruiter to assemble council"
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=5,
        help="Maximum deliberation rounds (default: 5)"
    )
    parser.add_argument(
        "--convergence-threshold",
        type=float,
        default=0.7,
        help="Agreement threshold for convergence (default: 0.7)"
    )

    args = parser.parse_args()
    handle_debug(args)

    try:
        # Load library and presets
        library = load_persona_library()
        presets = load_presets()

        # Determine personas
        if args.recruit:
            if recruit_council is None:
                logger.error("Recruiter not available")
                finalize(success=False)

            logger.info("🎯 Using Recruiter to assemble council...")
            persona_keys = recruit_council(args.proposal)
        elif args.preset:
            if args.preset not in presets:
                logger.error(f"Unknown preset: {args.preset}")
                logger.error(f"Available: {', '.join(presets.keys())}")
                finalize(success=False)

            persona_keys = presets[args.preset]["personas"]
            logger.info(f"Using preset '{args.preset}': {len(persona_keys)} personas")
        elif args.personas:
            persona_keys = [p.strip() for p in args.personas.split(",")]
        else:
            # Default: comprehensive
            persona_keys = presets.get("comprehensive", {}).get("personas", ["judge", "critic", "skeptic", "oracle", "innovator"])
            logger.info(f"Using default 'comprehensive': {len(persona_keys)} personas")

        # Build persona list
        personas = [
            (key, library["personas"][key])
            for key in persona_keys
            if key in library["personas"]
        ]

        if not personas:
            logger.error("No valid personas selected")
            finalize(success=False)

        logger.info(f"\nCouncil: {len(personas)} personas + 1 Arbiter")
        logger.info(f"Personas: {', '.join(k for k, _ in personas)}")

        # Enrich context
        session_id = os.getenv("CLAUDE_SESSION_ID", "unknown")
        logger.info("\nBuilding enriched context...")

        context_result = build_council_context(args.proposal, session_id, Path(_project_root))

        if not context_result["success"]:
            logger.error(f"Context enrichment failed: {context_result['error']}")
            enriched_context = args.proposal
        else:
            enriched_context = context_result["formatted"]

        # Call Timekeeper for dynamic limits (unless user overrode)
        scripts_dir = os.path.join(_project_root, ".claude", "ops")
        timekeeper_assessment = call_timekeeper(args.proposal, scripts_dir)

        # Use Timekeeper's recommendations if available, otherwise use user args or defaults
        if timekeeper_assessment:
            max_rounds = timekeeper_assessment["max_rounds"]
            convergence_threshold = timekeeper_assessment["convergence_threshold"]
        else:
            # Fallback to user args or defaults
            max_rounds = args.max_rounds
            convergence_threshold = args.convergence_threshold

        # Run multi-round deliberation
        print("\n" + "=" * 70)
        print("🏛️  MULTI-ROUND DELIBERATIVE COUNCIL")
        print("=" * 70)
        print(f"Proposal: {args.proposal}")
        print(f"Max Rounds: {max_rounds}")
        print(f"Convergence Threshold: {convergence_threshold*100:.0f}%")
        print(f"Initial Council: {len(personas)} personas")
        if timekeeper_assessment:
            print(f"Complexity: {timekeeper_assessment['complexity']} (Risk: {timekeeper_assessment['risk']})")

        deliberation = run_deliberation(
            args.proposal,
            personas,
            enriched_context,
            max_rounds=max_rounds,
            convergence_threshold=convergence_threshold
        )

        # Arbiter synthesis
        arbiter_model = library["arbiter"]["model"]
        final_verdict = call_arbiter_synthesis(args.proposal, deliberation, arbiter_model)

        # Save deliberation results
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            deliberations_dir = Path(_project_root) / ".claude" / "memory" / "deliberations"
            deliberations_dir.mkdir(parents=True, exist_ok=True)

            result_file = deliberations_dir / f"{session_id}_{timestamp}.json"

            deliberation_record = {
                "timestamp": timestamp,
                "session_id": session_id,
                "proposal": args.proposal,
                "config": {
                    "max_rounds": args.max_rounds,
                    "convergence_threshold": args.convergence_threshold,
                    "initial_personas": [k for k, _ in personas]
                },
                "rounds": deliberation["rounds"],
                "convergence": deliberation["convergence"],
                "final_personas": [k for k, _ in deliberation["final_personas"]],
                "total_rounds": deliberation["total_rounds"],
                "final_verdict": final_verdict
            }

            with open(result_file, 'w') as f:
                json.dump(deliberation_record, f, indent=2, default=str)

            logger.info(f"Deliberation saved: {result_file}")

        except Exception as e:
            logger.warning(f"Failed to save deliberation results: {e}")

        print("\n" + "=" * 70)
        print("💡 DELIBERATION COMPLETE")
        print("=" * 70)

        finalize(success=True)

    except KeyboardInterrupt:
        print("\n\n⚠️  Council deliberation interrupted by user")
        logger.warning("User interrupted council deliberation")
        finalize(success=False)
    except Exception as e:
        logger.error(f"Council deliberation failed: {e}")
        import traceback
        traceback.print_exc()
        finalize(success=False)


if __name__ == "__main__":
    main()
