#!/usr/bin/env python3
"""
Debt Tracker Hook: Automatically detects technical debt in code modifications

Parses transcript for Write/Edit tool calls and extracts technical debt patterns:
- TODO, FIXME, HACK, XXX comments
- Stub implementations (pass, ..., NotImplementedError)
- Incomplete error handling

Appends findings to .claude/memory/debt_ledger.jsonl for persistent tracking.
"""
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timezone


# Debt patterns to detect (type -> regex pattern)
DEBT_PATTERNS = {
    "TODO": r"#\s*TODO[:\s](.+?)(?:\n|$)",
    "FIXME": r"#\s*FIXME[:\s](.+?)(?:\n|$)",
    "HACK": r"#\s*HACK[:\s](.+?)(?:\n|$)",
    "XXX": r"#\s*XXX[:\s](.+?)(?:\n|$)",
    "STUB_PASS": r"^\s*pass\s*(?:#.*)?$",
    "STUB_ELLIPSIS": r"^\s*\.\.\.\s*(?:#.*)?$",
    "STUB_NOT_IMPL": r"raise\s+NotImplementedError",
}


def parse_transcript(transcript_path: str) -> list[dict]:
    """Parse JSONL transcript file."""
    messages = []
    try:
        with open(transcript_path, "r") as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return messages


def extract_tool_calls(messages: list[dict]) -> list[dict]:
    """
    Extract Write/Edit tool calls from assistant messages.

    Returns list of dicts: {"type": "Write"|"Edit", "file_path": str, "content": str}
    """
    tool_calls = []

    for entry in messages:
        if entry.get("type") != "assistant":
            continue

        message = entry.get("message", {})
        content = message.get("content", [])

        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict):
                continue

            block_type = block.get("type")

            # Write tool
            if block_type == "tool_use" and block.get("name") == "Write":
                params = block.get("input", {})
                tool_calls.append(
                    {
                        "type": "Write",
                        "file_path": params.get("file_path", ""),
                        "content": params.get("content", ""),
                    }
                )

            # Edit tool
            elif block_type == "tool_use" and block.get("name") == "Edit":
                params = block.get("input", {})
                # For Edit, we only care about the new_string content
                tool_calls.append(
                    {
                        "type": "Edit",
                        "file_path": params.get("file_path", ""),
                        "content": params.get("new_string", ""),
                    }
                )

    return tool_calls


def detect_debt(content: str) -> list[dict]:
    """
    Detect debt patterns in code content.

    Returns list of dicts: {"type": str, "context": str, "line": int}
    """
    findings = []
    lines = content.split("\n")

    for line_num, line in enumerate(lines, start=1):
        for debt_type, pattern in DEBT_PATTERNS.items():
            matches = re.finditer(pattern, line, re.MULTILINE)
            for match in matches:
                # Extract context (the comment text for comments, the line itself for stubs)
                if debt_type.startswith("STUB_"):
                    context = line.strip()
                else:
                    # For comment patterns, group(1) has the comment text
                    context = match.group(1).strip() if match.groups() else line.strip()

                findings.append(
                    {
                        "type": debt_type,
                        "context": context[:200],  # Limit to 200 chars
                        "line": line_num,
                    }
                )

    return findings


def append_to_ledger(ledger_path: Path, entries: list[dict]):
    """Append debt entries to the JSONL ledger."""
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    with open(ledger_path, "a") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def main():
    """Main hook execution."""
    # Load input
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    # Get required paths
    transcript_path = input_data.get("transcript_path", "")
    project_dir = input_data.get("cwd", "")

    if not transcript_path or not project_dir:
        sys.exit(0)

    # Prevent loops
    if input_data.get("stop_hook_active", False):
        sys.exit(0)

    # Parse transcript
    messages = parse_transcript(transcript_path)
    if not messages:
        sys.exit(0)

    # Extract tool calls
    tool_calls = extract_tool_calls(messages)
    if not tool_calls:
        sys.exit(0)

    # Detect debt in each tool call
    all_findings = []
    timestamp = datetime.now(timezone.utc).isoformat()

    for tool_call in tool_calls:
        file_path = tool_call["file_path"]
        content = tool_call["content"]

        findings = detect_debt(content)

        for finding in findings:
            all_findings.append(
                {
                    "timestamp": timestamp,
                    "session": Path(transcript_path).stem,
                    "file": file_path,
                    "type": finding["type"],
                    "context": finding["context"],
                    "line_estimate": finding["line"],
                }
            )

    # Write to ledger
    if all_findings:
        ledger_path = Path(project_dir) / ".claude" / "memory" / "debt_ledger.jsonl"
        append_to_ledger(ledger_path, all_findings)

        # Report to user
        print(f"📊 Detected {len(all_findings)} debt items in this session:")

        # Group by type for summary
        by_type = {}
        for finding in all_findings:
            debt_type = finding["type"]
            by_type[debt_type] = by_type.get(debt_type, 0) + 1

        for debt_type, count in sorted(by_type.items()):
            print(f"  • {debt_type}: {count}")

        print("  → Saved to .claude/memory/debt_ledger.jsonl")

    sys.exit(0)


if __name__ == "__main__":
    main()
