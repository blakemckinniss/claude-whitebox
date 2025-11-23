#!/usr/bin/env python3
"""
Meta-Learning System: Learn from User Overrides

Tracks SUDO/MANUAL/hook disable events, clusters common patterns,
and auto-generates exception rules to reduce false positives.

PHILOSOPHY:
When users bypass enforcement rules, they're teaching the system
what's actually wrong vs what's genuinely necessary. This module
learns from those lessons automatically.

WORKFLOW:
1. User uses "MANUAL" to bypass enforcement → Recorded
2. System clusters override patterns (e.g., "test file reads")
3. If pattern occurs >10 times with >70% consistency → Generate exception rule
4. Exception rule auto-applied to future enforcement decisions

USAGE:
    tracker = OverrideTracker()

    # Record override
    tracker.record_override(
        hook_name="batching_enforcer",
        bypass_type="MANUAL",
        context={"tool": "Read", "file_path": "test_foo.py", "reason": "test files"},
        turn=45
    )

    # Generate exception rules (run periodically)
    tracker.cluster_patterns()
    rules = tracker.generate_exception_rules()

    # Check if context matches exception
    should_bypass, rule = tracker.check_exception(hook_name, context)
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Paths
MEMORY_DIR = Path(__file__).resolve().parent.parent.parent / ".claude" / "memory"
OVERRIDE_LOG = MEMORY_DIR / "override_tracking.jsonl"
EXCEPTION_RULES_FILE = MEMORY_DIR / "exception_rules.json"


class OverrideTracker:
    """Track and learn from user overrides"""

    def __init__(self):
        self.override_log = OVERRIDE_LOG
        self.exception_rules_file = EXCEPTION_RULES_FILE

    def record_override(
        self,
        hook_name: str,
        bypass_type: str,
        context: Dict,
        turn: int,
        reason: Optional[str] = None,
    ) -> None:
        """
        Record a user override event.

        Args:
            hook_name: Name of hook that was bypassed
            bypass_type: "MANUAL" | "SUDO" | "disable"
            context: Context of the override (tool, file, pattern, etc.)
            turn: Turn number when override occurred
            reason: Optional user-provided reason
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "turn": turn,
            "hook_name": hook_name,
            "bypass_type": bypass_type,
            "context": context,
            "reason": reason,
        }

        self.override_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.override_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def load_overrides(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Load override history.

        Args:
            limit: Maximum number of recent overrides to load

        Returns:
            List of override entries
        """
        if not self.override_log.exists():
            return []

        overrides = []
        try:
            with open(self.override_log) as f:
                for line in f:
                    try:
                        overrides.append(json.loads(line.strip()))
                    except:
                        continue

            # Return most recent if limit specified
            if limit:
                return overrides[-limit:]
            return overrides
        except:
            return []

    def cluster_patterns(self, min_occurrences: int = 10) -> Dict[str, List[Dict]]:
        """
        Cluster override patterns by similarity.

        Args:
            min_occurrences: Minimum occurrences to form a cluster

        Returns:
            Dict mapping pattern_id to list of matching overrides
        """
        overrides = self.load_overrides(limit=1000)  # Last 1000 overrides

        # Group by hook + context similarity
        clusters = defaultdict(list)

        for override in overrides:
            # Generate cluster key from context
            hook = override["hook_name"]
            context = override["context"]

            # Extract key features for clustering
            features = []

            # Feature 1: Tool being used
            if "tool" in context:
                features.append(f"tool:{context['tool']}")

            # Feature 2: File pattern (test files, config files, etc.)
            if "file_path" in context:
                file_path = context["file_path"]
                if "test" in file_path:
                    features.append("file_type:test")
                elif file_path.endswith((".md", ".txt", ".json", ".yaml")):
                    features.append("file_type:config")
                elif "scratch/" in file_path:
                    features.append("file_type:scratch")

            # Feature 3: Operation type
            if "pattern" in context:
                features.append(f"pattern:{context['pattern']}")

            # Feature 4: User-provided reason (if present)
            if override.get("reason"):
                reason = override["reason"].lower()
                if "test" in reason:
                    features.append("reason:testing")
                elif "debug" in reason:
                    features.append("reason:debugging")
                elif "config" in reason or "setup" in reason:
                    features.append("reason:configuration")

            # Create cluster key
            cluster_key = f"{hook}|" + "|".join(sorted(features))
            clusters[cluster_key].append(override)

        # Filter clusters by min_occurrences
        significant_clusters = {
            key: overrides
            for key, overrides in clusters.items()
            if len(overrides) >= min_occurrences
        }

        return significant_clusters

    def generate_exception_rules(
        self, confidence_threshold: float = 0.70
    ) -> List[Dict]:
        """
        Generate exception rules from clustered patterns.

        Args:
            confidence_threshold: Min % of cluster to form rule (0-1)

        Returns:
            List of exception rules
        """
        clusters = self.cluster_patterns()
        rules = []

        for cluster_key, overrides in clusters.items():
            # Parse cluster key
            parts = cluster_key.split("|")
            hook_name = parts[0]
            features = parts[1:]

            # Calculate confidence (% of overrides in cluster vs total for hook)
            total_hook_overrides = len(
                [o for o in self.load_overrides(limit=1000) if o["hook_name"] == hook_name]
            )

            confidence = len(overrides) / total_hook_overrides if total_hook_overrides > 0 else 0

            if confidence < confidence_threshold:
                continue

            # Extract common patterns from overrides
            file_patterns = []
            tool_patterns = []
            reason_patterns = []

            for override in overrides:
                context = override["context"]

                if "file_path" in context:
                    file_path = context["file_path"]
                    # Extract pattern (e.g., test files)
                    if "test" in file_path and "test_.*\\.py" not in file_patterns:
                        file_patterns.append("test_.*\\.py")
                    elif "scratch/" in file_path and "scratch/.*" not in file_patterns:
                        file_patterns.append("scratch/.*")

                if "tool" in context:
                    tool = context["tool"]
                    if tool not in tool_patterns:
                        tool_patterns.append(tool)

                if override.get("reason"):
                    reason_patterns.append(override["reason"])

            # Generate rule
            rule = {
                "rule_id": f"{hook_name}_{len(rules)}",
                "hook_name": hook_name,
                "confidence": confidence,
                "occurrences": len(overrides),
                "created_at": datetime.now().isoformat(),
                "conditions": {
                    "tools": tool_patterns if tool_patterns else None,
                    "file_patterns": file_patterns if file_patterns else None,
                },
                "action": "allow",
                "reason": f"Auto-generated from {len(overrides)} override events ({confidence*100:.0f}% confidence)",
                "example_contexts": [o["context"] for o in overrides[:3]],
            }

            rules.append(rule)

        return rules

    def save_exception_rules(self, rules: List[Dict]) -> None:
        """Save exception rules to file"""
        self.exception_rules_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Load existing rules
            existing_rules = self.load_exception_rules()

            # Merge (deduplicate by rule_id)
            rules_by_id = {rule["rule_id"]: rule for rule in existing_rules}
            for rule in rules:
                rules_by_id[rule["rule_id"]] = rule

            # Save
            with open(self.exception_rules_file, "w") as f:
                json.dump(list(rules_by_id.values()), f, indent=2)
        except:
            pass

    def load_exception_rules(self) -> List[Dict]:
        """Load exception rules from file"""
        if not self.exception_rules_file.exists():
            return []

        try:
            with open(self.exception_rules_file) as f:
                return json.load(f)
        except:
            return []

    def check_exception(
        self, hook_name: str, context: Dict
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Check if context matches any exception rule.

        Args:
            hook_name: Name of hook being checked
            context: Context to check against rules

        Returns:
            Tuple of (should_bypass, matching_rule)
        """
        rules = self.load_exception_rules()

        for rule in rules:
            # Skip rules for different hooks
            if rule["hook_name"] != hook_name:
                continue

            # Check conditions
            conditions = rule["conditions"]
            matches = True

            # Check tool match
            if conditions.get("tools"):
                if "tool" not in context:
                    matches = False
                elif context["tool"] not in conditions["tools"]:
                    matches = False

            # Check file pattern match
            if conditions.get("file_patterns"):
                if "file_path" not in context:
                    matches = False
                else:
                    file_path = context["file_path"]
                    pattern_match = any(
                        re.search(pattern, file_path)
                        for pattern in conditions["file_patterns"]
                    )
                    if not pattern_match:
                        matches = False

            if matches:
                return (True, rule)

        return (False, None)

    def auto_update_rules(self, turn: int, update_interval: int = 100) -> List[Dict]:
        """
        Auto-generate and save exception rules periodically.

        Args:
            turn: Current turn number
            update_interval: How often to regenerate rules

        Returns:
            List of newly generated rules
        """
        # Only run at intervals
        if turn % update_interval != 0:
            return []

        # Generate new rules
        new_rules = self.generate_exception_rules()

        # Save
        if new_rules:
            self.save_exception_rules(new_rules)

        return new_rules

    def get_override_statistics(self) -> Dict:
        """
        Get statistics about overrides.

        Returns:
            Dict with override stats
        """
        overrides = self.load_overrides(limit=1000)

        if not overrides:
            return {
                "total_overrides": 0,
                "by_hook": {},
                "by_bypass_type": {},
                "exception_rules": 0,
            }

        # Count by hook
        by_hook = defaultdict(int)
        by_bypass_type = defaultdict(int)

        for override in overrides:
            by_hook[override["hook_name"]] += 1
            by_bypass_type[override["bypass_type"]] += 1

        # Load exception rules
        rules = self.load_exception_rules()

        return {
            "total_overrides": len(overrides),
            "by_hook": dict(by_hook),
            "by_bypass_type": dict(by_bypass_type),
            "exception_rules": len(rules),
            "clusters": len(self.cluster_patterns()),
        }

    def generate_report(self) -> str:
        """
        Generate human-readable report.

        Returns:
            Report string
        """
        stats = self.get_override_statistics()

        if stats["total_overrides"] == 0:
            return "📊 META-LEARNING: No overrides recorded yet"

        report = f"""📊 META-LEARNING REPORT

Total Overrides: {stats['total_overrides']}
Exception Rules: {stats['exception_rules']}
Pattern Clusters: {stats['clusters']}

Overrides by Hook:
"""

        for hook, count in sorted(
            stats["by_hook"].items(), key=lambda x: x[1], reverse=True
        ):
            report += f"  • {hook}: {count}\n"

        report += "\nBypass Types:\n"
        for bypass_type, count in stats["by_bypass_type"].items():
            report += f"  • {bypass_type}: {count}\n"

        # Show sample exception rules
        rules = self.load_exception_rules()
        if rules:
            report += f"\nExample Exception Rules:\n"
            for rule in rules[:3]:
                report += f"  • {rule['rule_id']}: {rule['reason']}\n"

        return report


# Convenience functions for hooks
def record_manual_bypass(hook_name: str, context: Dict, turn: int, reason: str = None):
    """Convenience function for recording MANUAL bypasses"""
    tracker = OverrideTracker()
    tracker.record_override(hook_name, "MANUAL", context, turn, reason)


def record_sudo_bypass(hook_name: str, context: Dict, turn: int, reason: str = None):
    """Convenience function for recording SUDO bypasses"""
    tracker = OverrideTracker()
    tracker.record_override(hook_name, "SUDO", context, turn, reason)


def check_exception_rule(hook_name: str, context: Dict) -> Tuple[bool, Optional[Dict]]:
    """Convenience function for checking exception rules"""
    tracker = OverrideTracker()
    return tracker.check_exception(hook_name, context)
