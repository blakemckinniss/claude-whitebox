# Auto-Tuning Scratch Enforcement Design

## The Problem
Manual tuning requires human revisiting → gets abandoned → feature dies.

## Solution: Self-Tuning System

### Architecture: Three-Phase Auto-Evolution

```
Phase 1: OBSERVE (Turns 1-20)
  ↓ (collect data, establish baseline)
Phase 2: WARN (Auto-triggers when pattern confidence >70%)
  ↓ (escalate if violations continue)
Phase 3: ENFORCE (Auto-triggers when ROI proven >3x)
  ↓ (self-adjusts thresholds based on false positive rate)
```

### Component 1: Adaptive Telemetry Hook
**File:** `.claude/hooks/scratch_enforcer.py`

**State File:** `.claude/memory/scratch_enforcement_state.json`

**Tracked Metrics:**
```json
{
  "phase": "observe|warn|enforce",
  "total_turns": 150,
  "patterns_detected": {
    "multi_read": {"count": 12, "avg_turns_wasted": 4.2, "scripts_written": 3},
    "multi_grep": {"count": 8, "avg_turns_wasted": 3.1, "scripts_written": 2},
    "multi_edit": {"count": 5, "avg_turns_wasted": 2.8, "scripts_written": 1}
  },
  "thresholds": {
    "detection_window": 5,  // turns to look back
    "min_repetitions": 4,   // tool calls to trigger
    "phase_transition_confidence": 0.70,
    "roi_threshold": 3.0    // 3x time savings required
  },
  "false_positives": {
    "total": 2,
    "rate": 0.05,  // 5% acceptable, >10% = loosen thresholds
    "last_adjustment": "2025-11-23T10:30:00"
  },
  "auto_adjustments": [
    {"turn": 45, "action": "transitioned_to_warn", "reason": "pattern_confidence_70%"},
    {"turn": 92, "action": "transitioned_to_enforce", "reason": "roi_proven_4.2x"},
    {"turn": 103, "action": "loosened_threshold_4_to_5", "reason": "false_positive_rate_12%"}
  ]
}
```

### Component 2: Self-Assessment Logic

**Trigger Conditions (Automatic):**

1. **Phase 1 → Phase 2 (OBSERVE → WARN):**
   - After 20 turns OR
   - Pattern detected 3+ times with consistent waste (variance <20%)
   - Confidence: `(scripts_written / patterns_detected) > 0.3`

2. **Phase 2 → Phase 3 (WARN → ENFORCE):**
   - Proven ROI: `avg_turns_saved / avg_turns_scripting > 3.0` AND
   - False positive rate <10% AND
   - At least 5 pattern detections

3. **Phase 3 → Phase 2 (BACKTRACK):**
   - False positive rate >15% for 10 consecutive turns
   - Auto-loosen: `min_repetitions += 1`

4. **Threshold Auto-Tuning:**
   - Every 50 turns: analyze false positive rate
   - If >10%: increase `min_repetitions` by 1
   - If <3%: decrease `min_repetitions` by 1 (more aggressive)
   - Log all adjustments with reasoning

### Component 3: Pattern Detection Engine

**Detectable Patterns:**

```python
PATTERNS = {
    "multi_read": {
        "tools": ["Read"],
        "window": 5,  # turns
        "threshold": 4,  # calls
        "exemptions": ["MANUAL", "reading test files sequentially"]
    },
    "multi_grep": {
        "tools": ["Grep"],
        "window": 5,
        "threshold": 4,
        "exemptions": ["iterative refinement with different patterns"]
    },
    "multi_edit": {
        "tools": ["Edit"],
        "window": 5,
        "threshold": 3,  # lower threshold - edits are expensive
        "exemptions": ["fixing syntax errors from previous edit"]
    },
    "file_iteration": {
        "tools": ["Read", "Edit", "Grep"],
        "detection": "regex in prompt: 'for each', 'all files', 'process.*files'",
        "threshold": 1,  # immediate trigger
        "exemptions": ["agent delegation mentioned"]
    }
}
```

### Component 4: Response Templates

**Phase 1 (OBSERVE):** Silent logging only
- No user-facing output
- Build confidence in detection accuracy

**Phase 2 (WARN):**
```
⚠️ SCRATCH SCRIPT OPPORTUNITY DETECTED

Pattern: {pattern_name}
Tools Used: {tool_list}
Turns Wasted: ~{estimated_waste}
Suggested Script: scratch/{suggested_name}.py

Auto-escalation: This will become a HARD BLOCK after ROI proven (3x savings)
Current Confidence: {confidence}% (need 70% + 3x ROI)

Bypass: Include "MANUAL" keyword if intentional
```

**Phase 3 (ENFORCE):**
```
🚫 SCRATCH SCRIPT REQUIRED

Pattern: {pattern_name} (detected {count} times, avg {avg_waste} turns wasted)
Proven ROI: {roi}x time savings via scripting

BLOCKED: Write script to scratch/{suggested_name}.py first

Bypass: User can override with "SUDO MANUAL" keyword
False Positive? Report reduces threshold sensitivity

Self-tuning: Current threshold = {threshold} (auto-adjusts based on accuracy)
```

