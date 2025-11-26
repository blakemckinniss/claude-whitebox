#!/usr/bin/env python3
"""
The X-Ray: Performs AST-based structural search on Python code (Classes, Functions, Imports, Decorators)
"""
import sys
import os
import ast
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


class CodeVisitor(ast.NodeVisitor):
    """AST visitor that finds and reports code structures."""

    def __init__(
        self, filename, target_type, target_name, show_details, show_decorators
    ):
        self.filename = filename
        self.target_type = target_type
        self.target_name = (
            re.compile(target_name, re.IGNORECASE) if target_name else None
        )
        self.show_details = show_details
        self.show_decorators = show_decorators
        self.results = []

    def match(self, name):
        """Check if name matches the target pattern."""
        if not self.target_name:
            return True
        return bool(self.target_name.search(name))

    def get_decorator_names(self, node):
        """Extract decorator names from a node."""
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                decorators.append(dec.func.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(
                    f"{dec.value.id}.{dec.attr}"
                    if hasattr(dec.value, "id")
                    else dec.attr
                )
        return decorators

    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        if self.target_type in ["def", "function", "all"]:
            # Check if name matches
            if self.match(node.name):
                # Get decorators
                decorators = self.get_decorator_names(node)

                # If searching for decorators, only show functions with that decorator
                if self.show_decorators and self.target_name:
                    if not any(self.target_name.search(d) for d in decorators):
                        self.generic_visit(node)
                        return

                # Get arguments
                args = []
                for arg in node.args.args:
                    args.append(arg.arg)
                if node.args.vararg:
                    args.append(f"*{node.args.vararg.arg}")
                if node.args.kwarg:
                    args.append(f"**{node.args.kwarg.arg}")

                result = {
                    "type": "function",
                    "name": node.name,
                    "args": args,
                    "decorators": decorators,
                    "lineno": node.lineno,
                    "docstring": ast.get_docstring(node) if self.show_details else None,
                }
                self.results.append(result)

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        """Visit async function definitions."""
        # Treat the same as regular functions
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        """Visit class definitions."""
        if self.target_type in ["class", "all"]:
            if self.match(node.name):
                # Get decorators
                decorators = self.get_decorator_names(node)

                # Get base classes
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(
                            f"{base.value.id}.{base.attr}"
                            if hasattr(base.value, "id")
                            else base.attr
                        )

                result = {
                    "type": "class",
                    "name": node.name,
                    "bases": bases,
                    "decorators": decorators,
                    "lineno": node.lineno,
                    "docstring": ast.get_docstring(node) if self.show_details else None,
                }
                self.results.append(result)

        self.generic_visit(node)

    def visit_Import(self, node):
        """Visit import statements."""
        if self.target_type in ["import", "all"]:
            for alias in node.names:
                if self.match(alias.name):
                    result = {
                        "type": "import",
                        "name": alias.name,
                        "alias": alias.asname,
                        "lineno": node.lineno,
                    }
                    self.results.append(result)

        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Visit from...import statements."""
        if self.target_type in ["import", "all"]:
            module = node.module or ""
            for alias in node.names:
                full_name = f"{module}.{alias.name}" if module else alias.name
                if self.match(full_name) or self.match(alias.name):
                    result = {
                        "type": "import_from",
                        "module": module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "lineno": node.lineno,
                    }
                    self.results.append(result)

        self.generic_visit(node)

    def visit_Call(self, node):
        """Visit function calls."""
        if self.target_type in ["call", "all"]:
            # Extract function name
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    func_name = f"{node.func.value.id}.{node.func.attr}"
                else:
                    func_name = node.func.attr

            if func_name and self.match(func_name):
                result = {"type": "call", "name": func_name, "lineno": node.lineno}
                self.results.append(result)

        self.generic_visit(node)


def scan_file(filepath, target_type, target_name, show_details, show_decorators):
    """Scan a single Python file for code structures."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=filepath)
        visitor = CodeVisitor(
            filepath, target_type, target_name, show_details, show_decorators
        )
        visitor.visit(tree)
        return visitor.results

    except SyntaxError as e:
        logger.debug(f"Syntax error in {filepath}: {e}")
        return []
    except Exception as e:
        logger.debug(f"Could not parse {filepath}: {e}")
        return []


def print_results(results, show_details):
    """Print search results in a formatted way."""
    if not results:
        print("\n❌ No matches found.\n")
        return

    # Group by file
    by_file = {}
    for result in results:
        filepath = result["filepath"]
        if filepath not in by_file:
            by_file[filepath] = []
        by_file[filepath].append(result)

    total = len(results)
    file_count = len(by_file)

    print(f"\n✅ Found {total} match(es) across {file_count} file(s)\n")
    print("=" * 70)

    for filepath, file_results in sorted(by_file.items()):
        print(f"\n📁 {filepath}")
        print("-" * 70)

        for result in file_results:
            result_type = result["type"]

            if result_type == "function":
                decorators_str = (
                    f" @{', @'.join(result['decorators'])}"
                    if result["decorators"]
                    else ""
                )
                print(
                    f"  🔹 DEF: {result['name']}({', '.join(result['args'])}){decorators_str}"
                )
                print(f"     📍 Line {result['lineno']}")
                if show_details and result["docstring"]:
                    doc_first_line = result["docstring"].strip().split("\n")[0]
                    print(f"     📄 {doc_first_line}")

            elif result_type == "class":
                bases_str = (
                    f" (inherits: {', '.join(result['bases'])})"
                    if result["bases"]
                    else ""
                )
                decorators_str = (
                    f" @{', @'.join(result['decorators'])}"
                    if result["decorators"]
                    else ""
                )
                print(f"  📦 CLASS: {result['name']}{bases_str}{decorators_str}")
                print(f"     📍 Line {result['lineno']}")
                if show_details and result["docstring"]:
                    doc_first_line = result["docstring"].strip().split("\n")[0]
                    print(f"     📄 {doc_first_line}")

            elif result_type == "import":
                alias_str = f" as {result['alias']}" if result["alias"] else ""
                print(f"  📥 IMPORT: {result['name']}{alias_str}")
                print(f"     📍 Line {result['lineno']}")

            elif result_type == "import_from":
                alias_str = f" as {result['alias']}" if result["alias"] else ""
                module_str = f"from {result['module']} " if result["module"] else ""
                print(f"  📥 IMPORT: {module_str}import {result['name']}{alias_str}")
                print(f"     📍 Line {result['lineno']}")

            elif result_type == "call":
                print(f"  📞 CALL: {result['name']}()")
                print(f"     📍 Line {result['lineno']}")

            print()

    print("=" * 70 + "\n")


def main():
    parser = setup_script(
        "The X-Ray: Performs AST-based structural search on Python code (Classes, Functions, Imports, Decorators)"
    )

    # Arguments
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory or file to scan (default: current directory)",
    )
    parser.add_argument(
        "--type",
        dest="search_type",
        choices=["def", "function", "class", "import", "call", "decorator", "all"],
        default="all",
        help="Type of code structure to find",
    )
    parser.add_argument("--name", help="Name pattern to search for (supports regex)")
    parser.add_argument(
        "--details", action="store_true", help="Show docstrings and additional details"
    )

    args = parser.parse_args()
    handle_debug(args)

    # Normalize path
    search_path = os.path.abspath(args.path)

    if not os.path.exists(search_path):
        logger.error(f"Path does not exist: {search_path}")
        finalize(success=False)

    print("\n" + "=" * 70)
    print("🔬 X-RAY: Structural Code Search")
    print("=" * 70)
    print(f"  Path: {search_path}")
    print(f"  Type: {args.search_type}")
    if args.name:
        print(f"  Name: {args.name}")
    print("=" * 70)

    if args.dry_run:
        logger.info("Dry-run mode: Would scan files but not actually parse")
        finalize(success=True)

    try:
        # Collect Python files
        python_files = []

        if os.path.isfile(search_path):
            if search_path.endswith(".py"):
                python_files.append(search_path)
        else:
            # Walk directory
            for root, dirs, files in os.walk(search_path):
                # Skip common directories
                dirs[:] = [
                    d
                    for d in dirs
                    if d not in [".git", "__pycache__", "node_modules", ".venv", "venv"]
                ]

                for file in files:
                    if file.endswith(".py"):
                        python_files.append(os.path.join(root, file))

        if not python_files:
            logger.warning("No Python files found in path")
            finalize(success=True)

        logger.info(f"Scanning {len(python_files)} Python file(s)...")

        # Scan all files
        all_results = []
        show_decorators = args.search_type == "decorator"

        for filepath in python_files:
            results = scan_file(
                filepath, args.search_type, args.name, args.details, show_decorators
            )
            for result in results:
                result["filepath"] = os.path.relpath(filepath, _project_root)
                all_results.append(result)

        # Print results
        print_results(all_results, args.details)

        logger.info(f"X-Ray complete: Found {len(all_results)} match(es)")

    except Exception as e:
        logger.error(f"X-Ray failed: {e}")
        import traceback

        traceback.print_exc()
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
