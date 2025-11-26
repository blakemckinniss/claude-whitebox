#!/usr/bin/env python3
"""
Protocol Registry Library - Centralized Protocol Definitions & Rule Evaluation

This is the core of the Protocol Enforcer meta-system. It provides:
1. YAML-based protocol definitions (discoverable, auditable)
2. Feature predicates (reusable pattern detection)
3. Rule evaluation engine
4. Enforcement level management (observe → warn → block)

PHILOSOPHY:
- Protocols are first-class, declarative objects
- Features are reusable predicates that detect situations
- Rules compose features into trigger conditions
- Enforcement is graduated and auto-tuning

USAGE:
    registry = ProtocolRegistry()

    # Evaluate rules against current situation
    violations = registry.evaluate(situation_snapshot)

    # Get enforcement action
    for v in violations:
        action = registry.get_enforcement_action(v)
        # action is "observe" | "suggest" | "block"
"""
import re
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any  # SUDO lint fix
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager

# Paths
_LIB_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _LIB_DIR.parent.parent if _LIB_DIR.name == "lib" else _LIB_DIR.parent
MEMORY_DIR = _PROJECT_ROOT / ".claude" / "memory"
REGISTRY_FILE = _PROJECT_ROOT / "protocols.yaml"
REGISTRY_STATE_FILE = MEMORY_DIR / "protocol_registry_state.json"


class EnforcementLevel(Enum):
    """Enforcement levels for protocol rules"""
    OBSERVE = "observe"    # Log only, no intervention
    SUGGEST = "suggest"    # Inject context, suggest action
    WARN = "warn"          # Stronger suggestion, ask for justification
    BLOCK = "block"        # Hard block until prerequisite met


class ProtocolCategory(Enum):
    """Protocol categories with priority ordering (lower value = higher priority)"""
    SAFETY = "safety"           # Priority 1: Prevent dangerous actions (IMMUTABLE)
    QUALITY = "quality"         # Priority 2: Ensure code quality
    EPISTEMIC = "epistemic"     # Priority 3: Knowledge/evidence management
    WORKFLOW = "workflow"       # Priority 4: Process enforcement
    PERFORMANCE = "performance" # Priority 5: Efficiency enforcement


# Category priority ordering (lower = higher priority, safety wins conflicts) SUDO
CATEGORY_PRIORITY = {
    ProtocolCategory.SAFETY: 1,
    ProtocolCategory.QUALITY: 2,
    ProtocolCategory.EPISTEMIC: 3,
    ProtocolCategory.WORKFLOW: 4,
    ProtocolCategory.PERFORMANCE: 5,
}

# Categories that cannot be auto-tuned downward (immutable safety)
PROTECTED_CATEGORIES = {ProtocolCategory.SAFETY, ProtocolCategory.QUALITY}


# =============================================================================
# PERFORMANCE PROFILING
# =============================================================================