### Component 5: Self-Correction Mechanism

**Feedback Loop:**
1. Hook detects pattern → suggests script
2. If I write script → `patterns_detected[pattern]["scripts_written"] += 1`
3. If I use "MANUAL" keyword → track as potential false positive
4. Every 50 turns → analyze:
   - If `scripts_written / patterns_detected < 0.3` → pattern is weak, raise threshold
   - If false_positive_rate > 10% → loosen enforcement
   - If roi consistently >5x → lower threshold (more aggressive)

**Learning Rate:**
- Adjust thresholds by ±1 per 50 turns (slow, stable learning)
- Never adjust more than 30% from baseline (prevent drift)
- Log all adjustments with justification

### Component 6: Integration with Existing Hooks

**Coordinate with:**
- `batching_analyzer.py` - Don't double-warn for same issue
- `performance_telemetry_collector.py` - Share metrics
- `epistemology.py` - Update confidence when scripts are written

**Data Sharing:**
```python
# Shared telemetry format
{
  "hook": "scratch_enforcer",
  "turn": 45,
  "pattern": "multi_read",
  "action": "warned",
  "tools_used": ["Read", "Read", "Read", "Read"],
  "estimated_waste": 3.5,
  "script_suggested": "scratch/compare_configs.py",
  "user_response": "wrote_script|ignored|used_MANUAL"
}
```

## Implementation Strategy

### Step 1: Build State Manager (Library Function)
```python
# scripts/lib/scratch_enforcement.py
def get_enforcement_state():
    """Load current phase, thresholds, metrics"""

def update_enforcement_state(pattern, action):
    """Track detection, update metrics"""

def should_enforce(pattern, tool_history):
    """Decision logic: observe/warn/block?"""

def auto_tune_thresholds():
    """Adjust based on false positive rate, ROI"""
```

### Step 2: Build PostToolUse Hook (Telemetry)
```python
# .claude/hooks/scratch_enforcer.py (PostToolUse)
# - Detect patterns in tool history
# - Update state metrics
# - Silent in Phase 1, warnings in Phase 2
```

### Step 3: Build PreToolUse Hook (Enforcement)
```python
# .claude/hooks/scratch_enforcer_gate.py (PreToolUse)
# - Check if pattern about to trigger
# - Block in Phase 3 if threshold exceeded
# - Allow bypass with "MANUAL" or "SUDO MANUAL"
```

### Step 4: Auto-Transition Logic
```python
# Runs every turn, decides phase transitions
if phase == "observe" and turns >= 20 and pattern_confidence > 0.7:
    transition_to_warn()
elif phase == "warn" and roi > 3.0 and false_positive_rate < 0.1:
    transition_to_enforce()
elif phase == "enforce" and false_positive_rate > 0.15:
    transition_to_warn()  # backtrack
```

### Step 5: Self-Tuning Cron
```python
# Every 50 turns (checked in PostToolUse)
if state["total_turns"] % 50 == 0:
    auto_tune_thresholds()
    report_metrics()
```

## Success Metrics (Self-Validated)

**The system tracks its own success:**
1. **Pattern Detection Accuracy:** `scripts_written / patterns_detected > 0.5` (50%+ hit rate)
2. **False Positive Rate:** <10% (measured via "MANUAL" bypass usage)
3. **ROI:** `avg_turns_saved / avg_script_writing_time > 3x`
4. **Adoption Rate:** After Phase 3, `scripts_written / patterns_detected > 0.8` (80%+ compliance)

**Auto-reporting (every 50 turns):**
```
📊 SCRATCH ENFORCEMENT AUTO-REPORT (Turn 100)

Phase: ENFORCE (auto-transitioned at Turn 67)
Patterns Detected: 23
Scripts Written: 19 (83% adoption)
Avg ROI: 4.2x time savings
False Positive Rate: 6% (within target <10%)

Auto-Adjustments Made:
  • Turn 67: Transitioned to ENFORCE (ROI proven 3.8x)
  • Turn 85: Tightened threshold 4→3 (FP rate 3%, very accurate)

Next Auto-Tune: Turn 150
```

## Failure Recovery

**If system becomes too aggressive:**
1. False positive rate >15% for 10 turns → auto-backtrack to WARN
2. User uses "SUDO MANUAL" → log as override, increase threshold by 1
3. Scripts written <30% → pattern detection is weak, disable that pattern

**If system becomes too passive:**
1. Detected patterns but no scripts written for 20 turns → increase warning intensity
2. ROI >10x consistently → lower thresholds (more aggressive enforcement)

## Zero-Maintenance Guarantee

**The system requires ZERO human intervention because:**
1. Auto-transitions between phases based on data
2. Auto-tunes thresholds based on accuracy
3. Auto-backtracks if too aggressive
4. Auto-reports every 50 turns for transparency
5. Self-validates via tracked metrics

**Human only intervenes if:**
- System is fundamentally broken (bug in code)
- Major workflow change requires pattern redefinition
- User explicitly wants to disable (remove from settings.json)

Otherwise: **Set it and forget it.**
