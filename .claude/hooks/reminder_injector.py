#!/usr/bin/env python3
"""
Reminder Injector Hook: Dynamic context injection based on trigger patterns.

Inspired by remindcc - reads markdown files from .claude/reminders/ with YAML
frontmatter triggers and injects matching content into prompts.

Trigger types:
  - phrase:text  - Case-insensitive substring match
  - word:text    - Word-boundary match (won't match "api" in "rapid")
  - regex:pattern - Full regex support
  - (empty)      - Always included

File format:
  ---
  trigger:
    - word:api
    - phrase:endpoint
    - regex:route|controller
  ---
  # Your context here
  Markdown content to inject when triggers match.
"""

import _lib_path  # noqa: F401
import sys
import json
import re
from pathlib import Path


REMINDERS_DIR = Path(__file__).parent.parent / "reminders"


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content

    lines = content.split("\n")
    end_idx = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        return {}, content

    frontmatter_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1:]).strip()

    # Simple YAML parsing for trigger list
    meta = {}
    current_key = None
    current_list = []

    for line in frontmatter_lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Key: value or Key:
        if ":" in stripped and not stripped.startswith("-"):
            if current_key and current_list:
                meta[current_key] = current_list
            key_part = stripped.split(":")[0].strip()
            val_part = stripped[len(key_part) + 1:].strip()
            current_key = key_part
            if val_part:
                meta[current_key] = val_part
                current_key = None
                current_list = []
            else:
                current_list = []
        elif stripped.startswith("-") and current_key:
            item = stripped[1:].strip()
            current_list.append(item)

    if current_key and current_list:
        meta[current_key] = current_list

    return meta, body


def matches_trigger(prompt: str, trigger: str) -> bool:
    """Check if prompt matches a single trigger."""
    prompt_lower = prompt.lower()

    if trigger.startswith("phrase:"):
        phrase = trigger[7:].lower()
        return phrase in prompt_lower

    elif trigger.startswith("word:"):
        word = trigger[5:]
        pattern = rf"\b{re.escape(word)}\b"
        return bool(re.search(pattern, prompt, re.IGNORECASE))

    elif trigger.startswith("regex:"):
        pattern = trigger[6:]
        try:
            return bool(re.search(pattern, prompt, re.IGNORECASE))
        except re.error:
            return False

    else:
        # Plain text = phrase match
        return trigger.lower() in prompt_lower


def load_reminders() -> list[tuple[list[str], str, str]]:
    """Load all reminder files. Returns [(triggers, content, filename), ...]"""
    reminders = []

    if not REMINDERS_DIR.exists():
        return reminders

    for md_file in REMINDERS_DIR.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(content)
            triggers = meta.get("trigger", [])
            if isinstance(triggers, str):
                triggers = [triggers]
            reminders.append((triggers, body, md_file.stem))
        except Exception:
            continue

    return reminders


def get_matching_reminders(prompt: str, reminders: list) -> list[tuple[str, str]]:
    """Return (content, filename) for all matching reminders."""
    matches = []

    for triggers, content, filename in reminders:
        # Empty triggers = always include
        if not triggers:
            matches.append((content, filename))
            continue

        # Check if any trigger matches
        for trigger in triggers:
            if matches_trigger(prompt, trigger):
                matches.append((content, filename))
                break

    return matches


def main():
    """UserPromptSubmit hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({}))
        sys.exit(0)

    user_prompt = input_data.get("user_prompt", "") or input_data.get("prompt", "")

    if not user_prompt:
        print(json.dumps({}))
        sys.exit(0)

    reminders = load_reminders()
    if not reminders:
        print(json.dumps({}))
        sys.exit(0)

    matches = get_matching_reminders(user_prompt, reminders)
    if not matches:
        print(json.dumps({}))
        sys.exit(0)

    # Format output
    parts = []
    for content, filename in matches:
        parts.append(f"[{filename}]\n{content}")

    context = "\n\n---\n\n".join(parts)
    output = {"additionalContext": f"<additional-user-instruction>\n{context}\n</additional-user-instruction>"}

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
