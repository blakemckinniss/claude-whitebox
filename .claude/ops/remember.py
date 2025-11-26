#!/usr/bin/env python3
"""
The Elephant: Manages persistent project memory (Context, Decisions, Lessons)
"""
import sys
import os
from datetime import datetime

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
from core import setup_script, finalize, logger, handle_debug, check_dry_run  # noqa: E402


def main():
    parser = setup_script(
        "The Elephant: Manages persistent project memory (Context, Decisions, Lessons)"
    )

    # Arguments
    parser.add_argument(
        "action",
        choices=["read", "add", "search"],
        default="read",
        nargs="?",
        help="Action to perform (read, add, search)",
    )
    parser.add_argument(
        "category",
        choices=["context", "decisions", "lessons", "all"],
        default="all",
        nargs="?",
        help="Memory category (context, decisions, lessons, all)",
    )
    parser.add_argument(
        "content", nargs="*", help="Content to add (required for 'add' action)"
    )

    args = parser.parse_args()
    handle_debug(args)

    # Join content if it's a list
    content_str = " ".join(args.content) if args.content else ""

    # Determine memory file paths
    memory_dir = os.path.join(_project_root, ".claude", "memory")
    memory_files = {
        "context": os.path.join(memory_dir, "__active_context.md"),
        "decisions": os.path.join(memory_dir, "__decisions.md"),
        "lessons": os.path.join(memory_dir, "__lessons.md"),
    }

    # Validate memory directory exists
    if not os.path.exists(memory_dir):
        logger.error(f"Memory directory not found: {memory_dir}")
        logger.error("Run: mkdir -p .claude/memory")
        finalize(success=False)

    if args.action == "read":
        # READ action
        if args.category == "all":
            for category, filepath in memory_files.items():
                if os.path.exists(filepath):
                    print(f"\n{'='*70}")
                    print(f"📄 {category.upper()}")
                    print("=" * 70)
                    with open(filepath, "r") as f:
                        print(f.read())
        else:
            filepath = memory_files.get(args.category)
            if not filepath or not os.path.exists(filepath):
                logger.error(f"Memory file not found: {args.category}")
                finalize(success=False)

            with open(filepath, "r") as f:
                print(f.read())

        logger.info("Memory retrieved successfully")

    elif args.action == "add":
        # ADD action
        if args.category == "all":
            logger.error(
                "Cannot add to 'all' categories. Specify: context, decisions, or lessons"
            )
            finalize(success=False)

        if not content_str:
            logger.error("Content required for 'add' action")
            logger.error('Usage: remember.py add <category> "Your content here"')
            finalize(success=False)

        if check_dry_run(args, f"add entry to {args.category}"):
            logger.info(f"Would add: {content_str}")
            finalize(success=True)

        filepath = memory_files.get(args.category)
        if not filepath:
            logger.error(f"Invalid category: {args.category}")
            finalize(success=False)

        # Create file if it doesn't exist
        if not os.path.exists(filepath):
            logger.warning(f"Creating new memory file: {filepath}")
            with open(filepath, "w") as f:
                f.write(f"# {args.category.title()}\n\n")

        # Append timestamped entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(filepath, "a") as f:
            f.write(f"\n### {timestamp}\n{content_str}\n")

        logger.info(f"Added to {args.category}: {content_str[:50]}...")
        print(f"\n✅ Memory stored in {args.category}")

    elif args.action == "search":
        # SEARCH action
        if not content_str:
            logger.error("Search query required")
            logger.error('Usage: remember.py search all "search term"')
            finalize(success=False)

        search_term = content_str.lower()
        found_results = False

        categories_to_search = (
            [args.category]
            if args.category != "all"
            else ["context", "decisions", "lessons"]
        )

        for category in categories_to_search:
            filepath = memory_files.get(category)
            if not filepath or not os.path.exists(filepath):
                continue

            with open(filepath, "r") as f:
                lines = f.readlines()

            # Search for matching lines
            matches = []
            for i, line in enumerate(lines):
                if search_term in line.lower():
                    # Include context (3 lines before and after)
                    start = max(0, i - 3)
                    end = min(len(lines), i + 4)
                    context = "".join(lines[start:end])
                    matches.append((i + 1, context))

            if matches:
                found_results = True
                print(f"\n{'='*70}")
                print(f"🔍 FOUND IN {category.upper()}")
                print("=" * 70)
                for line_num, context in matches:
                    print(f"\nLine {line_num}:")
                    print(context)
                    print("-" * 70)

        if not found_results:
            logger.warning(f"No results found for: {search_term}")
        else:
            logger.info(f"Search complete: '{search_term}'")

    finalize(success=True)


if __name__ == "__main__":
    main()
