#!/usr/bin/env python3
"""
Persona Output Parser
=====================

Parses structured output from council personas into programmatic dict format.

Handles:
- Required fields (VERDICT, CONFIDENCE, REASONING)
- Optional fields (INFO_NEEDED, ESCALATE_TO, AGREES_WITH, etc.)
- Multi-line sections
- Malformed outputs (graceful degradation)
"""
import re
from typing import Dict, List, Optional


class PersonaOutputParser:
    """Parser for structured persona outputs"""

    # Valid verdicts
    VALID_VERDICTS = {
        "PROCEED",
        "CONDITIONAL_GO",
        "STOP",
        "ABSTAIN",
        "ESCALATE"
    }

    def __init__(self):
        self.errors = []
        self.warnings = []

    def parse(self, raw_output: str, persona_name: str = "unknown") -> Dict:
        """
        Parse structured persona output.

        Returns:
            Dict with parsed fields, always includes:
                - verdict: str
                - confidence: int
                - reasoning: str
                - info_needed: List[str]
                - escalate_to: Optional[Dict]
                - agrees_with: List[str]
                - disagrees_with: List[Dict]
                - changed_position: Optional[Dict]
                - blockers: List[str]
                - recruits: Optional[Dict]
                - parse_success: bool
                - parse_errors: List[str]
                - parse_warnings: List[str]
        """
        self.errors = []
        self.warnings = []

        result = {
            "persona_name": persona_name,
            "verdict": None,
            "confidence": 0,
            "conviction": 50,  # Default to neutral conviction
            "reasoning": "",
            "info_needed": [],
            "escalate_to": None,
            "agrees_with": [],
            "disagrees_with": [],
            "changed_position": None,
            "blockers": [],
            "recruits": None,
            "parse_success": False,
            "parse_errors": [],
            "parse_warnings": []
        }

        # Extract required fields
        result["verdict"] = self._extract_verdict(raw_output)
        result["confidence"] = self._extract_confidence(raw_output)
        result["conviction"] = self._extract_conviction(raw_output)
        result["reasoning"] = self._extract_reasoning(raw_output)

        # Extract optional fields
        result["info_needed"] = self._extract_list_section(raw_output, "INFO_NEEDED")
        result["escalate_to"] = self._extract_escalate_to(raw_output)
        result["agrees_with"] = self._extract_agrees_with(raw_output)
        result["disagrees_with"] = self._extract_disagrees_with(raw_output)
        result["changed_position"] = self._extract_changed_position(raw_output)
        result["blockers"] = self._extract_list_section(raw_output, "BLOCKERS")
        result["recruits"] = self._extract_recruits(raw_output)

        # Check if parse was successful
        result["parse_success"] = (
            result["verdict"] is not None and
            result["reasoning"] and
            len(self.errors) == 0
        )

        result["parse_errors"] = self.errors
        result["parse_warnings"] = self.warnings

        return result

    def _extract_verdict(self, text: str) -> Optional[str]:
        """Extract VERDICT field"""
        match = re.search(r'^VERDICT:\s*(\w+)', text, re.MULTILINE | re.IGNORECASE)

        if not match:
            self.errors.append("Missing VERDICT field")
            return None

        verdict = match.group(1).upper()

        if verdict not in self.VALID_VERDICTS:
            self.errors.append(
                f"Invalid verdict '{verdict}'. "
                f"Must be one of: {', '.join(self.VALID_VERDICTS)}"
            )
            return None

        return verdict

    def _extract_confidence(self, text: str) -> int:
        """Extract CONFIDENCE field"""
        match = re.search(r'^CONFIDENCE:\s*(\d+)', text, re.MULTILINE | re.IGNORECASE)

        if not match:
            self.warnings.append("Missing CONFIDENCE field, defaulting to 0")
            return 0

        confidence = int(match.group(1))

        if confidence < 0 or confidence > 100:
            self.warnings.append(
                f"Confidence {confidence} out of range [0-100], clamping"
            )
            confidence = max(0, min(100, confidence))

        return confidence

    def _extract_conviction(self, text: str) -> int:
        """Extract CONVICTION field"""
        match = re.search(r'^CONVICTION:\s*(\d+)', text, re.MULTILINE | re.IGNORECASE)

        if not match:
            self.warnings.append("Missing CONVICTION field, defaulting to 50 (neutral)")
            return 50  # Neutral conviction

        conviction = int(match.group(1))

        if conviction < 0 or conviction > 100:
            self.warnings.append(
                f"Conviction {conviction} out of range [0-100], clamping"
            )
            conviction = max(0, min(100, conviction))

        return conviction

    def _extract_reasoning(self, text: str) -> str:
        """Extract REASONING field (can be multi-line)"""
        # Match from REASONING: until next section header or end
        match = re.search(
            r'^REASONING:\s*(.+?)(?=^\s*[A-Z_]+:|$)',
            text,
            re.MULTILINE | re.DOTALL | re.IGNORECASE
        )

        if not match:
            self.errors.append("Missing REASONING field")
            return ""

        reasoning = match.group(1).strip()

        if not reasoning:
            self.errors.append("REASONING field is empty")

        return reasoning

    def _extract_list_section(self, text: str, section_name: str) -> List[str]:
        """Extract a multi-line list section (e.g., INFO_NEEDED, BLOCKERS)"""
        # Match section header followed by lines starting with - or bullet
        pattern = (
            rf'^{section_name}:\s*\n'
            r'((?:^\s*[-•*]\s*.+\n?)+)'
        )

        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)

        if not match:
            return []

        list_text = match.group(1)

        # Extract individual items
        items = re.findall(r'^\s*[-•*]\s*(.+)', list_text, re.MULTILINE)

        # Clean up items
        items = [item.strip() for item in items if item.strip()]

        return items

    def _extract_escalate_to(self, text: str) -> Optional[Dict]:
        """Extract ESCALATE_TO field"""
        match = re.search(
            r'^ESCALATE_TO:\s*(\w+)\s*-\s*(.+)',
            text,
            re.MULTILINE | re.IGNORECASE
        )

        if not match:
            return None

        return {
            "persona": match.group(1).strip(),
            "reason": match.group(2).strip()
        }

    def _extract_agrees_with(self, text: str) -> List[str]:
        """Extract AGREES_WITH field"""
        match = re.search(
            r'^AGREES_WITH:\s*(.+?)(?:\s*-|$)',
            text,
            re.MULTILINE | re.IGNORECASE
        )

        if not match:
            return []

        # Parse comma-separated list
        personas_str = match.group(1).strip()
        personas = [p.strip() for p in personas_str.split(',')]

        return [p for p in personas if p]

    def _extract_disagrees_with(self, text: str) -> List[Dict]:
        """Extract DISAGREES_WITH field(s)"""
        matches = re.finditer(
            r'^DISAGREES_WITH:\s*(\w+)\s*-\s*(.+)',
            text,
            re.MULTILINE | re.IGNORECASE
        )

        disagreements = []

        for match in matches:
            disagreements.append({
                "persona": match.group(1).strip(),
                "reason": match.group(2).strip()
            })

        return disagreements

    def _extract_changed_position(self, text: str) -> Optional[Dict]:
        """Extract CHANGED_POSITION field"""
        match = re.search(
            r'^CHANGED_POSITION:\s*(\w+)\s*→\s*(\w+)\s*(?:\n\s*-\s*Reason:\s*(.+))?',
            text,
            re.MULTILINE | re.IGNORECASE
        )

        if not match:
            return None

        return {
            "from": match.group(1).strip(),
            "to": match.group(2).strip(),
            "reason": match.group(3).strip() if match.group(3) else ""
        }

    def _extract_recruits(self, text: str) -> Optional[Dict]:
        """Extract RECRUITS field"""
        match = re.search(
            r'^RECRUITS:\s*(\w+)\s*-\s*(.+)',
            text,
            re.MULTILINE | re.IGNORECASE
        )

        if not match:
            return None

        return {
            "persona": match.group(1).strip(),
            "reason": match.group(2).strip()
        }


# Convenience function
def parse_persona_output(raw_output: str, persona_name: str = "unknown") -> Dict:
    """Parse persona output (convenience wrapper)"""
    parser = PersonaOutputParser()
    return parser.parse(raw_output, persona_name)


