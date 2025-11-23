#!/usr/bin/env python3
"""
Error Detection & Classification Library
Provides autonomous error detection, risk/effort quantification, and remediation decisions
"""
import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path


class ErrorCategory(Enum):
    """Error category classification"""
    SECURITY = "security"
    DATA_LOSS = "data_loss"
    BREAKING_CHANGE = "breaking_change"
    LOGIC_ERROR = "logic_error"
    TEST_FAILURE = "test_failure"
    STYLE_DRIFT = "style_drift"
    ANTI_PATTERN = "anti_pattern"
    COMPLEXITY = "complexity"


class ActionDecision(Enum):
    """Decision on how to handle error"""
    AUTO_FIX = "auto_fix"
    CONSULT = "consult"
    DEFER = "defer"
    BLOCK = "block"


@dataclass
class ErrorReport:
    """Structured error report"""
    error_id: str
    category: ErrorCategory
    description: str
    file_path: Optional[str]
    line_number: Optional[int]
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    risk: int  # 0-100
    effort: int  # 0-100
    detected_at_turn: int
    tool_name: Optional[str]
    command: Optional[str]
    reversible: bool
    affects_production: bool
    has_tests: bool

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['category'] = self.category.value
        return data


@dataclass
class FixSuggestion:
    """Fix suggestion with execution plan"""
    approach: str
    steps: List[str]
    risk_after_fix: int
    reversible: bool
    one_click: bool
    code_change: Optional[str] = None


def calculate_risk(error: ErrorReport) -> int:
    """
    Calculate risk score (0-100) based on error characteristics

    Uses deterministic rules, no ML/heuristics

    Returns:
        int: Risk score 0-100
    """
    # Base risk by category (with fallback for unknown categories)
    risk_map = {
        ErrorCategory.SECURITY: 90,
        ErrorCategory.DATA_LOSS: 85,
        ErrorCategory.BREAKING_CHANGE: 70,
        ErrorCategory.LOGIC_ERROR: 50,
        ErrorCategory.TEST_FAILURE: 30,
        ErrorCategory.COMPLEXITY: 40,
        ErrorCategory.ANTI_PATTERN: 35,
        ErrorCategory.STYLE_DRIFT: 20,
    }
    base_risk = risk_map.get(error.category, 50)  # Default to medium risk if unknown

    # Modifiers
    if error.affects_production:
        base_risk += 10
    if not error.reversible:
        base_risk += 15
    if not error.has_tests:
        base_risk += 10

    return min(100, max(0, base_risk))


def calculate_effort(error: ErrorReport) -> int:
    """
    Calculate effort score (0-100) based on scope

    Returns:
        int: Effort score 0-100
    """
    # Effort heuristics based on description patterns
    description_lower = error.description.lower()

    # Single-line fixes
    if any(pattern in description_lower for pattern in [
        "print statement",
        "hardcoded",
        "import *",
        "missing import",
    ]):
        base_effort = 10

    # Function-level changes
    elif any(pattern in description_lower for pattern in [
        "function complexity",
        "refactor function",
        "missing docstring",
    ]):
        base_effort = 25

    # File-level changes
    elif any(pattern in description_lower for pattern in [
        "multiple functions",
        "class refactor",
        "missing tests",
    ]):
        base_effort = 40

    # Multi-file changes
    elif any(pattern in description_lower for pattern in [
        "cross-file",
        "api change",
        "breaking change",
    ]):
        base_effort = 70

    # Architecture changes
    elif any(pattern in description_lower for pattern in [
        "architecture",
        "system-wide",
        "migration",
    ]):
        base_effort = 95

    else:
        base_effort = 30  # Default

    # Modifiers
    if error.has_tests:
        base_effort -= 10
    if error.category == ErrorCategory.SECURITY:
        base_effort += 20  # Security fixes require careful review

    return min(100, max(0, base_effort))


