# Agent Parallelism: Free Context Workers

## The Key Insight

**Agents have separate context windows.** This means:
- Agent context does NOT consume main thread tokens
- Each agent can process 200k tokens independently
- Multiple agents = multiple free 200k context windows working in parallel
- Agent outputs are compressed summaries (50-200 words), not full context

## Architecture

```
Main Thread (200k tokens)
    ↓ Delegates (parallel)
    ├─→ Agent 1 (separate 200k context) → returns 100 words
    ├─→ Agent 2 (separate 200k context) → returns 100 words
    ├─→ Agent 3 (separate 200k context) → returns 100 words
    └─→ Agent 4 (separate 200k context) → returns 100 words

Main thread receives: 400 words (compressed)
Agents processed: 800k tokens (free to main thread)
```

## When to Use Agent Parallelism

### ✅ EXCELLENT Use Cases

1. **Multi-Module Analysis**
   - Task: "Analyze authentication, API, database, and UI modules for security issues"
   - Old way: Read all files sequentially → 50k tokens in main context
   - New way: 4 agents in parallel → each analyzes one module → 400 words returned

2. **Comparative Research**
   - Task: "Compare FastAPI, Flask, Django, and Sanic for our use case"
   - Old way: Research sequentially → 20k tokens of docs in main context
   - New way: 4 researcher agents in parallel → each researches one framework → 400 words returned

3. **Distributed Code Review**
   - Task: "Review all controllers in src/controllers/ for code quality"
   - Old way: Read 20 files → 30k tokens in main context
   - New way: 5 agents in parallel → each reviews 4 files → 500 words returned

4. **Parallel Testing**
   - Task: "Test auth, payments, notifications, and analytics modules"
   - Old way: Test sequentially → wait for each to complete
   - New way: 4 tester agents in parallel → all test simultaneously → 400 words summary

### ❌ POOR Use Cases

1. **Single File Operations**
   - Reading one config file → No need for agent (costs latency)
   - Direct Read tool is faster

2. **Dependent Sequential Work**
   - Step 1 output needed for Step 2 → Cannot parallelize
   - Must run sequentially

3. **Simple Queries**
   - "What's the current date?" → No need for agent overhead
   - Answer directly

## Example Invocations

### Example 1: Multi-Module Security Audit

**BEFORE (Sequential - BAD):**
```
Message 1: Read src/auth/login.py
Message 2: Analyze for security issues
Message 3: Read src/auth/register.py
Message 4: Analyze for security issues
Message 5: Read src/api/endpoints.py
Message 6: Analyze for security issues
...

Time: 6+ round trips
Context: 40k tokens consumed
```

**AFTER (Parallel Agents - OPTIMAL):**
```
Single Message:
<function_calls>
<invoke name="Task">
  <parameter name="subagent_type">researcher</parameter>
  <parameter name="description">Security audit of authentication module</parameter>
  <parameter name="prompt">Analyze all files in src/auth/ for security vulnerabilities (SQL injection, XSS, auth bypass, secrets exposure). Return summary of critical/high issues with file:line references.</parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">researcher</parameter>
  <parameter name="description">Security audit of API module</parameter>
  <parameter name="prompt">Analyze all files in src/api/ for security vulnerabilities (input validation, rate limiting, CORS, auth). Return summary of critical/high issues with file:line references.</parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">researcher</parameter>
  <parameter name="description">Security audit of database module</parameter>
  <parameter name="prompt">Analyze all files in src/database/ for security vulnerabilities (SQL injection, connection security, query parameterization). Return summary of critical/high issues with file:line references.</parameter>
</invoke>
</function_calls>

Time: 1 round trip (agents run in parallel)
Context: ~300 words consumed (agents absorbed the 40k tokens)
Speedup: 6x faster
Context savings: 99% (40k → 300 words)
```

### Example 2: Technology Stack Research

