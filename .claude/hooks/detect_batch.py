#!/usr/bin/env python3
"""
Batch Operation Detection Hook
Detects when user requests involve batch/bulk processing operations.
Triggers reminder to use parallel execution library for performance.
"""
import sys
import json

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

# Get user prompt
prompt = data.get("prompt", "").lower()

# Triggers indicating batch operations
batch_triggers = [
    "batch",
    "bulk",
    "mass",
    "all files",
    "all ",
    "every",
    "scan",
    "scrape",
    "crawl",
    "iterate",
    "loop through",
    "process multiple",
    "process all",
    "foreach",
    "for each",
    "convert all",
    "download all",
    "upload all",
    "delete all",
    "update all",
    "migrate all",
    "transform all",
]

# Check if prompt mentions batch operations
batch_detected = any(trigger in prompt for trigger in batch_triggers)

# Also check for plural indicators with action verbs
plural_indicators = [
    "files",
    "urls",
    "apis",
    "requests",
    "records",
    "rows",
    "items",
    "documents",
    "pages",
    "entries",
]
action_verbs = [
    "process",
    "fetch",
    "get",
    "download",
    "upload",
    "parse",
    "convert",
    "transform",
    "migrate",
    "update",
]

# Detect pattern like "process files" or "fetch urls"
for verb in action_verbs:
    for plural in plural_indicators:
        if f"{verb} {plural}" in prompt or f"{verb} all {plural}" in prompt:
            batch_detected = True
            break

if batch_detected:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": (
                        "⚠️ BATCH OPERATION DETECTED\n"
                        "PERFORMANCE PROTOCOL: Use `scripts.lib.parallel` to multi-thread this operation.\n"
                        "Example:\n"
                        "  from parallel import run_parallel\n"
                        '  results = run_parallel(process_func, items, max_workers=50, desc="Processing")'
                    ),
                }
            }
        )
    )

sys.exit(0)