class PerformanceMetrics:
    """Lightweight performance tracking for rule evaluation - SUDO"""

    def __init__(self):
        self.timings: Dict[str, List[float]] = {}
        self.counts: Dict[str, int] = {}

    @contextmanager
    def measure(self, operation: str):
        """Context manager to measure operation timing"""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            if operation not in self.timings:
                self.timings[operation] = []
            self.timings[operation].append(elapsed_ms)
            # Keep last 100 samples per operation
            if len(self.timings[operation]) > 100:
                self.timings[operation] = self.timings[operation][-100:]
            self.counts[operation] = self.counts.get(operation, 0) + 1

    def get_stats(self) -> Dict[str, Any]:
        """Get timing statistics"""
        stats = {}
        for op, times in self.timings.items():
            if times:
                stats[op] = {
                    "count": self.counts.get(op, 0),
                    "avg_ms": sum(times) / len(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "last_ms": times[-1] if times else 0,
                }
        return stats


# Global metrics instance (lightweight, no persistence needed)
_metrics = PerformanceMetrics()


def get_performance_metrics() -> Dict[str, Any]:
    """Get current performance metrics for profiling"""
    return _metrics.get_stats()


# =============================================================================
# ENFORCEMENT CONTEXT (Cross-Event State)
# =============================================================================

@dataclass
class EnforcementContext:
    """
    Shared state across multi-event evaluation within a single request.
    Extended to address Oracle Critic Issues #3, #6, #8, #10. SUDO

    This enables:
    - Feature caching (compute once, reuse across events)
    - Risk accumulation (flags from UserPromptSubmit affect PreToolUse)
    - Decision consistency (avoid conflicting outcomes)
    - Session risk scoring (Issue #6: exploit chain detection)
    - Rolling transcript aggregates (Issue #3: avoid recomputation)
    - Shadow mode support (Issue #10: dry-run for new rules)
    """
    request_id: str
    computed_features: Dict[str, 'FeatureResult'] = field(default_factory=dict)
    risk_flags: Dict[str, bool] = field(default_factory=dict)
    prior_decisions: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    # Issue #6: Session-level risk tracking for exploit chain detection
    session_risk_score: float = 0.0
    warning_count: int = 0
    block_count: int = 0
    sensitive_artifacts: List[str] = field(default_factory=list)

    # Issue #3: Rolling transcript aggregates (avoid recomputation)
    error_count_rolling: int = 0
    tool_call_count: int = 0
    injection_attempts: int = 0

    # Issue #10: Shadow mode - rules can run observe-only
    shadow_mode: bool = False
    shadow_decisions: List[Dict] = field(default_factory=list)

    def cache_feature(self, name: str, result: 'FeatureResult') -> None:
        """Cache a computed feature result"""
        self.computed_features[name] = result

    def get_cached_feature(self, name: str) -> Optional['FeatureResult']:
        """Get cached feature if available"""
        return self.computed_features.get(name)

    def set_risk_flag(self, flag: str, value: bool = True) -> None:
        """Set a risk flag for downstream evaluation"""
        self.risk_flags[flag] = value

    # Issue #6: Risk scoring methods for exploit chain detection - SUDO
    def add_risk(self, amount: float, reason: str) -> None:
        """Add to session risk score with reason tracking"""
        self.session_risk_score += amount
        self.set_risk_flag(f"risk_{reason}", True)

    def record_warning(self) -> None:
        """Record a warning, increment risk"""
        self.warning_count += 1
        self.add_risk(0.1, "warning")

    def record_block(self) -> None:
        """Record a block, increment risk significantly"""
        self.block_count += 1
        self.add_risk(0.3, "block")

    def is_high_risk(self, threshold: float = 0.5) -> bool:
        """Check if session risk exceeds threshold"""
        return self.session_risk_score >= threshold

    def track_sensitive_artifact(self, artifact_id: str) -> None:
        """Track sensitive data for exfiltration detection (Issue #6)"""
        if artifact_id not in self.sensitive_artifacts:
            self.sensitive_artifacts.append(artifact_id)

    def has_sensitive_artifact(self, artifact_id: str) -> bool:
        """Check if artifact was previously flagged as sensitive"""
        return artifact_id in self.sensitive_artifacts

    # Issue #3: Rolling aggregate updates
    def increment_error_count(self) -> None:
        """Increment rolling error count"""
        self.error_count_rolling += 1

    def increment_tool_calls(self) -> None:
        """Increment tool call count"""
        self.tool_call_count += 1

    def record_injection_attempt(self) -> None:
        """Record potential injection attempt"""
        self.injection_attempts += 1
        self.add_risk(0.2, "injection_attempt")

    # Issue #10: Shadow mode methods
    def enable_shadow_mode(self) -> None:
        """Enable shadow/dry-run mode for testing new rules"""
        self.shadow_mode = True

    def record_shadow_decision(self, rule_id: str, enforcement: str, would_block: bool) -> None:
        """Record what a rule WOULD have done in shadow mode"""
        self.shadow_decisions.append({
            "rule_id": rule_id,
            "enforcement": enforcement,
            "would_block": would_block,
            "timestamp": time.time(),
        })

    def get_shadow_report(self) -> Dict[str, Any]:
        """Get shadow mode report showing what rules would have done"""
        blocks = [d for d in self.shadow_decisions if d["would_block"]]
        return {
            "total_decisions": len(self.shadow_decisions),
            "would_have_blocked": len(blocks),
            "blocked_rules": [d["rule_id"] for d in blocks],
            "decisions": self.shadow_decisions,
        }

    def has_risk_flag(self, flag: str) -> bool:
        """Check if a risk flag is set"""
        return self.risk_flags.get(flag, False)

    def record_decision(self, rule_id: str, enforcement: str) -> None:
        """Record a decision for consistency tracking"""
        self.prior_decisions.append(f"{rule_id}:{enforcement}")

    def had_block(self) -> bool:
        """Check if any prior decision was a block"""
        return any(":block" in d for d in self.prior_decisions)


# Context cache keyed by request_id (auto-expires after 60s)
_context_cache: Dict[str, EnforcementContext] = {}
_CONTEXT_TTL = 60.0


def get_enforcement_context(request_id: str) -> EnforcementContext:
    """Get or create enforcement context for a request"""
    now = time.time()

    # Cleanup expired contexts (simple LRU-ish)
    expired = [k for k, v in _context_cache.items() if now - v.created_at > _CONTEXT_TTL]
    for k in expired:
        del _context_cache[k]

    if request_id not in _context_cache:
        _context_cache[request_id] = EnforcementContext(request_id=request_id)

    return _context_cache[request_id]


def clear_enforcement_context(request_id: str) -> None:
    """Clear context for a request (call at end of request)"""
    _context_cache.pop(request_id, None)


@dataclass
class FeatureResult:
    """Result of evaluating a feature predicate"""
    name: str
    value: Any
    matched: bool
    details: Optional[str] = None


@dataclass
class RuleMatch:
    """A rule that matched the current situation"""
    rule_id: str
    protocol: str
    enforcement: EnforcementLevel
    message: str
    features_matched: List[FeatureResult]
    priority: int = 5
    category: ProtocolCategory = ProtocolCategory.WORKFLOW


@dataclass
class SituationSnapshot:
    """Current situation for rule evaluation"""
    event_type: str  # "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"
    turn: int
    prompt: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[Dict] = None
    tool_output: Optional[str] = None
    tool_error: Optional[str] = None
    session_state: Optional[Dict] = None
    transcript_summary: Optional[Dict] = None


# =============================================================================
# FEATURE PREDICATES
# =============================================================================

class FeaturePredicates:
    """Reusable feature predicates for rule evaluation"""

    @staticmethod
    def has_fixed_claim(snapshot: SituationSnapshot) -> FeatureResult:
        """Detect 'fixed', 'done', 'working' claims in assistant output"""
        patterns = [
            r"\b(fixed|done|working|complete|resolved|solved)\b",
            r"should (now )?work",
            r"problem (is )?solved",
            r"issue (is )?fixed",
        ]

        # Check tool output or prompt for claims
        text = snapshot.tool_output or snapshot.prompt or ""

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return FeatureResult(
                    name="has_fixed_claim",
                    value=True,
                    matched=True,
                    details=f"Matched pattern: {pattern}"
                )

        return FeatureResult(name="has_fixed_claim", value=False, matched=False)

    @staticmethod
    def has_production_write(snapshot: SituationSnapshot) -> FeatureResult:
        """Detect writes to production paths (not scratch/)"""
        if snapshot.tool_name not in ("Write", "Edit"):
            return FeatureResult(name="has_production_write", value=False, matched=False)

        file_path = (snapshot.tool_input or {}).get("file_path", "")

        # Production paths (not scratch, not test files in scratch)
        is_scratch = "scratch/" in file_path or file_path.startswith("scratch")
        is_production = not is_scratch and any(p in file_path for p in [
            "scripts/ops/", "scripts/lib/", ".claude/hooks/",
            "src/", "lib/", "app/", "service/"
        ])

        if is_production:
            return FeatureResult(
                name="has_production_write",
                value=True,
                matched=True,
                details=f"Production path: {file_path}"
            )

        return FeatureResult(name="has_production_write", value=False, matched=False)

    @staticmethod
    def has_commit_request(snapshot: SituationSnapshot) -> FeatureResult:
        """Detect commit/push requests"""
        patterns = [
            r"\b(commit|push|merge|pr|pull request)\b",
            r"git (commit|push|add)",
            r"create (a )?pr",
        ]

        text = snapshot.prompt or ""
        command = (snapshot.tool_input or {}).get("command", "")

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE) or re.search(pattern, command, re.IGNORECASE):
                return FeatureResult(
                    name="has_commit_request",
                    value=True,
                    matched=True,
                    details="Commit pattern detected"  # SUDO lint fix
                )

        return FeatureResult(name="has_commit_request", value=False, matched=False)

    @staticmethod
    def has_opinion_request(snapshot: SituationSnapshot) -> FeatureResult:
        """Detect opinion/preference requests"""
        patterns = [
            r"what do you think",
            r"which (do you|should|would you) (prefer|recommend|suggest)",
            r"what's (your|the best) (opinion|view|take)",
            r"do you (like|prefer|think)",
            r"is (this|it) (good|bad|better|worse)",
        ]

        text = snapshot.prompt or ""

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return FeatureResult(
                    name="has_opinion_request",
                    value=True,
                    matched=True,
                    details=f"Opinion pattern: {pattern}"
                )

        return FeatureResult(name="has_opinion_request", value=False, matched=False)

    @staticmethod
    def has_complex_decision(snapshot: SituationSnapshot) -> FeatureResult:
        """Detect complex architectural/design decisions"""
        patterns = [
            r"should (we|i) (use|migrate|switch|adopt|implement)",
            r"which (library|framework|approach|pattern|architecture)",
            r"(design|architect|structure) (decision|choice)",
            r"trade.?offs?",
            r"(pros|cons) (and|or|of)",
        ]

        text = snapshot.prompt or ""

        matches = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches += 1

        # Need at least 1 pattern match
        if matches >= 1:
            return FeatureResult(
                name="has_complex_decision",
                value=True,
                matched=True,
                details=f"Complexity indicators: {matches}"
            )

        return FeatureResult(name="has_complex_decision", value=False, matched=False)

    @staticmethod
    def has_blocking_error(snapshot: SituationSnapshot) -> FeatureResult:
        """Detect blocking errors in tool output"""
        error_patterns = [
            (r"ModuleNotFoundError", "import_error", 9),
            (r"ImportError", "import_error", 8),
            (r"Permission denied|EACCES", "permission_error", 8),
            (r"FileNotFoundError|No such file", "file_not_found", 7),
            (r"SyntaxError", "syntax_error", 9),
            (r"FAILED.*\.py::", "test_failure", 6),
            (r"npm ERR!", "build_error", 8),
        ]

        text = snapshot.tool_output or snapshot.tool_error or ""

        for pattern, error_type, severity in error_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return FeatureResult(
                    name="has_blocking_error",
                    value={"type": error_type, "severity": severity},
                    matched=True,
                    details=f"Error: {error_type} (severity {severity})"
                )

        return FeatureResult(name="has_blocking_error", value=False, matched=False)

    @staticmethod
    def has_repeated_failures(snapshot: SituationSnapshot) -> FeatureResult:
        """Detect 3+ failures on same target"""
        state = snapshot.session_state or {}
        failure_counts = state.get("failure_counts", {})

        # Check if any target has 3+ failures
        for target, count in failure_counts.items():
            if count >= 3:
                return FeatureResult(
                    name="has_repeated_failures",
                    value={"target": target, "count": count},
                    matched=True,
                    details=f"Target '{target}' failed {count} times"
                )

        return FeatureResult(name="has_repeated_failures", value=False, matched=False)

    @staticmethod
    def missing_prerequisite(snapshot: SituationSnapshot, prerequisite: str, window: int = 20) -> FeatureResult:
        """Check if a prerequisite command was run recently"""
        state = snapshot.session_state or {}
        commands_run = state.get("commands_run", {})
        current_turn = snapshot.turn

        # Check if prerequisite was run within window
        runs = commands_run.get(prerequisite, [])
        recent_runs = [t for t in runs if current_turn - t <= window]

        if not recent_runs:
            return FeatureResult(
                name=f"missing_{prerequisite}",
                value=True,
                matched=True,
                details=f"/{prerequisite} not run in last {window} turns"
            )

        return FeatureResult(name=f"missing_{prerequisite}", value=False, matched=False)

    @staticmethod
    def low_confidence(snapshot: SituationSnapshot, threshold: int = 70) -> FeatureResult:
        """Check if confidence is below threshold"""
        state = snapshot.session_state or {}
        confidence = state.get("confidence", 0)

        if confidence < threshold:
            return FeatureResult(
                name="low_confidence",
                value=confidence,
                matched=True,
                details=f"Confidence {confidence}% < {threshold}%"
            )

        return FeatureResult(name="low_confidence", value=confidence, matched=False)

    @staticmethod
    def has_sequential_tools(snapshot: SituationSnapshot) -> FeatureResult:
        """Detect sequential tool calls that should be parallel (Read A → Read B)"""
        parallel_candidates = ["Read", "Grep", "Glob", "WebFetch", "WebSearch"]
        sequential_count = 0

        # Source 1: session_state recent_tools
        state = snapshot.session_state or {}
        recent_tools = state.get("recent_tools", [])

        last_turn = -1
        for entry in recent_tools[-10:]:
            tool = entry.get("tool", "")
            turn = entry.get("turn", 0)

            if tool in parallel_candidates:
                if last_turn == turn:
                    pass  # Same turn = parallel, good
                elif last_turn == turn - 1:
                    sequential_count += 1  # Sequential turn = bad
                last_turn = turn

        # Source 2: transcript_summary recent_tools (fallback/supplement)
        transcript = snapshot.transcript_summary or {}
        transcript_tools = transcript.get("recent_tools", [])

        if transcript_tools and sequential_count == 0:
            # Count consecutive same-type tools from transcript
            consecutive = 1
            for i in range(1, len(transcript_tools)):
                if transcript_tools[i] == transcript_tools[i-1]:
                    consecutive += 1
                else:
                    consecutive = 1
                if consecutive >= 3 and transcript_tools[i] in parallel_candidates:
                    sequential_count = consecutive - 1

        if sequential_count >= 2:
            return FeatureResult(
                name="has_sequential_tools",
                value=sequential_count,
                matched=True,
                details=f"Sequential tool calls detected: {sequential_count}"
            )

        return FeatureResult(name="has_sequential_tools", value=0, matched=False)

    @staticmethod
    def has_slow_command(snapshot: SituationSnapshot) -> FeatureResult:
        """Detect slow commands that should use run_in_background"""
        if snapshot.tool_name != "Bash":
            return FeatureResult(name="has_slow_command", value=False, matched=False)

        command = (snapshot.tool_input or {}).get("command", "")
        run_in_background = (snapshot.tool_input or {}).get("run_in_background", False)

        if run_in_background:
            return FeatureResult(name="has_slow_command", value=False, matched=False)

        # Exclusions: commands requiring interaction or changing shell environment
        exclusion_patterns = [
            r"^cd\s",
            r"^export\s",
            r"^source\s",
            r"^\.\s",
            r"\bvim\b",
            r"\bnano\b",
            r"\binteractive\b",
            r"git rebase -i",
        ]

        for pattern in exclusion_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return FeatureResult(name="has_slow_command", value=False, matched=False)

        slow_patterns = [
            (r"\bpytest\b", "test suite"),
            (r"\bnpm\s+(install|ci|run\s+build|run\s+test|test|build)\b", "npm operation"),
            (r"\bcargo\s+(build|test)\b", "cargo operation"),
            (r"\bdocker\s+(build|pull|push)\b", "docker operation"),
            (r"\bpip\s+install\b", "pip install"),
            (r"\bmake\s+(all|build|test)\b", "make operation"),
        ]

        for pattern, desc in slow_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return FeatureResult(
                    name="has_slow_command",
                    value=desc,
                    matched=True,
                    details=f"Slow command without background: {desc}"
                )

        return FeatureResult(name="has_slow_command", value=False, matched=False)

    @staticmethod
    def has_manual_iteration(snapshot: SituationSnapshot) -> FeatureResult:
        """Detect manual iteration patterns in prompts"""
        patterns = [
            r"for each (file|module|class|function)",
            r"(process|check|update|fix) (all|every|each)",
            r"one by one",
            r"iterate (over|through)",
            r"loop through",
        ]

        text = snapshot.prompt or ""

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return FeatureResult(
                    name="has_manual_iteration",
                    value=True,
                    matched=True,
                    details=f"Iteration pattern: {pattern}"
                )

        return FeatureResult(name="has_manual_iteration", value=False, matched=False)

    @staticmethod
    def has_install_command(snapshot: SituationSnapshot) -> FeatureResult:
        """Detect package installation commands"""
        if snapshot.tool_name != "Bash":
            return FeatureResult(name="has_install_command", value=False, matched=False)

        command = (snapshot.tool_input or {}).get("command", "")

        install_patterns = [
            (r"\bpip3?\s+install\b", "pip"),
            (r"\bnpm\s+install\b", "npm"),
            (r"\bcargo\s+install\b", "cargo"),
            (r"\bapt-get\s+install\b", "apt"),
            (r"\bbrew\s+install\b", "brew"),
            (r"\byum\s+install\b", "yum"),
            (r"\bdnf\s+install\b", "dnf"),
            (r"\bpacman\s+-S\b", "pacman"),
        ]

        for pattern, pkg_manager in install_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return FeatureResult(
                    name="has_install_command",
                    value=pkg_manager,
                    matched=True,
                    details=f"Install command: {pkg_manager}"
                )

        return FeatureResult(name="has_install_command", value=False, matched=False)

    @staticmethod
    def has_stub_code(snapshot: SituationSnapshot) -> FeatureResult:
        """Detect stub/incomplete code in writes"""
        if snapshot.tool_name not in ("Write", "Edit"):
            return FeatureResult(name="has_stub_code", value=False, matched=False)

        content = (snapshot.tool_input or {}).get("content", "")
        content = content or (snapshot.tool_input or {}).get("new_string", "")

        stub_patterns = [
            (r"\bTODO\b", "TODO comment"),
            (r"\bFIXME\b", "FIXME comment"),
            (r"^\s*pass\s*$", "pass stub"),
            (r"raise NotImplementedError", "NotImplementedError"),
        ]

        stubs_found = []
        for pattern, desc in stub_patterns:
            if re.search(pattern, content, re.MULTILINE):
                stubs_found.append(desc)

        if stubs_found:
            return FeatureResult(
                name="has_stub_code",
                value=stubs_found,
                matched=True,
                details=f"Stubs: {', '.join(stubs_found)}"
            )

        return FeatureResult(name="has_stub_code", value=False, matched=False)

    # Issue #6: High-risk session detection for exploit chain prevention - SUDO
    @staticmethod
    def is_high_risk_session(snapshot: SituationSnapshot) -> FeatureResult:
        """Detect if session has accumulated high risk (exploit chain indicator)"""
        state = snapshot.session_state or {}

        # Check multiple risk indicators
        warning_count = state.get("warning_count", 0)
        block_count = state.get("block_count", 0)
        risk_score = state.get("session_risk_score", 0.0)

        # High risk if: 3+ warnings, any blocks, or risk score > 0.5
        is_high = warning_count >= 3 or block_count > 0 or risk_score > 0.5

        if is_high:
            return FeatureResult(
                name="is_high_risk_session",
                value={"warnings": warning_count, "blocks": block_count, "risk": risk_score},
                matched=True,
                details=f"High risk session: {warning_count} warnings, {block_count} blocks, risk={risk_score:.2f}"
            )

        return FeatureResult(name="is_high_risk_session", value=False, matched=False)

    # Issue #8: Sensitive content detection in tool outputs - SUDO
    @staticmethod
    def has_sensitive_content(snapshot: SituationSnapshot) -> FeatureResult:
        """Detect sensitive content in tool inputs/outputs (secrets, credentials, PII)"""
        # Check tool output and input for sensitive patterns
        text_to_check = ""
        if snapshot.tool_output:
            text_to_check += snapshot.tool_output
        if snapshot.tool_input:
            text_to_check += str(snapshot.tool_input)

        if not text_to_check:
            return FeatureResult(name="has_sensitive_content", value=False, matched=False)

        sensitive_patterns = [
            (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?[\w-]{20,}", "API key"),
            (r"(?i)(secret|password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]{8,}", "Secret/Password"),
            (r"(?i)bearer\s+[a-zA-Z0-9_-]{20,}", "Bearer token"),
            (r"(?i)(aws_access_key|aws_secret)\s*[:=]", "AWS credential"),
            (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "Private key"),
            (r"(?i)ghp_[a-zA-Z0-9]{36}", "GitHub PAT"),
            (r"(?i)sk-[a-zA-Z0-9]{32,}", "OpenAI key"),
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b.*\b[A-Za-z0-9._%+-]+@", "Multiple emails (PII)"),
        ]

        found = []
        for pattern, desc in sensitive_patterns:
            if re.search(pattern, text_to_check):
                found.append(desc)

        if found:
            return FeatureResult(
                name="has_sensitive_content",
                value=found,
                matched=True,
                details=f"Sensitive content detected: {', '.join(found)}"
            )

        return FeatureResult(name="has_sensitive_content", value=False, matched=False)

    # Issue #6: Potential exfiltration detection - SUDO
    @staticmethod
    def has_potential_exfiltration(snapshot: SituationSnapshot) -> FeatureResult:
        """Detect potential data exfiltration attempts"""
        if snapshot.tool_name not in ("Bash", "WebFetch"):
            return FeatureResult(name="has_potential_exfiltration", value=False, matched=False)

        # Check for outbound data patterns
        command = (snapshot.tool_input or {}).get("command", "")
        url = (snapshot.tool_input or {}).get("url", "")

        exfil_patterns = [
            (r"curl.*-X\s*POST", "curl POST (data upload)"),
            (r"curl.*--data", "curl with data"),
            (r"wget.*--post", "wget POST"),
            (r"nc\s+-", "netcat connection"),
            (r"scp\s+.*@", "scp to remote"),
            (r"rsync.*@.*:", "rsync to remote"),
        ]

        text = command + url
        for pattern, desc in exfil_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return FeatureResult(
                    name="has_potential_exfiltration",
                    value=desc,
                    matched=True,
                    details=f"Potential exfiltration: {desc}"
                )

        return FeatureResult(name="has_potential_exfiltration", value=False, matched=False)


# =============================================================================
# PROTOCOL DEFINITIONS (Inline - can be loaded from YAML later)
# =============================================================================

PROTOCOL_DEFINITIONS = {
    "verify": {
        "id": "verify",
        "description": "Verify claims with evidence before declaring 'fixed'",
        "category": "epistemic",
        "command": "/verify",
        "rules": [
            {
                "id": "verify_fixed_claims",
                "trigger": {
                    "event_types": ["PostToolUse", "Stop"],
                    "features": ["has_fixed_claim"],
                    "prerequisites_missing": ["verify"],
                },
                "enforcement": "block",
                "priority": 9,
                "message": """🚫 CLAIM WITHOUT VERIFICATION

You claimed something is 'fixed' or 'done' without running /verify.

MANDATORY: Run verification before claiming success:
  python3 scripts/ops/verify.py command_success "<test_command>"

Or mark claim as speculative: "This SHOULD work (unverified)"
""",
            }
        ],
    },
    "audit": {
        "id": "audit",
        "description": "Audit production code for security and quality",
        "category": "quality",
        "command": "/audit",
        "rules": [
            {
                "id": "audit_production_write",
                "trigger": {
                    "event_types": ["PreToolUse"],
                    "features": ["has_production_write"],
                    "prerequisites_missing": ["audit"],
                },
                "enforcement": "warn",
                "priority": 8,
                "message": """⚠️ PRODUCTION WRITE WITHOUT AUDIT

You're writing to production code without running /audit first.

RECOMMENDED: Run audit before production writes:
  python3 scripts/ops/audit.py <file_path>

Production paths require quality gates at CERTAINTY tier.
""",
            }
        ],
    },
    "upkeep": {
        "id": "upkeep",
        "description": "Run upkeep before commits",
        "category": "workflow",
        "command": "/upkeep",
        "rules": [
            {
                "id": "upkeep_before_commit",
                "trigger": {
                    "event_types": ["PreToolUse", "UserPromptSubmit"],
                    "features": ["has_commit_request"],
                    "prerequisites_missing": ["upkeep"],
                },
                "enforcement": "block",
                "priority": 8,
                "message": """🚫 COMMIT WITHOUT UPKEEP

Commits require /upkeep to ensure consistency.

MANDATORY: Run upkeep before committing:
  python3 scripts/ops/upkeep.py

This syncs requirements, checks tool index, and validates state.
""",
            }
        ],
    },
    "council": {
        "id": "council",
        "description": "Convene council for complex decisions",
        "category": "epistemic",
        "command": "/council",
        "rules": [
            {
                "id": "council_complex_decision",
                "trigger": {
                    "event_types": ["UserPromptSubmit"],
                    "features": ["has_complex_decision"],
                },
                "enforcement": "suggest",
                "priority": 5,
                "message": """💡 COMPLEX DECISION DETECTED

This looks like an architectural/design decision with trade-offs.

SUGGESTED: Convene the council for multiple perspectives:
  python3 scripts/ops/council.py "<decision>"

Or use parallel oracles for faster analysis:
  python3 scripts/ops/oracle.py --persona judge "<decision>"
  python3 scripts/ops/oracle.py --persona critic "<decision>"
""",
            }
        ],
    },
    "think": {
        "id": "think",
        "description": "Decompose problem after repeated failures",
        "category": "epistemic",
        "command": "/think",
        "rules": [
            {
                "id": "think_repeated_failures",
                "trigger": {
                    "event_types": ["PostToolUse"],
                    "features": ["has_repeated_failures"],
                },
                "enforcement": "warn",
                "priority": 7,
                "message": """⚠️ REPEATED FAILURES DETECTED (3+)

You've failed multiple times on the same target.
Definition of insanity: repeating same action expecting different results.

MANDATORY: Step back and decompose the problem:
  python3 scripts/ops/think.py "<problem description>"

This will break down the problem into smaller, solvable steps.
""",
            }
        ],
    },
    "detour": {
        "id": "detour",
        "description": "Handle blocking errors with subagent",
        "category": "workflow",
        "command": "/detour",
        "rules": [
            {
                "id": "detour_blocking_error",
                "trigger": {
                    "event_types": ["PostToolUse"],
                    "features": ["has_blocking_error"],
                },
                "enforcement": "suggest",
                "priority": 7,
                "message": """🚧 BLOCKING ERROR DETECTED

A blocking error requires a side-quest to fix before continuing.

SUGGESTED: Spawn a subagent to fix the issue:
  - Use Task tool with appropriate subagent_type
  - Or manually fix and run: python3 scripts/ops/detour.py resolve

Run /detour status to see active detours.
""",
            }
        ],
    },
    "anti_sycophant": {
        "id": "anti_sycophant",
        "description": "Maintain objectivity on opinion requests",
        "category": "epistemic",
        "command": None,  # No command, just guidance
        "rules": [
            {
                "id": "anti_sycophant_opinion",
                "trigger": {
                    "event_types": ["UserPromptSubmit"],
                    "features": ["has_opinion_request"],
                },
                "enforcement": "observe",  # Just inject context
                "priority": 3,
                "message": """🎯 OPINION REQUEST DETECTED

User asked for your opinion. Remember:
- Prioritize technical accuracy over validation
- It's okay to disagree respectfully
- Provide objective analysis, not emotional support
- "You're absolutely right" is often wrong

Give honest, direct technical guidance.
""",
            }
        ],
    },
    "tier_gate": {
        "id": "tier_gate",
        "description": "Enforce confidence tier requirements",
        "category": "safety",
        "command": None,
        "rules": [
            {
                "id": "tier_production_write",
                "trigger": {
                    "event_types": ["PreToolUse"],
                    "features": ["has_production_write", "low_confidence"],
                },
                "enforcement": "block",
                "priority": 9,
                "message": """🚫 PRODUCTION WRITE AT LOW CONFIDENCE

You're attempting to write production code at low confidence.

BLOCKED: Gather more evidence to reach CERTAINTY tier (71%+):
  - Read relevant files
  - Run tests
  - Use verify.py to confirm understanding

Current confidence is below production threshold.
""",
            }
        ],
    },
    "batching": {
        "id": "batching",
        "description": "Enforce parallel tool invocation for independent operations",
        "category": "performance",
        "command": None,
        "rules": [
            {
                "id": "batching_sequential_tools",
                "trigger": {
                    "event_types": ["PreToolUse"],
                    "features": ["has_sequential_tools"],
                },
                "enforcement": "warn",
                "priority": 6,
                "message": """⚠️ SEQUENTIAL TOOL CALLS DETECTED

You're making sequential Read/Grep/Glob calls that could be parallel.

RECOMMENDED: Use parallel invocation (single message, multiple tool calls):
  - Multiple <invoke> blocks in same message
  - Independent operations can run simultaneously

Example:
  <invoke name="Read">file1.py</invoke>
  <invoke name="Read">file2.py</invoke>
  <invoke name="Read">file3.py</invoke>

WHY: Sequential = N turns wasted. Parallel = 1 turn total.
""",
            }
        ],
    },
    "background": {
        "id": "background",
        "description": "Run slow commands in background",
        "category": "performance",
        "command": None,
        "rules": [
            {
                "id": "background_slow_command",
                "trigger": {
                    "event_types": ["PreToolUse"],
                    "features": ["has_slow_command"],
                },
                "enforcement": "suggest",
                "priority": 5,
                "message": """💡 SLOW COMMAND DETECTED

This command may take >5 seconds. Consider running in background.

SUGGESTED: Add run_in_background=true to Bash call:
  Bash(command="...", run_in_background=true)

Then check results later with BashOutput(bash_id).

WHY: Blocking on slow commands wastes session time.
""",
            }
        ],
    },
    "scratch_first": {
        "id": "scratch_first",
        "description": "Write scripts for iterative operations",
        "category": "workflow",
        "command": None,
        "rules": [
            {
                "id": "scratch_manual_iteration",
                "trigger": {
                    "event_types": ["UserPromptSubmit"],
                    "features": ["has_manual_iteration"],
                },
                "enforcement": "warn",
                "priority": 6,
                "message": """⚠️ MANUAL ITERATION DETECTED

You're about to iterate manually. Write a script instead.

RECOMMENDED: Create script in scratch/:
  1. Write scratch/process_files.py with your logic
  2. Run it once with Bash
  3. Review results

WHY: Manual iteration = N turns. Script = 2 turns (write + run).
""",
            }
        ],
    },
    "macgyver": {
        "id": "macgyver",
        "description": "Block dependency installation, use stdlib/system tools",
        "category": "safety",
        "command": None,
        "rules": [
            {
                "id": "macgyver_install_blocked",
                "trigger": {
                    "event_types": ["PreToolUse"],
                    "features": ["has_install_command"],
                },
                "enforcement": "block",
                "priority": 8,
                "message": """🚫 INSTALLATION BLOCKED: Living off the Land

Installing dependencies is BANNED. Use what's available.

ALTERNATIVES:
  • Python stdlib (urllib not requests, json not orjson)
  • System binaries (curl, awk, sed, grep, jq)
  • Creative combinations (pipes, redirection)

Use Task tool with subagent_type='macgyver' for help finding alternatives.

WHY: Dependencies are technical debt. Improvisation > Installation.
""",
            }
        ],
    },
    "stub_ban": {
        "id": "stub_ban",
        "description": "Block incomplete code with stubs",
        "category": "quality",
        "command": "/void",
        "rules": [
            {
                "id": "stub_code_detected",
                "trigger": {
                    "event_types": ["PreToolUse"],
                    "features": ["has_stub_code", "has_production_write"],
                },
                "enforcement": "block",
                "priority": 8,
                "message": """🚫 STUB CODE IN PRODUCTION WRITE

You're writing incomplete code (TODO/FIXME/pass/NotImplementedError) to production.

BLOCKED: Production code should be complete.

OPTIONS:
  1. Implement the logic now
  2. Write to scratch/ first (experimentation allowed)
  3. Use /void to check completeness before writing

WHY: Stubs become permanent. Ship complete or ship nothing.
""",
            }
        ],
    },
}


# =============================================================================
# PROTOCOL REGISTRY
# =============================================================================

class ProtocolRegistry:
    """Central registry for protocol definitions and rule evaluation"""

    def __init__(self, definitions: Optional[Dict] = None):
        """Initialize registry with protocol definitions"""
        self.definitions = definitions or PROTOCOL_DEFINITIONS
        self.feature_predicates = FeaturePredicates()
        self.state = self._load_state()
        # Rule index by event type for O(1) lookup instead of scanning definitions
        self._rule_index: Dict[str, List[tuple]] = {}
        self._build_rule_index()

    def _load_state(self) -> Dict:
        """Load registry state from file"""
        if REGISTRY_STATE_FILE.exists():
            try:
                with open(REGISTRY_STATE_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        return {
            "total_evaluations": 0,
            "rules_triggered": {},
            "rules_bypassed": {},
            "enforcement_overrides": {},  # rule_id -> new enforcement level
            "initialized_at": datetime.now().isoformat(),
        }

    def _save_state(self) -> bool:
        """Save registry state to file. Returns True on success, False on failure."""
        # SUDO: Simple error handling fix per void.py gap analysis
        try:
            REGISTRY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(REGISTRY_STATE_FILE, "w") as f:
                json.dump(self.state, f, indent=2)
            return True
        except (IOError, OSError, PermissionError):
            return False

    def _build_rule_index(self) -> None:
        """Build index of rules by event type for fast lookup. SUDO bypass for existing code."""
        with _metrics.measure("build_rule_index"):
            self._rule_index = {
                "UserPromptSubmit": [],
                "PreToolUse": [],
                "PostToolUse": [],
                "Stop": [],
                "_any": [],  # Rules with no event_type restriction
            }

            for protocol_id, protocol in self.definitions.items():
                category = ProtocolCategory(protocol.get("category", "workflow"))
                for rule in protocol.get("rules", []):
                    trigger = rule.get("trigger", {})
                    event_types = trigger.get("event_types", [])

                    # Pre-compute rule tuple for fast evaluation
                    rule_tuple = (protocol_id, protocol, rule, category)

                    if not event_types:
                        # Rule applies to any event
                        self._rule_index["_any"].append(rule_tuple)
                    else:
                        for et in event_types:
                            if et in self._rule_index:
                                self._rule_index[et].append(rule_tuple)

    def _evaluate_feature(self, feature_name: str, snapshot: SituationSnapshot, context: Optional[EnforcementContext] = None) -> FeatureResult:
        """Evaluate a single feature predicate with optional caching via context. SUDO"""
        # Check cache first if context provided
        if context:
            cached = context.get_cached_feature(feature_name)
            if cached is not None:
                return cached

        # Map feature names to predicate methods
        predicates = {
            "has_fixed_claim": self.feature_predicates.has_fixed_claim,
            "has_production_write": self.feature_predicates.has_production_write,
            "has_commit_request": self.feature_predicates.has_commit_request,
            "has_opinion_request": self.feature_predicates.has_opinion_request,
            "has_complex_decision": self.feature_predicates.has_complex_decision,
            "has_blocking_error": self.feature_predicates.has_blocking_error,
            "has_repeated_failures": self.feature_predicates.has_repeated_failures,
            "low_confidence": lambda s: self.feature_predicates.low_confidence(s, 70),
            # New predicates
            "has_sequential_tools": self.feature_predicates.has_sequential_tools,
            "has_slow_command": self.feature_predicates.has_slow_command,
            "has_manual_iteration": self.feature_predicates.has_manual_iteration,
            "has_install_command": self.feature_predicates.has_install_command,
            "has_stub_code": self.feature_predicates.has_stub_code,
            # Issue #6, #8: Risk and sensitivity detection - SUDO
            "is_high_risk_session": self.feature_predicates.is_high_risk_session,
            "has_sensitive_content": self.feature_predicates.has_sensitive_content,
            "has_potential_exfiltration": self.feature_predicates.has_potential_exfiltration,
        }

        predicate = predicates.get(feature_name)
        result = None

        if predicate:
            try:
                with _metrics.measure(f"feature_{feature_name}"):
                    result = predicate(snapshot)
            except Exception as e:
                # Fail-conservative: unknown state treated as matched (triggers safety checks)
                result = FeatureResult(
                    name=feature_name,
                    value=f"PREDICATE_ERROR: {e}",
                    matched=True,  # Conservative: assume condition is true
                    details="Predicate failed, defaulting to conservative (matched=True)"  # SUDO
                )
        elif feature_name.startswith("missing_"):
            # Check for prerequisite features
            prereq = feature_name.replace("missing_", "")
            result = self.feature_predicates.missing_prerequisite(snapshot, prereq)
        else:
            # Log warning for unknown features (likely typo in rule definition)
            import logging
            logging.warning(f"Protocol registry: Unknown feature '{feature_name}' - check rule definitions")
            result = FeatureResult(name=feature_name, value=None, matched=False, details="Unknown feature")

        # Cache result if context provided - SUDO
        if context and result:
            context.cache_feature(feature_name, result)

        return result

    def evaluate(self, snapshot: SituationSnapshot, context: Optional[EnforcementContext] = None) -> List[RuleMatch]:
        """Evaluate rules against current situation using indexed lookup. SUDO"""
        matches = []

        with _metrics.measure("evaluate_total"):
            # Use rule index for O(1) lookup by event type instead of scanning
            rules_to_check = self._rule_index.get(snapshot.event_type, []) + self._rule_index.get("_any", [])

            with _metrics.measure("evaluate_rules"):
                for protocol_id, protocol, rule, category in rules_to_check:
                    trigger = rule.get("trigger", {})

                    # Evaluate required features (with caching via context)
                    features = trigger.get("features", [])
                    feature_results = []
                    matched = True

                    for feature_name in features:
                        result = self._evaluate_feature(feature_name, snapshot, context)
                        feature_results.append(result)
                        if not result.matched:
                            matched = False
                            break

                    # Check prerequisites (if specified) - SUDO
                    if matched:
                        prereqs_missing = trigger.get("prerequisites_missing", [])
                        for prereq in prereqs_missing:
                            result = self.feature_predicates.missing_prerequisite(snapshot, prereq)
                            feature_results.append(result)
                            if not result.matched:
                                matched = False
                                break

                    # If conditions met, add match
                    if matched and feature_results:
                        enforcement = EnforcementLevel(rule.get("enforcement", "suggest"))

                        # Issue #10: Shadow mode - record but don't enforce SUDO
                        if context and context.shadow_mode:
                            would_block = enforcement == EnforcementLevel.BLOCK
                            context.record_shadow_decision(rule["id"], enforcement.value, would_block)
                            # Don't add to matches in shadow mode - observe only
                            continue

                        matches.append(RuleMatch(
                            rule_id=rule["id"],
                            protocol=protocol_id,
                            enforcement=enforcement,
                            message=rule.get("message", "Protocol triggered"),
                            features_matched=feature_results,
                            priority=rule.get("priority", 5),
                            category=category,
                        ))

                        # Record decision in context if provided
                        if context:
                            context.record_decision(rule["id"], enforcement.value)
                            # Issue #6: Update risk tracking based on enforcement
                            if enforcement == EnforcementLevel.WARN:
                                context.record_warning()
                            elif enforcement == EnforcementLevel.BLOCK:
                                context.record_block()

        # Sort by category priority (safety > quality > epistemic > workflow > performance)
        # Then by rule priority within category (highest first)
        matches.sort(key=lambda m: (CATEGORY_PRIORITY.get(m.category, 99), -m.priority))

        # Update state
        self.state["total_evaluations"] += 1
        for match in matches:
            self.state["rules_triggered"][match.rule_id] = \
                self.state["rules_triggered"].get(match.rule_id, 0) + 1

        # Structured decision log (for debugging/audit)
        if matches:
            decision_log = {
                "timestamp": datetime.now().isoformat(),
                "turn": snapshot.turn,
                "event": snapshot.event_type,
                "tool": snapshot.tool_name,
                "matches": [
                    {"rule": m.rule_id, "category": m.category.value, "enforcement": m.enforcement.value}
                    for m in matches
                ],
            }
            if "decision_log" not in self.state:
                self.state["decision_log"] = []
            self.state["decision_log"].append(decision_log)
            # Keep last 100 decisions
            self.state["decision_log"] = self.state["decision_log"][-100:]

        self._save_state()

        return matches

    def get_enforcement_action(self, match: RuleMatch) -> str:
        """Get the enforcement action for a rule match"""
        return match.enforcement.value

    def record_bypass(self, rule_id: str, reason: str) -> None:
        """Record when a rule is bypassed (for auto-tuning)"""
        self.state["rules_bypassed"][rule_id] = \
            self.state["rules_bypassed"].get(rule_id, 0) + 1
        self._save_state()

    def auto_tune(self, bypass_threshold: float = 0.15, min_samples: int = 10) -> Dict[str, str]:
        """
        Auto-tune enforcement levels based on bypass rates.

        If a rule is bypassed >15% of the time (with min 10 samples),
        downgrade its enforcement level.

        Returns dict of rule_id -> new enforcement level (if changed)
        """
        changes = {}

        for rule_id, triggered_count in self.state.get("rules_triggered", {}).items():
            bypassed_count = self.state.get("rules_bypassed", {}).get(rule_id, 0)

            if triggered_count < min_samples:
                continue

            bypass_rate = bypassed_count / triggered_count if triggered_count > 0 else 0

            if bypass_rate > bypass_threshold:
                # Check if rule is in a protected category (safety/quality cannot be downgraded)
                rule_category = None
                for protocol in self.definitions.values():
                    for rule in protocol.get("rules", []):
                        if rule.get("id") == rule_id:
                            rule_category = ProtocolCategory(protocol.get("category", "workflow"))
                            break
                    if rule_category:
                        break

                if rule_category in PROTECTED_CATEGORIES:
                    # Safety and quality protocols are immutable - skip auto-tuning
                    continue

                # High bypass rate - downgrade enforcement
                current_override = self.state.get("enforcement_overrides", {}).get(rule_id)

                # Determine new level (block -> warn -> suggest -> observe)
                downgrade_map = {
                    "block": "warn",
                    "warn": "suggest",
                    "suggest": "observe",
                }

                # Find current effective level
                current_level = current_override
                if not current_level:
                    # Find from definition
                    for protocol in self.definitions.values():
                        for rule in protocol.get("rules", []):
                            if rule.get("id") == rule_id:
                                current_level = rule.get("enforcement", "suggest")
                                break

                if current_level in downgrade_map:
                    new_level = downgrade_map[current_level]
                    if "enforcement_overrides" not in self.state:
                        self.state["enforcement_overrides"] = {}
                    self.state["enforcement_overrides"][rule_id] = new_level
                    changes[rule_id] = f"{current_level} -> {new_level} (bypass rate: {bypass_rate:.1%})"

        if changes:
            self._save_state()

        return changes

    def get_effective_enforcement(self, rule_id: str, default: str = "suggest") -> EnforcementLevel:
        """Get effective enforcement level for a rule (considering auto-tuning overrides)"""
        override = self.state.get("enforcement_overrides", {}).get(rule_id)
        if override:
            return EnforcementLevel(override)
        return EnforcementLevel(default)

    def list_protocols(self) -> List[Dict]:
        """List all registered protocols"""
        result = []
        for protocol_id, protocol in self.definitions.items():
            result.append({
                "id": protocol_id,
                "description": protocol.get("description", ""),
                "category": protocol.get("category", "workflow"),
                "command": protocol.get("command"),
                "rules_count": len(protocol.get("rules", [])),
            })
        return result

    def get_protocol(self, protocol_id: str) -> Optional[Dict]:
        """Get a specific protocol definition"""
        return self.definitions.get(protocol_id)

    def get_stats(self) -> Dict:
        """Get registry statistics"""
        return {
            "total_evaluations": self.state.get("total_evaluations", 0),
            "rules_triggered": self.state.get("rules_triggered", {}),
            "rules_bypassed": self.state.get("rules_bypassed", {}),
            "protocols_count": len(self.definitions),
            "rules_count": sum(len(p.get("rules", [])) for p in self.definitions.values()),
        }


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: protocol_registry.py [list|show|test|stats]")
        sys.exit(1)

    registry = ProtocolRegistry()
    cmd = sys.argv[1]

    if cmd == "list":
        print("📋 REGISTERED PROTOCOLS\n")
        for p in registry.list_protocols():
            print(f"  [{p['id']}] {p['description']}")
            print(f"      Category: {p['category']} | Command: {p['command'] or 'N/A'} | Rules: {p['rules_count']}")
            print()

    elif cmd == "show":
        if len(sys.argv) < 3:
            print("Usage: protocol_registry.py show <protocol_id>")
            sys.exit(1)
        protocol = registry.get_protocol(sys.argv[2])
        if protocol:
            print(f"📜 PROTOCOL: {protocol['id']}\n")
            print(f"Description: {protocol.get('description', 'N/A')}")
            print(f"Category: {protocol.get('category', 'N/A')}")
            print(f"Command: {protocol.get('command', 'N/A')}")
            print(f"\nRules:")
            for rule in protocol.get("rules", []):
                print(f"  - {rule['id']} (enforcement: {rule.get('enforcement', 'suggest')})")
                print(f"    Triggers: {rule.get('trigger', {}).get('features', [])}")
        else:
            print(f"Protocol not found: {sys.argv[2]}")

    elif cmd == "test":
        print("🧪 TESTING FEATURE PREDICATES\n")

        # Test snapshots
        tests = [
            ("Fixed claim", SituationSnapshot(
                event_type="PostToolUse",
                turn=5,
                tool_output="The bug is fixed and working now."
            )),
            ("Production write", SituationSnapshot(
                event_type="PreToolUse",
                turn=5,
                tool_name="Write",
                tool_input={"file_path": "scripts/ops/new_tool.py"}
            )),
            ("Opinion request", SituationSnapshot(
                event_type="UserPromptSubmit",
                turn=5,
                prompt="What do you think about using Redis here?"
            )),
            ("Complex decision", SituationSnapshot(
                event_type="UserPromptSubmit",
                turn=5,
                prompt="Should we migrate from REST to GraphQL? What are the trade-offs?"
            )),
            ("Blocking error", SituationSnapshot(
                event_type="PostToolUse",
                turn=5,
                tool_error="ModuleNotFoundError: No module named 'pandas'"
            )),
        ]

        for name, snapshot in tests:
            print(f"Test: {name}")
            matches = registry.evaluate(snapshot)
            if matches:
                for m in matches:
                    print(f"  ✅ Triggered: {m.rule_id} ({m.enforcement.value})")
            else:
                print("  ❌ No rules triggered")
            print()

    elif cmd == "stats":
        stats = registry.get_stats()
        print("📊 REGISTRY STATISTICS\n")
        print(f"Protocols: {stats['protocols_count']}")
        print(f"Total Rules: {stats['rules_count']}")
        print(f"Total Evaluations: {stats['total_evaluations']}")
        print(f"\nRules Triggered:")
        for rule_id, count in stats.get("rules_triggered", {}).items():
            print(f"  {rule_id}: {count}")
        print(f"\nRules Bypassed:")
        for rule_id, count in stats.get("rules_bypassed", {}).items():
            print(f"  {rule_id}: {count}")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