def decide_action(risk: int, effort: int) -> ActionDecision:
    """
    Decide action based on risk/effort matrix

    Decision Matrix:
    - Low risk + Low effort = AUTO_FIX
    - Low risk + Medium effort = CONSULT
    - Low risk + High effort = DEFER
    - Medium risk + Low effort = CONSULT
    - Medium risk + Medium+ effort = DEFER
    - High risk + Any effort = BLOCK + CONSULT

    Args:
        risk: Risk score 0-100
        effort: Effort score 0-100

    Returns:
        ActionDecision: Recommended action
    """
    # High risk always requires consultation
    if risk >= 70:
        return ActionDecision.BLOCK

    # Medium risk
    if 40 <= risk < 70:
        if effort <= 20:
            return ActionDecision.CONSULT
        else:
            return ActionDecision.DEFER

    # Low risk
    if risk < 40:
        if effort <= 20:
            return ActionDecision.AUTO_FIX
        elif effort <= 50:
            return ActionDecision.CONSULT
        else:
            return ActionDecision.DEFER

    # Fallback
    return ActionDecision.CONSULT


def classify_tool_error(tool_name: str, error_message: str, tool_input: Dict) -> Optional[ErrorReport]:
    """
    Classify error from tool failure

    Args:
        tool_name: Name of tool that failed
        error_message: Error message text
        tool_input: Tool input parameters

    Returns:
        ErrorReport if classifiable, None otherwise
    """
    # Safety checks
    if not error_message:
        return None
    if tool_input is None:
        tool_input = {}

    error_lower = error_message.lower()

    # File not found
    if "no such file" in error_lower or "file not found" in error_lower:
        return ErrorReport(
            error_id=f"tool-error-{tool_name.lower()}",
            category=ErrorCategory.LOGIC_ERROR,
            description=f"File not found: {tool_input.get('file_path', 'unknown')}",
            file_path=tool_input.get('file_path'),
            line_number=None,
            severity="MEDIUM",
            risk=40,
            effort=15,
            detected_at_turn=0,
            tool_name=tool_name,
            command=None,
            reversible=True,
            affects_production=False,
            has_tests=False,
        )

    # Permission denied
    if "permission denied" in error_lower:
        return ErrorReport(
            error_id=f"tool-error-{tool_name.lower()}",
            category=ErrorCategory.SECURITY,
            description=f"Permission denied: {tool_input.get('file_path', 'unknown')}",
            file_path=tool_input.get('file_path'),
            line_number=None,
            severity="HIGH",
            risk=70,
            effort=30,
            detected_at_turn=0,
            tool_name=tool_name,
            command=None,
            reversible=True,
            affects_production=True,
            has_tests=False,
        )

    # Syntax error
    if "syntax error" in error_lower or "invalid syntax" in error_lower:
        return ErrorReport(
            error_id=f"tool-error-{tool_name.lower()}",
            category=ErrorCategory.LOGIC_ERROR,
            description=f"Syntax error in {tool_input.get('file_path', 'code')}",
            file_path=tool_input.get('file_path'),
            line_number=None,
            severity="MEDIUM",
            risk=50,
            effort=20,
            detected_at_turn=0,
            tool_name=tool_name,
            command=None,
            reversible=True,
            affects_production=False,
            has_tests=False,
        )

    return None


