#!/usr/bin/env python3
"""
Pattern Detection Library
Detects anti-patterns in AI behavior: hallucinations, insanity, falsehoods, loops
"""
import re
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher


def detect_hallucination(
    transcript: List[Dict], evidence_ledger: List[Dict]
) -> Optional[Dict]:
    """
    Detect hallucination: Claiming to have done something without tool evidence

    Args:
        transcript: List of conversation messages
        evidence_ledger: List of tool usage records from session state

    Returns:
        Dict with violation details if detected, None otherwise
    """
    # Common claim patterns
    CLAIM_PATTERNS = {
        r"I (?:verified|checked|confirmed)": {
            "required_tools": ["Bash"],
            "required_keywords": ["verify.py", "/verify"],
            "description": "verification",
        },
        r"I (?:tested|ran tests)": {
            "required_tools": ["Bash"],
            "required_keywords": ["pytest", "test"],
            "description": "testing",
        },
        r"I (?:read|examined|reviewed)\s+(?:the\s+)?([^\s]+\.py)": {
            "required_tools": ["Read"],
            "description": "file reading",
        },
        r"I (?:researched|looked up|searched for)": {
            "required_tools": ["Bash", "WebSearch"],
            "required_keywords": ["research.py", "/research"],
            "description": "research",
        },
        r"I (?:formatted|ran black on)": {
            "required_tools": ["Bash"],
            "required_keywords": ["black"],
            "description": "formatting",
        },
    }

    # Get last assistant message
    assistant_messages = [m for m in transcript if m.get("role") == "assistant"]
    if not assistant_messages:
        return None

    last_message = assistant_messages[-1]
    content = str(last_message.get("content", ""))

    # Check each claim pattern
    for pattern, requirements in CLAIM_PATTERNS.items():
        matches = re.finditer(pattern, content, re.IGNORECASE)

        for match in matches:
            claim_text = match.group(0)
            description = requirements["description"]

            # Check if required tools were used
            required_tools = requirements.get("required_tools", [])
            required_keywords = requirements.get("required_keywords", [])

            # Look for tool usage in evidence ledger
            found_evidence = False

            for evidence in evidence_ledger:
                tool = evidence.get("tool", "")
                target = str(evidence.get("target", "")).lower()

                # Check if tool matches
                if tool in required_tools:
                    # If keywords specified, check for them
                    if required_keywords:
                        if any(kw.lower() in target for kw in required_keywords):
                            found_evidence = True
                            break
                    else:
                        found_evidence = True
                        break

            if not found_evidence:
                return {
                    "type": "hallucination",
                    "claim": claim_text,
                    "description": description,
                    "required_tools": required_tools,
                    "message": f"Claimed '{claim_text}' but no {description} tool usage found in evidence ledger",
                }

    return None


def detect_insanity(transcript: List[Dict]) -> Optional[Dict]:
    """
    Detect insanity: Repeating the same failing action 3+ times

    Args:
        transcript: List of conversation messages

    Returns:
        Dict with violation details if detected, None otherwise
    """
    # Track tool call failures
    failures: Dict[str, int] = {}
    tool_call_pattern = r"<invoke name=\"(\w+)\">"
    error_pattern = r"<error>|Exit code [1-9]|failed|error:"

    for i, message in enumerate(transcript):
        content = str(message.get("content", ""))

        # Look for tool invocations
        tool_matches = re.finditer(tool_call_pattern, content)

        for tool_match in tool_matches:
            tool_name = tool_match.group(1)

            # Get parameter values (simplified - look for file_path, command, etc.)
            file_match = re.search(r'file_path[">]+([^"<]+)', content)
            cmd_match = re.search(r'command[">]+([^"<]+)', content)

            target = ""
            if file_match:
                target = file_match.group(1)
            elif cmd_match:
                target = cmd_match.group(1)[:50]  # First 50 chars

            # Check if next message (likely function result) contains error
            if i + 1 < len(transcript):
                next_msg = str(transcript[i + 1].get("content", ""))
                if re.search(error_pattern, next_msg, re.IGNORECASE):
                    # This tool call failed
                    key = f"{tool_name}:{target}"
                    failures[key] = failures.get(key, 0) + 1

                    if failures[key] >= 3:
                        return {
                            "type": "insanity",
                            "tool": tool_name,
                            "target": target,
                            "failures": failures[key],
                            "message": f"Attempted '{tool_name}' on '{target}' {failures[key]} times despite failures. Definition of insanity: repeating same action expecting different results.",
                        }

    return None


def detect_falsehood(transcript: List[Dict]) -> Optional[Dict]:
    """
    Detect falsehood: Self-contradiction without new evidence

    Args:
        transcript: List of conversation messages

    Returns:
        Dict with violation details if detected, None otherwise
    """
    # Extract factual statements from assistant messages
    statements = []

    # Patterns for factual claims
    FACT_PATTERNS = [
        r"((?:File|The file) .+? (?:exists|does not exist|is missing|was (?:found|not found)))",
        r"((?:File|The file) .+? (?:contains|has|includes))",
        r"(I (?:read|examined|found) .+? (?:file|config))",
        r"(Tests? (?:pass|fail|are passing|are failing|succeed|failed))",
        r"(The .+? (?:is|are|was|were) .+)",
        r"(Confidence (?:is|was) \d+%)",
    ]

    assistant_messages = [
        (i, m) for i, m in enumerate(transcript) if m.get("role") == "assistant"
    ]

    for idx, message in assistant_messages:
        content = str(message.get("content", ""))

        for pattern in FACT_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                statements.append(
                    {"turn": idx, "statement": match.group(1), "content": content}
                )

    # Look for contradictions
    for i, stmt1 in enumerate(statements):
        for stmt2 in statements[i + 1 :]:
            # Check if statements are about the same subject but contradict
            if are_contradictory(stmt1["statement"], stmt2["statement"]):
                # Check if new evidence gathered between statements
                evidence_between = has_evidence_between(
                    transcript, stmt1["turn"], stmt2["turn"]
                )

                if not evidence_between:
                    return {
                        "type": "falsehood",
                        "statement1": stmt1["statement"],
                        "statement2": stmt2["statement"],
                        "turn1": stmt1["turn"],
                        "turn2": stmt2["turn"],
                        "message": f"Contradiction detected: '{stmt1['statement']}' vs '{stmt2['statement']}' without new evidence between statements",
                    }

    return None


