# Circuit Breaker & Memory Protection System Design

## Problem Statement
As the AI framework grows more sophisticated, we need automatic protection against:
1. **Runaway Loops** - Hooks triggering hooks, tool failures repeating infinitely
2. **Memory Leaks** - Unbounded JSONL/JSON growth, session state accumulation
3. **Resource Exhaustion** - Agent spawn storms, external API abuse

## Design Philosophy
- **FAIL FAST** - Stop immediately when pattern detected, don't wait for OOM
- **SELF-HEALING** - Auto-rotate logs, prune old state, reset circuit breakers
- **OBSERVABLE** - Clear telemetry showing what fired and why
- **CONFIGURABLE** - Thresholds tunable via config, not hardcoded

---

## 1. Circuit Breaker System

### Pattern Detection

**Loop Types:**
- **Hook Recursion** - Same hook executing >N times in M turns
- **Tool Failure Loop** - Same tool failing >N times in M turns
- **Sequential Abuse** - Same tool called >N times sequentially
- **Agent Spawn Storm** - >N agents spawned in M turns
- **External API Spam** - >N API calls in M seconds

**Detection Strategy:**
```python
# Sliding window counters per pattern type
circuit_state = {
    "hook_recursion": {"window": [], "threshold": 5, "window_size": 10},
    "tool_failure": {"window": [], "threshold": 3, "window_size": 5},
    "sequential_tools": {"window": [], "threshold": 10, "window_size": 1},
    "agent_spawn": {"window": [], "threshold": 5, "window_size": 10},
    "external_api": {"window": [], "threshold": 10, "window_size": 60}  # 10/min
}
```

**State Transitions:**
- **CLOSED** (normal) → **OPEN** (blocked) when threshold exceeded
- **OPEN** → **HALF_OPEN** after cooldown period (exponential backoff)
- **HALF_OPEN** → **CLOSED** if next attempt succeeds
- **HALF_OPEN** → **OPEN** if next attempt fails (backoff increases)

**Enforcement:**
- **OPEN state**: Hard block with error message + cooldown time
- **HALF_OPEN**: Allow 1 probe attempt, monitor closely
- **CLOSED**: Normal operation, sliding window monitoring

### Cooldown Strategy
```
Attempt 1: 5s cooldown
Attempt 2: 10s cooldown
Attempt 3: 30s cooldown
Attempt 4: 60s cooldown
Attempt 5+: 300s cooldown (5 min) + alert to user
```

---

## 2. Memory Protection System

### JSONL Rotation (Telemetry Files)

**Files:**
- `performance_telemetry.jsonl`
- `batching_telemetry.jsonl`
- `fallacy_telemetry.jsonl`
- `background_telemetry.jsonl`

**Strategy:**
- **Rotation Trigger**: File >50KB OR >1000 lines OR >7 days old
- **Rotation Action**:
  - Rename current to `{name}.{timestamp}.jsonl.gz` (compressed)
  - Keep last 5 rotations (delete older)
  - Create fresh file
- **Automatic**: Runs on SessionStart hook (no user intervention)

### Session State Pruning

**Files:**
- `session_{id}_state.json` (per session)

**Strategy:**
- **Prune Trigger**: Session >7 days old AND not active
- **Prune Action**:
  - Archive to `session_archives/{date}/{id}_state.json.gz`
  - Delete from active memory
  - Keep last 10 sessions in active memory max
- **Automatic**: Runs on SessionStart (cleanup old sessions)

### Evidence Ledger Truncation

**Problem**: `evidence_ledger` array grows unbounded in session state

**Strategy:**
- **Hard Limit**: Max 100 entries per session
- **Truncation**: Keep last 100 entries when saving state
- **Aggregation**: Summarize old entries (count, avg boost) before discarding

### Tool History Cap

**Problem**: `tool_history` tracked for pattern detection grows unbounded

**Strategy:**
- **Hard Limit**: Max 50 entries (covers 10-turn sliding window at 5 tools/turn)
- **Circular Buffer**: Oldest entries evicted automatically
- **Per-session**: Resets on new session

---

## 3. Resource Limits

### Agent Spawn Rate Limit

**Protection:**
- Max 5 concurrent agents at any time
- Max 10 agent spawns per session (prevents spawn storms)
- Cooldown: 10s between agent spawns

**Bypass**: User keyword "SUDO PARALLEL" allows burst spawning

### External API Rate Limits

**Oracle/Swarm/Research:**
- Max 10 calls per minute (sliding window)
- Max 50 calls per session
- Cost tracking: Warn at $1 spent, block at $5 spent

**Enforcement:**
- PreToolUse hook blocks `Bash` if command contains `oracle.py/swarm.py/research.py`
- Checks rate limits, returns cooldown time if exceeded

---

## 4. Auto-Recovery Mechanisms

### Self-Healing Actions

**On Circuit Breaker Trip:**
1. Log incident to `.claude/memory/circuit_breaker_incidents.jsonl`
2. Display clear message: "Circuit breaker tripped: {reason}. Cooldown: {time}s"
3. Suggest workaround: "Use scratch script or agent delegation instead"
4. Auto-reset after cooldown expires

**On Memory Threshold:**
1. Auto-rotate logs (compress + archive)
2. Prune old sessions (move to archive)
3. Truncate evidence ledgers (keep last 100)
4. Report: "Memory cleanup: {files_rotated}, {sessions_pruned}, {space_freed}"

