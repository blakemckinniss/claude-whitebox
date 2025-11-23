#!/usr/bin/env python3
"""
Scratch Enforcement Library: Self-Tuning Iteration Detection

Manages auto-tuning enforcement of scratch-first philosophy.
Tracks patterns, adjusts thresholds, and provides enforcement logic.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Paths
MEMORY_DIR = Path(__file__).resolve().parent.parent.parent / ".claude" / "memory"
STATE_FILE = MEMORY_DIR / "scratch_enforcement_state.json"
TELEMETRY_FILE = MEMORY_DIR / "scratch_telemetry.jsonl"

# Pattern definitions
PATTERNS = {
    "multi_read": {
        "tools": ["Read"],
        "window": 5,  # turns to look back
        "threshold": 4,  # calls to trigger
        "exemptions": ["MANUAL", "SEQUENTIAL"],
        "suggested_script": "compare_files.py",
    },
    "multi_grep": {
        "tools": ["Grep"],
        "window": 5,
        "threshold": 4,
        "exemptions": ["iterative refinement", "MANUAL"],
        "suggested_script": "batch_search.py",
    },
    "multi_edit": {
        "tools": ["Edit"],
        "window": 5,
        "threshold": 3,  # Lower - edits are expensive
        "exemptions": ["syntax error fix", "MANUAL"],
        "suggested_script": "batch_edit.py",
    },
    "file_iteration": {
        "tools": ["Read", "Edit", "Grep"],
        "detection": r"(?:for each|all files|process.*files|iterate.*files)",
        "threshold": 1,  # Immediate trigger
        "exemptions": ["agent delegation", "Task tool", "MANUAL"],
        "suggested_script": "process_files.py",
    },
}

# Default state structure
DEFAULT_STATE = {
    "phase": "observe",  # observe | warn | enforce
    "total_turns": 0,
    "patterns_detected": {},
    "thresholds": {
        "detection_window": 5,
        "min_repetitions": 4,
        "phase_transition_confidence": 0.70,
        "roi_threshold": 3.0,
    },
    "false_positives": {"total": 0, "rate": 0.0, "last_adjustment": None},
    "auto_adjustments": [],
    "initialized_at": datetime.now().isoformat(),
}


def get_enforcement_state() -> Dict:
    """Load current enforcement state, initialize if needed"""
    if not STATE_FILE.exists():
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(DEFAULT_STATE, f, indent=2)
        return DEFAULT_STATE.copy()

    try:
        with open(STATE_FILE) as f:
            state = json.load(f)

        # Ensure patterns_detected initialized
        if "patterns_detected" not in state:
            state["patterns_detected"] = {}

        for pattern_name in PATTERNS.keys():
            if pattern_name not in state["patterns_detected"]:
                state["patterns_detected"][pattern_name] = {
                    "count": 0,
                    "avg_turns_wasted": 0.0,
                    "scripts_written": 0,
                    "manual_bypasses": 0,
                }

        return state
    except:
        return DEFAULT_STATE.copy()


def save_enforcement_state(state: Dict) -> None:
    """Save enforcement state to file"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def log_telemetry(
    turn: int, pattern: str, action: str, tools_used: List[str], metadata: Dict = None
) -> None:
    """Log telemetry event to JSONL"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "turn": turn,
        "pattern": pattern,
        "action": action,  # detected | warned | blocked | script_written | bypassed
        "tools": tools_used,
        "metadata": metadata or {},
    }

    TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TELEMETRY_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def detect_pattern_in_prompt(prompt: str) -> Optional[str]:
    """
    Detect file_iteration pattern in user prompt.

    Returns pattern name if detected, None otherwise.
    """
    prompt_lower = prompt.lower()

    # Check file_iteration detection regex
    pattern_config = PATTERNS["file_iteration"]
    if "detection" in pattern_config:
        if re.search(pattern_config["detection"], prompt_lower):
            # Check exemptions
            for exemption in pattern_config["exemptions"]:
                if exemption.lower() in prompt_lower:
                    return None
            return "file_iteration"

    return None


def detect_pattern_in_history(
    tool_name: str, tool_history: List[Dict], current_turn: int
) -> Optional[Tuple[str, int]]:
    """
    Detect patterns in tool usage history.

    Args:
        tool_name: Name of tool just used
        tool_history: List of recent tool uses: [{"tool": str, "turn": int}, ...]
        current_turn: Current turn number

    Returns:
        Tuple of (pattern_name, count) if pattern detected, None otherwise
    """
    state = get_enforcement_state()
    window = state["thresholds"]["detection_window"]

    # Check each pattern
    for pattern_name, pattern_config in PATTERNS.items():
        # Skip if tool not in pattern's tool list
        if "tools" not in pattern_config or tool_name not in pattern_config["tools"]:
            continue

        # Count matching tools within window
        matching_tools = [
            h
            for h in tool_history
            if h["tool"] in pattern_config["tools"]
            and (current_turn - h["turn"]) <= window
        ]

        count = len(matching_tools)
        threshold = pattern_config.get("threshold", state["thresholds"]["min_repetitions"])

        if count >= threshold:
            return (pattern_name, count)

    return None


def should_enforce(
    pattern_name: str, state: Dict, prompt: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """
    Decision logic: Should we observe/warn/block?

    Args:
        pattern_name: Name of detected pattern
        state: Current enforcement state
        prompt: User prompt (to check for bypass keywords)

    Returns:
        Tuple[str, Optional[str]]: (action, message)
        - action: "observe" | "warn" | "block"
        - message: Message to display (None if observe)
    """
    phase = state["phase"]

    # Check for bypass keywords in prompt
    if prompt:
        bypass_keywords = ["MANUAL", "SUDO MANUAL"]
        if any(keyword in prompt for keyword in bypass_keywords):
            return ("observe", None)  # Bypass triggered

    # Phase 1: OBSERVE - silent data collection
    if phase == "observe":
        return ("observe", None)

    # Phase 2: WARN - suggestions only
    elif phase == "warn":
        pattern_data = state["patterns_detected"].get(pattern_name, {})
        count = pattern_data.get("count", 0)
        avg_waste = pattern_data.get("avg_turns_wasted", 0.0)
        suggested = PATTERNS[pattern_name]["suggested_script"]

        message = f"""⚠️ SCRATCH SCRIPT OPPORTUNITY DETECTED

