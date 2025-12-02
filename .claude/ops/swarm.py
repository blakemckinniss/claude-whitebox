#!/usr/bin/env python3
"""
Oracle Swarm: Massive Parallel External Reasoning

Spawns 10-1000 oracles in parallel for massive cognitive throughput.
Builds on oracle.py (single-shot) and council.py (multi-round).

Usage:
  # Multi-perspective analysis (10 oracles)
  swarm.py --analyze "Should we migrate to microservices?" --personas judge,critic,skeptic,innovator,advocate

  # Hypothesis generation (20 oracles)
  swarm.py --generate 20 "Design a scalable authentication system"

  # Code review (1 oracle per file)
  swarm.py --review "src/**/*.py" --focus security

  # Test generation (100 oracles)
  swarm.py --test-cases 100 ".claude/ops/verify.py"

  # Batch consultation (custom prompts)
  swarm.py --batch 10 --custom-prompt "You are a security expert" "Review architecture"

Modes:
  --analyze: Multi-perspective analysis (default: 5 personas)
  --generate N: Generate N unique approaches/solutions
  --review PATTERN: Review files matching pattern
  --test-cases N: Generate N test cases
  --batch N: Generic batch mode (N identical prompts)
"""
import sys
import os
import glob as glob_module
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import re

# Add .claude/lib to path (minimal bootstrap, then use get_project_root)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
from core import setup_script, finalize, logger, handle_debug, get_project_root  # noqa: E402
from oracle import call_openrouter, OracleAPIError  # noqa: E402

# Project root available via get_project_root() if needed

# Default personas for analyze mode
DEFAULT_PERSONAS = ["judge", "critic", "skeptic", "innovator", "advocate"]

# Persona system prompts (imported from oracle.py logic)
PERSONAS = {
    "judge": "You are The Judge. Analyze ROI, YAGNI, and bikeshedding. Be brutal about unnecessary work.",
    "critic": "You are The Critic. Attack assumptions. Find the fatal flaw. Expose blind spots.",
    "skeptic": "You are The Skeptic. Find failure modes, security risks, and logical fallacies.",
    "innovator": "You are The Innovator. Propose creative alternatives and novel approaches.",
    "advocate": "You are The Advocate. Champion user needs and stakeholder concerns.",
    "security": "You are The Security Expert. Find vulnerabilities, injection points, and data integrity issues.",
    "performance": "You are The Performance Expert. Identify bottlenecks, scalability issues, and optimization opportunities.",
    "legal": "You are The Legal Advisor. Assess compliance, regulatory, and liability concerns.",
    "ux": "You are The UX Expert. Evaluate usability, accessibility, and user experience.",
    "data": "You are The Data Analyst. Assess data implications, analytics, and insights.",
}