def classify_bash_error(command: str, exit_code: int, stdout: str, stderr: str) -> Optional[ErrorReport]:
    """
    Classify error from bash command failure

    Args:
        command: Bash command executed
        exit_code: Exit code
        stdout: Standard output
        stderr: Standard error

    Returns:
        ErrorReport if classifiable, None otherwise
    """
    # Test failures
    if "pytest" in command or "python -m pytest" in command:
        if exit_code != 0:
            # Parse pytest output for failure details
            failure_count = 0
            if "failed" in stdout.lower():
                match = re.search(r"(\d+) failed", stdout)
                if match:
                    failure_count = int(match.group(1))

            return ErrorReport(
                error_id="test-failure",
                category=ErrorCategory.TEST_FAILURE,
                description=f"Pytest failed: {failure_count} test(s) failing",
                file_path=None,
                line_number=None,
                severity="MEDIUM",
                risk=30,
                effort=25,
                detected_at_turn=0,
                tool_name="Bash",
                command=command,
                reversible=True,
                affects_production=False,
                has_tests=True,
            )

    # Git operation failures
    if command.startswith("git "):
        if exit_code != 0:
            return ErrorReport(
                error_id="git-error",
                category=ErrorCategory.LOGIC_ERROR,
                description=f"Git operation failed: {stderr[:100]}",
                file_path=None,
                line_number=None,
                severity="LOW",
                risk=20,
                effort=15,
                detected_at_turn=0,
                tool_name="Bash",
                command=command,
                reversible=True,
                affects_production=False,
                has_tests=False,
            )

    # Command not found
    if "command not found" in stderr.lower():
        return ErrorReport(
            error_id="command-not-found",
            category=ErrorCategory.LOGIC_ERROR,
            description=f"Command not found: {command.split()[0]}",
            file_path=None,
            line_number=None,
            severity="LOW",
            risk=10,
            effort=20,
            detected_at_turn=0,
            tool_name="Bash",
            command=command,
            reversible=True,
            affects_production=False,
            has_tests=False,
        )

    return None


def detect_anti_patterns(file_path: str, content: str) -> List[ErrorReport]:
    """
    Detect anti-patterns in code content

    Args:
        file_path: Path to file
        content: File content

    Returns:
        List of ErrorReport objects
    """
    errors = []
    lines = content.split('\n')

    # Anti-pattern definitions (from anti_patterns.md)
    patterns = [
        # Security
        (r'(sk-proj-|ghp_|AWS_SECRET|api[_-]?key\s*=\s*["\'](?!.*getenv))',
         ErrorCategory.SECURITY, "Hardcoded secret detected", 95, 10),
        (r"shell\s*=\s*True",
         ErrorCategory.SECURITY, "Shell injection risk (shell=True)", 90, 15),
        (r'cursor\.execute\([^?]*f["\']',
         ErrorCategory.SECURITY, "SQL injection risk (f-string in query)", 95, 20),

        # Code quality
        (r"except\s*:",
         ErrorCategory.ANTI_PATTERN, "Blind exception catching", 25, 10),
        (r"global\s+\w+",
         ErrorCategory.ANTI_PATTERN, "Global variable mutation", 30, 15),
        (r"print\s*\(",
         ErrorCategory.STYLE_DRIFT, "Use logger.info instead of print", 15, 5),
        (r"from\s+\w+\s+import\s+\*",
         ErrorCategory.ANTI_PATTERN, "Wildcard import", 20, 10),

        # Incomplete code
        (r"TODO:",
         ErrorCategory.ANTI_PATTERN, "TODO comment found", 10, 5),
        (r"pass\s*$",
         ErrorCategory.ANTI_PATTERN, "Stub implementation (pass)", 20, 15),
    ]

    for i, line in enumerate(lines, start=1):
        for pattern, category, description, risk, effort in patterns:
            if re.search(pattern, line):
                errors.append(ErrorReport(
                    error_id=f"anti-pattern-{file_path}-{i}",
                    category=category,
                    description=f"{description} at line {i}",
                    file_path=file_path,
                    line_number=i,
                    severity="CRITICAL" if risk >= 70 else "WARNING",
                    risk=risk,
                    effort=effort,
                    detected_at_turn=0,
                    tool_name="StaticAnalysis",
                    command=None,
                    reversible=True,
                    affects_production="scratch/" not in file_path,
                    has_tests=False,
                ))

    return errors


