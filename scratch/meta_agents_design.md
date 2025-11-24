# Meta-Agents: Agents That Build Agents

## The Problem

You have a complex meta-system:
- 47 hooks across 8 lifecycle events
- 26 operational scripts
- 20+ protocols documented in CLAUDE.md
- Epistemology system with rewards/penalties
- Agent delegation infrastructure

**Current gap:** No agents specialized in building/testing/optimizing this meta-system itself.

## The Solution: 6 New Meta-Agents

### 1. The Architect (Hook Designer)

**Name:** `architect`
**Purpose:** Design and implement new hooks/protocols
**Tools:** Bash, Read, Write, Edit, Glob, Grep
**Trigger:** User says "create new hook", "add new protocol", "design enforcement"

**Capabilities:**
- Analyzes existing hook patterns
- Designs new hooks following project conventions
- Implements PreToolUse/PostToolUse/UserPromptSubmit hooks
- Registers in settings.json
- Tests hook execution

**Example Use:**
```
User: "Create a hook that blocks commits without tests"

Architect:
1. Reads existing hooks (tier_gate.py, command_prerequisite_gate.py)
2. Designs test_coverage_gate.py (PreToolUse on Bash "git commit")
3. Implements logic: checks if modified files have corresponding tests
4. Registers in settings.json
5. Tests with dry-run commit
6. Returns: Hook implementation + test results
```

**Value:** Reduces time to create new enforcement mechanisms from hours to minutes.

---

### 2. The Validator (Hook Tester)

**Name:** `validator`
**Purpose:** Test hooks and protocols systematically
**Tools:** Bash, Read, Write, Glob, Grep
**Trigger:** User says "test hooks", "verify protocols", "check enforcement"

**Capabilities:**
- Generates test scenarios for all hooks
- Runs hooks with mock inputs
- Verifies expected behavior (allow/deny/context injection)
- Checks hook registration in settings.json
- Detects hook collisions or conflicts

**Example Use:**
```
User: "Test all performance protocol hooks"

Validator:
1. Finds performance-related hooks (performance_gate.py, performance_reward.py, meta_cognition_performance.py)
2. Generates test inputs:
   - Bash loop command (should block)
   - Normal command (should allow)
   - Parallel tool calls (should reward)
3. Runs each hook with test inputs
4. Verifies outputs match expectations
5. Returns: Test report (15/15 tests passed)
```

**Value:** Ensures hooks work as designed, catches regressions.

---

### 3. The Cartographer (System Mapper)

**Name:** `cartographer`
**Purpose:** Map and visualize the entire meta-system
**Tools:** Bash, Read, Write, Glob, Grep
**Trigger:** User says "map system", "visualize protocols", "show dependencies"

**Capabilities:**
- Maps all hooks → lifecycle events
- Traces protocol dependencies (which hooks enforce which protocols)
- Generates dependency graphs (hook → script → library)
- Identifies orphaned hooks or unused protocols
- Creates visual diagrams (mermaid/graphviz)

**Example Use:**
```
User: "Map the Epistemological Protocol"

Cartographer:
1. Finds all epistemology-related components:
   - Hooks: confidence_gate.py, tier_gate.py, evidence_tracker.py, etc.
   - Library: scripts/lib/epistemology.py
   - State: .claude/memory/session_*_state.json
2. Maps data flow:
   UserPromptSubmit → confidence_init.py → initialize session
   PreToolUse → tier_gate.py → check confidence → block/allow
   PostToolUse → evidence_tracker.py → update confidence
3. Generates mermaid diagram
4. Identifies: 12 hooks, 1 library, 3 state files, 45 integration points
```

**Value:** Understand complex system interactions, find gaps.

---

### 4. The Auditor (Meta-Quality Gate)

**Name:** `auditor`
**Purpose:** Audit hooks and scripts for quality/security
**Tools:** Bash, Read, Glob, Grep
**Trigger:** User says "audit hooks", "review meta-system quality"

**Capabilities:**
- Runs audit.py on all hooks
- Checks for common hook anti-patterns:
  - Fail-open on error (security risk)
  - Missing error handling
  - Incorrect JSON output format
  - Performance issues (slow hooks block tools)
- Verifies hook execution permissions
- Checks settings.json correctness

