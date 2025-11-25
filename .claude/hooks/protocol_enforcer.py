#!/usr/bin/env python3
"""
Protocol Enforcer Hook v2: Enhanced with Telemetry, Fast Path, and Observability

IMPROVEMENTS FROM ORACLE ANALYSIS:
1. TELEMETRY (Judge Priority #1): Structured counters, latency tracking, deny rates
2. FAST PATH (Critic #10): Low-risk tools bypass heavy analysis
3. OBSERVABILITY (Critic #9): Human-readable decision explanations
4. GRACEFUL DEGRADATION (Critic #10): Fail-open with heavy logging on errors

PHILOSOPHY:
- Single source of truth: Protocol Registry defines rules
- Multi-event: Works across different lifecycle stages
- Graduated enforcement: observe → suggest → warn → block
- Fast and safe: Wrapped in try/except for graceful degradation
- Observable: Every decision is logged with reason

INPUT FORMATS BY EVENT:
1. UserPromptSubmit: {"prompt": "...", "turn": N, "session_id": "..."}
2. PreToolUse: {"tool_name": "...", "tool_input": {...}, "turn": N, "session_id": "..."}
3. PostToolUse: {"tool_name": "...", "tool_input": {...}, "toolResult": {...}, "turn": N}

OUTPUT FORMATS:
- Suggestions/Warnings: {"hookSpecificOutput": {"hookEventName": "<event>", "additionalContext": "..."}}
- Blocks: {"decision": "block", "reason": "..."}
"""

import sys
import json
import time
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

# =============================================================================
# CONSTANTS & CONFIG
# =============================================================================

SUDO_CHECK_BUFFER = 5000  # Characters to check for SUDO keyword
MAX_TRANSCRIPT_SIZE = 50 * 1024 * 1024  # 50MB limit for safety

# Fast path: tools that skip heavy analysis (low-risk, high-frequency)
FAST_PATH_TOOLS = frozenset({
    "Read", "Glob", "Grep",  # Read-only operations
    "TodoWrite",  # Internal tracking
    "BashOutput",  # Just reading output
})

# Tools that ALWAYS get full analysis (high-risk)
FULL_ANALYSIS_TOOLS = frozenset({
    "Write", "Edit", "Bash",  # Mutating operations
    "Task",  # Agent delegation
    "WebFetch", "WebSearch",  # External communication
})

# =============================================================================
# TELEMETRY (Judge Priority #1)
# =============================================================================

