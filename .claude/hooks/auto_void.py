#!/usr/bin/env python3
"""
Auto-Void Stop Hook: Automatically runs void.py on modified production files

Triggers: Stop lifecycle
Policy: Confidence-based enforcement
- CERTAINTY (71-85%): MANDATORY void check with warnings
- TRUSTED (86-94%): OPTIONAL void check (silent unless issues)
- Other tiers: No action

Philosophy: If you're manually requesting void after every task completion,
it should be automated. This hook ensures completeness checks happen
automatically when confidence is in the "production work but need gates" range.
"""
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import load_session_state, get_confidence_tier

# Production zones that require void checks
PRODUCTION_ZONES = [
    "scripts/ops/",
    "scripts/lib/",
    ".claude/hooks/",
]

# Confidence tier policies
TIER_POLICIES = {
    "IGNORANCE": None,  # No action
    "HYPOTHESIS": None,  # No action
    "WORKING": None,  # No action
    "CERTAINTY": "mandatory",  # Always check, always report
    "TRUSTED": "optional",  # Check but only report issues
    "EXPERT": None,  # No action
}


def parse_transcript(transcript_path: str) -> List[Dict]:
    """Parse JSONL transcript file."""
    messages = []
    try:
        with open(transcript_path, "r") as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
    except FileNotFoundError:
        print(
            f"⚠️  WARNING: Transcript file not found: {transcript_path}",
            file=sys.stderr,
        )
        return []
    except json.JSONDecodeError as e:
        print(
            f"⚠️  WARNING: Transcript file corrupted: {e} - completeness checks skipped",
            file=sys.stderr,
        )
        return []
    return messages


def extract_modified_python_files(
    transcript: List[Dict], project_root: Path
) -> List[Path]:
    """
    Extract Python files modified via Write/Edit tools in production zones.

    Returns:
        List of absolute paths to modified Python files in production zones
    """
    modified_files = set()

    for entry in transcript:
        if entry.get("type") != "assistant":
            continue

        message = entry.get("message", {})
        content = message.get("content", [])

        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict):
                continue

            # Check for tool use
            if block.get("type") == "tool_use":
                tool_name = block.get("name", "")
                tool_input = block.get("input", {})

                # Write or Edit operations
                if tool_name in ["Write", "Edit"]:
                    file_path = tool_input.get("file_path")
                    if not file_path:
                        continue

                    # Convert to Path and resolve
                    path = Path(file_path)
                    if not path.is_absolute():
                        path = project_root / path

                    # Filter: Only Python files
                    if path.suffix != ".py":
                        continue

                    # Filter: Only production zones
                    try:
                        relative = path.relative_to(project_root)
                        rel_str = str(relative)

                        is_production = any(
                            rel_str.startswith(zone) for zone in PRODUCTION_ZONES
                        )

                        if is_production:
                            modified_files.add(path)
                    except ValueError:
                        # Path is outside project root
                        continue

    return sorted(list(modified_files))