**Example Use:**
```
User: "Audit all PreToolUse hooks for security"

Auditor:
1. Finds all PreToolUse hooks (15 files)
2. For each hook:
   - Runs audit.py (security scan)
   - Checks error handling (must not crash)
   - Verifies fail-safe behavior (fail closed, not open)
   - Tests with malformed input
3. Detects issues:
   - old_hook.py: Fails open on exception (CRITICAL)
   - slow_hook.py: Takes 5 seconds (WARNING)
4. Returns: Security report with recommendations
```

**Value:** Prevents security holes in enforcement layer.

---

### 5. The Optimizer-Meta (Meta-System Performance)

**Name:** `optimizer-meta`
**Purpose:** Optimize hooks and protocols for performance
**Tools:** Bash, Read, Write, Edit, Glob, Grep
**Trigger:** User says "optimize hooks", "speed up enforcement"

**Capabilities:**
- Profiles hook execution time
- Identifies slow hooks (>500ms)
- Optimizes hook logic (caching, early returns)
- Parallelizes independent hook checks
- Reduces redundant file reads across hooks

**Example Use:**
```
User: "Why are tool calls slow? Optimize hooks."

Optimizer-Meta:
1. Measures hook execution time per tool:
   - Bash: 5 hooks, total 1.2s per call
   - Write: 5 hooks, total 2.1s per call
2. Profiles individual hooks:
   - ban_stubs.py: 800ms (reads file twice)
   - command_prerequisite_gate.py: 400ms (loads session state 3x)
3. Optimizations:
   - Cache file reads within hook execution
   - Share session state across hooks (single load)
   - Early return patterns
4. Result: Write tool latency 2.1s → 0.6s (3.5x faster)
```

**Value:** Reduces tool latency, improves UX.

---

### 6. The Documenter (Meta-System Documentation)

**Name:** `documenter`
**Purpose:** Auto-generate and maintain CLAUDE.md
**Tools:** Bash, Read, Write, Edit, Glob, Grep
**Trigger:** User says "update docs", "regenerate CLAUDE.md", "document protocols"

**Capabilities:**
- Scans all hooks and extracts metadata (trigger, purpose, behavior)
- Generates protocol documentation from hook implementations
- Updates CLAUDE.md sections automatically
- Creates cross-reference index (protocol → hooks → scripts)
- Validates CLAUDE.md against actual system state

**Example Use:**
```
User: "Update CLAUDE.md to reflect current hook state"

Documenter:
1. Scans all hooks:
   - Extracts docstrings and comments
   - Identifies which protocols they enforce
   - Maps to lifecycle events
2. Compares with CLAUDE.md:
   - Finds 3 undocumented hooks
   - Finds 2 documented protocols with no enforcement
3. Generates updates:
   - Adds new protocol sections
   - Updates tool registry table
   - Adds hook reference table
4. Returns: Updated CLAUDE.md + change summary
```

**Value:** Keeps docs synchronized with reality, reduces drift.

---

## Agent Comparison Matrix

| Agent | Primary Role | Input | Output | Parallelizable? |
|-------|-------------|-------|--------|-----------------|
| **architect** | Create hooks/protocols | Design requirements | Working hook + tests | No (sequential design) |
| **validator** | Test hooks | Hook files | Test report | YES (test hooks in parallel) |
| **cartographer** | Map system | Codebase | Dependency graph | No (needs global view) |
| **auditor** | Quality/security | Hook files | Security report | YES (audit hooks in parallel) |
| **optimizer-meta** | Performance | Hook files | Optimized hooks | No (needs profiling) |
| **documenter** | Documentation | Codebase | Updated CLAUDE.md | No (needs coherent output) |

## Parallel Execution Opportunities

**Scenario:** "Audit and validate all hooks"
```
<function_calls>
<invoke name="Task">
  <parameter name="subagent_type">validator</parameter>
  <parameter name="description">Test all hooks</parameter>
  <parameter name="prompt">Run test scenarios for all 47 hooks, verify behavior</parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">auditor</parameter>
  <parameter name="description">Security audit all hooks</parameter>
  <parameter name="prompt">Check all hooks for security issues, fail-open bugs</parameter>
</invoke>
</function_calls>

Result: Both run in parallel (1 round trip instead of 2)
```

---

## Implementation Priority

### Tier 1 (High Impact, Low Effort)
1. **validator** - Critical for testing hooks as system grows
2. **documenter** - Prevents CLAUDE.md drift (already happening)

### Tier 2 (High Impact, Medium Effort)
3. **architect** - Accelerates protocol development
4. **auditor** - Security critical for enforcement layer

