#!/usr/bin/env python3
"""
The Project Manager: Manages the Definition of Done (DoD) for the current task.
"""
import sys
import os
import json
import requests

# Add scripts/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
# Find project root by looking for 'scripts' directory
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

# Punch list file location
PUNCH_LIST_FILE = os.path.join(_project_root, ".claude", "memory", "punch_list.json")


def load_punch_list():
    """Load the punch list from disk."""
    if not os.path.exists(PUNCH_LIST_FILE):
        return None

    try:
        with open(PUNCH_LIST_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load punch list: {e}")
        return None


def save_punch_list(data):
    """Save the punch list to disk."""
    try:
        os.makedirs(os.path.dirname(PUNCH_LIST_FILE), exist_ok=True)
        with open(PUNCH_LIST_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save punch list: {e}")
        return False


def generate_checklist_via_oracle(description, model):
    """Generate exhaustive checklist by consulting The Oracle."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("Missing OPENROUTER_API_KEY environment variable")
        return None

    system_prompt = """You are an Exhaustive Project Manager. You are pedantic and thorough.

The user will describe a task. Your job is to break it down into a complete, rigorous checklist.

Rules:
1. Be EXHAUSTIVE: Include tests, documentation, verification, cleanup
2. Be SPECIFIC: No vague items like "Fix the code" - be precise
3. Be ATOMIC: Each item should be a single, verifiable action
4. Include VALIDATION: Each implementation step should have a verification step
5. Cover ALL aspects: Implementation, testing, documentation, cleanup

Output format:
Return ONLY a JSON array of items. Each item is a string.
Example:
["Update models.py schemas", "Update views.py validation", "Update tests/test_users.py", "Update swagger.json", "Verify backward compatibility", "Run test suite", "Update CHANGELOG.md"]

Do NOT include any explanation or markdown. Just the JSON array."""

    logger.info("Consulting The Oracle for exhaustive checklist...")

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/claude-code/whitebox",
        }

        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Break down this task into an exhaustive, pedantic checklist:\n\n{description}",
                },
            ],
            "extra_body": {"reasoning": {"enabled": True}},
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=120,
        )
        response.raise_for_status()
        result = response.json()

        content = result["choices"][0]["message"].get("content", "")

        # Parse the JSON array from content
        # The model might wrap it in markdown, so let's extract
        content = content.strip()
        if content.startswith("```"):
            # Remove markdown code blocks
            lines = content.split("\n")
            content = "\n".join([l for l in lines if not l.startswith("```")])

        items = json.loads(content)

        if not isinstance(items, list):
            logger.error("Oracle did not return a list")
            return None

        logger.info(f"Generated {len(items)} checklist items")
        return items

    except requests.exceptions.RequestException as e:
        logger.error(f"Oracle communication failed: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Oracle response as JSON: {e}")
        logger.error(f"Response content: {content}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None


def action_init(description, model):
    """Initialize a new punch list."""
    # Check if punch list already exists
    existing = load_punch_list()
    if existing:
        logger.warning("⚠️  Punch list already exists!")
        logger.info(f"Current task: {existing.get('description', 'Unknown')}")
        logger.info(f"Progress: {existing.get('percent', 0)}%")
        user_input = input("Overwrite? (yes/no): ")
        if user_input.lower() != "yes":
            logger.info("Cancelled")
            return False

    # Generate checklist via Oracle
    items_list = generate_checklist_via_oracle(description, model)
    if not items_list:
        logger.error("Failed to generate checklist")
        return False

    # Create punch list structure
    punch_list = {
        "description": description,
        "items": [{"text": item, "done": False} for item in items_list],
        "percent": 0,
    }

    # Save to disk
    if not save_punch_list(punch_list):
        return False

    # Display the generated list
    print("\n" + "=" * 70)
    print("📋 DEFINITION OF DONE - PUNCH LIST")
    print("=" * 70)
    print(f"TASK: {description}\n")
    for i, item in enumerate(punch_list["items"], 1):
        print(f"  [ ] {i}. {item['text']}")
    print("\n" + "=" * 70)
    print(f"Total items: {len(punch_list['items'])}")
    print("Completion: 0%")
    print("=" * 70 + "\n")

    logger.info(f"Initialized punch list with {len(items_list)} items")
    return True


def action_check(index):
    """Mark an item as done."""
    punch_list = load_punch_list()
    if not punch_list:
        logger.error("No punch list exists. Run 'scope.py init' first.")
        return False

    items = punch_list["items"]

    # Validate index
    if index < 1 or index > len(items):
        logger.error(f"Invalid index {index}. Must be between 1 and {len(items)}")
        return False

    # Mark as done (convert to 0-indexed)
    item_idx = index - 1
    if items[item_idx]["done"]:
        logger.warning(f"⚠️  Item {index} is already marked as done")
    else:
        items[item_idx]["done"] = True
        logger.info(f"✅ Marked item {index} as DONE: {items[item_idx]['text']}")

    # Recalculate percentage
    done_count = sum(1 for item in items if item["done"])
    punch_list["percent"] = int((done_count / len(items)) * 100)

    # Save
    if not save_punch_list(punch_list):
        return False

    # Show progress
    print(
        f"\n📊 Progress: {done_count}/{len(items)} items complete ({punch_list['percent']}%)\n"
    )

    # Show remaining items
    remaining = [
        f"{i+1}. {item['text']}" for i, item in enumerate(items) if not item["done"]
    ]
    if remaining:
        print("Remaining items:")
        for r in remaining[:5]:  # Show first 5
            print(f"  [ ] {r}")
        if len(remaining) > 5:
            print(f"  ... and {len(remaining) - 5} more")
    else:
        print("🎉 ALL ITEMS COMPLETE! 🎉")

    print()
    return True


def action_status():
    """Show the current punch list status."""
    punch_list = load_punch_list()
    if not punch_list:
        logger.info(
            "No active punch list. Run 'scope.py init <description>' to create one."
        )
        return True

    items = punch_list["items"]
    done_count = sum(1 for item in items if item["done"])

    print("\n" + "=" * 70)
    print("📋 PUNCH LIST STATUS")
    print("=" * 70)
    print(f"TASK: {punch_list['description']}\n")

    for i, item in enumerate(items, 1):
        checkbox = "[x]" if item["done"] else "[ ]"
        print(f"  {checkbox} {i}. {item['text']}")

    print("\n" + "=" * 70)
    print(
        f"Progress: {done_count}/{len(items)} items complete ({punch_list['percent']}%)"
    )
    print("=" * 70 + "\n")

    if punch_list["percent"] == 100:
        print("✅ DEFINITION OF DONE: SATISFIED\n")
        logger.info("Task is 100% complete!")
    else:
        remaining = len(items) - done_count
        print(f"⚠️  INCOMPLETE: {remaining} item(s) remaining\n")
        logger.warning(f"Task is {punch_list['percent']}% complete. Keep grinding!")

    return True


def main():
    parser = setup_script(
        "The Project Manager: Manages the Definition of Done (DoD) for the current task."
    )

    # Custom arguments
    parser.add_argument(
        "action", choices=["init", "check", "status"], help="Action to perform"
    )
    parser.add_argument(
        "value",
        nargs="?",
        help="Value for action (description for init, index for check)",
    )
    parser.add_argument(
        "--model",
        default="google/gemini-3-pro-preview",
        help="OpenRouter model for checklist generation (default: gemini-2.0-flash-thinking)",
    )

    args = parser.parse_args()
    handle_debug(args)

    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would perform action but not save changes")
        finalize(success=True)

    try:
        success = False

        if args.action == "init":
            if not args.value:
                logger.error("'init' action requires a description")
                logger.error('Usage: scope.py init "Task description"')
                finalize(success=False)
            success = action_init(args.value, args.model)

        elif args.action == "check":
            if not args.value:
                logger.error("'check' action requires an item index")
                logger.error("Usage: scope.py check <N>")
                finalize(success=False)
            try:
                index = int(args.value)
                success = action_check(index)
            except ValueError:
                logger.error(f"Invalid index: {args.value}. Must be a number.")
                finalize(success=False)

        elif args.action == "status":
            success = action_status()

        finalize(success=success)

    except Exception as e:
        logger.error(f"Operation failed: {e}")
        finalize(success=False)


if __name__ == "__main__":
    main()