def detect_loop(transcript: List[Dict]) -> Optional[Dict]:
    """
    Detect loop: Repeating the same proposal/approach 3+ times

    Args:
        transcript: List of conversation messages

    Returns:
        Dict with violation details if detected, None otherwise
    """
    # Extract proposals from assistant messages
    proposals = []

    # Patterns for proposals/suggestions
    PROPOSAL_PATTERNS = [
        r"(?:Let me|I'll|I will|We should|We could) (.{20,200})",
        r"(?:Next step:|Step \d+:) (.{20,200})",
        r"(?:Recommendation:|Suggested approach:) (.{20,200})",
    ]

    assistant_messages = [m for m in transcript if m.get("role") == "assistant"]

    for message in assistant_messages:
        content = str(message.get("content", ""))

        for pattern in PROPOSAL_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                proposals.append(match.group(1).strip())

    # Look for repeated proposals (>75% similarity - slightly lower threshold)
    proposal_counts: Dict[str, List[str]] = {}

    for proposal in proposals:
        # Check similarity with existing proposal groups
        found_group = False

        for key, group in proposal_counts.items():
            # Check similarity with any proposal in the group (not just key)
            max_similarity = max(
                SequenceMatcher(None, proposal, existing).ratio() for existing in group
            )

            if max_similarity >= 0.75:
                group.append(proposal)
                found_group = True
                break

        if not found_group:
            proposal_counts[proposal] = [proposal]

    # Check for proposals repeated 3+ times
    for key, group in proposal_counts.items():
        if len(group) >= 3:
            return {
                "type": "loop",
                "proposal": key[:100],  # First 100 chars
                "occurrences": len(group),
                "message": f"Repeated the same proposal {len(group)} times: '{key[:100]}...'. This indicates circular reasoning or lack of progress.",
            }

    return None


# Helper functions


def are_contradictory(statement1: str, statement2: str) -> bool:
    """
    Check if two statements are contradictory

    Simple heuristic: Look for negation patterns on similar subjects
    """
    s1 = statement1.lower()
    s2 = statement2.lower()

    # Extract key subject (file name, etc.) from both statements
    # Look for file names
    file1 = re.search(r"([\w_-]+\.py|config\.[\w]+)", s1)
    file2 = re.search(r"([\w_-]+\.py|config\.[\w]+)", s2)

    # If both mention same file, check for contradictory claims
    if file1 and file2 and file1.group(1) == file2.group(1):
        # Special case: "does not exist" vs "read" or "contains"
        if (
            ("does not exist" in s1 or "missing" in s1)
            and ("read" in s2 or "contains" in s2 or "has" in s2)
        ) or (
            ("does not exist" in s2 or "missing" in s2)
            and ("read" in s1 or "contains" in s1 or "has" in s1)
        ):
            return True

    # Check if statements are about the same subject (>50% similarity)
    similarity = SequenceMatcher(None, s1, s2).ratio()
    if similarity < 0.5:
        return False

    # Check for opposite claims
    CONTRADICTION_PAIRS = [
        ("exists", "does not exist"),
        ("exists", "missing"),
        ("exists", "not found"),
        ("found", "not found"),
        ("pass", "fail"),
        ("is", "is not"),
        ("has", "does not have"),
        ("contains", "does not contain"),
        ("working", "broken"),
        ("working", "not working"),
    ]

    for pos, neg in CONTRADICTION_PAIRS:
        if (pos in s1 and neg in s2) or (neg in s1 and pos in s2):
            return True

    return False


def has_evidence_between(transcript: List[Dict], turn1: int, turn2: int) -> bool:
    """
    Check if new evidence was gathered between two turns

    Evidence includes: tool calls, function results, user input
    """
    for i in range(turn1 + 1, turn2):
        if i < len(transcript):
            message = transcript[i]
            role = message.get("role", "")

            # New evidence = tool calls, function results, user prompts
            if role == "user":
                return True  # User provided new info

            content = str(message.get("content", ""))
            if "<invoke" in content or "<function_results>" in content:
                return True  # Tool usage = new evidence

    return False


def analyze_patterns(transcript: List[Dict], evidence_ledger: List[Dict]) -> List[Dict]:
    """
    Run all pattern detectors and return list of violations

    Args:
        transcript: Full conversation transcript
        evidence_ledger: Tool usage evidence from session state

    Returns:
        List of detected violations (empty if none)
    """
    violations = []

    # Run each detector
    hallucination = detect_hallucination(transcript, evidence_ledger)
    if hallucination:
        violations.append(hallucination)

    insanity = detect_insanity(transcript)
    if insanity:
        violations.append(insanity)

    falsehood = detect_falsehood(transcript)
    if falsehood:
        violations.append(falsehood)

    loop = detect_loop(transcript)
    if loop:
        violations.append(loop)

    return violations