### Tier 3 (Medium Impact, High Effort)
5. **cartographer** - Useful but complex to implement
6. **optimizer-meta** - Performance nice-to-have (hooks already fast)

---

## Agent Templates

### Template: Meta-Agent Frontmatter

```markdown
---
name: architect
description: AUTO-INVOKE when user says "create hook", "new protocol", "add enforcement". Designs and implements hooks following project patterns. Only agent that modifies .claude/hooks/.
tools: Bash, Read, Write, Edit, Glob, Grep
model: sonnet
skills: tool_index
---
```

### Template: Meta-Agent Structure

```markdown
# You are The [Agent Name], the [role]

**AUTO-INVOCATION TRIGGER:**
- User keywords: [...]
- Hook: [optional auto-trigger hook]

**Tool Scoping:** [explain tool access]
**Why:** [rationale for tool scope]

## 🎯 Your Purpose: [One-liner]

[Detailed explanation]

## 📋 The [Agent Name] Protocol

### 1. [Step 1 Name]
[Instructions]

### 2. [Step 2 Name]
[Instructions]

### 3. Return Format
[Expected output structure]

## 🚫 What You Do NOT Do
[Anti-patterns]

## ✅ What You DO
[Best practices]

## 🧠 Your Mindset
[Philosophy]

## 🎯 Success Criteria
[How to know you succeeded]
```

---

## Integration with Existing Agents

### Agent Interaction Patterns

**Scenario 1: New Protocol Development**
```
User: "Create a protocol that enforces API rate limits"

Main → architect (design hook)
  → validator (test hook)
    → auditor (security review)
      → documenter (update CLAUDE.md)
```

**Scenario 2: System Health Check**
```
User: "Is the meta-system healthy?"

Main → (parallel)
  ├─→ validator (test all hooks)
  ├─→ auditor (security audit)
  ├─→ cartographer (map dependencies)
  └─→ optimizer-meta (profile performance)

Main: Synthesize 4 reports → health score
```

**Scenario 3: Hook Optimization**
```
User: "Tool calls are slow, investigate"

Main → optimizer-meta (profile hooks)
  → (if changes needed) architect (redesign)
    → validator (test changes)
      → documenter (update docs)
```

---

## Meta-Agent Benefits

### 1. Accelerated Development
- Creating new protocols: 2 hours → 15 minutes (architect)
- Testing hooks: 30 min → 2 min (validator in parallel)

### 2. Quality Assurance
- Automated security audits (auditor)
- Comprehensive testing (validator)
- Documentation sync (documenter)

### 3. System Understanding
- Dependency visualization (cartographer)
- Performance insights (optimizer-meta)
- Cross-reference index (documenter)

### 4. Maintenance Reduction
- Auto-generated docs (documenter)
- Automated testing (validator)
- Proactive quality gates (auditor)

---

## Implementation Checklist

For each meta-agent:

- [ ] Create `.claude/agents/<name>.md` with frontmatter
- [ ] Document auto-invocation triggers
- [ ] Define tool scope and permissions
- [ ] Write protocol steps
- [ ] Add success criteria
- [ ] Test with example scenarios
- [ ] Register in agent index
- [ ] Update CLAUDE.md with agent description

---

## Anti-Patterns to Avoid

### ❌ Meta-Agent Overuse
- Don't spawn architect for trivial hook tweaks
- Use direct Edit for simple changes

### ❌ Serial Meta-Agent Chains
- Don't: architect → validator → auditor → documenter (serial)
- Do: architect → (validator + auditor in parallel) → documenter

### ❌ Meta-Agent Bloat
- Keep agents focused (single responsibility)
- Don't create "god agent" that does everything

---

## Success Metrics

**Before Meta-Agents:**
- New protocol development: 2-4 hours
- Hook testing: Manual, incomplete
- Documentation: Often stale
- Security audits: Sporadic

**After Meta-Agents:**
- New protocol development: 15-30 minutes (architect + validator)
- Hook testing: Automated, comprehensive (validator)
- Documentation: Auto-synced (documenter)
- Security audits: Continuous (auditor)

**Estimated Impact:**
- 8x faster protocol development
- 100% hook test coverage (vs ~40% manual)
- Zero doc drift (auto-sync)
- Continuous security posture

---

## Next Steps

1. **Immediate:** Create `validator` agent (highest ROI)
2. **This week:** Create `documenter` agent (prevents drift)
3. **Next week:** Create `architect` agent (accelerates development)
4. **Future:** Create remaining agents based on need
