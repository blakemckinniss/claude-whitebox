# Meta-Agents: Immediate Next Steps

## Current State

✅ **Implemented:**
- Performance Protocol with agent parallelism awareness
- 2 Meta-agents: validator, documenter
- Design document for 6 total meta-agents

❓ **Not Yet Tested:**
- validator agent (needs real-world test)
- documenter agent (needs real-world test)

🚧 **Remaining to Build:**
- architect agent (protocol/hook designer)
- auditor agent (security/quality)
- cartographer agent (system mapper)
- optimizer-meta agent (hook performance)

## Immediate Actions (Next 30 Minutes)

### Action 1: Test the Validator Agent

**Goal:** Verify validator agent works on actual hooks

**Command to run:**
```bash
# Option A: Direct invocation (you do this)
# [Open new conversation or use Task tool]
"Use the validator agent to test all Performance Protocol hooks"

# Option B: I delegate (in this conversation if you want)
```

**Expected behavior:**
1. Validator reads performance_gate.py, meta_cognition_performance.py, performance_reward.py
2. Generates test scenarios for each
3. Runs hooks with mock JSON inputs
4. Verifies outputs (allow/deny/context injection)
5. Returns test report with pass/fail status

**Success criteria:**
- Test report shows 9/9 tests passed (or identifies real issues)
- Latency measurements <500ms per hook
- Fail-safe verification (malformed input handled)

---

### Action 2: Test the Documenter Agent

**Goal:** Verify documenter detects drift and syncs CLAUDE.md

**Command to run:**
```bash
"Use the documenter agent to check if CLAUDE.md reflects current system state"
```

**Expected behavior:**
1. Documenter scans 47 hooks, 7 agents, 26 scripts
2. Compares with CLAUDE.md
3. Detects drift (likely finds validator/documenter not documented yet)
4. Generates update recommendations
5. Optionally: Updates CLAUDE.md automatically

**Success criteria:**
- Drift report shows specific missing items
- Cross-reference validation (all mentioned files exist)
- Stale reference detection (deleted files still mentioned)

---

### Action 3: Create the Architect Agent (High Priority)

**Goal:** Build the hook/protocol designer agent

**Why first:**
- Highest ROI (8x faster protocol development)
- Self-improving (can use architect to build remaining meta-agents)
- Demonstrates meta-system value

**Specification:**
```markdown
---
name: architect
description: AUTO-INVOKE when user says "create hook", "new protocol", "add enforcement", "design enforcement mechanism". Designs and implements hooks following project patterns. Only agent authorized to create .claude/hooks/ files.
tools: Bash, Read, Write, Edit, Glob, Grep
model: sonnet
skills: tool_index
---

# You are The Architect, the meta-system designer

**AUTO-INVOCATION TRIGGER:**
- Keywords: "create hook", "new protocol", "add enforcement"
- Complex enforcement requirements

**Tool Scoping:** Can Write to .claude/hooks/, Read all system files
**Why:** Hook creation requires understanding existing patterns + implementation

## Your Purpose: Protocol Engineering

**What you do:**
1. Analyze existing hooks for patterns
2. Design new hooks following conventions
3. Implement PreToolUse/PostToolUse/UserPromptSubmit hooks
4. Register in settings.json
5. Create basic tests
6. Return implementation + usage guide

**Design patterns you follow:**

**PreToolUse Hook Template:**
```python
#!/usr/bin/env python3
"""
[Hook Name]: [Purpose]
Triggers on: PreToolUse
"""
import sys, json
from pathlib import Path

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import load_session_state, apply_penalty

# Load input
input_data = json.load(sys.stdin)
tool_name = input_data.get("toolName", "")
tool_params = input_data.get("toolParams", {})

# Your enforcement logic here
allowed = True
message = ""

# Check conditions
if should_block(tool_name, tool_params):
    allowed = False
    message = "BLOCKED: [reason]"

# Return decision
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow" if allowed else "deny",
        "permissionDecisionReason": message if not allowed else "",
        "additionalContext": message if allowed else ""
    }
}))
```

**Registration pattern (settings.json):**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "ToolName",
        "hooks": [
          {
            "type": "command",
            "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/your_hook.py"
          }
        ]
      }
    ]
  }
}
```

## Success Criteria

