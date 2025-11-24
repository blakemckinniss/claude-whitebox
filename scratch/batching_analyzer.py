#!/usr/bin/env python3
"""
Batching Analyzer Hook (UserPromptSubmit)

Analyzes user prompts for batching opportunities and injects guidance.

DETECTS:
- Multiple file/path references → Suggest parallel Read
- Multiple search terms → Suggest parallel Grep
- Multiple URLs → Suggest parallel WebFetch
- Large scale operations → Suggest parallel.py script
"""

import sys
import json
import re

def analyze_prompt_for_batching(prompt):
    """
    Analyze user prompt for batching opportunities.

    Returns: (should_suggest: bool, suggestion: str)
    """
    prompt_lower = prompt.lower()
    suggestions = []

    # Pattern 1: Multiple files mentioned
    file_patterns = [
        r'read\s+(?:these\s+)?files?[:\s]',
        r'check\s+(?:these\s+)?files?[:\s]',
        r'analyze\s+(?:these\s+)?files?[:\s]',
        r'files?\s+(?:named|called|at)',
    ]

    file_list_detected = any(re.search(pattern, prompt_lower) for pattern in file_patterns)

    # Count file-like references (paths with / or . extensions)
    file_refs = len(re.findall(r'\S+\.(py|ts|js|tsx|jsx|json|md|txt|yaml|yml)', prompt))

    if file_list_detected or file_refs >= 2:
        suggestions.append({
            "type": "parallel_read",
            "message": """
💡 BATCHING OPPORTUNITY: Multiple Files

Use parallel Read invocation:
  <invoke name="Read"><parameter name="file_path">file1.py</parameter></invoke>
  <invoke name="Read"><parameter name="file_path">file2.py</parameter></invoke>
  <invoke name="Read"><parameter name="file_path">file3.py</parameter></invoke>

Benefits: 3x faster, single response, cleaner output.
"""
        })

    # Pattern 2: Multiple search terms
    search_patterns = [
        r'search\s+for\s+\w+\s+(?:and|,)\s+\w+',
        r'find\s+(?:all\s+)?(?:instances|occurrences)\s+of',
        r'grep\s+(?:for\s+)?\w+\s+(?:and|,)',
    ]

    search_list_detected = any(re.search(pattern, prompt_lower) for pattern in search_patterns)

    if search_list_detected:
        suggestions.append({
            "type": "parallel_grep",
            "message": """
💡 BATCHING OPPORTUNITY: Multiple Searches

Use parallel Grep invocation:
  <invoke name="Grep"><parameter name="pattern">pattern1</parameter></invoke>
  <invoke name="Grep"><parameter name="pattern">pattern2</parameter></invoke>
  <invoke name="Grep"><parameter name="pattern">pattern3</parameter></invoke>

Benefits: 3x faster search, consolidated results.
"""
        })

    # Pattern 3: Multiple URLs
    url_count = len(re.findall(r'https?://\S+', prompt))

    if url_count >= 2:
        suggestions.append({
            "type": "parallel_web",
            "message": """
💡 BATCHING OPPORTUNITY: Multiple URLs

Use parallel WebFetch invocation:
  <invoke name="WebFetch">
    <parameter name="url">url1</parameter>
    <parameter name="prompt">extract info</parameter>
  </invoke>
  <invoke name="WebFetch">
    <parameter name="url">url2</parameter>
    <parameter name="prompt">extract info</parameter>
  </invoke>

Benefits: 10x faster (network latency hides in parallelism).
"""
        })

    # Pattern 4: Large-scale operations (should use script + parallel.py)
    scale_keywords = [
        (r'(?:all|every|each)\s+(?:file|module|component)', 'files'),
        (r'(?:100|hundreds?|thousands?|many)', 'items'),
        (r'entire\s+(?:directory|folder|codebase)', 'directory'),
        (r'batch\s+(?:process|convert|transform)', 'batch'),
    ]

    large_scale = any(re.search(pattern, prompt_lower) for pattern, _ in scale_keywords)

    if large_scale:
        suggestions.append({
            "type": "script_with_parallel",
            "message": """
💡 LARGE-SCALE OPERATION DETECTED

For bulk processing, write a scratch script with parallel.py:

  from scripts.lib.parallel import run_parallel

  def process_item(item):
      # Your logic here
      return result

  results = run_parallel(
      process_item,
      items,
      max_workers=50,
      desc="Processing items"
  )

Benefits: 50x faster, progress bar, error resilience.

RULE: Do NOT use native tools in loops. Write scripts.
"""
        })

    return suggestions


def main():
    """Main analysis logic"""
    try:
        data = json.load(sys.stdin)
    except:
        sys.exit(0)

    prompt = data.get("prompt", "")

    if not prompt:
        sys.exit(0)

    # Analyze for batching opportunities
    suggestions = analyze_prompt_for_batching(prompt)

    # If suggestions exist, inject them as context
    if suggestions:
        context_lines = ["\n⚡ PERFORMANCE OPTIMIZATION OPPORTUNITIES:"]

        for suggestion in suggestions:
            context_lines.append(suggestion["message"])

        context = "\n".join(context_lines)

        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context
            }
        }

        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