def call_oracle_worker(args):
    """
    Worker function for parallel oracle invocation.

    Args:
        args: tuple of (worker_id, prompt, model)

    Returns:
        dict with worker_id, content, reasoning, success
    """
    worker_id, prompt, model = args

    try:
        # Build message
        messages = [{"role": "user", "content": prompt}]

        # Call OpenRouter
        result = call_openrouter(messages, model=model, timeout=120)

        return {
            "worker_id": worker_id,
            "content": result["content"],
            "reasoning": result["reasoning"],
            "success": True,
            "error": None
        }

    except OracleAPIError as e:
        logger.error(f"Worker {worker_id} failed: {e}")
        return {
            "worker_id": worker_id,
            "content": None,
            "reasoning": None,
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Worker {worker_id} unexpected error: {e}")
        return {
            "worker_id": worker_id,
            "content": None,
            "reasoning": None,
            "success": False,
            "error": str(e)
        }


def run_swarm(prompts, model="google/gemini-2.0-flash-thinking-exp", max_workers=50, requests_per_minute=60):
    """
    Execute oracle swarm in parallel with rate limiting.

    Args:
        prompts: List of prompt strings
        model: OpenRouter model to use
        max_workers: Maximum concurrent workers
        requests_per_minute: Rate limit (default 60/min to avoid API quota issues)

    Returns:
        List of result dicts
    """
    # Prepare worker arguments
    worker_args = [
        (i, prompt, model)
        for i, prompt in enumerate(prompts)
    ]

    # Apply safety limits
    if len(prompts) > 100:
        logger.warning(f"⚠️ Large swarm ({len(prompts)} prompts). Consider costs. Limiting to 20 workers.")
        max_workers = min(max_workers, 20)

    # Limit workers
    num_workers = min(max_workers, len(prompts))

    # Calculate delay between request batches for rate limiting
    # If we have more prompts than RPM allows, we need to pace ourselves
    min_delay = 60.0 / requests_per_minute if requests_per_minute > 0 else 0

    logger.info(f"Spawning {len(prompts)} oracles with {num_workers} workers (rate: {requests_per_minute}/min)...")

    results = []
    completed = 0
    total = len(prompts)
    last_submit_time = 0

    # Execute in parallel with rate limiting
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {}

        # Submit with rate limiting
        for args in worker_args:
            # Rate limit: ensure minimum delay between submissions
            now = time.time()
            elapsed = now - last_submit_time
            if elapsed < min_delay and last_submit_time > 0:
                time.sleep(min_delay - elapsed)

            future = executor.submit(call_oracle_worker, args)
            futures[future] = args[0]
            last_submit_time = time.time()

        # Collect results
        for future in as_completed(futures):
            worker_id = futures[future]
            result = future.result()
            results.append(result)
            completed += 1

            if result["success"]:
                print(f"✅ Worker {worker_id+1}/{total} complete")
            else:
                print(f"❌ Worker {worker_id+1}/{total} failed: {result['error']}")

    # Sort by worker_id to maintain order
    results.sort(key=lambda r: r["worker_id"])

    return results


def build_analyze_prompts(query, personas):
    """Build prompts for multi-perspective analysis"""
    prompts = []

    for persona in personas:
        if persona in PERSONAS:
            system_prompt = PERSONAS[persona]
            prompt = f"{system_prompt}\n\n{query}"
        else:
            logger.warning(f"Unknown persona: {persona}, using generic prompt")
            prompt = f"Analyze the following from the {persona} perspective:\n\n{query}"

        prompts.append(prompt)

    return prompts


def build_generate_prompts(query, count):
    """Build prompts for hypothesis generation"""
    base_prompt = f"""Generate a UNIQUE approach to the following problem. Be creative and different from common solutions.

Problem: {query}

Requirements:
- Propose a specific, actionable solution
- Explain why this approach is different
- List key tradeoffs
- Rate feasibility (1-10)
"""

    # Add variation to each prompt to encourage diversity
    variations = [
        "Focus on simplicity and minimalism.",
        "Focus on scalability and performance.",
        "Focus on security and reliability.",
        "Focus on developer experience.",
        "Focus on cost optimization.",
        "Focus on rapid iteration.",
        "Focus on long-term maintainability.",
        "Focus on user experience.",
        "Focus on data integrity.",
        "Focus on backwards compatibility.",
    ]

    prompts = []
    for i in range(count):
        variation = variations[i % len(variations)]
        prompt = f"{base_prompt}\n{variation}"
        prompts.append(prompt)

    return prompts


def build_review_prompts(file_pattern, focus="security"):
    """Build prompts for code review"""
    # Expand glob pattern
    files = glob_module.glob(file_pattern, recursive=True)

    if not files:
        logger.warning(f"No files matched pattern: {file_pattern}")
        return []

    logger.info(f"Found {len(files)} files to review")

    prompts = []
    for file_path in files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            prompt = f"""Review the following code for {focus} issues:

File: {file_path}

```
{content}
```

Provide:
1. List of issues found (with line numbers if possible)
2. Severity rating (CRITICAL/HIGH/MEDIUM/LOW)
3. Recommended fixes
"""
            prompts.append(prompt)

        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            continue

    return prompts


def build_test_prompts(target, count):
    """Build prompts for test case generation"""
    # Read target if it's a file
    if os.path.isfile(target):
        try:
            with open(target, 'r') as f:
                target_content = f.read()
            context = f"File: {target}\n\n```\n{target_content}\n```"
        except Exception as e:
            logger.warning(f"Could not read {target}: {e}")
            context = f"Target: {target}"
    else:
        context = f"Target: {target}"

    # Test categories
    categories = [
        ("happy-path", "Test normal, expected usage"),
        ("edge-case", "Test boundary conditions and unusual inputs"),
        ("error-handling", "Test error conditions and exception handling"),
        ("integration", "Test integration with other components"),
    ]

    prompts = []
    for i in range(count):
        category_name, category_desc = categories[i % len(categories)]

        prompt = f"""Generate a UNIQUE test case for the following:

{context}

Test Category: {category_name}
Focus: {category_desc}

Provide:
1. Test function name
2. Test scenario description
3. Setup/teardown requirements
4. Assertions to check
5. Expected behavior

Make this test different from common test patterns.
"""
        prompts.append(prompt)

    return prompts


def synthesize_analyze_results(results, personas):
    """Aggregate multi-perspective analysis"""
    print("\n" + "="*70)
    print("📊 MULTI-PERSPECTIVE ANALYSIS")
    print("="*70)

    successful = [r for r in results if r["success"]]

    print(f"\nOracles: {len(successful)}/{len(results)} successful")
    print(f"Personas: {', '.join(personas)}\n")

    # Display each perspective
    for i, result in enumerate(successful):
        persona = personas[i] if i < len(personas) else f"Oracle {i+1}"
        print(f"\n{'─'*70}")
        print(f"🎭 {persona.upper()}")
        print(f"{'─'*70}")
        print(result["content"])

    print("\n" + "="*70)


def synthesize_generate_results(results):
    """Aggregate hypothesis generation"""
    print("\n" + "="*70)
    print("💡 GENERATED APPROACHES")
    print("="*70)

    successful = [r for r in results if r["success"]]

    print(f"\nGenerated: {len(successful)}/{len(results)} unique approaches\n")

    # Display each approach
    for i, result in enumerate(successful, 1):
        print(f"\n{'─'*70}")
        print(f"Approach {i}")
        print(f"{'─'*70}")
        print(result["content"])

    print("\n" + "="*70)


def synthesize_review_results(results, files):
    """Aggregate code review findings"""
    print("\n" + "="*70)
    print("🔍 CODE REVIEW RESULTS")
    print("="*70)

    successful = [r for r in results if r["success"]]

    print(f"\nReviewed: {len(successful)}/{len(results)} files\n")

    # Extract severity counts
    severity_pattern = re.compile(r'\b(CRITICAL|HIGH|MEDIUM|LOW)\b', re.IGNORECASE)
    severity_counts = Counter()

    for result in successful:
        matches = severity_pattern.findall(result["content"])
        for match in matches:
            severity_counts[match.upper()] += 1

    # Display summary
    if severity_counts:
        print("Severity Breakdown:")
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                print(f"  {severity}: {count}")
        print()

    # Display findings per file
    for i, result in enumerate(successful):
        file_path = files[i] if i < len(files) else f"File {i+1}"
        print(f"\n{'─'*70}")
        print(f"📄 {file_path}")
        print(f"{'─'*70}")
        print(result["content"])

    print("\n" + "="*70)


def synthesize_test_results(results):
    """Aggregate test case generation"""
    print("\n" + "="*70)
    print("🧪 GENERATED TEST CASES")
    print("="*70)

    successful = [r for r in results if r["success"]]

    print(f"\nGenerated: {len(successful)}/{len(results)} test cases\n")

    # Group by category (if mentioned in output)
    categories = {
        "happy-path": [],
        "edge-case": [],
        "error-handling": [],
        "integration": [],
        "other": []
    }

    for result in successful:
        content = result["content"].lower()
        categorized = False
        for category in categories:
            if category in content:
                categories[category].append(result["content"])
                categorized = True
                break
        if not categorized:
            categories["other"].append(result["content"])

    # Display by category
    for category, tests in categories.items():
        if tests:
            print(f"\n{'─'*70}")
            print(f"Category: {category.upper()} ({len(tests)} tests)")
            print(f"{'─'*70}")
            for i, test in enumerate(tests, 1):
                print(f"\n--- Test {i} ---")
                print(test)

    print("\n" + "="*70)


def main():
    parser = setup_script("Oracle Swarm: Massive Parallel External Reasoning")

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--analyze",
        metavar="QUERY",
        help="Multi-perspective analysis mode"
    )
    mode_group.add_argument(
        "--generate",
        type=int,
        metavar="COUNT",
        help="Hypothesis generation mode (generate COUNT unique approaches)"
    )
    mode_group.add_argument(
        "--review",
        metavar="PATTERN",
        help="Code review mode (review files matching glob pattern)"
    )
    mode_group.add_argument(
        "--test-cases",
        type=int,
        metavar="COUNT",
        help="Test generation mode (generate COUNT test cases)"
    )
    mode_group.add_argument(
        "--batch",
        type=int,
        metavar="COUNT",
        help="Generic batch mode (run COUNT identical prompts)"
    )

    # Input/query
    parser.add_argument(
        "query",
        nargs="?",
        help="Query/target for the swarm operation"
    )

    # Mode-specific options
    parser.add_argument(
        "--personas",
        help="Comma-separated persona list (for --analyze mode)"
    )
    parser.add_argument(
        "--focus",
        default="security",
        help="Review focus (for --review mode, default: security)"
    )
    parser.add_argument(
        "--custom-prompt",
        help="Custom system prompt (for --batch mode)"
    )

    # Execution options
    parser.add_argument(
        "--model",
        default="google/gemini-2.0-flash-thinking-exp",
        help="OpenRouter model to use (default: gemini-2.0-flash-thinking-exp)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=50,
        help="Maximum concurrent workers (default: 50)"
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=60,
        help="Requests per minute rate limit (default: 60)"
    )

    args = parser.parse_args()
    handle_debug(args)

    # Validate arguments
    if not args.query and not args.review and not args.analyze:
        parser.error("Query required unless using --review or --analyze mode")

    # Dry run check
    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would execute swarm with following config:")
        if args.analyze:
            logger.info("Mode: analyze")
            logger.info(f"Query: {args.analyze}")
            logger.info(f"Personas: {args.personas or ', '.join(DEFAULT_PERSONAS)}")
        elif args.generate:
            logger.info("Mode: generate")
            logger.info(f"Count: {args.generate}")
            logger.info(f"Query: {args.query}")
        elif args.review:
            logger.info("Mode: review")
            logger.info(f"Pattern: {args.review}")
            logger.info(f"Focus: {args.focus}")
        elif args.test_cases:
            logger.info("Mode: test-cases")
            logger.info(f"Count: {args.test_cases}")
            logger.info(f"Target: {args.query}")
        elif args.batch:
            logger.info("Mode: batch")
            logger.info(f"Count: {args.batch}")
            logger.info(f"Query: {args.query}")

        logger.info(f"Model: {args.model}")
        logger.info(f"Max workers: {args.max_workers}")
        finalize(success=True)

    try:
        # Build prompts based on mode
        if args.analyze:
            query = args.analyze
            personas = args.personas.split(",") if args.personas else DEFAULT_PERSONAS
            prompts = build_analyze_prompts(query, personas)
            mode = "analyze"
            mode_data = {"personas": personas, "files": None}

        elif args.generate:
            count = args.generate
            query = args.query
            prompts = build_generate_prompts(query, count)
            mode = "generate"
            mode_data = {"personas": None, "files": None}

        elif args.review:
            pattern = args.review
            prompts = build_review_prompts(pattern, args.focus)
            files = glob_module.glob(pattern, recursive=True)
            mode = "review"
            mode_data = {"personas": None, "files": files}

        elif args.test_cases:
            count = args.test_cases
            target = args.query
            prompts = build_test_prompts(target, count)
            mode = "test-cases"
            mode_data = {"personas": None, "files": None}

        elif args.batch:
            count = args.batch
            query = args.query

            # Build batch prompts (all identical or with custom prompt)
            if args.custom_prompt:
                base_prompt = f"{args.custom_prompt}\n\n{query}"
            else:
                base_prompt = query

            prompts = [base_prompt] * count
            mode = "batch"
            mode_data = {"personas": None, "files": None}

        if not prompts:
            logger.error("No prompts generated. Check your inputs.")
            finalize(success=False)

        # Execute swarm
        print(f"\n🐝 Spawning {len(prompts)} oracles...")
        results = run_swarm(
            prompts,
            model=args.model,
            max_workers=args.max_workers,
            requests_per_minute=args.rate_limit
        )

        # Synthesize results
        if mode == "analyze":
            synthesize_analyze_results(results, mode_data["personas"])
        elif mode == "generate":
            synthesize_generate_results(results)
        elif mode == "review":
            synthesize_review_results(results, mode_data["files"])
        elif mode == "test-cases":
            synthesize_test_results(results)
        elif mode == "batch":
            # Generic output for batch mode
            print("\n" + "="*70)
            print("📦 BATCH RESULTS")
            print("="*70)
            successful = [r for r in results if r["success"]]
            print(f"\nCompleted: {len(successful)}/{len(results)}\n")
            for i, result in enumerate(successful, 1):
                print(f"\n{'─'*70}")
                print(f"Oracle {i}")
                print(f"{'─'*70}")
                print(result["content"])
            print("\n" + "="*70)

        # Summary
        successful_count = sum(1 for r in results if r["success"])
        failed_count = len(results) - successful_count

        print(f"\n✅ Swarm complete: {successful_count} successful, {failed_count} failed")

        finalize(success=True)

    except OracleAPIError as e:
        logger.error(f"Oracle API error: {e}")
        finalize(success=False)
    except Exception as e:
        logger.error(f"Swarm execution failed: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        finalize(success=False)


if __name__ == "__main__":
    main()