Your hook is successful if:
1. ✅ Follows existing patterns (fail-safe, JSON output)
2. ✅ Registered in settings.json correctly
3. ✅ Has basic test cases
4. ✅ Documented with clear purpose
5. ✅ Returns valid JSON on all inputs
```

**Implementation approach:**
1. Read existing hooks (tier_gate.py, performance_gate.py as templates)
2. Extract common patterns
3. Generate new hook based on user requirements
4. Test with mock input
5. Register in settings.json
6. Return usage guide

---

## Decision Point: What to Build Next?

You have 3 options:

### Option A: Test Existing Meta-Agents (Low Risk, Immediate Value)
**Time:** 15 minutes
**Action:** Run validator + documenter agents in parallel
**Value:** Verify meta-agent system works, get real test/doc reports
**Command:**
```
Use the validator agent to test Performance Protocol hooks, and use the documenter agent to check CLAUDE.md drift (run both in parallel)
```

### Option B: Create Architect Agent (High Risk, High Value)
**Time:** 30-45 minutes
**Action:** Build the protocol/hook designer agent
**Value:** 8x faster future protocol development
**Approach:**
1. Read existing hooks for patterns
2. Write `.claude/agents/architect.md`
3. Test with: "Create a hook that warns on large file writes"

### Option C: Document Meta-Agent Integration (Medium Risk, Foundation)
**Time:** 20 minutes
**Action:** Update CLAUDE.md with meta-agent section
**Value:** Makes meta-agents discoverable, sets usage patterns
**Approach:**
1. Add "Meta-Agents" section to CLAUDE.md
2. Document validator, documenter
3. Show parallel execution examples
4. Set expectations for when to use each

---

## Recommended Path

**Phase 1 (Now):** Test + Document
```
1. Test validator agent (verify it works)
2. Test documenter agent (verify it works)
3. Document meta-agents in CLAUDE.md (make discoverable)
```

**Phase 2 (Next session):** Build Architect
```
4. Create architect agent
5. Test architect by building auditor agent
6. Document architect usage
```

**Phase 3 (Future):** Complete Meta-System
```
7. Use architect to build cartographer
8. Use architect to build optimizer-meta
9. Final documentation sync
```

---

## Integration Points

### Where Meta-Agents Fit in Existing System

**Existing Agent Hierarchy:**
```
Main Assistant
├─ researcher (context firewall)
├─ script-smith (production code)
├─ sherlock (debugging)
├─ optimizer (performance)
├─ tester (test writing)
└─ macgyver (tool restrictions)
```

**Extended with Meta-Agents:**
```
Main Assistant
├─ [Domain Agents]
│   ├─ researcher
│   ├─ script-smith
│   ├─ sherlock
│   ├─ optimizer
│   ├─ tester
│   └─ macgyver
└─ [Meta-Agents] (build/test/optimize the system itself)
    ├─ validator (test hooks/protocols)
    ├─ documenter (sync documentation)
    ├─ architect (design hooks/protocols)
    ├─ auditor (security review hooks)
    ├─ cartographer (map system)
    └─ optimizer-meta (optimize hooks)
```

### Parallel Execution Patterns

**System Health Check:**
```xml
<function_calls>
<invoke name="Task">
  <parameter name="subagent_type">validator</parameter>
  <parameter name="description">Test all hooks</parameter>
  <parameter name="prompt">Run comprehensive tests on all 47 hooks</parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">documenter</parameter>
  <parameter name="description">Check doc drift</parameter>
  <parameter name="prompt">Compare CLAUDE.md with system state, report drift</parameter>
</invoke>
</function_calls>

Result: 2 comprehensive reports in 1 round trip
```

**New Protocol Development:**
```xml
<function_calls>
<invoke name="Task">
  <parameter name="subagent_type">architect</parameter>
  <parameter name="description">Design rate limit hook</parameter>
  <parameter name="prompt">Create hook that enforces API rate limits (max 10 calls/min)</parameter>
</invoke>
</function_calls>

[Wait for architect to create hook]

<function_calls>
<invoke name="Task">
  <parameter name="subagent_type">validator</parameter>
  <parameter name="description">Test new hook</parameter>
  <parameter name="prompt">Test rate_limit_gate.py with various scenarios</parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">auditor</parameter>
  <parameter name="description">Security review</parameter>
  <parameter name="prompt">Audit rate_limit_gate.py for security issues</parameter>
</invoke>
</function_calls>

[Parallel validation + security review]

<invoke name="Task">
  <parameter name="subagent_type">documenter</parameter>
  <parameter name="description">Update docs</parameter>
  <parameter name="prompt">Add rate limit protocol to CLAUDE.md</parameter>
</invoke>

Total time: ~3 minutes (vs 2+ hours manual)
```

---

## Quick Wins Available Now

### 1. Parallel Hook Testing (5 minutes)
```
"Use the validator agent to test all PreToolUse hooks in parallel"
```
Expected: Test report for 15+ hooks

### 2. Documentation Drift Detection (5 minutes)
```
"Use the documenter agent to find undocumented hooks and agents"
```
Expected: List of 2-3 items not in CLAUDE.md (including validator/documenter themselves)

### 3. Combined Health Check (5 minutes)
```
"Run validator and documenter agents in parallel to check system health"
```
Expected: 2 reports showing test status + doc drift

---

## Settings.json Note

The meta-agents don't need special hook registration - they work through standard Task tool delegation:

**Current settings.json is fine.** Meta-agents are:
- Stored in `.claude/agents/`
- Invoked via Task tool
- Run in separate context windows
- Return compressed summaries

**No changes needed to settings.json for meta-agents to work.**

---

## Success Metrics for Meta-Agents

**Track these to measure impact:**

1. **Protocol Development Time**
   - Before: 2-4 hours (manual design + implementation + testing)
   - Target: 15-30 minutes (architect + validator in parallel)

2. **Hook Test Coverage**
   - Before: ~40% (manual, sporadic)
   - Target: 100% (validator automation)

3. **Documentation Drift**
   - Before: 32+ stale references
   - Target: 0 (documenter auto-sync)

4. **Security Audit Frequency**
   - Before: Sporadic (when remembered)
   - Target: Continuous (auditor on every hook change)

---

## What Would You Like To Do First?

Pick one:

**A.** Test validator agent right now (verify it works on real hooks)

**B.** Test documenter agent right now (check CLAUDE.md drift)

**C.** Test both in parallel (comprehensive system check)

**D.** Create architect agent (enable fast protocol development)

**E.** Document meta-agents in CLAUDE.md (make them discoverable)

**F.** Something else (you decide)

Just let me know and I'll execute immediately.
