#!/usr/bin/env python3
"""
Auto-Tuning Framework: Reusable Self-Tuning Enforcement Pattern

Extracted from scratch_enforcement.py to make the pattern reusable
across ALL enforcement systems (batching, prerequisites, performance, etc.)

PHILOSOPHY:
Every enforcement system should:
1. Start passive (OBSERVE phase)
2. Auto-tune based on outcomes (FP rate + ROI)
3. Self-correct when wrong (backtrack if FP >15%)
4. Report progress transparently (every N turns)
5. Learn from user overrides (MANUAL/SUDO keywords)
6. Require ZERO manual revisiting

USAGE:
    tuner = AutoTuner(
        system_name="batching_enforcement",
        state_file=Path(".claude/memory/batching_state.json"),
        patterns={"sequential_reads": {...}},
        default_phase="observe"
    )

    # In PreToolUse hook:
    detection = tuner.detect_pattern(tool_history, current_turn)
    if detection:
        action, message = tuner.should_enforce(detection, user_prompt)
        if action == "block":
            # Block execution

    # In PostToolUse hook:
    tuner.update_metrics(pattern, turns_wasted, script_written, bypassed)
    tuner.check_phase_transition(current_turn)
    tuner.auto_tune_thresholds(current_turn)
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any


class AutoTuner:
    """Self-tuning enforcement framework"""

    def __init__(
        self,
        system_name: str,
        state_file: Path,
        patterns: Dict[str, Dict],
        default_phase: str = "observe",
        default_thresholds: Optional[Dict] = None,
    ):
        """
        Initialize auto-tuner.

        Args:
            system_name: Name of enforcement system (e.g., "batching", "prerequisites")
            state_file: Path to JSON state file
            patterns: Pattern definitions (see PATTERN_SCHEMA below)
            default_phase: Initial phase ("observe" | "warn" | "enforce")
            default_thresholds: Override default threshold values
        """
        self.system_name = system_name
        self.state_file = state_file
        self.patterns = patterns

        # Default thresholds (can be overridden)
        self.default_thresholds = {
            "detection_window": 5,  # turns to look back
            "min_repetitions": 4,  # tool calls to trigger
            "phase_transition_confidence": 0.70,  # % for OBSERVE → WARN
            "roi_threshold": 3.0,  # ROI for WARN → ENFORCE
            "fp_backtrack_threshold": 0.15,  # FP rate for ENFORCE → WARN
            "fp_loosen_threshold": 0.10,  # FP rate to loosen thresholds
            "fp_tighten_threshold": 0.03,  # FP rate to tighten thresholds
            "roi_tighten_threshold": 5.0,  # ROI to enable tightening
            "max_threshold_adjustment": 0.30,  # Max ±30% from baseline
            "auto_tune_interval": 50,  # Auto-tune every N turns
            "auto_report_interval": 50,  # Report every N turns
        }

        if default_thresholds:
            self.default_thresholds.update(default_thresholds)

        # Default state structure
        self.default_state = {
            "phase": default_phase,
            "total_turns": 0,
            "patterns_detected": {},
            "thresholds": self.default_thresholds.copy(),
            "false_positives": {"total": 0, "rate": 0.0, "last_adjustment": None},
            "auto_adjustments": [],
            "initialized_at": datetime.now().isoformat(),
        }

        # Initialize pattern metrics
        for pattern_name in patterns.keys():
            self.default_state["patterns_detected"][pattern_name] = {
                "count": 0,
                "avg_turns_wasted": 0.0,
                "scripts_written": 0,
                "manual_bypasses": 0,
                "baseline_threshold": patterns[pattern_name].get("threshold", 4),
            }

    def get_state(self) -> Dict:
        """Load current state, initialize if needed"""
        if not self.state_file.exists():
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(self.default_state, f, indent=2)
            return self.default_state.copy()

        try:
            with open(self.state_file) as f:
                state = json.load(f)

            # Ensure all patterns initialized
            if "patterns_detected" not in state:
                state["patterns_detected"] = {}

            for pattern_name in self.patterns.keys():
                if pattern_name not in state["patterns_detected"]:
                    state["patterns_detected"][pattern_name] = self.default_state[
                        "patterns_detected"
                    ][pattern_name].copy()

            return state
        except:
            return self.default_state.copy()

    def save_state(self, state: Dict) -> None:
        """Save state to file"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def detect_pattern(
        self, context: Any, current_turn: int
    ) -> Optional[Tuple[str, int, Dict]]:
        """
        Detect patterns in context (implementation-specific).

        Args:
            context: Context to analyze (e.g., tool_history, user_prompt)
            current_turn: Current turn number

        Returns:
            Tuple of (pattern_name, count, metadata) if detected, None otherwise
        """
        # This is a base method - implementations should override
        # or use pattern-specific detection functions
        return None

    def should_enforce(
        self, pattern_name: str, prompt: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Decision logic: Should we observe/warn/block?

        Args:
            pattern_name: Name of detected pattern
            prompt: User prompt (to check for bypass keywords)

        Returns:
            Tuple[str, Optional[str]]: (action, message)
            - action: "observe" | "warn" | "block"
            - message: Message to display (None if observe)
        """
        state = self.get_state()
        phase = state["phase"]

        # Check for bypass keywords
        if prompt:
            bypass_keywords = ["MANUAL", "SUDO MANUAL"]
            if any(keyword in prompt for keyword in bypass_keywords):
                return ("observe", None)

        pattern_config = self.patterns.get(pattern_name, {})
        pattern_data = state["patterns_detected"].get(pattern_name, {})

        # Phase 1: OBSERVE - silent data collection
        if phase == "observe":
            return ("observe", None)

        # Phase 2: WARN - suggestions only
        elif phase == "warn":
            count = pattern_data.get("count", 0)
            avg_waste = pattern_data.get("avg_turns_wasted", 0.0)
            suggested = pattern_config.get("suggested_action", "Write a script")

            message = f"""⚠️ {self.system_name.upper()} OPPORTUNITY DETECTED

Pattern: {pattern_name}
Detected: {count} times (avg {avg_waste:.1f} turns wasted)
Suggestion: {suggested}

Auto-escalation: This will become a HARD BLOCK after ROI proven (3x savings)

Bypass: Include "MANUAL" keyword if intentional
"""
            return ("warn", message)

        # Phase 3: ENFORCE - hard blocks
        elif phase == "enforce":
            count = pattern_data.get("count", 0)
            avg_waste = pattern_data.get("avg_turns_wasted", 0.0)
            scripts_written = pattern_data.get("scripts_written", 0)
            roi = (avg_waste / 2.0) if scripts_written > 0 else 0

            threshold = pattern_config.get(
                "threshold", state["thresholds"]["min_repetitions"]
            )
            suggested = pattern_config.get("suggested_action", "Write a script")

            message = f"""🚫 {self.system_name.upper()} ENFORCEMENT

Pattern: {pattern_name}
Detected: {count} times (avg {avg_waste:.1f} turns wasted)
Proven ROI: {roi:.1f}x time savings

BLOCKED: {suggested}

Bypass: User can override with "SUDO MANUAL" keyword
False Positive? Use "MANUAL" to report and reduce threshold sensitivity

Self-tuning: Current threshold = {threshold} (auto-adjusts based on accuracy)
"""
            return ("block", message)

        return ("observe", None)

    def update_metrics(
        self,
        pattern_name: str,
        turns_wasted: int,
        script_written: bool = False,
        bypassed: bool = False,
    ) -> None:
        """
        Update pattern statistics after detection.

        Args:
            pattern_name: Name of detected pattern
            turns_wasted: Estimated turns wasted on this occurrence
            script_written: True if user wrote alternative solution
            bypassed: True if user used MANUAL bypass
        """
        state = self.get_state()

        if pattern_name not in state["patterns_detected"]:
            return

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

        self.save_state(state)

    def auto_tune_thresholds(self, turn: int) -> List[str]:
        """
        Auto-adjust thresholds based on false positive rate and ROI.

        Args:
            turn: Current turn number

        Returns:
            List of adjustment messages
        """
        state = self.get_state()

        # Only run at intervals
        if turn % state["thresholds"]["auto_tune_interval"] != 0:
            return []

        adjustments = []
        fp_rate = state["false_positives"]["rate"]
        thresholds = state["thresholds"]

        # Rule 1: If FP rate >10%, loosen thresholds
        if fp_rate > thresholds["fp_loosen_threshold"]:
            old_threshold = thresholds["min_repetitions"]
            baseline = self.default_thresholds["min_repetitions"]
            max_increase = int(baseline * (1 + thresholds["max_threshold_adjustment"]))

            new_threshold = min(old_threshold + 1, max_increase)
            thresholds["min_repetitions"] = new_threshold

            adjustment = {
                "turn": turn,
                "action": f"loosened_threshold_{old_threshold}_to_{new_threshold}",
                "reason": f"false_positive_rate_{fp_rate*100:.0f}%",
            }
            state["auto_adjustments"].append(adjustment)
            adjustments.append(
                f"Loosened threshold {old_threshold} → {new_threshold} (FP rate {fp_rate*100:.0f}%)"
            )

            state["false_positives"]["last_adjustment"] = datetime.now().isoformat()

        # Rule 2: If FP rate <3% and ROI >5x, tighten thresholds
        elif fp_rate < thresholds["fp_tighten_threshold"]:
            # Calculate average ROI
            total_roi = 0
            pattern_count = 0

            for pattern_data in state["patterns_detected"].values():
                if pattern_data["scripts_written"] > 0:
                    avg_waste = pattern_data["avg_turns_wasted"]
                    roi = avg_waste / 2.0
                    total_roi += roi
                    pattern_count += 1

            if pattern_count > 0:
                avg_roi = total_roi / pattern_count

                if avg_roi > thresholds["roi_tighten_threshold"]:
                    old_threshold = thresholds["min_repetitions"]
                    baseline = self.default_thresholds["min_repetitions"]
                    min_threshold = max(
                        int(baseline * (1 - thresholds["max_threshold_adjustment"])), 2
                    )

                    new_threshold = max(old_threshold - 1, min_threshold)
                    thresholds["min_repetitions"] = new_threshold

                    adjustment = {
                        "turn": turn,
                        "action": f"tightened_threshold_{old_threshold}_to_{new_threshold}",
                        "reason": f"high_roi_{avg_roi:.1f}x_low_fp_{fp_rate*100:.0f}%",
                    }
                    state["auto_adjustments"].append(adjustment)
                    adjustments.append(
                        f"Tightened threshold {old_threshold} → {new_threshold} (ROI {avg_roi:.1f}x, FP {fp_rate*100:.0f}%)"
                    )

                    state["false_positives"]["last_adjustment"] = datetime.now().isoformat()

        self.save_state(state)
        return adjustments

    def check_phase_transition(self, turn: int) -> Optional[str]:
        """
        Check if phase transition should occur.

        Args:
            turn: Current turn number

        Returns:
            Transition message if occurred, None otherwise
        """
        state = self.get_state()
        state["total_turns"] = turn
        phase = state["phase"]

        # OBSERVE → WARN
        if phase == "observe":
            pattern_detections = sum(
                p["count"] for p in state["patterns_detected"].values()
            )

            if turn >= 20 or pattern_detections >= 3:
                total_scripts = sum(
                    p["scripts_written"] for p in state["patterns_detected"].values()
                )
                confidence = (
                    total_scripts / pattern_detections if pattern_detections > 0 else 0
                )

                if (
                    confidence >= state["thresholds"]["phase_transition_confidence"]
                    or turn >= 20
                ):
                    state["phase"] = "warn"
                    adjustment = {
                        "turn": turn,
                        "action": "transitioned_to_warn",
                        "reason": f"pattern_confidence_{confidence*100:.0f}%_or_turns_{turn}",
                    }
                    state["auto_adjustments"].append(adjustment)
                    self.save_state(state)

                    return f"""📊 {self.system_name.upper()}: AUTO-TRANSITION TO WARN PHASE

Reason: Pattern confidence {confidence*100:.0f}% OR {turn} turns elapsed
Action: Will now show warnings for detected patterns
Next Phase: ENFORCE (triggers when ROI proven >3x)
"""

        # WARN → ENFORCE
        elif phase == "warn":
            total_roi = 0
            pattern_count = 0

            for pattern_data in state["patterns_detected"].values():
                if pattern_data["scripts_written"] > 0:
                    avg_waste = pattern_data["avg_turns_wasted"]
                    roi = avg_waste / 2.0
                    total_roi += roi
                    pattern_count += 1

            if pattern_count > 0:
                avg_roi = total_roi / pattern_count
                fp_rate = state["false_positives"]["rate"]
                total_detections = sum(
                    p["count"] for p in state["patterns_detected"].values()
                )

                if (
                    avg_roi > state["thresholds"]["roi_threshold"]
                    and fp_rate < state["thresholds"]["fp_loosen_threshold"]
                    and total_detections >= 5
                ):
                    state["phase"] = "enforce"
                    adjustment = {
                        "turn": turn,
                        "action": "transitioned_to_enforce",
                        "reason": f"roi_proven_{avg_roi:.1f}x_fp_{fp_rate*100:.0f}%",
                    }
                    state["auto_adjustments"].append(adjustment)
                    self.save_state(state)

                    return f"""🚀 {self.system_name.upper()}: AUTO-TRANSITION TO ENFORCE PHASE

Proven ROI: {avg_roi:.1f}x time savings
False Positive Rate: {fp_rate*100:.0f}% (target <10%)
Total Detections: {total_detections}

Action: Will now HARD BLOCK detected patterns
Bypass: Users can override with "SUDO MANUAL" keyword
Self-Tuning: Thresholds will auto-adjust if FP rate increases
"""

        # ENFORCE → WARN (backtrack)
        elif phase == "enforce":
            fp_rate = state["false_positives"]["rate"]

            if fp_rate > state["thresholds"]["fp_backtrack_threshold"]:
                state["phase"] = "warn"
                adjustment = {
                    "turn": turn,
                    "action": "backtracked_to_warn",
                    "reason": f"high_fp_rate_{fp_rate*100:.0f}%",
                }
                state["auto_adjustments"].append(adjustment)
                self.save_state(state)

                return f"""⚠️ {self.system_name.upper()}: AUTO-BACKTRACK TO WARN PHASE

Reason: False positive rate {fp_rate*100:.0f}% (threshold 15%)
Action: Reverting to warnings (no hard blocks)
Self-Tuning: Thresholds will be loosened automatically
"""

        return None

    def generate_report(self, turn: int) -> str:
        """
        Generate auto-report.

        Args:
            turn: Current turn number

        Returns:
            Report string
        """
        state = self.get_state()

        # Only report at intervals and in WARN/ENFORCE phases
        if turn % state["thresholds"]["auto_report_interval"] != 0:
            return ""

        if state["phase"] == "observe":
            return ""

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

        return f"""📊 {self.system_name.upper()} AUTO-REPORT (Turn {turn})

Phase: {state['phase'].upper()}
Patterns Detected: {total_detections}
Scripts Written: {total_scripts} ({adoption_rate*100:.0f}% adoption)
Avg ROI: {avg_roi:.1f}x time savings
False Positive Rate: {fp_rate*100:.0f}% (target <10%)

Auto-Adjustments Made:
{adjustment_summary}

Next Auto-Tune: Turn {turn + state['thresholds']['auto_tune_interval']}
"""


# PATTERN SCHEMA (for documentation)
PATTERN_SCHEMA = {
    "pattern_name": {
        "threshold": 4,  # Number of occurrences to trigger
        "suggested_action": "Write a scratch script",  # What user should do instead
        "detection_logic": "Custom detection function",  # How to detect pattern
    }
}
