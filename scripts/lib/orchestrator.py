#!/usr/bin/env python3
"""
The Orchestrator - Central Autonomous Workflow Coordinator

Manages coordination between autonomous systems:
- Guardian (auto-test loop)
- Committer (auto-commit)
- Documentarian (auto-docs sync)
- Janitor (auto-cleanup)

Philosophy: Human provides intent, AI handles complete execution.
"""

import json
import time
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


class WorkflowState(Enum):
    """Workflow execution states"""
    IDLE = "idle"
    TESTING = "testing"
    DOCUMENTING = "documenting"
    COMMITTING = "committing"
    CLEANING = "cleaning"
    FAILED = "failed"
    COMPLETE = "complete"


class ActionType(Enum):
    """Types of autonomous actions"""
    TEST = "test"
    FIX = "fix"
    DOCUMENT = "document"
    COMMIT = "commit"
    CLEANUP = "cleanup"
    ESCALATE = "escalate"


@dataclass
class WorkflowEvent:
    """Event in autonomous workflow"""
    timestamp: float
    event_type: str
    trigger: str
    action: str
    result: str
    metadata: Dict


@dataclass
class QualityGate:
    """Quality gate check result"""
    name: str
    passed: bool
    message: str
    timestamp: float


class Orchestrator:
    """Central coordinator for autonomous workflows"""

    def __init__(self, project_dir: Path, config: Dict):
        self.project_dir = project_dir
        self.config = config
        self.state_file = project_dir / ".claude" / "memory" / "orchestrator_state.json"
        self.log_file = project_dir / ".claude" / "memory" / "automation_log.jsonl"

        # Load or initialize state
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load orchestrator state"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except:
                pass

        # Default state
        return {
            "workflow_state": WorkflowState.IDLE.value,
            "current_turn": 0,
            "pending_actions": [],
            "quality_gates": [],
            "last_commit": None,
            "last_cleanup": None,
            "escalations": []
        }

    def _save_state(self):
        """Persist orchestrator state"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def _log_event(self, event: WorkflowEvent):
        """Log workflow event to audit trail"""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.log_file, 'a') as f:
            f.write(json.dumps(asdict(event)) + "\n")

    def trigger_workflow(self, trigger: str, metadata: Dict) -> Dict:
        """
        Main entry point for workflow triggering.

        Args:
            trigger: What triggered the workflow (code_change, session_end, etc)
            metadata: Context about the trigger

        Returns:
            Workflow execution plan
        """
        self.state["current_turn"] += 1

        # Determine workflow based on trigger
        if trigger == "code_change":
            return self._handle_code_change(metadata)
        elif trigger == "session_end":
            return self._handle_session_end(metadata)
        elif trigger == "periodic_cleanup":
            return self._handle_periodic_cleanup(metadata)
        else:
            return {"status": "unknown_trigger", "actions": []}

    def _handle_code_change(self, metadata: Dict) -> Dict:
        """
        Handle code change trigger.

        Workflow:
        1. Guardian: Test code
        2. If tests pass:
           - Documentarian: Update docs
           - Committer: Prepare commit
        3. If all quality gates pass:
           - Committer: Execute commit
        """
        changed_files = metadata.get("files", [])
        is_production = any("scripts/ops/" in f for f in changed_files)

        workflow = {
            "trigger": "code_change",
            "actions": []
        }

        # Step 1: Guardian (if production code)
        if is_production and self.config.get("guardian", {}).get("enabled", True):
            workflow["actions"].append({
                "system": "guardian",
                "action": "test_code",
                "files": changed_files,
                "blocking": True  # Must pass before continuing
            })

        # Step 2: Documentarian (if scripts/ops/ or .claude/hooks/)
        watch_paths = self.config.get("documentarian", {}).get("watch_paths", [])
        needs_docs = any(
            any(watch in f for watch in watch_paths)
            for f in changed_files
        )

        if needs_docs and self.config.get("documentarian", {}).get("enabled", True):
            workflow["actions"].append({
                "system": "documentarian",
                "action": "sync_docs",
                "files": changed_files,
                "blocking": False  # Can run in parallel with testing
            })

        # Step 3: Committer (always, but after quality gates)
        if self.config.get("committer", {}).get("enabled", True):
            workflow["actions"].append({
                "system": "committer",
                "action": "prepare_commit",
                "files": changed_files,
                "blocking": False,  # Preparation can happen anytime
                "execute_after": ["guardian", "documentarian"]  # Wait for these
            })

        return workflow

    def _handle_session_end(self, metadata: Dict) -> Dict:
        """
        Handle session end trigger.

        Workflow:
        1. Guardian: Final test sweep
        2. Janitor: Cleanup workspace
        3. Committer: Auto-commit if changes exist
        """
        workflow = {
            "trigger": "session_end",
            "actions": []
        }

        # Step 1: Final tests
        if self.config.get("guardian", {}).get("enabled", True):
            workflow["actions"].append({
                "system": "guardian",
                "action": "final_sweep",
                "blocking": True
            })

        # Step 2: Cleanup
        if self.config.get("janitor", {}).get("enabled", True):
            workflow["actions"].append({
                "system": "janitor",
                "action": "cleanup_session",
                "blocking": False
            })

        # Step 3: Final commit
        if self.config.get("committer", {}).get("enabled", True):
            workflow["actions"].append({
                "system": "committer",
                "action": "final_commit",
                "blocking": False,
                "execute_after": ["guardian", "janitor"]
            })

        return workflow

    def _handle_periodic_cleanup(self, metadata: Dict) -> Dict:
        """
        Handle periodic cleanup trigger.

        Workflow:
        1. Janitor: Archive old files
        2. Janitor: Remove duplicates
        3. Report: Summary of cleanup
        """
        workflow = {
            "trigger": "periodic_cleanup",
            "actions": []
        }

        if self.config.get("janitor", {}).get("enabled", True):
            workflow["actions"].append({
                "system": "janitor",
                "action": "periodic_cleanup",
                "blocking": False
            })

        return workflow

    def record_quality_gate(self, gate: QualityGate):
        """Record quality gate check result"""
        self.state["quality_gates"].append({
            "name": gate.name,
            "passed": gate.passed,
            "message": gate.message,
            "timestamp": gate.timestamp
        })

        self._save_state()

        # Log event
        event = WorkflowEvent(
            timestamp=time.time(),
            event_type="quality_gate",
            trigger="automatic",
            action=f"check_{gate.name}",
            result="pass" if gate.passed else "fail",
            metadata={"message": gate.message}
        )
        self._log_event(event)

    def all_quality_gates_passed(self) -> bool:
        """Check if all quality gates have passed"""
        if not self.state["quality_gates"]:
            return False

        return all(gate["passed"] for gate in self.state["quality_gates"])

    def clear_quality_gates(self):
        """Reset quality gates (after commit)"""
        self.state["quality_gates"] = []
        self._save_state()

    def escalate_to_user(self, reason: str, context: Dict):
        """Escalate issue to user (autonomous system failed)"""
        escalation = {
            "timestamp": time.time(),
            "reason": reason,
            "context": context
        }

        self.state["escalations"].append(escalation)
        self._save_state()

        # Log event
        event = WorkflowEvent(
            timestamp=time.time(),
            event_type="escalation",
            trigger="autonomous_failure",
            action="escalate_to_user",
            result="pending_user_action",
            metadata={"reason": reason, "context": context}
        )
        self._log_event(event)

        return {
            "status": "escalated",
            "reason": reason,
            "message": f"""
