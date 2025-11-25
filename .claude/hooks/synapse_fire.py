#!/usr/bin/env python3
"""
Synapse Fire Hook v2: Multi-lifecycle associative memory injection

ENHANCEMENT: Fires on UserPromptSubmit, PreToolUse, and PostToolUse
- UserPromptSubmit: Analyzes user prompt (original behavior)
- PreToolUse: Analyzes Claude's recent transcript for self-thought patterns
- PostToolUse: Analyzes tool results + Claude's reasoning

This enables "self-synapse" - Claude's own thinking triggers memory recall.
"""
import sys
import json
import subprocess
import hashlib
import time
import re
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

# SESSION-LEVEL CACHE
CACHE_DIR = Path("/tmp/claude_synapse_cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL = 300  # 5 minutes

# Transcript analysis config
MAX_TRANSCRIPT_CHUNK = 8000  # chars to analyze from recent transcript
ASSISTANT_PATTERN = re.compile(r'(?:^|\n)(?:assistant|Claude):\s*(.+?)(?=\n(?:user|human|assistant|Claude):|$)', re.IGNORECASE | re.DOTALL)

def get_cache_key(session_id: str, text: str, lifecycle: str) -> str:
    """Generate cache key from session + text prefix + lifecycle"""
    text_prefix = text[:100].lower().strip()
    return hashlib.md5(f"{session_id}:{lifecycle}:{text_prefix}".encode()).hexdigest()

def get_cached_result(cache_key: str) -> Optional[Dict]:
    """Get cached spark result"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        if time.time() - cache_file.stat().st_mtime < CACHE_TTL:
            try:
                with open(cache_file) as f:
                    return json.load(f)
            except Exception:
                pass
    return None

def set_cached_result(cache_key: str, result: Dict):
    """Cache spark result"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    try:
        with open(cache_file, 'w') as f:
            json.dump(result, f)
    except Exception:
        pass

def output_result(lifecycle: str, context: str = ""):
    """Output hook result with appropriate lifecycle name"""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": lifecycle,
            "additionalContext": context,
        }
    }))
    sys.exit(0)

def extract_claude_thoughts(transcript_path: str) -> str:
    """
    Extract Claude's recent thoughts from transcript.
    Returns concatenated assistant messages for pattern matching.
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return ""

    try:
        with open(transcript_path, 'r') as f:
            # Seek to end and read last chunk for performance
            f.seek(0, 2)  # End of file
            file_size = f.tell()
            read_start = max(0, file_size - MAX_TRANSCRIPT_CHUNK)
            f.seek(read_start)
            chunk = f.read()

        # Extract assistant/Claude messages
        # Look for patterns like "assistant: ..." or Claude's output
        thoughts = []

        # Simple heuristic: Find text between tool calls that isn't user input
        # This captures Claude's reasoning before/after tool use
        lines = chunk.split('\n')
        in_assistant_block = False
        current_block = []

        for line in lines:
            # Skip tool invocations and results
            if '<' in line or 'tool_result' in line.lower():
                if current_block:
                    thoughts.append(' '.join(current_block))
                    current_block = []
                continue

            # Skip obvious user messages
            if line.strip().startswith('Human:') or line.strip().startswith('user:'):
                if current_block:
                    thoughts.append(' '.join(current_block))
                    current_block = []
                continue

            # Collect assistant reasoning
            stripped = line.strip()
            if stripped and len(stripped) > 20:  # Meaningful content
                current_block.append(stripped)

        if current_block:
            thoughts.append(' '.join(current_block))

        # Return last N thoughts (most recent reasoning)
        return ' '.join(thoughts[-3:])[:2000]

    except Exception:
        return ""

def run_spark(text: str) -> Optional[Dict]:
    """Run spark.py on given text and return parsed output"""
    if not text or len(text.strip()) < 10:
        return None

    try:
        result = subprocess.run(
            ["python3", "scripts/ops/spark.py", text, "--json"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.environ.get("CLAUDE_PROJECT_ROOT", str(Path(__file__).resolve().parent.parent.parent))
        )

        if result.returncode != 0:
            return None

        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None

def build_context(spark_output: Dict, source: str = "prompt") -> str:
    """Build additional context string from spark output"""
    if not spark_output or not spark_output.get("has_associations", False):
        return ""

    context_lines = [f"\n🧠 SUBCONSCIOUS RECALL ({source}):"]

    # Add protocol/tool associations
    associations = spark_output.get("associations", [])
    if associations:
        context_lines.append("\n📚 Relevant Protocols & Tools:")
        for assoc in associations[:5]:
            context_lines.append(f"   • {assoc}")

    # Add memories from lessons.md
    memories = spark_output.get("memories", [])
    if memories:
        context_lines.append("\n💭 Relevant Past Experiences:")
        for memory in memories:
            if len(memory) > 100:
                memory = memory[:97] + "..."
            context_lines.append(f"   • {memory}")

    # Add random constraint (lateral thinking)
    constraint = spark_output.get("constraint")
    if constraint:
        context_lines.append("\n💡 Lateral Thinking Spark:")
        context_lines.append(f"   • {constraint}")

    context_lines.append("")
    return "\n".join(context_lines)


def main():
    # Load input
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        output_result("UserPromptSubmit", "")

    # Detect lifecycle from input structure
    tool_name = input_data.get("tool_name")
    tool_result = input_data.get("toolResult")
    prompt = input_data.get("prompt")
    session_id = input_data.get("session_id", "")
    transcript_path = input_data.get("transcript_path", "")

    # Determine lifecycle - check if key EXISTS (not just non-None value)
    # Official schema: PostToolUse has "tool_response", PreToolUse has "tool_name" but no "tool_response"
    if "tool_response" in input_data or "toolResult" in input_data:
        lifecycle = "PostToolUse"
    elif tool_name:
        lifecycle = "PreToolUse"
    else:
        lifecycle = "UserPromptSubmit"

    # Determine what text to analyze
    if lifecycle == "UserPromptSubmit":
        # Original behavior: analyze user prompt
        text_to_analyze = prompt or ""
        source = "User Prompt"
    else:
        # NEW: Analyze Claude's recent transcript thoughts
        text_to_analyze = extract_claude_thoughts(transcript_path)
        source = "Self-Thought Pattern"

        # Also check tool input for relevant keywords (e.g., file paths, commands)
        tool_input = input_data.get("tool_input", {})
        if isinstance(tool_input, dict):
            # Extract searchable content from tool input
            tool_text_parts = []
            for key, value in tool_input.items():
                if isinstance(value, str) and len(value) < 500:
                    tool_text_parts.append(value)
            if tool_text_parts:
                text_to_analyze = f"{text_to_analyze} {' '.join(tool_text_parts)}"

    if not text_to_analyze or not session_id:
        output_result(lifecycle, "")

    # Check cache
    cache_key = get_cache_key(session_id, text_to_analyze, lifecycle)
    cached = get_cached_result(cache_key)

    if cached:
        output_result(lifecycle, cached.get("context", ""))

    # Run spark analysis
    spark_output = run_spark(text_to_analyze)

    if not spark_output or not spark_output.get("has_associations", False):
        set_cached_result(cache_key, {"context": ""})
        output_result(lifecycle, "")

    # Build context
    context = build_context(spark_output, source)

    # Cache and output
    set_cached_result(cache_key, {"context": context})
    output_result(lifecycle, context)


if __name__ == "__main__":
    main()
