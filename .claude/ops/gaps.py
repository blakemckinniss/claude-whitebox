#!/usr/bin/env python3
"""
The Void Hunter: Scans code for missing functionality, stubs, and logical gaps.
"""
import sys
import os
import re
import requests

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

# Stub patterns to detect incomplete code
STUB_PATTERNS = [
    (r"#\s*TODO", "TODO comment"),
    (r"#\s*FIXME", "FIXME comment"),
    (r"def\s+\w+\([^)]*\):\s*pass\s*$", "Function stub (pass)"),
    (r"def\s+\w+\([^)]*\):\s*\.\.\.\s*$", "Function stub (...)"),
    (r"raise\s+NotImplementedError", "NotImplementedError"),
    (r"return\s+None\s*#.*stub", "Stub return"),
]


def hunt_stubs(file_path):
    """Scan a file for stub patterns."""
    stubs_found = []

    try:
        with open(file_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                for pattern, description in STUB_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        stubs_found.append(
                            {
                                "line": line_num,
                                "type": description,
                                "content": line.strip(),
                            }
                        )
    except Exception as e:
        logger.error(f"Failed to scan {file_path}: {e}")
        return []

    return stubs_found


def analyze_gaps_via_oracle(file_path, model):
    """Analyze code for logical gaps using The Oracle."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("Missing OPENROUTER_API_KEY environment variable")
        return None

    # Read the file content
    try:
        with open(file_path, "r") as f:
            code_content = f.read()
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return None

    system_prompt = """You are The Void Hunter. You analyze code for what is MISSING, not what exists.

The user will provide code. Your job is to find:

1. **CRUD Asymmetry:** If there's a Create, is there a Delete? If there's a Read, is there a Write?
2. **Error Handling Gaps:** Are there operations that can fail but have no try/except? Are exceptions caught but ignored?
3. **Config Hardcoding:** Are there magic numbers, hardcoded paths, or constants that should be env vars?
4. **Missing User Feedback:** Do operations succeed/fail silently? Are there no logs, no return values, no status indicators?

Output format:
## 🕳️ GAPS DETECTED

### CRUD Asymmetry
[List operations that exist without their complement]

### Error Handling Gaps
[List operations that can fail but have no error handling]

### Config Hardcoding
[List hardcoded values that should be configurable]

### Missing Feedback
[List operations that provide no feedback on success/failure]

If no gaps found, say "✅ NO GAPS DETECTED"

Be thorough. Be pedantic. The goal is to find what SHOULD be there but ISN'T."""

    logger.info("Consulting The Oracle for gap analysis...")

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
                    "content": f"Analyze this code for gaps:\n\n```python\n{code_content}\n```",
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
        return content

    except requests.exceptions.RequestException as e:
        logger.error(f"Oracle communication failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None


def main():
    parser = setup_script(
        "The Void Hunter: Scans code for missing functionality, stubs, and logical gaps."
    )

    # Custom arguments
    parser.add_argument("target", help="Python file to scan for gaps")
    parser.add_argument(
        "--model",
        default="google/gemini-3-pro-preview",
        help="OpenRouter model for gap analysis (default: gemini-3-pro-preview)",
    )
    parser.add_argument(
        "--stub-only",
        action="store_true",
        help="Only hunt for stubs, skip Oracle analysis",
    )

    args = parser.parse_args()
    handle_debug(args)

    logger.info(f"Scanning {args.target} for voids...")

    if not os.path.exists(args.target):
        logger.error(f"File not found: {args.target}")
        finalize(success=False)

    if not args.target.endswith(".py"):
        logger.error("Only Python files are supported")
        finalize(success=False)

    try:
        # Phase 1: Stub Hunting
        logger.info("🔍 Phase 1: Stub Hunting")
        stubs = hunt_stubs(args.target)

        if stubs:
            print("\n" + "=" * 70)
            print("🚨 STUBS DETECTED")
            print("=" * 70)
            for stub in stubs:
                print(f"  Line {stub['line']}: {stub['type']}")
                print(f"    → {stub['content']}")
            print("=" * 70)
            print(f"Total stubs: {len(stubs)}\n")
        else:
            logger.info("✅ No stubs detected")

        # Phase 2: Logical Gap Analysis (unless --stub-only)
        if not args.stub_only:
            logger.info("🔍 Phase 2: Logical Gap Analysis")
            gap_analysis = analyze_gaps_via_oracle(args.target, args.model)

            if gap_analysis:
                print("\n" + "=" * 70)
                print("🕳️ ORACLE GAP ANALYSIS")
                print("=" * 70)
                print(gap_analysis)
                print("=" * 70 + "\n")
            else:
                logger.warning("⚠️  Oracle analysis failed")

        # Summary
        has_issues = len(stubs) > 0
        if has_issues:
            logger.warning(
                f"⚠️  Completeness check FAILED: {len(stubs)} stub(s) detected"
            )
            finalize(success=False)
        else:
            logger.info("✅ Completeness check PASSED")

    except Exception as e:
        logger.error(f"Operation failed: {e}")
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