Pattern: {pattern_name}
Detected: {count} times (avg {avg_waste:.1f} turns wasted)
Suggested Script: scratch/{suggested}

Auto-escalation: This will become a HARD BLOCK after ROI proven (3x savings)

Bypass: Include "MANUAL" keyword if intentional
"""
        return ("warn", message)

    # Phase 3: ENFORCE - hard blocks
    elif phase == "enforce":
        pattern_data = state["patterns_detected"].get(pattern_name, {})
        count = pattern_data.get("count", 0)
        avg_waste = pattern_data.get("avg_turns_wasted", 0.0)
        scripts_written = pattern_data.get("scripts_written", 0)
        roi = (avg_waste / 2.0) if scripts_written > 0 else 0  # Estimate

        threshold = PATTERNS[pattern_name].get("threshold", 4)
        suggested = PATTERNS[pattern_name]["suggested_script"]

        message = f"""🚫 SCRATCH SCRIPT REQUIRED

Pattern: {pattern_name}
Detected: {count} times (avg {avg_waste:.1f} turns wasted)
Proven ROI: {roi:.1f}x time savings via scripting

BLOCKED: Write script to scratch/{suggested} first

Bypass: User can override with "SUDO MANUAL" keyword
False Positive? Use "MANUAL" to report and reduce threshold sensitivity

