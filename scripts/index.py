#!/usr/bin/env python3
"""
Script Registry Generator - Auto-indexes all scripts in the arsenal.

Scans scripts/ directory and generates a markdown table of available tools.
"""
import os
import ast
from pathlib import Path

ROOT_DIR = Path(__file__).parent
OUTPUT_FILE = ROOT_DIR.parent / ".claude" / "skills" / "tool_index.md"
SCRIPT_DIR = ROOT_DIR


def get_docstring(filepath):
    """Extract docstring from Python file"""
    try:
        with open(filepath, "r") as f:
            tree = ast.parse(f.read())
        docstring = ast.get_docstring(tree)
        if docstring:
            # Return first line only
            return docstring.split('\n')[0].strip()
        return "No description provided"
    except Exception as e:
        return f"Error parsing: {e}"


def get_bash_description(filepath):
    """Extract description from bash script comments"""
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
            # Look for first comment after shebang
            for line in lines[1:6]:  # Check first 5 lines
                line = line.strip()
                if line.startswith('#') and not line.startswith('#!'):
                    return line.lstrip('#').strip()
        return "No description provided"
    except:
        return "Error reading file"


def main():
    print(f"🔍 Scanning {SCRIPT_DIR}...")

    scripts = []

    # Walk through scripts directory
    for root, dirs, files in os.walk(SCRIPT_DIR):
        # Skip lib directory
        if 'lib' in root:
            continue

        for file in files:
            # Skip meta scripts
            if file in ["scaffold.py", "index.py", "__init__.py"]:
                continue

            filepath = Path(root) / file
            rel_path = filepath.relative_to(ROOT_DIR.parent)

            if file.endswith(".py"):
                description = get_docstring(filepath)
                scripts.append((str(rel_path), description))
            elif file.endswith(".sh"):
                description = get_bash_description(filepath)
                scripts.append((str(rel_path), description))

    # Sort by path
    scripts.sort()

    # Ensure output directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Write index
    with open(OUTPUT_FILE, "w") as f:
        f.write("# 🛠️ Script Registry\n\n")
        f.write("Auto-generated index of available tools in the arsenal.\n\n")
        f.write(f"**Total scripts:** {len(scripts)}\n\n")
        f.write("| Script | Description |\n")
        f.write("|:-------|:------------|\n")

        for path, desc in scripts:
            f.write(f"| `{path}` | {desc} |\n")

        f.write("\n---\n")
        f.write("*Last updated by `scripts/index.py`*\n")

    print(f"✅ Generated registry: {OUTPUT_FILE}")
    print(f"📊 Indexed {len(scripts)} scripts")


if __name__ == "__main__":
    main()