def generate_fix_suggestions(error: ErrorReport) -> List[FixSuggestion]:
    """
    Generate fix suggestions for an error

    Args:
        error: ErrorReport object

    Returns:
        List of FixSuggestion objects
    """
    suggestions = []

    # Security: Hardcoded secrets
    if "hardcoded secret" in error.description.lower():
        suggestions.append(FixSuggestion(
            approach="Migrate to environment variable",
            steps=[
                "1. Identify secret name",
                "2. Replace with os.getenv('SECRET_NAME')",
                "3. Add secret to .env file (if not exists)",
                "4. Run verify.py grep_text to confirm",
            ],
            risk_after_fix=10,
            reversible=True,
            one_click=True,
            code_change="Replace hardcoded string with os.getenv()",
        ))
        suggestions.append(FixSuggestion(
            approach="Remove secret (disable feature temporarily)",
            steps=[
                "1. Comment out line with secret",
                "2. Add TODO for proper implementation",
                "3. Disable feature using feature flag",
            ],
            risk_after_fix=5,
            reversible=True,
            one_click=False,
        ))

    # Style: print() instead of logger
    elif "print" in error.description.lower():
        suggestions.append(FixSuggestion(
            approach="Replace with logger.info()",
            steps=[
                "1. Replace print( with logger.info(",
                "2. Ensure logger is imported",
                "3. Run audit to verify",
            ],
            risk_after_fix=5,
            reversible=True,
            one_click=True,
            code_change="s/print(/logger.info(/",
        ))

    # Anti-pattern: Wildcard import
    elif "wildcard import" in error.description.lower():
        suggestions.append(FixSuggestion(
            approach="Replace with explicit imports",
            steps=[
                "1. Identify which symbols are used",
                "2. Replace 'from X import *' with 'from X import a, b, c'",
                "3. Run tests to verify",
            ],
            risk_after_fix=15,
            reversible=True,
            one_click=False,
        ))

    # Anti-pattern: Blind exception
    elif "exception catching" in error.description.lower():
        suggestions.append(FixSuggestion(
            approach="Catch specific exception types",
            steps=[
                "1. Identify expected exception types",
                "2. Replace 'except:' with 'except SpecificError:'",
                "3. Add logging for unexpected exceptions",
            ],
            risk_after_fix=20,
            reversible=True,
            one_click=False,
        ))

    # Test failure
    elif error.category == ErrorCategory.TEST_FAILURE:
        suggestions.append(FixSuggestion(
            approach="Investigate and fix test failures",
            steps=[
                "1. Run pytest with -v flag for details",
                "2. Identify failing assertion or error",
                "3. Fix implementation or update test",
                "4. Re-run tests to verify",
            ],
            risk_after_fix=25,
            reversible=True,
            one_click=False,
        ))

    # Default suggestion
    if not suggestions:
        suggestions.append(FixSuggestion(
            approach="Manual investigation required",
            steps=[
                "1. Read the file and understand context",
                "2. Consult oracle.py for expert advice",
                "3. Apply fix manually",
                "4. Run verify to confirm",
            ],
            risk_after_fix=error.risk,
            reversible=False,
            one_click=False,
        ))

    return suggestions


def should_auto_fix(error: ErrorReport, action: ActionDecision) -> Tuple[bool, str]:
    """
    Determine if error should be auto-fixed

    Args:
        error: ErrorReport object
        action: ActionDecision from decision matrix

    Returns:
        Tuple[bool, str]: (should_fix, reason)
    """
    # Must be AUTO_FIX action
    if action != ActionDecision.AUTO_FIX:
        return False, f"Action is {action.value}, not AUTO_FIX"

    # Must be reversible
    if not error.reversible:
        return False, "Fix is not reversible"

    # Must not affect production without tests
    if error.affects_production and not error.has_tests:
        return False, "Production change without test coverage"

    # Must have low risk
    if error.risk > 40:
        return False, f"Risk too high: {error.risk}%"

    # Must have low effort
    if error.effort > 20:
        return False, f"Effort too high: {error.effort}%"

    return True, "Criteria met for auto-fix"