def run_void_check(
    file_path: Path, project_root: Path, timeout: int = 30
) -> Optional[Dict]:
    """
    Run void.py on a file (stub-only mode to avoid Oracle costs).

    Args:
        file_path: Path to file to check
        project_root: Project root directory
        timeout: Subprocess timeout in seconds (default: 30)

    Returns:
        Dict with results or None if check failed:
        {
            "file": Path,
            "clean": bool,
            "stub_count": int,
            "stubs": List[str]  # Formatted stub descriptions
        }
    """
    void_script = project_root / "scripts" / "ops" / "void.py"
    if not void_script.exists():
        # CRITICAL: void.py is missing - warn to stderr
        print(
            f"⚠️  WARNING: void.py not found at {void_script} - completeness checks disabled",
            file=sys.stderr,
        )
        return None

    try:
        result = subprocess.run(
            [sys.executable, str(void_script), str(file_path), "--stub-only"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(project_root),
        )

        # Parse output for stub information
        stubs = []
        stub_count = 0

        for line in result.stdout.split("\n"):
            # Match stub detection lines like "  Line 42: TODO comment"
            if line.strip().startswith("Line "):
                stubs.append(line.strip())
                stub_count += 1
            # Match total stub count line
            elif "Total stubs:" in line:
                try:
                    stub_count = int(line.split(":")[-1].strip())
                except ValueError:
                    pass

        return {
            "file": file_path,
            "clean": result.returncode == 0,
            "stub_count": stub_count,
            "stubs": stubs,
        }

    except subprocess.TimeoutExpired:
        print(
            f"⚠️  WARNING: void.py timed out on {file_path.name} (>{timeout}s) - skipping",
            file=sys.stderr,
        )
        return None
    except subprocess.SubprocessError as e:
        print(
            f"⚠️  WARNING: void.py failed on {file_path.name}: {e}",
            file=sys.stderr,
        )
        return None


def format_results(
    results: List[Dict], policy: str, confidence: int, tier_name: str
) -> str:
    """Format void check results for user display."""
    if not results:
        return ""

    # Filter based on policy
    if policy == "optional":
        # Only show files with issues
        results = [r for r in results if not r["clean"]]
        if not results:
            return ""  # All clean, silent success

    output = [f"\n🔍 Auto-Void Check ({tier_name} tier, {confidence}% confidence):\n"]

    for result in results:
        file_path = result["file"]
        clean = result["clean"]
        stub_count = result["stub_count"]
        stubs = result["stubs"]

        # Relative path for readability
        try:
            rel_path = file_path.relative_to(Path.cwd())
        except ValueError:
            rel_path = file_path

        if clean:
            output.append(f"   ✅ {rel_path} - Clean")
        else:
            output.append(f"   ⚠️  {rel_path} - {stub_count} stub(s) detected")
            for stub in stubs[:5]:  # Limit to first 5 stubs
                output.append(f"       {stub}")
            if len(stubs) > 5:
                output.append(f"       ... and {len(stubs) - 5} more")

    if policy == "mandatory":
        output.append(
            "\n💡 Tip: Run `void.py <file>` with full Oracle analysis for deeper inspection"
        )

    return "\n".join(output)


def main():
    """Main hook execution."""
    # Load input
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # Invalid input, exit silently

    session_id = input_data.get("session_id", "unknown")
    transcript_path = input_data.get("transcript_path", "")
    project_root = Path(input_data.get("cwd", "."))

    if not transcript_path or not Path(transcript_path).exists():
        sys.exit(0)

    # Load session state to get confidence
    state = load_session_state(session_id)
    if not state:
        # Default to CERTAINTY policy (safe fallback)
        confidence = 75
        tier_name = "CERTAINTY"
        print(
            f"ℹ️  INFO: Session state not found, using default policy (CERTAINTY, 75%)",
            file=sys.stderr,
        )
    else:
        confidence = state.get("confidence", 0)
        tier_name, _ = get_confidence_tier(confidence)

    # Check policy for current tier
    policy = TIER_POLICIES.get(tier_name)
    if policy is None:
        # No action for this tier
        sys.exit(0)

    # Parse transcript and extract modified files
    transcript = parse_transcript(transcript_path)
    modified_files = extract_modified_python_files(transcript, project_root)

    if not modified_files:
        # No production Python files modified
        sys.exit(0)

    # Run void checks on all modified files
    results = []
    for file_path in modified_files:
        result = run_void_check(file_path, project_root)
        if result:
            results.append(result)

    if not results:
        # All void checks failed (script missing, errors, etc.)
        sys.exit(0)

    # Format and display results
    output = format_results(results, policy, confidence, tier_name)
    if output:
        print(output)

    # Always exit 0 (Stop hooks don't block)
    sys.exit(0)


if __name__ == "__main__":
    main()
