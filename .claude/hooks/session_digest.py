#!/usr/bin/env python3
"""
Session Digest Hook: Automatically generates structured session summaries

Parses conversation transcript and generates a compressed, structured digest:
- Summary of key decisions and actions
- Current topic/focus area
- User sentiment and friction points
- Active entities (files, technologies, concepts)

Uses OpenRouter Oracle for high-quality summarization.
Stores digests in .claude/memory/session_digests/<session_id>.json
"""
import sys
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone


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


def extract_conversation_text(messages: list[dict]) -> str:
    """
    Extract human-readable conversation text from transcript.

    Returns formatted text: "User: ...\nAssistant: ..."
    """
    conversation = []

    for entry in messages:
        role = entry.get("type", "")
        message = entry.get("message", {})
        content = message.get("content", [])

        if role == "user":
            # User messages are typically simple strings
            if isinstance(content, str):
                conversation.append(f"User: {content[:500]}")
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")[:500]
                        conversation.append(f"User: {text}")

        elif role == "assistant":
            # Assistant messages - extract text blocks only (not tool calls)
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))

                if text_parts:
                    combined = " ".join(text_parts)[:500]
                    conversation.append(f"Assistant: {combined}")

    return "\n\n".join(conversation)


def load_env_file(project_dir: str):
    """Load environment variables from .env file if it exists."""
    env_path = Path(project_dir) / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    os.environ[key] = value


def generate_digest(
    conversation_text: str, session_id: str, project_dir: str
) -> dict | None:
    """
    Generate structured digest using Oracle (OpenRouter).

    Returns dict with keys: summary, current_topic, user_sentiment, active_entities, metadata
    """
    # Load .env file to get API key
    load_env_file(project_dir)

    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None

    # Construct prompt for Oracle
    prompt = f"""Analyze this conversation and generate a structured session digest.

CONVERSATION:
{conversation_text[:4000]}

Generate a JSON object with:
1. "summary": 2-3 sentence summary of what was accomplished
2. "current_topic": The main focus/topic (e.g., "Database Migration", "Bug Fix in Auth")
3. "user_sentiment": Brief assessment (e.g., "Productive", "Frustrated with errors", "Exploring options")
4. "active_entities": List of 3-5 key items mentioned (files, technologies, concepts)
5. "key_decisions": List of 2-3 major decisions or conclusions reached

Output ONLY valid JSON, no markdown.
"""

    # Use Oracle via OpenRouter
    try:
        # Pass current environment (with loaded .env vars) to subprocess
        result = subprocess.run(
            ["python3", f"{project_dir}/scripts/ops/consult.py", prompt],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_dir,
            env=os.environ.copy(),  # Pass environment with API key
        )

        if result.returncode != 0:
            return None

        # Parse Oracle response (consult.py returns formatted output)
        response_text = result.stdout.strip()

        # Extract the ORACLE ADVICE section (actual content)
        if "ORACLE ADVICE" in response_text:
            # Split at ORACLE ADVICE header and take everything after the separator line
            parts = response_text.split("ORACLE ADVICE")
            if len(parts) > 1:
                advice_section = parts[1]
                # Skip the separator line (===...)
                lines = advice_section.split("\n")
                # Find first non-separator line
                content_lines = [
                    l for l in lines if l.strip() and not l.strip().startswith("=")
                ]
                response_text = "\n".join(content_lines).strip()

        # Try to extract JSON from response (Oracle might wrap it in markdown)
        json_match = response_text
        if "```json" in response_text:
            json_match = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_match = response_text.split("```")[1].split("```")[0].strip()

        digest = json.loads(json_match)

        # Add metadata
        digest["metadata"] = {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message_count": conversation_text.count("User:")
            + conversation_text.count("Assistant:"),
        }

        return digest

    except (
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        FileNotFoundError,
        Exception,
    ):
        return None


def save_digest(digest: dict, session_id: str, project_dir: str):
    """Save digest to .claude/memory/session_digests/<session_id>.json"""
    digest_dir = Path(project_dir) / ".claude" / "memory" / "session_digests"
    digest_dir.mkdir(parents=True, exist_ok=True)

    digest_path = digest_dir / f"{session_id}.json"

    with open(digest_path, "w") as f:
        json.dump(digest, f, indent=2)


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

    # Extract session ID from transcript path
    session_id = Path(transcript_path).stem

    # Parse transcript
    messages = parse_transcript(transcript_path)
    if not messages or len(messages) < 3:  # Skip trivial sessions
        sys.exit(0)

    # Extract conversation text
    conversation_text = extract_conversation_text(messages)
    if not conversation_text or len(conversation_text) < 100:  # Skip empty/trivial
        sys.exit(0)

    # Generate digest
    digest = generate_digest(conversation_text, session_id, project_dir)

    if digest:
        save_digest(digest, session_id, project_dir)

        # Report to user
        print("📝 Session digest generated:")
        print(f"  Topic: {digest.get('current_topic', 'N/A')}")
        print(f"  Sentiment: {digest.get('user_sentiment', 'N/A')}")
        print(f"  Summary: {digest.get('summary', 'N/A')[:100]}...")
        print(f"  → Saved to .claude/memory/session_digests/{session_id}.json")
    else:
        # Failed to generate (missing API key or error)
        # Don't report failure - this is optional feature
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
