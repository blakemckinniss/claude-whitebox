#!/usr/bin/env python3
"""
Build the complete performance_gate.py hook file.
This script approach prevents truncation issues.
"""
from pathlib import Path

HOOK_CODE = r'''#!/usr/bin/env python3
"""
Performance Gate Hook: Blocks sequential operations when parallel is possible
Triggers on: PreToolUse
Philosophy: LLMs think sequentially by default. Force parallel thinking.
"""
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import load_session_state, apply_penalty

# Performance anti-patterns
BATCH_LOOP_PATTERNS = [
    r'\bfor\s+\w+\s+in\s+.*?\.(txt|py|js|json|md|csv)',  # for file in *.txt
    r'\bwhile\s+read\s+',  # while read line
    r'\bseq\s+\d+',  # seq 1 10
    r'\bxargs\s+-I',  # xargs -I
]

FILE_ITERATION_SIGNALS = [
    "for each file",
    "all the files",
    "every file",
    "each .py file",
    "iterate through",
    "process all",
    "batch",
]

# Tools that commonly get used sequentially when parallel is better
PARALLELIZABLE_TOOLS = {"Read", "Grep", "Glob", "Task", "Bash"}


def detect_bash_loop(command: str) -> Optional[str]:
    """Detect Bash loop patterns that should use parallel.py instead"""
    for pattern in BATCH_LOOP_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return pattern
    return None


def analyze_conversation_for_parallel_opportunity(conversation_history: List[Dict], current_tool: str) -> Optional[Tuple[str, int]]:
    """
    Detect if we're making sequential tool calls when parallel is possible.
    Returns (pattern_name, count) or None
    """
    # Look at last 10 messages
    recent = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history

    # Count same tool uses in separate assistant messages
    tool_count = 0
    for msg in recent:
        if msg.get("role") == "assistant" and "tool_uses" in msg:
            for use in msg["tool_uses"]:
                if use.get("toolName") == current_tool:
                    tool_count += 1

    # 2+ uses of same tool across messages = sequential pattern
    if tool_count >= 2:
        return ("sequential_tool_calls", tool_count)

    # Check last assistant message for iteration planning signals
    for msg in reversed(recent):
        if msg.get("role") == "assistant":
            text = msg.get("text", "").lower()
            for signal in FILE_ITERATION_SIGNALS:
                if signal in text:
                    return ("planned_iteration", 1)
            break

    return None


def get_parallel_guidance(tool_name: str, pattern: str, count: int, command: Optional[str] = None) -> str:
    """Generate specific guidance for parallelization"""

    if tool_name == "Bash" and command and detect_bash_loop(command):
        return f"""
🚫 PERFORMANCE GATE: Bash loop detected

You're about to run a sequential loop. With unlimited bandwidth, this is WASTEFUL.

BLOCKED COMMAND:
{command}

REQUIRED ALTERNATIVE: Write a script using parallel.py

Example Template:
```python
#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib.parallel import run_parallel

def process_item(filepath):
    # Your processing logic here
    # (read file, grep, transform, etc.)
    return result

items = list(Path(".").glob("*.txt"))  # Or whatever your target is
results = run_parallel(
    process_item,
    items,
    max_workers=50,  # Use that unlimited bandwidth!
    desc="Processing files"
)

# Handle results
for item, result, error in results:
    if error:
        print(f"FAIL: {{item}} - {{error}}")
    else:
        print(f"OK: {{item}} - {{result}}")
```

Why This Matters:
- Sequential loop: 100 files = 100 seconds (1 file/sec)
- Parallel (50 workers): 100 files = 2 seconds (50 files/sec)
- YOU HAVE UNLIMITED BANDWIDTH - stopping you from using it is a crime against efficiency

PENALTY: -20% confidence for wasting resources
"""

    if tool_name == "Read" and count >= 2:
        return f"""
🚫 PERFORMANCE GATE: Sequential Read pattern detected

You've made {count} separate Read calls. ALL independent file reads MUST be parallel.

BLOCKED ACTION: Sequential Read call #{count + 1}

REQUIRED ALTERNATIVE: Single message with multiple Read calls

CORRECT PATTERN:
<function_calls>
<invoke name="Read">
<parameter name="file_path">/path/to/file1.py