**On Resource Exhaustion:**
1. Kill oldest running agent if max concurrent reached
2. Force cooldown on external APIs
3. Alert user: "Resource limit reached. Pausing to prevent exhaustion."

---

## 5. Implementation Plan

### Files to Create

**Libraries:**
- `scripts/lib/circuit_breaker.py` - Core circuit breaker logic
- `scripts/lib/memory_cleanup.py` - Log rotation, session pruning
- `scripts/lib/resource_limits.py` - Agent/API rate limiting

**Hooks:**
- `.claude/hooks/circuit_breaker_monitor.py` (PostToolUse - track patterns)
- `.claude/hooks/circuit_breaker_gate.py` (PreToolUse - enforce blocks)
- `.claude/hooks/memory_janitor.py` (SessionStart - auto-cleanup)
- `.claude/hooks/resource_limiter.py` (PreToolUse - rate limits)

**Tools:**
- `scripts/ops/circuit_status.py` - Show current circuit breaker state
- `scripts/ops/reset_circuit.py` - Manual reset (admin override)
- `scripts/ops/memory_report.py` - Show memory usage + cleanup stats

### Testing

**Test Scenarios:**
1. Trigger hook recursion (hook calls itself 6 times) → Verify circuit trips
2. Fail same tool 4 times in 5 turns → Verify exponential backoff
3. Spawn 6 agents simultaneously → Verify rate limit blocks 6th
4. Call oracle.py 11 times in 30s → Verify API rate limit
5. Let telemetry grow >1000 lines → Verify auto-rotation
6. Create 15 sessions → Verify old sessions pruned (keep 10)

**Success Criteria:**
- All 6 test scenarios pass
- No false positives (legitimate usage not blocked)
- Memory usage stays <5MB for .claude/memory/
- Circuit breakers auto-reset after cooldown
- User gets clear feedback on why blocked + how to bypass

---

## 6. Configuration

**File:** `.claude/memory/circuit_breaker_config.json`

```json
{
  "circuit_breakers": {
    "hook_recursion": {
      "enabled": true,
      "threshold": 5,
      "window_turns": 10,
      "cooldown_base_seconds": 5
    },
    "tool_failure": {
      "enabled": true,
      "threshold": 3,
      "window_turns": 5,
      "cooldown_base_seconds": 10
    },
    "sequential_tools": {
      "enabled": true,
      "threshold": 10,
      "window_turns": 1,
      "cooldown_base_seconds": 5
    },
    "agent_spawn": {
      "enabled": true,
      "threshold": 5,
      "window_turns": 10,
      "cooldown_base_seconds": 10
    },
    "external_api": {
      "enabled": true,
      "threshold": 10,
      "window_seconds": 60,
      "session_max": 50,
      "cooldown_base_seconds": 30
    }
  },
  "memory_limits": {
    "telemetry_max_lines": 1000,
    "telemetry_max_kb": 50,
    "telemetry_max_age_days": 7,
    "telemetry_keep_rotations": 5,
    "session_max_active": 10,
    "session_max_age_days": 7,
    "evidence_ledger_max": 100,
    "tool_history_max": 50
  },
  "resource_limits": {
    "max_concurrent_agents": 5,
    "max_agents_per_session": 10,
    "agent_spawn_cooldown_seconds": 10,
    "api_rate_limit_per_minute": 10,
    "api_session_max": 50,
    "api_cost_warn_usd": 1.0,
    "api_cost_block_usd": 5.0
  }
}
```

---

## 7. Monitoring Dashboard

**Command:** `/circuit-status`

**Output:**
```
🔒 CIRCUIT BREAKER STATUS

Active Breakers:
  • tool_failure: OPEN (cooldown: 23s remaining)
    - Last trip: Turn 45 (pytest failed 3x in 5 turns)
    - Next attempt allowed: Turn 48

  • All others: CLOSED (normal operation)

Memory Health:
  • Total: 487KB / 5MB limit (9.7% used)
  • Telemetry: 308 lines (30% of 1000 limit)
  • Sessions: 10 active (at limit)
  • Next auto-cleanup: SessionStart

Resource Usage:
  • Agents: 2/5 concurrent (40% capacity)
  • API calls: 7/10 this minute (70% rate)
  • API cost: $0.34 / $1.00 warn threshold

Incidents Last 24h:
  • 2 circuit trips (tool_failure x2)
  • 0 memory cleanups
  • 0 resource exhaustions
```

---

## Summary

**Key Benefits:**
1. **Prevents infinite loops** - Hard stops on detected patterns
2. **Prevents memory leaks** - Auto-rotation, pruning, truncation
3. **Prevents resource exhaustion** - Rate limits on agents/APIs
4. **Self-healing** - No manual intervention required
5. **Observable** - Clear telemetry and status dashboard
6. **Configurable** - Easy tuning without code changes

**Zero Maintenance:**
- All cleanups automatic (SessionStart hook)
- All circuit resets automatic (cooldown expiry)
- All rate limits automatic (sliding windows)

**User Experience:**
- Clear error messages explaining why blocked
- Cooldown time displayed (not vague "try again later")
- Bypass keywords for intentional bursts (SUDO)
- Status command to understand current state