Self-tuning: Current threshold = {threshold} (auto-adjusts based on accuracy)
"""
        return ("block", message)

    return ("observe", None)


def update_pattern_detection(
    pattern_name: str, turns_wasted: int, script_written: bool = False, bypassed: bool = False
) -> None:
    """
    Update pattern statistics after detection.

    Args:
        pattern_name: Name of detected pattern
        turns_wasted: Estimated turns wasted on this occurrence
        script_written: True if user wrote a scratch script
        bypassed: True if user used MANUAL bypass
    """
    state = get_enforcement_state()

    if pattern_name not in state["patterns_detected"]:
        state["patterns_detected"][pattern_name] = {
            "count": 0,
            "avg_turns_wasted": 0.0,
            "scripts_written": 0,
            "manual_bypasses": 0,
        }

    pattern_data = state["patterns_detected"][pattern_name]

    # Update count
    pattern_data["count"] += 1

    # Update average turns wasted (running average)
    old_avg = pattern_data["avg_turns_wasted"]
    old_count = pattern_data["count"] - 1
    new_avg = ((old_avg * old_count) + turns_wasted) / pattern_data["count"]
    pattern_data["avg_turns_wasted"] = new_avg

    # Track script writing
    if script_written:
        pattern_data["scripts_written"] += 1

    # Track bypasses (potential false positives)
    if bypassed:
        pattern_data["manual_bypasses"] += 1
        state["false_positives"]["total"] += 1

    # Recalculate false positive rate
    total_detections = sum(p["count"] for p in state["patterns_detected"].values())
    if total_detections > 0:
        state["false_positives"]["rate"] = (
            state["false_positives"]["total"] / total_detections
        )

    save_enforcement_state(state)


def auto_tune_thresholds(state: Dict, turn: int) -> List[str]:
    """
    Auto-adjust thresholds based on false positive rate and ROI.

    Returns:
        List of adjustment messages
    """
    adjustments = []

    fp_rate = state["false_positives"]["rate"]
    thresholds = state["thresholds"]

    # Rule 1: If FP rate >10%, loosen thresholds
    if fp_rate > 0.10:
        old_threshold = thresholds["min_repetitions"]
        thresholds["min_repetitions"] = min(old_threshold + 1, 10)  # Cap at 10

        adjustment = {
            "turn": turn,
            "action": f"loosened_threshold_{old_threshold}_to_{thresholds['min_repetitions']}",
            "reason": f"false_positive_rate_{fp_rate*100:.0f}%",
        }
        state["auto_adjustments"].append(adjustment)
        adjustments.append(
            f"Loosened threshold {old_threshold} → {thresholds['min_repetitions']} (FP rate {fp_rate*100:.0f}%)"
        )

        state["false_positives"]["last_adjustment"] = datetime.now().isoformat()

    # Rule 2: If FP rate <3% and ROI >5x, tighten thresholds (more aggressive)
    elif fp_rate < 0.03:
        # Calculate average ROI across all patterns
        total_roi = 0
        pattern_count = 0

        for pattern_name, pattern_data in state["patterns_detected"].items():
            if pattern_data["scripts_written"] > 0:
                avg_waste = pattern_data["avg_turns_wasted"]
                roi = avg_waste / 2.0  # Assume script takes ~2 turns
                total_roi += roi
                pattern_count += 1

        if pattern_count > 0:
            avg_roi = total_roi / pattern_count
            if avg_roi > 5.0:
                old_threshold = thresholds["min_repetitions"]
                thresholds["min_repetitions"] = max(old_threshold - 1, 2)  # Floor at 2

                adjustment = {
                    "turn": turn,
                    "action": f"tightened_threshold_{old_threshold}_to_{thresholds['min_repetitions']}",
                    "reason": f"high_roi_{avg_roi:.1f}x_low_fp_{fp_rate*100:.0f}%",
                }
                state["auto_adjustments"].append(adjustment)
                adjustments.append(
                    f"Tightened threshold {old_threshold} → {thresholds['min_repetitions']} (ROI {avg_roi:.1f}x, FP {fp_rate*100:.0f}%)"
                )

                state["false_positives"]["last_adjustment"] = datetime.now().isoformat()

    save_enforcement_state(state)
    return adjustments


def check_phase_transition(state: Dict, turn: int) -> Optional[str]:
    """
    Check if phase transition should occur.

    Returns:
        Transition message if transition occurred, None otherwise
    """
    phase = state["phase"]
    total_turns = state["total_turns"]

    # Phase 1 → Phase 2 (OBSERVE → WARN)
    if phase == "observe":
        # Trigger after 20 turns OR 3+ detections with consistent waste
        pattern_detections = sum(
            p["count"] for p in state["patterns_detected"].values()
        )

        if total_turns >= 20 or pattern_detections >= 3:
            # Check pattern confidence (scripts_written / patterns_detected)
            total_scripts = sum(
                p["scripts_written"] for p in state["patterns_detected"].values()
            )
            confidence = (
                total_scripts / pattern_detections if pattern_detections > 0 else 0
            )

            if confidence >= 0.3 or total_turns >= 20:
                state["phase"] = "warn"
                adjustment = {
                    "turn": turn,
                    "action": "transitioned_to_warn",
                    "reason": f"pattern_confidence_{confidence*100:.0f}%_or_turns_{total_turns}",
                }
                state["auto_adjustments"].append(adjustment)
                save_enforcement_state(state)

                return f"""📊 SCRATCH ENFORCEMENT: AUTO-TRANSITION TO WARN PHASE