🚨 AUTONOMOUS SYSTEM ESCALATION

Reason: {reason}

Context: {json.dumps(context, indent=2)}

Action Required: Manual intervention needed.

Escalation #{len(self.state['escalations'])}
"""
        }

    def get_audit_trail(self, limit: int = 50) -> List[Dict]:
        """Get recent audit trail entries"""
        if not self.log_file.exists():
            return []

        entries = []
        with open(self.log_file) as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except:
                    continue

        # Return most recent entries
        return entries[-limit:]


def load_config(project_dir: Path) -> Dict:
    """Load automation configuration"""
    config_file = project_dir / ".claude" / "memory" / "automation_config.json"

    if config_file.exists():
        with open(config_file) as f:
            return json.load(f)

    # Default configuration
    return {
        "guardian": {
            "enabled": True,
            "max_fix_attempts": 3,
            "test_on_write": True,
            "test_on_edit": True
        },
        "committer": {
            "enabled": True,
            "dry_run": True,  # Safe default
            "auto_push": False,
            "require_tests_passing": True,
            "require_quality_gates": True
        },
        "documentarian": {
            "enabled": True,
            "watch_paths": ["scripts/ops/", ".claude/hooks/"],
            "update_targets": ["CLAUDE.md"]
        },
        "janitor": {
            "enabled": True,
            "archive_threshold_days": 7,
            "cleanup_frequency_turns": 50
        },
        "orchestrator": {
            "enabled": True,
            "coordination_mode": "sequential"
        }
    }


def main():
    """CLI interface for orchestrator"""
    import sys

    project_dir = Path.cwd()

    # Find project root
    while not (project_dir / "scripts" / "lib").exists() and project_dir != project_dir.parent:
        project_dir = project_dir.parent

    config = load_config(project_dir)
    orchestrator = Orchestrator(project_dir, config)

    if len(sys.argv) < 2:
        print("Usage: orchestrator.py <command> [args]")
        print()
        print("Commands:")
        print("  status      - Show current orchestrator state")
        print("  trigger     - Trigger workflow (for testing)")
        print("  audit       - Show recent audit trail")
        print("  escalations - Show pending escalations")
        sys.exit(1)

    command = sys.argv[1]

    if command == "status":
        print(json.dumps(orchestrator.state, indent=2))

    elif command == "trigger":
        if len(sys.argv) < 3:
            print("Usage: orchestrator.py trigger <trigger_type>")
            sys.exit(1)

        trigger = sys.argv[2]
        metadata = {"test": True}

        workflow = orchestrator.trigger_workflow(trigger, metadata)
        print(json.dumps(workflow, indent=2))

    elif command == "audit":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        trail = orchestrator.get_audit_trail(limit=limit)

        for entry in trail:
            print(f"[{entry['event_type']}] {entry['action']} → {entry['result']}")
            print(f"  Trigger: {entry['trigger']}")
            print()

    elif command == "escalations":
        if orchestrator.state["escalations"]:
            print(f"Pending escalations: {len(orchestrator.state['escalations'])}")
            for escalation in orchestrator.state["escalations"]:
                print(f"- {escalation['reason']}")
        else:
            print("No pending escalations")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
