#!/usr/bin/env python3
"""
Synapse Fire Hook: Injects associative memory context based on user prompt
"""
import sys
import json
import subprocess

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    # If can't parse input, pass through
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

# Get user prompt
prompt = input_data.get("prompt", "")

if not prompt:
    # No prompt, nothing to analyze
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

try:
    # Run spark.py to get associations
    result = subprocess.run(
        ["python3", "scripts/ops/spark.py", prompt, "--json"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    if result.returncode != 0:
        # Spark failed, pass through without context
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": "",
                    }
                }
            )
        )
        sys.exit(0)

    # Parse spark output
    spark_output = json.loads(result.stdout)

    # Check if there are any associations
    if not spark_output.get("has_associations", False):
        # No associations found, pass through
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": "",
                    }
                }
            )
        )
        sys.exit(0)

    # Build additional context message
    context_lines = ["\n🧠 SUBCONSCIOUS RECALL (Associative Memory):"]

    # Add protocol/tool associations
    associations = spark_output.get("associations", [])
    if associations:
        context_lines.append("\n📚 Relevant Protocols & Tools:")
        for assoc in associations[:5]:  # Limit to top 5
            context_lines.append(f"   • {assoc}")

    # Add memories from lessons.md
    memories = spark_output.get("memories", [])
    if memories:
        context_lines.append("\n💭 Relevant Past Experiences:")
        for memory in memories:
            # Truncate long memories
            if len(memory) > 100:
                memory = memory[:97] + "..."
            context_lines.append(f"   • {memory}")

    # Add random constraint (lateral thinking)
    constraint = spark_output.get("constraint")
    if constraint:
        context_lines.append("\n💡 Lateral Thinking Spark:")
        context_lines.append(f"   • {constraint}")

    context_lines.append("")  # Blank line at end

    # Join all context lines
    additional_context = "\n".join(context_lines)

    # Output the hook result with injected context
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": additional_context,
                }
            }
        )
    )

except subprocess.TimeoutExpired:
    # Spark took too long, skip context injection
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "",
                }
            }
        )
    )
except Exception:
    # Any error, pass through without context
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "",
                }
            }
        )
    )

sys.exit(0)