Reason: Pattern confidence {confidence*100:.0f}% (need 30%+) OR {total_turns} turns elapsed
Action: Will now show warnings for detected patterns
Next Phase: ENFORCE (triggers when ROI proven >3x)
"""

    # Phase 2 → Phase 3 (WARN → ENFORCE)
    elif phase == "warn":
        # Calculate average ROI
        total_roi = 0
        pattern_count = 0

        for pattern_name, pattern_data in state["patterns_detected"].items():
            if pattern_data["scripts_written"] > 0:
                avg_waste = pattern_data["avg_turns_wasted"]
                roi = avg_waste / 2.0
                total_roi += roi
                pattern_count += 1

        if pattern_count > 0:
            avg_roi = total_roi / pattern_count
            fp_rate = state["false_positives"]["rate"]

            # Trigger if ROI >3x AND FP rate <10% AND at least 5 detections
            total_detections = sum(
                p["count"] for p in state["patterns_detected"].values()
            )

            if avg_roi > 3.0 and fp_rate < 0.10 and total_detections >= 5:
                state["phase"] = "enforce"
                adjustment = {
                    "turn": turn,
                    "action": "transitioned_to_enforce",
                    "reason": f"roi_proven_{avg_roi:.1f}x_fp_{fp_rate*100:.0f}%",
                }
                state["auto_adjustments"].append(adjustment)
                save_enforcement_state(state)

                return f"""🚀 SCRATCH ENFORCEMENT: AUTO-TRANSITION TO ENFORCE PHASE

Proven ROI: {avg_roi:.1f}x time savings via scripting
False Positive Rate: {fp_rate*100:.0f}% (target <10%)
Total Detections: {total_detections}

Action: Will now HARD BLOCK detected patterns
Bypass: Users can override with "SUDO MANUAL" keyword
Self-Tuning: Thresholds will auto-adjust if FP rate increases
"""

    # Phase 3 → Phase 2 (BACKTRACK on high FP rate)
    elif phase == "enforce":
        fp_rate = state["false_positives"]["rate"]

        # Backtrack if FP rate >15% (too aggressive)
        if fp_rate > 0.15:
            state["phase"] = "warn"
            adjustment = {
                "turn": turn,
                "action": "backtracked_to_warn",
                "reason": f"high_fp_rate_{fp_rate*100:.0f}%",
            }
            state["auto_adjustments"].append(adjustment)
            save_enforcement_state(state)

            return f"""⚠️ SCRATCH ENFORCEMENT: AUTO-BACKTRACK TO WARN PHASE

Reason: False positive rate {fp_rate*100:.0f}% (threshold 15%)
Action: Reverting to warnings (no hard blocks)
Self-Tuning: Thresholds will be loosened automatically
"""

    return None


def generate_auto_report(state: Dict, turn: int) -> str:
    """
    Generate auto-report every 50 turns.

    Returns:
        Report string
    """
    total_detections = sum(p["count"] for p in state["patterns_detected"].values())
    total_scripts = sum(
        p["scripts_written"] for p in state["patterns_detected"].values()
    )
    adoption_rate = total_scripts / total_detections if total_detections > 0 else 0

    # Calculate ROI
    total_roi = 0
    pattern_count = 0
    for pattern_data in state["patterns_detected"].values():
        if pattern_data["scripts_written"] > 0:
            avg_waste = pattern_data["avg_turns_wasted"]
            roi = avg_waste / 2.0
            total_roi += roi
            pattern_count += 1

    avg_roi = total_roi / pattern_count if pattern_count > 0 else 0

    fp_rate = state["false_positives"]["rate"]

    # Recent adjustments (last 3)
    recent_adjustments = state["auto_adjustments"][-3:]
    adjustment_summary = "\n".join(
        [
            f"  • Turn {adj['turn']}: {adj['action']} ({adj['reason']})"
            for adj in recent_adjustments
        ]
    )

    if not adjustment_summary:
        adjustment_summary = "  • No adjustments yet"

    return f"""📊 SCRATCH ENFORCEMENT AUTO-REPORT (Turn {turn})

Phase: {state['phase'].upper()} (auto-transitioned)
Patterns Detected: {total_detections}
Scripts Written: {total_scripts} ({adoption_rate*100:.0f}% adoption)
Avg ROI: {avg_roi:.1f}x time savings
False Positive Rate: {fp_rate*100:.0f}% (target <10%)

Auto-Adjustments Made:
{adjustment_summary}

Next Auto-Tune: Turn {turn + 50}
"""
