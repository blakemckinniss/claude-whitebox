# The Performance Protocol (Meta-Cognition Gate)

## Problem Statement
LLM operates sequentially by default, missing parallelization opportunities:
- Sequential tool calls when independent operations could run parallel
- Manual operations when script could batch
- Single-threaded loops when parallel.py exists
- Reactive warnings (UserPromptSubmit) instead of proactive blocking (PreToolUse)

## Design: The Three-Layer Performance Gate

### Layer 1: Pre-Action Analysis (PreToolUse Hook)
**Trigger:** Before EVERY tool use (Read, Write, Edit, Bash, Grep, Glob, Task, etc.)

**Analysis:**
1. **Pattern Detection:** Identify performance anti-patterns
   - Sequential tool calls (multiple Read/Grep in one message)
   - Bash loops over files (for file in *.txt)
   - Manual operations on >3 items
   - Grep without parallel search scope

2. **Context Window:** Look back N turns to detect emerging patterns
   - 3+ similar tool calls in last 5 turns → batch opportunity
   - Planning phase mentioning "for each file" → script signal

3. **Opportunity Classification:**
   - **MANDATORY_PARALLEL:** Multiple independent tool calls → BLOCK with correction
   - **SHOULD_SCRIPT:** Repetitive manual work → BLOCK with script template
   - **SHOULD_BATCH:** Sequential Bash loop → BLOCK with parallel.py pattern
   - **OPTIMAL:** Action already optimized → ALLOW

4. **Enforcement:**
   - BLOCK action with specific correction (not just warning)
   - Provide exact code pattern to use
   - Force resubmission with optimized approach

### Layer 2: Cognitive Pre-Flight Check (Before Response)
**Trigger:** Internal meta-cognition before generating response

**Questions (Meta-Prompt):**
1. "Am I about to make multiple tool calls?"
   - YES → Can they run in parallel? (Check dependencies)
   - If parallel-safe → Use single message with multiple tool blocks

2. "Am I planning to do something >3 times?"
   - YES → Should I write a script to scratch/?
   - Check if scratch/ has similar script already

3. "Does this involve file iteration?"
   - YES → Is parallel.py appropriate?
   - Provide specific parallel.py invocation

4. "Am I about to delegate to agent?"
   - YES → Can I delegate multiple agents in parallel?
   - Use single message with multiple Task calls

### Layer 3: Reinforcement Learning (Confidence System)
**Reward Actions:**
- Parallel tool calls in single message: +15%
- Writing script instead of manual: +20%
- Using parallel.py correctly: +25%
- Proactive optimization: +10%

**Penalize Actions:**
- Sequential tools when parallel possible: -20%
- Manual repetition when script exists: -15%
- Ignoring performance gate: -25%

## Implementation Plan

### Hook: `.claude/hooks/performance_gate.py` (PreToolUse)
```python
# Detect anti-patterns:
# - Multiple Read calls planned (check conversation history)
# - Bash loop patterns (for, while, seq)
# - Manual file iteration
# - Sequential Grep when parallel possible

# BLOCK with specific corrections:
# - "Use single message with 3 Read tool calls in parallel"
# - "Write script to scratch/batch_operation.py using parallel.py"
# - "Use parallel.py with batch_map(func, items, max_workers=50)"
```

### Meta-Prompt Injection (UserPromptSubmit)
```python
# Before you respond, ask yourself:
# 1. Multiple tool calls? → Parallel?
# 2. Repetition >3 times? → Script?
# 3. File iteration? → parallel.py?
# 4. Multiple agents? → Parallel delegation?
```

### Reinforcement (PostToolUse + detect_confidence_reward.py)
```python
# Detect optimized actions:
# - Multiple tool uses in single message → +15%
# - Script creation for batch → +20%
# - parallel.py usage → +25%
```

## Anti-Patterns to Detect

### Sequential Tool Calls
```
❌ BAD:
Message 1: Read file1
Message 2: Read file2
Message 3: Read file3

✅ GOOD:
Single Message: Read file1 + Read file2 + Read file3 (parallel)
```

### Manual Iteration
```
❌ BAD:
for file in *.py; do grep "TODO" $file; done

✅ GOOD:
from parallel import run_parallel
files = glob("*.py")
results = run_parallel(lambda f: grep_file(f, "TODO"), files, max_workers=50)
```

### Sequential Agents
```
❌ BAD:
Message 1: Task(researcher, "FastAPI docs")
Wait for response...
Message 2: Task(researcher, "Pydantic docs")

✅ GOOD:
Single Message: Task(researcher, "FastAPI") + Task(researcher, "Pydantic") (parallel)
```

### Manual File Operations
```
❌ BAD:
Read file1 → Edit file1 → Read file2 → Edit file2 → ...

✅ GOOD:
Script: scratch/batch_edit.py with parallel.py
```

## Cognitive Trigger Phrases

**User Input Signals:**
- "for each file"
- "all the X"
- "every Y"
- "batch"
- "multiple files"

**LLM Planning Signals:**
- "I'll read each file..."
- "Let me check all..."
- "I'll iterate through..."

**Context Signals:**
- 3+ similar tool calls in history
- Bash loops detected in previous turn
- User frustrated by slowness

## Success Metrics

1. **Reduction in Sequential Anti-Patterns:**
   - Baseline: Count sequential tool calls in last 10 sessions
   - Target: 80% reduction

2. **Increased Parallel Usage:**
   - Track single-message multi-tool calls
   - Track parallel.py invocations
   - Track parallel agent delegation

3. **Faster Task Completion:**
   - Measure turn count for batch operations
   - Compare before/after optimization

4. **User Satisfaction:**
   - Track "this is slow" complaints
   - Track manual overrides of gate

## Edge Cases

1. **Dependent Operations:**
   - Read config → Parse → Read based on config
   - Must run sequentially
   - Gate should ALLOW (no parallel opportunity)

2. **Low Item Count:**
   - 1-2 files → Manual acceptable
   - 3+ files → Script/parallel required

3. **User Override:**
   - User explicitly requests sequential
   - Gate should warn but allow

4. **Script Already Exists:**
   - Check scratch/ before suggesting new script
   - Suggest reusing existing tool

## Open Questions

1. **How aggressive should blocking be?**
   - Option A: Soft warnings (can ignore)
   - Option B: Hard blocks (cannot proceed)
   - **RECOMMENDATION:** Hard block for MANDATORY_PARALLEL, soft warn for SHOULD_SCRIPT

2. **Should gate analyze planned actions from conversation?**
   - LLM says "I'll read file1, then file2, then file3"
   - Block BEFORE first tool call?
   - **RECOMMENDATION:** Yes, parse last assistant message for planning signals

3. **How to handle mixed operations?**
   - Read (independent) + Edit (dependent on Read)
   - **RECOMMENDATION:** Allow Read in parallel, then Edit sequentially

4. **Integration with epistemology.py?**
   - Should low confidence prevent optimization?
   - **RECOMMENDATION:** No, optimization is orthogonal to confidence