**BEFORE (Sequential - BAD):**
```
Message 1: Research FastAPI pros/cons
Message 2: Research Flask pros/cons
Message 3: Research Django pros/cons
Message 4: Compare results manually

Time: 4 round trips
Context: 15k tokens (documentation excerpts)
```

**AFTER (Parallel Agents - OPTIMAL):**
```
Single Message:
<function_calls>
<invoke name="Task">
  <parameter name="subagent_type">researcher</parameter>
  <parameter name="description">FastAPI research</parameter>
  <parameter name="prompt">Research FastAPI 2025: async support, performance benchmarks, ecosystem maturity, type safety, documentation quality. Return 100-word summary with key pros/cons.</parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">researcher</parameter>
  <parameter name="description">Flask research</parameter>
  <parameter name="prompt">Research Flask 2025: ecosystem, async support, performance, simplicity, extensions. Return 100-word summary with key pros/cons.</parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">researcher</parameter>
  <parameter name="description">Django research</parameter>
  <parameter name="prompt">Research Django 2025: batteries-included features, ORM, admin, async support, performance. Return 100-word summary with key pros/cons.</parameter>
</invoke>
</function_calls>

Time: 1 round trip
Context: ~300 words consumed
Speedup: 4x faster
Context savings: 98% (15k → 300 words)
```

### Example 3: Distributed Code Review

**BEFORE (Sequential - BAD):**
```
for controller in controllers:
    read controller
    analyze code quality
    check for bugs
    verify tests exist

Time: 20 controllers × 4 actions = 80 operations
Context: 50k tokens (all controller code)
```

**AFTER (Parallel Agents - OPTIMAL):**
```
# First, group controllers (4 per agent for efficiency)
controllers_grouped = [
    ["UserController", "AuthController", "ProfileController", "SettingsController"],
    ["ProductController", "OrderController", "CartController", "PaymentController"],
    ["NotificationController", "EmailController", "SMSController", "PushController"],
    ["AnalyticsController", "ReportController", "DashboardController", "AdminController"],
    ["SearchController", "FilterController", "ExportController", "ImportController"]
]

Single Message:
<function_calls>
<invoke name="Task">
  <parameter name="subagent_type">code-reviewer</parameter>
  <parameter name="description">Review user management controllers</parameter>
  <parameter name="prompt">Review src/controllers/user/*.py for code quality, bugs, test coverage. Return summary: critical issues, warnings, test gaps. Format: controller:line - issue.</parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">code-reviewer</parameter>
  <parameter name="description">Review e-commerce controllers</parameter>
  <parameter name="prompt">Review src/controllers/commerce/*.py for code quality, bugs, test coverage. Return summary: critical issues, warnings, test gaps. Format: controller:line - issue.</parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">code-reviewer</parameter>
  <parameter name="description">Review notification controllers</parameter>
  <parameter name="prompt">Review src/controllers/notifications/*.py for code quality, bugs, test coverage. Return summary: critical issues, warnings, test gaps. Format: controller:line - issue.</parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">code-reviewer</parameter>
  <parameter name="description">Review admin controllers</parameter>
  <parameter name="prompt">Review src/controllers/admin/*.py for code quality, bugs, test coverage. Return summary: critical issues, warnings, test gaps. Format: controller:line - issue.</parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">code-reviewer</parameter>
  <parameter name="description">Review utility controllers</parameter>
  <parameter name="prompt">Review src/controllers/utils/*.py for code quality, bugs, test coverage. Return summary: critical issues, warnings, test gaps. Format: controller:line - issue.</parameter>
</invoke>
</function_calls>

Time: 1 round trip (5 agents work in parallel on 20 controllers)
Context: ~500 words consumed (agents absorbed 50k tokens)
Speedup: 20x faster (1 round trip vs 20+ sequential reads/analyses)
Context savings: 99% (50k → 500 words)
```

## Best Practices

### 1. Group Related Work
- Don't spawn 20 agents for 20 files
- Group into logical units (4-5 files per agent)
- Reduces overhead while maintaining parallelism

### 2. Clear Prompts
- Each agent gets specific instructions
- Include output format requirements
- Specify compression target (e.g., "100-word summary")