@dataclass
class TelemetryState:
    """Structured telemetry for observability - persisted to disk"""
    total_executions: int = 0
    total_allows: int = 0
    total_denials: int = 0
    denials_by_rule: Dict[str, int] = field(default_factory=dict)
    denials_by_category: Dict[str, int] = field(default_factory=dict)
    latency_samples: List[float] = field(default_factory=list)  # Last 100 samples
    fast_path_hits: int = 0
    fast_path_misses: int = 0
    errors: int = 0
    sudo_overrides: int = 0
    last_updated: str = ""

    def record_execution(self, latency_ms: float, allowed: bool, rule_id: Optional[str] = None,
                         category: Optional[str] = None, fast_path: bool = False):
        """Record an execution with all metrics"""
        self.total_executions += 1
        self.last_updated = datetime.now().isoformat()

        # Latency tracking (keep last 100)
        self.latency_samples.append(latency_ms)
        if len(self.latency_samples) > 100:
            self.latency_samples = self.latency_samples[-100:]

        # Decision tracking
        if allowed:
            self.total_allows += 1
        else:
            self.total_denials += 1
            if rule_id:
                self.denials_by_rule[rule_id] = self.denials_by_rule.get(rule_id, 0) + 1
            if category:
                self.denials_by_category[category] = self.denials_by_category.get(category, 0) + 1

        # Fast path tracking
        if fast_path:
            self.fast_path_hits += 1
        else:
            self.fast_path_misses += 1

    def record_error(self):
        """Record a hook error (graceful degradation)"""
        self.errors += 1
        self.last_updated = datetime.now().isoformat()

    def record_sudo(self):
        """Record SUDO override usage"""
        self.sudo_overrides += 1
        self.last_updated = datetime.now().isoformat()

    def get_stats(self) -> Dict[str, Any]:
        """Get telemetry statistics"""
        avg_latency = sum(self.latency_samples) / len(self.latency_samples) if self.latency_samples else 0
        p95_latency = sorted(self.latency_samples)[int(len(self.latency_samples) * 0.95)] if len(self.latency_samples) >= 20 else avg_latency
        denial_rate = self.total_denials / self.total_executions if self.total_executions > 0 else 0
        fast_path_rate = self.fast_path_hits / self.total_executions if self.total_executions > 0 else 0

        return {
            "total_executions": self.total_executions,
            "total_allows": self.total_allows,
            "total_denials": self.total_denials,
            "denial_rate": f"{denial_rate:.1%}",
            "avg_latency_ms": f"{avg_latency:.2f}",
            "p95_latency_ms": f"{p95_latency:.2f}",
            "fast_path_rate": f"{fast_path_rate:.1%}",
            "errors": self.errors,
            "sudo_overrides": self.sudo_overrides,
            "top_denial_rules": dict(sorted(self.denials_by_rule.items(), key=lambda x: -x[1])[:5]),
        }

    def to_dict(self) -> Dict:
        return {
            "total_executions": self.total_executions,
            "total_allows": self.total_allows,
            "total_denials": self.total_denials,
            "denials_by_rule": self.denials_by_rule,
            "denials_by_category": self.denials_by_category,
            "latency_samples": self.latency_samples,
            "fast_path_hits": self.fast_path_hits,
            "fast_path_misses": self.fast_path_misses,
            "errors": self.errors,
            "sudo_overrides": self.sudo_overrides,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'TelemetryState':
        return cls(
            total_executions=data.get("total_executions", 0),
            total_allows=data.get("total_allows", 0),
            total_denials=data.get("total_denials", 0),
            denials_by_rule=data.get("denials_by_rule", {}),
            denials_by_category=data.get("denials_by_category", {}),
            latency_samples=data.get("latency_samples", []),
            fast_path_hits=data.get("fast_path_hits", 0),
            fast_path_misses=data.get("fast_path_misses", 0),
            errors=data.get("errors", 0),
            sudo_overrides=data.get("sudo_overrides", 0),
            last_updated=data.get("last_updated", ""),
        )


# Global telemetry (loaded/saved per session)
_telemetry: Optional[TelemetryState] = None
_telemetry_file: Optional[Path] = None


def get_telemetry() -> TelemetryState:
    """Get or load telemetry state"""
    global _telemetry, _telemetry_file

    if _telemetry is None:
        # Find project root
        project_dir = Path.cwd()
        while not (project_dir / "scripts" / "lib").exists() and project_dir != project_dir.parent:
            project_dir = project_dir.parent

        _telemetry_file = project_dir / ".claude" / "memory" / "protocol_enforcer_telemetry.json"

        if _telemetry_file.exists():
            try:
                with open(_telemetry_file) as f:
                    _telemetry = TelemetryState.from_dict(json.load(f))
            except (json.JSONDecodeError, IOError):
                _telemetry = TelemetryState()
        else:
            _telemetry = TelemetryState()

    return _telemetry


def save_telemetry():
    """Save telemetry state to disk"""
    global _telemetry, _telemetry_file
    if _telemetry and _telemetry_file:
        try:
            _telemetry_file.parent.mkdir(parents=True, exist_ok=True)
            with open(_telemetry_file, "w") as f:
                json.dump(_telemetry.to_dict(), f, indent=2)
        except (IOError, OSError):
            pass  # Graceful degradation - telemetry loss is acceptable


# =============================================================================
# DECISION LOG (Observability - Critic #9)
# =============================================================================

@dataclass
class DecisionLog:
    """Structured decision log entry for audit trail"""
    timestamp: str
    event_type: str
    tool_name: Optional[str]
    turn: int
    decision: str  # "allow", "block", "warn", "suggest"
    rule_id: Optional[str]
    category: Optional[str]
    explanation: str  # Human-readable explanation
    latency_ms: float
    fast_path: bool
    sudo_bypass: bool = False

    def to_dict(self) -> Dict:
        return {
            "ts": self.timestamp,
            "event": self.event_type,
            "tool": self.tool_name,
            "turn": self.turn,
            "decision": self.decision,
            "rule": self.rule_id,
            "category": self.category,
            "why": self.explanation,
            "latency_ms": self.latency_ms,
            "fast_path": self.fast_path,
            "sudo": self.sudo_bypass,
        }


def log_decision(log: DecisionLog):
    """Log a decision for audit trail (append to file)"""
    try:
        project_dir = Path.cwd()
        while not (project_dir / "scripts" / "lib").exists() and project_dir != project_dir.parent:
            project_dir = project_dir.parent

        log_file = project_dir / ".claude" / "memory" / "protocol_enforcer_decisions.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(log_file, "a") as f:
            f.write(json.dumps(log.to_dict()) + "\n")

        # Rotate log if too large (keep last 1000 entries)
        if log_file.stat().st_size > 100_000:  # 100KB
            lines = log_file.read_text().strip().split("\n")
            log_file.write_text("\n".join(lines[-1000:]) + "\n")
    except (IOError, OSError):
        pass  # Graceful degradation


# =============================================================================
# FAST PATH (Critic #10 - Performance)
# =============================================================================

def should_fast_path(tool_name: Optional[str], event_type: str) -> bool:
    """
    Determine if this request should use fast path (skip heavy analysis).

    Fast path criteria:
    1. Tool is in FAST_PATH_TOOLS (read-only, low-risk)
    2. Event is not PreToolUse for mutation tools
    3. Not a UserPromptSubmit (always needs prompt analysis)
    """
    # UserPromptSubmit always needs analysis (prompt patterns)
    if event_type == "UserPromptSubmit":
        return False

    # No tool = default to full analysis
    if not tool_name:
        return False

    # Explicit fast path tools
    if tool_name in FAST_PATH_TOOLS:
        return True

    # Explicit full analysis tools
    if tool_name in FULL_ANALYSIS_TOOLS:
        return False

    # PostToolUse on read-only tools can fast path
    if event_type == "PostToolUse" and tool_name in FAST_PATH_TOOLS:
        return True

    # Default: full analysis for unknown tools
    return False


# =============================================================================
# LIBRARY IMPORTS (after project root detection)
# =============================================================================

PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

sys.path.insert(0, str(PROJECT_DIR / "scripts" / "lib"))

try:
    from protocol_registry import (
        ProtocolRegistry, SituationSnapshot, RuleMatch, EnforcementLevel,
        get_enforcement_context, PROTECTED_CATEGORIES
    )
    # Note: ProtocolCategory used via match.category in PROTECTED_CATEGORIES check
    from epistemology import load_session_state, initialize_session_state
    IMPORTS_OK = True
except ImportError as e:
    IMPORTS_OK = False
    IMPORT_ERROR = str(e)


# =============================================================================
# INPUT PARSING
# =============================================================================

def parse_input(data: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """Parse input data to determine event type and extract relevant fields."""
    if "prompt" in data and "tool_name" not in data:
        event_type = "UserPromptSubmit"
    elif "tool_name" in data and "toolResult" not in data:
        event_type = "PreToolUse"
    elif "tool_name" in data and "toolResult" in data:
        event_type = "PostToolUse"
    else:
        event_type = "Unknown"

    return event_type, data


# =============================================================================
# TRANSCRIPT ANALYSIS (optimized)
# =============================================================================

def extract_transcript_patterns(data: Dict[str, Any]) -> Optional[Dict]:
    """
    Extract patterns from recent transcript for context-aware rule evaluation.
    OPTIMIZED: Cached regex compilation, early exit on no transcript.
    """
    import re

    transcript_path = data.get("transcript_path", "")
    if not transcript_path or not os.path.exists(transcript_path):
        return None

    try:
        with open(transcript_path, 'r') as tf:
            transcript = tf.read()

        # Only analyze last 10000 chars for performance
        chunk = transcript[-10000:] if len(transcript) > 10000 else transcript

        # Filter out tool output to avoid matching code patterns
        chunk = re.sub(r'<function_results>.*?</function_results>', '', chunk, flags=re.DOTALL)
        chunk = re.sub(r'<output>.*?</output>', '', chunk, flags=re.DOTALL)
        chunk = re.sub(r'```[\s\S]*?```', '', chunk)

        patterns = {
            "recent_tools": [],
            "error_count": 0,
            "fixed_claims": False,
            "iteration_detected": False,
        }

        # Count errors (compiled patterns for performance)
        error_count = sum(len(re.findall(ep, chunk, re.IGNORECASE))
                         for ep in [r"Error:", r"FAILED", r"Exception", r"Traceback"])
        patterns["error_count"] = error_count

        # Detect fixed claims
        if re.search(r"\b(fixed|done|working|complete|resolved)\b", chunk, re.IGNORECASE):
            patterns["fixed_claims"] = True

        # Detect iteration language
        if re.search(r"for each|one by one|iterate|loop through", chunk, re.IGNORECASE):
            patterns["iteration_detected"] = True

        # Extract recent tool names
        tool_matches = re.findall(r'tool_name["\s:]+(\w+)', chunk)
        patterns["recent_tools"] = tool_matches[-10:] if tool_matches else []

        return patterns
    except (IOError, OSError):
        return None


# =============================================================================
# SNAPSHOT BUILDING
# =============================================================================

def build_snapshot(event_type: str, data: Dict[str, Any], session_state: Optional[Dict]) -> SituationSnapshot:
    """Build SituationSnapshot from input data."""
    turn = data.get("turn", 0)
    tool_name = data.get("tool_name")
    tool_input = data.get("tool_input")

    # Extract tool output/error
    tool_result = data.get("tool_response") or data.get("toolResult", {})
    tool_output = None
    tool_error = None

    if isinstance(tool_result, dict):
        content = tool_result.get("content")
        if isinstance(content, list) and content:
            tool_output = "\n".join(
                item.get("text", "") for item in content if isinstance(item, dict)
            )
        elif isinstance(content, str):
            tool_output = content
        tool_error = tool_result.get("error")

    prompt = data.get("prompt")
    transcript_summary = extract_transcript_patterns(data)

    return SituationSnapshot(
        event_type=event_type,
        turn=turn,
        prompt=prompt,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output,
        tool_error=tool_error,
        session_state=session_state,
        transcript_summary=transcript_summary,
    )


# =============================================================================
# SUDO BYPASS CHECK
# =============================================================================

def check_sudo_bypass(data: Dict[str, Any]) -> bool:
    """Check if SUDO keyword is in recent transcript."""
    transcript_path = data.get("transcript_path", "")
    if not transcript_path:
        return False

    try:
        if not os.path.exists(transcript_path):
            return False

        file_size = os.path.getsize(transcript_path)
        if file_size > MAX_TRANSCRIPT_SIZE:
            with open(transcript_path, 'r') as tf:
                tf.seek(max(0, file_size - SUDO_CHECK_BUFFER))
                return "SUDO" in tf.read(SUDO_CHECK_BUFFER)
        else:
            with open(transcript_path, 'r') as tf:
                transcript = tf.read()
                last_chunk = transcript[-SUDO_CHECK_BUFFER:] if len(transcript) > SUDO_CHECK_BUFFER else transcript
                return "SUDO" in last_chunk
    except (IOError, OSError):
        return False


# =============================================================================
# OUTPUT FORMATTING (with explanations)
# =============================================================================

def generate_explanation(matches: List[RuleMatch], event_type: str, tool_name: Optional[str]) -> str:
    """Generate human-readable explanation for the decision."""
    if not matches:
        return f"No protocol violations detected for {event_type}" + (f" on {tool_name}" if tool_name else "")

    match = matches[0]  # Highest priority match

    explanations = {
        "verify_fixed_claims": "Claimed 'fixed/done' without running /verify first",
        "audit_production_write": "Writing to production code without /audit check",
        "upkeep_before_commit": "Attempting commit without running /upkeep",
        "council_complex_decision": "Complex architectural decision detected - consider /council",
        "think_repeated_failures": "Multiple failures on same target - need /think decomposition",
        "tier_production_write": "Attempting production write at low confidence level",
        "batching_sequential_tools": "Sequential tool calls could be parallelized",
        "background_slow_command": "Slow command should use run_in_background=true",
        "scratch_manual_iteration": "Manual iteration detected - write scratch script instead",
        "macgyver_install_blocked": "Package installation blocked - use stdlib/system tools",
        "stub_code_detected": "Incomplete code (TODO/stub) in production write",
    }

    return explanations.get(match.rule_id, f"Protocol violation: {match.rule_id}")


def format_output(event_type: str, matches: List[RuleMatch], sudo_bypass: bool,
                  explanation: str, latency_ms: float) -> Dict[str, Any]:
    """Format hook output based on rule matches."""
    if not matches:
        return {
            "hookSpecificOutput": {
                "hookEventName": event_type,
            }
        }

    highest_match = matches[0]

    # SUDO bypass (non-protected categories only)
    if sudo_bypass and highest_match.enforcement == EnforcementLevel.BLOCK:
        return {
            "hookSpecificOutput": {
                "hookEventName": event_type,
                "additionalContext": f"""⚠️ SUDO BYPASS: Protocol enforcement overridden

Rule: {highest_match.rule_id}
Original enforcement: BLOCK
Protocol: {highest_match.protocol}
Why blocked: {explanation}

{highest_match.message}

⚠️ Proceeding with SUDO override (latency: {latency_ms:.1f}ms)"""
            }
        }

    # Hard block
    if highest_match.enforcement == EnforcementLevel.BLOCK:
        return {
            "decision": "block",
            "reason": f"""🚫 {explanation}

{highest_match.message}

(Protocol: {highest_match.protocol}, Rule: {highest_match.rule_id}, Latency: {latency_ms:.1f}ms)"""
        }

    # Warning
    if highest_match.enforcement == EnforcementLevel.WARN:
        return {
            "hookSpecificOutput": {
                "hookEventName": event_type,
                "additionalContext": f"""⚠️ {explanation}

{highest_match.message}"""
            }
        }

    # Suggestion
    if highest_match.enforcement == EnforcementLevel.SUGGEST:
        return {
            "hookSpecificOutput": {
                "hookEventName": event_type,
                "additionalContext": f"""💡 {explanation}

{highest_match.message}"""
            }
        }

    # Observe (no output)
    return {
        "hookSpecificOutput": {
            "hookEventName": event_type,
        }
    }


# =============================================================================
# MAIN HOOK LOGIC
# =============================================================================

def main():
    """Main hook logic with telemetry and fast path"""
    start_time = time.perf_counter()
    telemetry = get_telemetry()

    # Parse input
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "Unknown"}}))
        sys.exit(0)

    # Check imports
    if not IMPORTS_OK:
        telemetry.record_error()
        save_telemetry()
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "Unknown",
                "additionalContext": f"⚠️ Protocol Enforcer: Import error - {IMPORT_ERROR}"
            }
        }))
        sys.exit(0)

    # Capture event_type early for error logging
    captured_event_type = "Unknown"
    try:
        event_type, _ = parse_input(data)
        captured_event_type = event_type

        if event_type == "Unknown":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "Unknown"}}))
            sys.exit(0)

        tool_name = data.get("tool_name")

        # FAST PATH CHECK (Critic #10)
        if should_fast_path(tool_name, event_type):
            latency_ms = (time.perf_counter() - start_time) * 1000
            telemetry.record_execution(latency_ms, allowed=True, fast_path=True)
            save_telemetry()

            # Log fast path decision
            log_decision(DecisionLog(
                timestamp=datetime.now().isoformat(),
                event_type=event_type,
                tool_name=tool_name,
                turn=data.get("turn", 0),
                decision="allow",
                rule_id=None,
                category=None,
                explanation=f"Fast path: {tool_name} is low-risk",
                latency_ms=latency_ms,
                fast_path=True,
            ))

            print(json.dumps({"hookSpecificOutput": {"hookEventName": event_type}}))
            sys.exit(0)

        # FULL ANALYSIS PATH
        session_id = data.get("session_id", "unknown")
        session_state = load_session_state(session_id)
        if not session_state:
            session_state = initialize_session_state(session_id)

        snapshot = build_snapshot(event_type, data, session_state)

        # Get enforcement context for caching
        request_id = f"{session_id}_{data.get('turn', 0)}"
        context = get_enforcement_context(request_id)

        # Populate rolling aggregates
        if snapshot.transcript_summary:
            ts = snapshot.transcript_summary
            context.error_count_rolling = ts.get("error_count", 0)
            context.tool_call_count = len(ts.get("recent_tools", []))

        if event_type == "PreToolUse":
            context.increment_tool_calls()

        # Check for prior block
        if context.had_block():
            latency_ms = (time.perf_counter() - start_time) * 1000
            telemetry.record_execution(latency_ms, allowed=False, rule_id="prior_block", fast_path=False)
            save_telemetry()
            print(json.dumps({
                "decision": "block",
                "reason": "🚫 Prior event in this request was blocked. Maintaining consistency."
            }))
            sys.exit(0)

        # Evaluate rules
        registry = ProtocolRegistry()
        matches = registry.evaluate(snapshot, context=context)

        # Check SUDO bypass
        sudo_bypass = check_sudo_bypass(data)

        # Handle protected category bypasses
        if sudo_bypass and matches:
            telemetry.record_sudo()
            for match in matches:
                if match.category in PROTECTED_CATEGORIES and match.enforcement == EnforcementLevel.BLOCK:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    telemetry.record_execution(latency_ms, allowed=False,
                                               rule_id=match.rule_id,
                                               category=match.category.value,
                                               fast_path=False)
                    save_telemetry()

                    log_decision(DecisionLog(
                        timestamp=datetime.now().isoformat(),
                        event_type=event_type,
                        tool_name=tool_name,
                        turn=data.get("turn", 0),
                        decision="block",
                        rule_id=match.rule_id,
                        category=match.category.value,
                        explanation=f"NON-BYPASSABLE: {match.category.value} rules cannot be overridden",
                        latency_ms=latency_ms,
                        fast_path=False,
                        sudo_bypass=True,
                    ))

                    print(json.dumps({
                        "decision": "block",
                        "reason": f"""🛑 NON-BYPASSABLE SAFETY BLOCK

Rule: {match.rule_id}
Category: {match.category.value.upper()} (Protected)
Protocol: {match.protocol}

{match.message}

⛔ SUDO OVERRIDE DENIED: {match.category.value.upper()} category rules cannot be bypassed."""
                    }))
                    sys.exit(0)
                else:
                    registry.record_bypass(match.rule_id, "SUDO override")

        # Auto-tuning (every 50 evaluations)
        stats = registry.get_stats()
        if stats.get("total_evaluations", 0) % 50 == 0 and stats.get("total_evaluations", 0) > 0:
            tuning_changes = registry.auto_tune()
            if tuning_changes:
                print(f"🔧 Auto-tuning applied: {tuning_changes}", file=sys.stderr)

        # Generate explanation and format output
        latency_ms = (time.perf_counter() - start_time) * 1000
        explanation = generate_explanation(matches, event_type, tool_name)
        output = format_output(event_type, matches, sudo_bypass, explanation, latency_ms)

        # Record telemetry
        allowed = "decision" not in output or output.get("decision") != "block"
        rule_id = matches[0].rule_id if matches else None
        category = matches[0].category.value if matches else None
        telemetry.record_execution(latency_ms, allowed, rule_id, category, fast_path=False)
        save_telemetry()

        # Log decision
        log_decision(DecisionLog(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            tool_name=tool_name,
            turn=data.get("turn", 0),
            decision="allow" if allowed else "block",
            rule_id=rule_id,
            category=category,
            explanation=explanation,
            latency_ms=latency_ms,
            fast_path=False,
            sudo_bypass=sudo_bypass,
        ))

        print(json.dumps(output))
        sys.exit(0)

    except Exception as e:
        # Graceful degradation - allow on error
        latency_ms = (time.perf_counter() - start_time) * 1000
        telemetry.record_error()
        save_telemetry()

        log_decision(DecisionLog(
            timestamp=datetime.now().isoformat(),
            event_type=captured_event_type,
            tool_name=data.get("tool_name"),
            turn=data.get("turn", 0),
            decision="allow",
            rule_id=None,
            category=None,
            explanation=f"Error (graceful degradation): {type(e).__name__}",
            latency_ms=latency_ms,
            fast_path=False,
        ))

        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": data.get("tool_name", "Unknown"),
                "additionalContext": f"⚠️ Protocol Enforcer error (allowing): {type(e).__name__}"
            }
        }))
        sys.exit(0)


if __name__ == "__main__":
    main()
