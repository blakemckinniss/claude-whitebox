#!/usr/bin/env python3
"""
Assemble multiple expert perspectives in parallel for comprehensive decision analysis

THE COUNCIL PROTOCOL (18th Protocol)

When making major architectural decisions, don't rely on a single perspective.
Assemble The Council - multiple expert protocols that analyze the proposal
from different angles:

  • The Judge: Value/ROI assessment (Does this matter?)
  • The Critic: Assumption attack (Are you delusional?)
  • The Skeptic: Risk analysis (How will this fail?)
  • The Thinker: Sequential decomposition (How to break it down?)
  • The Oracle: External reasoning (What are the implications?)

All perspectives are gathered in parallel, then synthesized into a unified
decision matrix.
"""
import sys
import os
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add scripts/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
# Find project root by looking for 'scripts' directory
_current = _script_dir
while _current != '/':
    if os.path.exists(os.path.join(_current, 'scripts', 'lib', 'core.py')):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with scripts/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, 'scripts', 'lib'))
from core import setup_script, finalize, logger, handle_debug, check_dry_run


def consult_protocol(protocol_name, script_path, proposal, model=None):
    """
    Consult a single protocol expert.

    Returns: (protocol_name, output, success)
    """
    logger.info(f"Consulting {protocol_name}...")
    cmd = ["python3", script_path, proposal]
    if model:
        cmd.extend(["--model", model])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return (protocol_name, result.stdout, True)
        else:
            return (protocol_name, f"ERROR: {result.stderr}", False)
    except subprocess.TimeoutExpired:
        return (protocol_name, "ERROR: Timeout (60s exceeded)", False)
    except Exception as e:
        return (protocol_name, f"ERROR: {e}", False)


def main():
    parser = setup_script("Assemble multiple expert perspectives in parallel for comprehensive decision analysis")
    parser.add_argument('proposal', help="Architectural proposal or decision to analyze")
    parser.add_argument('--model', help="LLM model to use (default: gemini-3-pro-preview)")
    parser.add_argument('--skip', nargs='+', choices=['judge', 'critic', 'skeptic', 'thinker', 'oracle'],
                        help="Skip specific council members")
    parser.add_argument('--only', nargs='+', choices=['judge', 'critic', 'skeptic', 'thinker', 'oracle'],
                        help="Consult only specific members")
    parser.add_argument('--max-workers', type=int, default=5, help="Max parallel workers")

    args = parser.parse_args()
    handle_debug(args)

    # Define council members
    council_members = {
        'judge': os.path.join(_project_root, 'scripts/ops/judge.py'),
        'critic': os.path.join(_project_root, 'scripts/ops/critic.py'),
        'skeptic': os.path.join(_project_root, 'scripts/ops/skeptic.py'),
        'thinker': os.path.join(_project_root, 'scripts/ops/think.py'),
        'oracle': os.path.join(_project_root, 'scripts/ops/consult.py'),
    }

    # Filter members based on --skip or --only
    if args.only:
        active_members = {k: v for k, v in council_members.items() if k in args.only}
    elif args.skip:
        active_members = {k: v for k, v in council_members.items() if k not in args.skip}
    else:
        active_members = council_members

    logger.info(f"🏛️  Assembling The Council ({len(active_members)} members)")
    logger.info(f"📋 Proposal: {args.proposal[:100]}...")

    if args.dry_run:
        logger.warning("⚠️  DRY RUN MODE: Would consult the following members:")
        for name in active_members.keys():
            logger.warning(f"  • {name.capitalize()}")
        finalize(success=True)

    try:
        # ============================================================
        # PARALLEL CONSULTATION
        # ============================================================
        perspectives = {}

        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            # Submit all consultations
            futures = {
                executor.submit(consult_protocol, name, path, args.proposal, args.model): name
                for name, path in active_members.items()
            }

            # Collect results as they complete
            for future in as_completed(futures):
                protocol_name, output, success = future.result()
                perspectives[protocol_name] = {
                    'output': output,
                    'success': success
                }

                status = "✅" if success else "❌"
                logger.info(f"{status} {protocol_name.capitalize()} consultation complete")

        # ============================================================
        # SYNTHESIS & PRESENTATION
        # ============================================================
        print("\n" + "="*70)
        print("🏛️  THE COUNCIL'S VERDICT")
        print("="*70)
        print(f"\n📋 PROPOSAL: {args.proposal}")
        print("\n" + "-"*70 + "\n")

        # Present each perspective
        for name in ['judge', 'critic', 'skeptic', 'thinker', 'oracle']:
            if name not in perspectives:
                continue

            perspective = perspectives[name]
            icon = {
                'judge': '⚖️',
                'critic': '🥊',
                'skeptic': '🔥',
                'thinker': '🧠',
                'oracle': '🔮'
            }.get(name, '•')

            print(f"{icon} THE {name.upper()}'S PERSPECTIVE:")
            print("-" * 70)

            if perspective['success']:
                print(perspective['output'])
            else:
                print(f"⚠️  Consultation failed: {perspective['output']}")

            print("\n" + "-"*70 + "\n")

        # Summary
        successful = sum(1 for p in perspectives.values() if p['success'])
        total = len(perspectives)

        print("="*70)
        print(f"📊 COUNCIL SUMMARY: {successful}/{total} perspectives gathered")
        print("="*70)

        # ============================================================

    except Exception as e:
        logger.error(f"Council assembly failed: {e}")
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