### 3. Balance Granularity
- Too many agents (20+) → scheduling overhead
- Too few agents (1-2) → underutilized parallelism
- Sweet spot: 3-6 agents for most tasks

### 4. Use Appropriate Agent Types

| Task Type | Agent | Why |
|-----------|-------|-----|
| Research/docs | researcher | Context firewall (500→50 words) |
| Code analysis | researcher or custom | Good at reading+summarizing |
| Code writing | script-smith | Quality gates enforced |
| Debugging | sherlock | Read-only prevents loops |
| Code review | custom code-reviewer | Focused on quality patterns |
| Testing | tester | Test-specific expertise |

### 5. Compress Output
- Agents should return summaries, not raw data
- Target: 50-200 words per agent
- Include only actionable information
- Use bullet points and file:line references

## Performance Impact

### Traditional Sequential Approach
```
Task: Analyze 5 modules for security
Time: 5 modules × 2 min/module = 10 minutes
Context: 50k tokens consumed
Round trips: 15+ (read files, analyze, discuss)
```

### Agent Parallel Approach
```
Task: Analyze 5 modules for security
Time: 1 round trip = 2 minutes (all parallel)
Context: 500 words consumed
Round trips: 1
Speedup: 5x faster
Context savings: 99%
```

## Cognitive Load Reduction

**Main Thread Stays Focused:**
- Receives compressed summaries
- Makes high-level decisions
- Coordinates work
- Not bogged down in details

**Agents Handle Details:**
- Read large files
- Process verbose documentation
- Analyze complex code
- Return only actionable insights

## The Free Context Advantage

**Main Thread:** 200k token limit
**With 5 Parallel Agents:** Effectively 1 million tokens (200k × 5)

**Example:**
- Main thread: 20k tokens used
- 5 agents: Each processes 40k tokens = 200k total
- Total effective processing: 220k tokens
- Main thread pollution: 0 tokens (agents return summaries)
- **Result: 10x context expansion with zero main thread cost**

## Implementation Checklist

When considering agent parallelism:

- [ ] Can this work be divided into independent units?
- [ ] Would sequential processing take >3 round trips?
- [ ] Is each unit large enough to justify agent overhead? (>500 lines or >1k tokens)
- [ ] Can agent output be compressed to <200 words?
- [ ] Are 3-6 agents appropriate for this task?

If yes to all: **USE PARALLEL AGENTS**

## Anti-Patterns to Avoid

### ❌ Agent for Single File
```
# BAD - agent overhead not worth it
<invoke name="Task">
  <parameter name="subagent_type">researcher</parameter>
  <parameter name="prompt">Read config.yaml and tell me the timeout value</parameter>
</invoke>

# GOOD - direct read
<invoke name="Read">
  <parameter name="file_path">config.yaml</parameter>
</invoke>
```

### ❌ Sequential Agent Invocations
```
# BAD - defeats the purpose
Message 1: Task(researcher, "analyze module A")
Wait...
Message 2: Task(researcher, "analyze module B")
Wait...

# GOOD - parallel in one message
Message 1:
  Task(researcher, "analyze module A")
  Task(researcher, "analyze module B")
  Task(researcher, "analyze module C")
```

### ❌ Too Many Agents
```
# BAD - 50 agents for 50 files creates scheduling overhead
for file in 50_files:
    spawn agent for file

# GOOD - group into 5-10 agents
for group in 10_groups_of_5:
    spawn agent for group
```

## Conclusion

**The Golden Rule:**
> If a task involves >3 independent units of work, >500 lines each, use parallel agents in a single message.

**The Economics:**
- Agent latency: ~30 seconds
- Sequential latency: 30 seconds × N units
- Parallel latency: 30 seconds (all units simultaneously)
- Context saved: 99% (summaries vs raw data)

**The Result:**
- N× speedup (where N = number of agents)
- 99% context savings
- Cleaner main thread focus
- Unlimited effective context (each agent = 200k)
