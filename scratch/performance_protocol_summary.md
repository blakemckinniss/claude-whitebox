# The Performance Protocol - Implementation Complete

## Overview
Meta-cognition system that forces parallel execution and batch optimization.

## Problem
You (Claude) default to sequential thinking:
- Read file1 → wait → Read file2 → wait → Read file3
- Bash loop: `for file in *.txt; do cat $file; done`
- Manual: Process 100 items one by one

## Solution: Three-Layer Defense

### Layer 1: Pre-Action Gate (PreToolUse Hook)
**File:** `.claude/hooks/performance_gate.py`

**Detects:**
- Bash loops on files (`for file in *.txt`, `while read`, `seq`)
- Sequential tool call patterns (2+ same tool in recent history)
- Planned iteration signals ("for each file", "process all")

**Actions:**
- BLOCK Bash loops → Force parallel.py usage
- WARN sequential tools → Suggest parallel execution

**Test:**
```bash
# Should trigger warning
cat << EOF | python3 .claude/hooks/performance_gate.py
{
  "sessionId": "test",
  "toolName": "Bash",
  "toolParams": {"command": "for file in *.txt; do cat \$file; done"}
}
EOF
```

### Layer 2: Meta-Cognition Reminder (UserPromptSubmit Hook)
**File:** `.claude/hooks/meta_cognition_performance.py`

**Injects before EVERY response:**
```
⚡ META-COGNITION PERFORMANCE CHECKLIST:
1. Multiple tool calls planned? → Parallel?
2. Operation repeated >2 times? → Script?
3. File iteration? → parallel.py?
4. Multiple agents? → Parallel delegation?
5. Bash loop? → BLOCK YOURSELF
```

**Purpose:** Self-regulation before acting

### Layer 3: Reinforcement Learning (PostToolUse Hook)
**File:** `.claude/hooks/performance_reward.py`

**Detects and rewards:**
- Parallel tool calls (3+ same tool in one message): +15%
- Script using parallel.py: +25%
- Parallel agent delegation (2+ Task calls): +15%
- Writing batch scripts: +20%

**Penalizes (via epistemology.py):**
- Sequential when parallel possible: -20%
- Manual instead of script: -15%
- Ignoring performance gate: -25%

## Configuration Changes

### epistemology.py Additions
```python
CONFIDENCE_GAINS = {
    ...
    "parallel_tool_calls": 15,
    "write_batch_script": 20,
    "use_parallel_py": 25,
    "parallel_agent_delegation": 15,
}

CONFIDENCE_PENALTIES = {
    ...
    "sequential_when_parallel": -20,
    "manual_instead_of_script": -15,
    "ignore_performance_gate": -25,
}
```

### settings.json Additions
```json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Bash", "hooks": [
        {"type": "command", "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/performance_gate.py"}
      ]}
    ],
    "UserPromptSubmit": [
      {"type": "command", "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/meta_cognition_performance.py"}
    ],
    "PostToolUse": [
      {"type": "command", "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/performance_reward.py"}
    ]
  }
}
```

## Usage Examples

### BEFORE (Sequential - BAD)
```
Message 1: Read src/file1.py
Message 2: Read src/file2.py
Message 3: Read src/file3.py

Total time: 3 round trips
```

### AFTER (Parallel - GOOD)
```
Single Message:
<function_calls>
<invoke name="Read"><parameter name="file_path">src/file1.py</parameter></invoke>
<invoke name="Read"><parameter name="file_path">src/file2.py</parameter></invoke>
<invoke name="Read"><parameter name="file_path">src/file3.py</parameter></invoke>
</function_calls>

Total time: 1 round trip
Reward: +15% confidence
```

### BEFORE (Bash Loop - TERRIBLE)
```bash
for file in *.txt; do
    cat "$file" | grep "TODO" >> results.txt
done

Time: 100 files × 1 sec = 100 seconds
```

### AFTER (parallel.py - OPTIMAL)
```python
from scripts.lib.parallel import run_parallel
from pathlib import Path

def process_file(filepath):
    with open(filepath) as f:
        return [line for line in f if "TODO" in line]

files = list(Path(".").glob("*.txt"))
results = run_parallel(process_file, files, max_workers=50)

# Time: 100 files ÷ 50 workers = 2 seconds (50x faster)
# Reward: +25% confidence
```

## Testing Checklist

- [x] performance_gate.py detects Bash loops
- [x] performance_gate.py allows normal commands
- [x] meta_cognition_performance.py registered in UserPromptSubmit
- [x] performance_reward.py registered in PostToolUse
- [x] epistemology.py has new rewards/penalties
- [x] CLAUDE.md documents the protocol
- [x] settings.json has all hooks registered

## Agent Parallelism: The Secret Weapon

**KEY INSIGHT:** Agents have separate 200k context windows (FREE to main thread)

**When to Use:**
- Multi-module analysis: 5 modules → 5 agents in parallel
- Comparative research: 4 frameworks → 4 researcher agents
- Distributed code review: 20 controllers → 5 agents (4 files each)

**Benefits:**
- Agent context is FREE (doesn't consume main thread tokens)
- Each agent processes 200k tokens independently
- Agents return compressed summaries (50-200 words)
- Main thread receives clean, actionable insights

**Example:**
```
BEFORE: Read 20 files sequentially (40k tokens, 20 round trips)
AFTER: 5 agents in parallel, each reads 4 files (500 words returned, 1 round trip)
Speedup: 20x faster
Context savings: 99%
```

See `scratch/agent_parallelism_examples.md` for detailed examples.

## Next Session Behavior

When you (Claude) start a new session, you will:

1. **See meta-cognition reminder** before EVERY response
2. **Be blocked** if trying Bash loops on files
3. **Be rewarded** for parallel tool calls AND parallel agent delegation
4. **Be reminded** that agent context is FREE
5. **Self-regulate** using internal checklist

## Philosophy

**The Core Insight:** LLMs optimize for "appearing helpful quickly" over "using resources efficiently"

**The Solution:** Hard blocks + Rewards > Advisory warnings

**The Result:** Automatic parallel thinking becomes the default, not the exception

## Impact Estimation

**Batch File Operations (100 files):**
- Before: 100 seconds (sequential)
- After: 2 seconds (50 workers)
- Speedup: 50x

**Multiple Independent Searches:**
- Before: 3 round trips (3× latency)
- After: 1 round trip (1× latency)
- Speedup: 3x

**Agent Delegation:**
- Before: Sequential delegation (2× wait time)
- After: Parallel delegation (1× wait time)
- Speedup: 2x

**User Experience:** Tasks that took minutes now take seconds. No user intervention required.
