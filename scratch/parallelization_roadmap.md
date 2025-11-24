# Parallelization Optimization Roadmap

**Status:** Analysis Complete  
**Goal:** Maximize threading, batching, and parallel processing across all components  
**Hardware Constraints:** NONE (unlimited bandwidth)

---

## Executive Summary

**Current State:**
- ✅ Swarm.py: 50 workers, optimal mass parallelization
- ✅ Council.py: Personas run in parallel within rounds
- ⚠️ Hook execution: 21 hooks run sequentially (~1050ms latency)
- ⚠️ Agent delegation: Sequential pattern (underutilized)
- ⚠️ Default max_workers: 10 (should be 50+)

**Impact Potential:** 50-100× speedup on common operations

---

## Priority 1: CRITICAL (Immediate Implementation)

### 1.1 Parallelize Hook Execution

**Problem:**
- 21 UserPromptSubmit hooks run SEQUENTIALLY
- Latency: ~1050ms (21 × 50ms) per user prompt
- Blocks every user interaction

**Solution:**
Create parallel hook executor that batches independent hooks

**Implementation:**
1. Analyze hook dependencies (which must run sequentially)
2. Create dependency graph
3. Build hook_executor.py with ThreadPoolExecutor
4. Update settings.json to use batched execution

**Impact:** 10-20× speedup (1050ms → 50-100ms)

---

### 1.2 Enforce Parallel Agent Delegation Pattern

**Problem:**
- Claude CAN spawn multiple agents in parallel
- Current behavior: Sequential agent calls
- Wastes free context bandwidth

**Solution:**
Update CLAUDE.md to MANDATE parallel agent invocation:

```
RULE: When delegating to 2+ agents, MUST use single message with multiple Task calls
FORBIDDEN: Sequential agent delegation
```

Add hook to detect and BLOCK sequential agent patterns.

**Implementation:**
1. Update CLAUDE.md § Agent Delegation
2. Create detect_sequential_agents.py hook (PreToolUse:Task)
3. Update meta_cognition_performance.py to remind about parallel agents

**Impact:** N× speedup for N agents (3 agents = 3× faster)

---

## Priority 2: HIGH (Next Sprint)

### 2.1 Increase Default max_workers

**Problem:**
- parallel.py defaults to max_workers=10
- Hardware supports 50+ concurrent threads
- 5× performance left on table

**Solution:**
```python
# Update scripts/lib/parallel.py

def run_parallel(
    func: Callable,
    items: List[Any],
    max_workers: int = 50,  # Changed from 10
    desc: str = "Processing",
    fail_fast: bool = False,
):
```

**Implementation:**
1. Update parallel.py defaults (10 → 50)
2. Add auto-tuning: `max_workers = min(len(items), 50)`
3. Update all scripts using parallel.py

**Impact:** 5× speedup for batch I/O operations

---

### 2.2 Add Oracle Batch Mode

**Problem:**
- Consulting 3 personas = 3 sequential oracle.py calls
- Each call: ~3s (total: 9s)
- Could be parallelized to 3s

**Solution:**
Add --batch mode to oracle.py:

```bash
# Sequential (9s)
oracle.py --persona judge "proposal"
oracle.py --persona critic "proposal"
oracle.py --persona skeptic "proposal"

# Parallel (3s)
oracle.py --batch judge,critic,skeptic "proposal"
```

**Implementation:**
1. Add --batch flag to oracle.py
2. Use ThreadPoolExecutor to call personas in parallel
3. Aggregate results in structured output
4. Update CLAUDE.md to recommend batch mode

**Impact:** 3-5× speedup for multi-persona consultation

---

### 2.3 Optimize Council Multi-Round Deliberation

**Problem:**
- Round 2 waits for Round 1 to fully complete
- Arbiter synthesis is sequential bottleneck
- Could overlap rounds speculatively

**Solution:**
Speculative parallel rounds:
- Round N personas start while Round N-1 Arbiter is synthesizing
- If convergence detected, cancel Round N
- If not converged, Round N results ready immediately

**Implementation:**
1. Refactor council.py deliberation loop
2. Add speculative execution mode
3. Add cancellation logic for converged states

**Impact:** 30-50% speedup for multi-round councils

---

## Priority 3: MEDIUM (Future Optimization)

### 3.1 Context Offloading to Parallel Agents

**Problem:**
- Large file reads (1000+ lines) pollute main context
- Reading 10 files = 10,000 lines in main context
- Agent context is FREE (separate window)

**Solution:**
Systematically delegate heavy I/O to parallel agents:

```
Instead of:
- Read file1.py (1000 lines)
- Read file2.py (1000 lines)
- Read file3.py (1000 lines)
Total: 3000 lines in main context

Use:
- Spawn 3 Explore agents in parallel
- Each agent: Read 1 file, return summary (50 lines)
Total: 150 lines in main context (95% savings)
```

**Implementation:**
1. Add delegation patterns to CLAUDE.md
2. Create agent_offload.py helper
3. Update hooks to suggest agent delegation for large operations

**Impact:** 50-90% context savings on large operations

---

### 3.2 Hook Execution Monitoring

**Problem:**
- No visibility into hook performance
- Cannot identify slow hooks
- Cannot optimize without data

**Solution:**
Add hook performance tracker:

```python
# .claude/hooks/hook_performance_tracker.py
# Records execution time per hook
# Outputs slowest hooks weekly
# Suggests optimization targets
```

**Implementation:**
1. Create hook_performance_tracker.py (PostToolUse)
2. Store timing data in .claude/memory/hook_performance.jsonl
3. Add weekly report to upkeep.py

**Impact:** Data-driven optimization (identify slow hooks)

---

## Implementation Priority Queue

| Priority | Item | Impact | Effort | ROI |
|----------|------|--------|--------|-----|
| 🔴 P1 | Parallelize hooks | 10-20× | Medium | 🔥🔥🔥 |
| 🔴 P1 | Enforce parallel agents | N× | Low | 🔥🔥🔥 |
| 🟡 P2 | Increase max_workers | 5× | Trivial | 🔥🔥 |
| 🟡 P2 | Oracle batch mode | 3-5× | Low | 🔥🔥 |
| 🟡 P2 | Speculative council rounds | 30-50% | High | 🔥 |
| 🟢 P3 | Context offloading | 50-90% | Medium | 🔥 |
| 🟢 P3 | Hook monitoring | Data | Low | 🔥 |

---

## Quick Wins (Can Implement Today)

1. **Update parallel.py default (5min)**
   - Change max_workers: 10 → 50
   - Immediate 5× speedup

2. **Add parallel agent reminder to CLAUDE.md (10min)**
   - Document parallel invocation pattern
   - Update meta_cognition hook

3. **Create oracle batch mode (30min)**
   - Add --batch flag
   - Parallel persona execution

**Total time:** 45 minutes  
**Total impact:** 15-25× speedup on common operations

---

## Long-Term Vision

**Ultimate State:**
- All hooks run in parallel (dependency-aware batching)
- All agents spawn in parallel by default
- All file operations use max parallelization (50+ workers)
- All oracle consultations batched
- Context offloading standard practice

**Result:**
- 50-100× faster overall system
- 90% context savings on large operations
- Sub-100ms latency for all hooks
- Optimal hardware utilization

**Philosophy:**
> "Hardware is cheap. Bandwidth is free. Sequential execution is a bug."
> — The Whitebox Manifesto
