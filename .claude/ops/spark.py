#!/usr/bin/env python3
"""
The Synapse: Scans prompt for keywords and retrieves associated memories and protocols
"""
import sys
import os
import json
import re
import random

# Add .claude/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
# Find project root by looking for '.claude' directory
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


def query_lessons(keywords, max_results=3):
    """Scans the Pain Log for past trauma related to these keywords."""
    matches = []
    lessons_path = os.path.join(_project_root, ".claude", "memory", "__lessons.md")

    try:
        with open(lessons_path, "r") as f:
            lines = f.readlines()

        for line in lines:
            # Skip headers and empty lines
            if line.startswith("#") or not line.strip():
                continue

            # Check if any keyword appears in this line
            line_lower = line.lower()
            if any(keyword.lower() in line_lower for keyword in keywords):
                # Clean up the line
                cleaned = line.strip()
                if cleaned and cleaned not in matches:
                    matches.append(cleaned)

                if len(matches) >= max_results:
                    break

    except FileNotFoundError:
        logger.debug(f"Lessons file not found: {lessons_path}")
    except Exception as e:
        logger.debug(f"Error reading lessons: {e}")

    return matches


def extract_keywords_from_pattern(pattern):
    """Extract simple keywords from a regex pattern for lesson searching."""
    # Remove regex special characters
    keywords = (
        pattern.replace("(", "")
        .replace(")", "")
        .replace("|", " ")
        .replace("\\", "")
        .split()
    )
    # Filter out very short keywords
    return [k for k in keywords if len(k) > 3]


def main():
    parser = setup_script(
        "The Synapse: Scans prompt for keywords and retrieves associated memories and protocols"
    )

    parser.add_argument("prompt", help="The user prompt to analyze for associations")
    parser.add_argument(
        "--no-constraints",
        action="store_true",
        help="Disable random constraint injection",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output JSON only (no logging)"
    )

    args = parser.parse_args()
    handle_debug(args)

    if not args.json:
        logger.info("Firing synapses for prompt analysis...")

    if args.dry_run:
        logger.warning("⚠️  DRY RUN MODE: Would analyze prompt but not output results")
        finalize(success=True)

    try:
        # Load synapse map
        synapse_path = os.path.join(_project_root, ".claude", "memory", "__synapses.json")

        with open(synapse_path, "r") as f:
            synapses = json.load(f)

        patterns = synapses.get("patterns", {})
        random_constraints = synapses.get("random_constraints", [])
        meta = synapses.get("meta", {})

        max_associations = meta.get("max_associations", 5)
        max_memories = meta.get("max_memories", 3)
        constraint_probability = meta.get("constraint_probability", 0.10)

        prompt_lower = args.prompt.lower()

        # 1. Check Synapse Map (Static Associations)
        associations = []
        active_keywords = []
        matched_patterns = []

        for pattern, links in patterns.items():
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                matched_patterns.append(pattern)
                associations.extend(links[:max_associations])  # Limit per pattern

                # Extract keywords from pattern for lesson search
                keywords = extract_keywords_from_pattern(pattern)
                active_keywords.extend(keywords)

        # Remove duplicates while preserving order
        associations = list(dict.fromkeys(associations))[:max_associations]

        # 2. Check Pain Log (Dynamic Associations)
        memories = []
        if active_keywords:
            memories = query_lessons(active_keywords, max_results=max_memories)

        # 3. Random Constraint Injection (Lateral Thinking)
        constraint = None
        if not args.no_constraints and random_constraints:
            if random.random() < constraint_probability:
                constraint = random.choice(random_constraints)

        # 4. Build output
        output = {
            "has_associations": len(associations) > 0
            or len(memories) > 0
            or constraint is not None,
            "associations": associations,
            "memories": memories,
            "constraint": constraint,
            "matched_patterns": matched_patterns,
        }

        # Output JSON
        print(json.dumps(output, indent=2))

        if not args.json:
            if output["has_associations"]:
                logger.info(
                    f"Found {len(associations)} associations, {len(memories)} memories"
                )
                if constraint:
                    logger.info("Lateral thinking constraint injected")
            else:
                logger.info("No strong associations found for this prompt")

    except FileNotFoundError as e:
        logger.error(f"Synapse map not found: {e}")
        # Output empty associations
        print(
            json.dumps(
                {
                    "has_associations": False,
                    "associations": [],
                    "memories": [],
                    "constraint": None,
                    "matched_patterns": [],
                }
            )
        )
        finalize(success=False)

    except Exception as e:
        logger.error(f"Synapse firing failed: {e}")
        import traceback

        traceback.print_exc()
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
