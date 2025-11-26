#!/usr/bin/env python3
"""
The Probe: Introspects Python modules/objects to reveal the ACTUAL runtime API
"""
import sys
import os
import importlib
import inspect
import re

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


def main():
    parser = setup_script(
        "The Probe: Introspects Python modules/objects to reveal the ACTUAL runtime API"
    )

    # Arguments
    parser.add_argument(
        "target",
        help="Module or object to inspect (e.g., 'json', 'requests.models.Response', 'os.path')",
    )
    parser.add_argument(
        "--grep", help="Filter attributes by pattern (case-insensitive)"
    )
    parser.add_argument(
        "--show-dunder",
        action="store_true",
        help="Include __dunder__ methods in output",
    )

    args = parser.parse_args()
    handle_debug(args)

    # Dry-run doesn't apply here (read-only operation)
    if args.dry_run:
        logger.info("Dry-run mode has no effect (read-only operation)")

    try:
        # Parse target path (e.g., "os.path" -> module "os", attribute "path")
        parts = args.target.split(".")
        module_name = parts[0]

        logger.info(f"Importing module: {module_name}")

        # Import the base module
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            logger.error(f"Failed to import '{module_name}': {e}")
            logger.error("Make sure the module is installed: pip install <module>")
            finalize(success=False)

        # Navigate to nested attributes if needed
        obj = module
        obj_path = module_name

        for attr_name in parts[1:]:
            try:
                obj = getattr(obj, attr_name)
                obj_path += f".{attr_name}"
            except AttributeError:
                logger.error(f"Attribute '{attr_name}' not found in {obj_path}")
                logger.error(
                    f"Available attributes: {', '.join([a for a in dir(obj) if not a.startswith('_')])[:200]}"
                )
                finalize(success=False)

        # Header
        print("\n" + "=" * 70)
        print(f"🔬 PROBE RESULTS: {args.target}")
        print("=" * 70)

        # Show version if available
        if hasattr(obj, "__version__"):
            print(f"\n📦 Version: {obj.__version__}")
        elif hasattr(module, "__version__"):
            print(f"\n📦 Module Version: {module.__version__}")

        # Show type
        print(f"🔖 Type: {type(obj).__name__}")
        print(f"🔖 Full Type: {type(obj)}")

        # If it's a callable, show signature and docstring
        if callable(obj):
            print("\n📋 SIGNATURE:")
            try:
                sig = inspect.signature(obj)
                print(f"  {args.target}{sig}")
            except (ValueError, TypeError):
                print("  (signature unavailable)")

            if obj.__doc__:
                print("\n📖 DOCSTRING:")
                # Print first 500 chars of docstring
                doc = obj.__doc__.strip()
                if len(doc) > 500:
                    print(f"  {doc[:500]}...")
                else:
                    print(f"  {doc}")

        # Get all attributes
        all_attrs = dir(obj)

        # Filter out dunder methods unless requested
        if not args.show_dunder:
            attrs = [
                a for a in all_attrs if not (a.startswith("__") and a.endswith("__"))
            ]
        else:
            attrs = all_attrs

        # Apply grep filter if provided
        if args.grep:
            pattern = re.compile(args.grep, re.IGNORECASE)
            attrs = [a for a in attrs if pattern.search(a)]

        # Categorize attributes
        methods = []
        properties = []
        other = []

        for attr_name in attrs:
            try:
                attr = getattr(obj, attr_name)
                if callable(attr):
                    # Try to get signature
                    try:
                        sig = inspect.signature(attr)
                        methods.append((attr_name, str(sig)))
                    except (ValueError, TypeError):
                        methods.append((attr_name, "(...)"))
                elif isinstance(inspect.getattr_static(obj, attr_name), property):
                    properties.append(attr_name)
                else:
                    other.append(attr_name)
            except Exception:
                # Some attributes may not be accessible
                other.append(attr_name)

        # Print results
        if methods:
            print(f"\n🔧 METHODS ({len(methods)}):")
            for name, sig in sorted(methods):
                print(f"  • {name}{sig}")

        if properties:
            print(f"\n🏷️  PROPERTIES ({len(properties)}):")
            for name in sorted(properties):
                print(f"  • {name}")

        if other:
            print(f"\n📦 ATTRIBUTES ({len(other)}):")
            for name in sorted(other):
                print(f"  • {name}")

        # Summary
        total = len(methods) + len(properties) + len(other)
        print(f"\n{'='*70}")
        print(f"✅ Found {total} attributes")
        if args.grep:
            print(f"   (filtered by: '{args.grep}')")
        if not args.show_dunder:
            print("   (excluding __dunder__ methods - use --show-dunder to see them)")
        print("=" * 70 + "\n")

        logger.info(f"Probe complete: {args.target}")

    except Exception as e:
        logger.error(f"Probe failed: {e}")
        import traceback

        traceback.print_exc()
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
