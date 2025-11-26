#!/usr/bin/env python3
"""
Council Deliberation Engine
============================

Multi-round deliberative council with convergence detection, information
gathering, and user interaction.

Handles:
- Convergence detection (agreement threshold)
- Information gathering (codebase search, memory, user questions)
- User interaction (pause/resume for clarifications)
- Dynamic persona recruitment
- Multi-round deliberation loop
"""
import re
import json
import subprocess
from typing import Dict, List, Tuple
from collections import Counter
from pathlib import Path

# Import parser


class ConvergenceDetector:
    """Detects when council has reached sufficient agreement"""

    def __init__(self, threshold: float = 0.7):
        """
        Args:
            threshold: Fraction of personas that must agree (0.0-1.0)
        """
        self.threshold = threshold

    def check_convergence(self, round_outputs: List[Dict]) -> Dict:
        """
        Check if personas have converged on a decision using conviction-weighted voting.

        Returns:
            Dict with:
                - converged: bool
                - agreement_ratio: float
                - dominant_verdict: str
                - weighted_scores: dict (verdict -> weighted score)
                - has_new_requests: bool
                - has_escalations: bool
                - has_recruitments: bool
                - has_low_conviction_stalemate: bool
        """
        verdicts = [p["verdict"] for p in round_outputs if p["verdict"]]

        if not verdicts:
            return {
                "converged": False,
                "agreement_ratio": 0.0,
                "dominant_verdict": None,
                "reason": "No valid verdicts"
            }

        # Calculate conviction-weighted scores
        weighted_scores = {}
        total_weight = 0.0

        for p in round_outputs:
            verdict = p.get("verdict")
            if not verdict:
                continue

            confidence = p.get("confidence", 0) / 100.0  # Normalize to 0-1
            conviction = p.get("conviction", 50) / 100.0  # Normalize to 0-1

            # Weight = confidence * conviction
            # High confidence + high conviction = maximum influence
            # Low conviction reduces influence even with high confidence
            weight = confidence * conviction

            if verdict not in weighted_scores:
                weighted_scores[verdict] = 0.0

            weighted_scores[verdict] += weight
            total_weight += weight

        if total_weight == 0:
            # Fallback to simple majority if all personas have 0 weight
            verdict_counts = Counter(verdicts)
            most_common_verdict, count = verdict_counts.most_common(1)[0]
            agreement_ratio = count / len(verdicts)
        else:
            # Find dominant verdict by weighted score
            most_common_verdict = max(weighted_scores.keys(), key=lambda v: weighted_scores[v])
            agreement_ratio = weighted_scores[most_common_verdict] / total_weight

        # Detect low-conviction stalemate (bikeshedding)
        avg_conviction = sum(p.get("conviction", 50) for p in round_outputs) / len(round_outputs)
        has_low_conviction_stalemate = (
            agreement_ratio < 0.60 and  # Low agreement
            avg_conviction < 60  # Low average conviction
        )

        # Check for new information requests
        has_new_requests = any(
            len(p.get("info_needed", [])) > 0 for p in round_outputs
        )

        # Check for escalations
        has_escalations = any(
            p.get("escalate_to") is not None for p in round_outputs
        )

        # Check for recruitment requests
        has_recruitments = any(
            p.get("recruits") is not None for p in round_outputs
        )

        # Convergence criteria:
        # 1. Agreement threshold met (via weighted voting)
        # 2. No new information requests
        # 3. No new escalations
        # 4. No new recruitment requests
        # 5. NOT a low-conviction stalemate (bikeshedding)
        converged = (
            agreement_ratio >= self.threshold and
            not has_new_requests and
            not has_escalations and
            not has_recruitments and
            not has_low_conviction_stalemate
        )

        return {
            "converged": converged,
            "agreement_ratio": agreement_ratio,
            "dominant_verdict": most_common_verdict,
            "weighted_scores": weighted_scores,
            "has_new_requests": has_new_requests,
            "has_escalations": has_escalations,
            "has_recruitments": has_recruitments,
            "has_low_conviction_stalemate": has_low_conviction_stalemate,
            "avg_conviction": avg_conviction,
            "reason": self._get_convergence_reason(
                converged, agreement_ratio, has_new_requests,
                has_escalations, has_recruitments, has_low_conviction_stalemate
            )
        }

    def _get_convergence_reason(
        self, converged, ratio, requests, escalations, recruitments, low_conviction_stalemate=False
    ) -> str:
        """Get human-readable convergence status"""
        if converged:
            return f"Converged: {ratio*100:.0f}% weighted agreement, no pending requests"

        reasons = []
        if ratio < self.threshold:
            reasons.append(f"Weighted agreement {ratio*100:.0f}% < {self.threshold*100:.0f}%")
        if requests:
            reasons.append("New information requests pending")
        if escalations:
            reasons.append("Escalations pending")
        if recruitments:
            reasons.append("Recruitment requests pending")
        if low_conviction_stalemate:
            reasons.append("Low-conviction bikeshedding detected")

        return "Not converged: " + ", ".join(reasons)


class InformationGatherer:
    """Gathers requested information from codebase/memory/user"""

    def __init__(self, project_root: Path, file_patterns: List[str] = None):
        self.project_root = project_root
        self.file_patterns = file_patterns or ["*.py", "*.js", "*.ts", "*.tsx", "*.go", "*.rs", "*.md"]

    def gather_all_requests(
        self, round_outputs: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Gather all information requests from personas.

        Returns:
            (gathered_info, missing_info)
        """
        all_requests = []

        # Collect all INFO_NEEDED items
        for persona_output in round_outputs:
            persona_name = persona_output["persona_name"]
            for item in persona_output.get("info_needed", []):
                all_requests.append({
                    "id": f"{persona_name}_{len(all_requests)}",
                    "requested_by": persona_name,
                    "description": item,
                    "priority": self._extract_priority(item),
                    "type": self._classify_request(item)
                })

        # Try to gather each request
        gathered = []
        missing = []

        for req in all_requests:
            result = self._attempt_gather(req)

            if result["success"]:
                gathered.append({
                    "request": req,
                    "data": result["data"],
                    "source": result["source"]
                })
            else:
                missing.append(req)

        return gathered, missing

    def _extract_priority(self, item: str) -> str:
        """Extract priority from request (looks for ⚠️ CRITICAL:)"""
        if "⚠️ CRITICAL" in item or "CRITICAL:" in item:
            return "critical"
        return "normal"

    def _classify_request(self, item: str) -> str:
        """Classify request type for routing"""
        item_lower = item.lower()

        if any(kw in item_lower for kw in ["team", "members", "people", "who"]):
            return "user_question"

        if any(kw in item_lower for kw in ["current", "metrics", "volume", "latency", "p95"]):
            return "metrics"

        if any(kw in item_lower for kw in ["file", "code", "implementation", "uses"]):
            return "codebase_search"

        if any(kw in item_lower for kw in ["budget", "cost", "timeline", "when"]):
            return "user_question"

        # Default
        return "codebase_search"

    def _attempt_gather(self, request: Dict) -> Dict:
        """Attempt to gather information for a request"""
        req_type = request["type"]

        if req_type == "codebase_search":
            return self._search_codebase(request)
        elif req_type == "metrics":
            return self._search_metrics(request)
        elif req_type == "user_question":
            # Cannot auto-gather, needs user
            return {"success": False, "reason": "Requires user input"}
        else:
            return {"success": False, "reason": f"Unknown request type: {req_type}"}

    def _search_codebase(self, request: Dict) -> Dict:
        """Search codebase for relevant info"""
        description = request["description"]

        # Extract potential search terms
        # Look for quoted terms or capitalized words
        terms = re.findall(r'"([^"]+)"', description)
        if not terms:
            terms = re.findall(r'\b[A-Z][a-zA-Z]+\b', description)

        if not terms:
            return {"success": False, "reason": "Could not extract search terms"}

        # Try to search for terms using ripgrep (rg)
        for term in terms[:3]:  # Try first 3 terms
            try:
                # Build glob patterns for rg
                glob_args = []
                for pattern in self.file_patterns:
                    glob_args.extend(["--glob", pattern])

                result = subprocess.run(
                    ["rg", "-i", "--max-count", "10"] + glob_args + [term, str(self.project_root)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0 and result.stdout.strip():
                    # Found something
                    lines = result.stdout.strip().split("\n")[:10]  # First 10 matches
                    return {
                        "success": True,
                        "data": "\n".join(lines),
                        "source": f"codebase search for '{term}'"
                    }
            except Exception:
                continue

        return {"success": False, "reason": "No matches found in codebase"}

    def _search_metrics(self, request: Dict) -> Dict:
        """Search for metrics in memory/logs"""
        # Check session state for metrics
        memory_dir = self.project_root / ".claude" / "memory"

        if not memory_dir.exists():
            return {"success": False, "reason": "No memory directory"}

        # Try to find in session digests
        digests_dir = memory_dir / "session_digests"

        if digests_dir.exists():
            for digest_file in digests_dir.glob("*.json"):
                try:
                    with open(digest_file) as f:
                        data = json.load(f)

                    # Check if digest mentions relevant terms
                    summary = data.get("summary", "").lower()
                    if any(term in summary for term in ["metric", "performance", "latency"]):
                        return {
                            "success": True,
                            "data": data.get("summary", "No summary"),
                            "source": f"session {digest_file.stem}"
                        }
                except Exception:
                    continue

        return {"success": False, "reason": "No metrics found in memory"}


class UserInteraction:
    """Handles pausing and asking user for information"""

    @staticmethod
    def ask_for_information(missing_requests: List[Dict]) -> Dict[str, str]:
        """
        Pause consultation and ask user for information.

        Returns:
            Dict mapping request IDs to user responses
        """
        if not missing_requests:
            return {}

        print("\n" + "=" * 70)
        print("⏸️  COUNCIL PAUSED - INFORMATION NEEDED")
        print("=" * 70)
        print("\nThe council requires additional information to proceed:\n")

        user_responses = {}

        for i, req in enumerate(missing_requests, 1):
            priority_marker = "⚠️ CRITICAL" if req["priority"] == "critical" else ""

            print(f"{i}. {priority_marker} {req['description']}")
            print(f"   Requested by: {req['requested_by']}")
            print(f"   Type: {req['type']}")
            print()

            # For non-critical, allow skip
            if req["priority"] != "critical":
                response = input("   Your answer (or 'skip'): ").strip()
                if response.lower() == "skip":
                    continue
            else:
                response = input("   Your answer (REQUIRED): ").strip()
                while not response:
                    print("   ⚠️  This is a critical question, answer required")
                    response = input("   Your answer: ").strip()

            user_responses[req["id"]] = response

        print("\n✅ Thank you. Resuming deliberation...\n")
        return user_responses


def build_round_context(
    proposal: str,
    round_history: List[Dict],
    persona_key: str,
    enriched_context: str = ""
) -> str:
    """
    Build context for persona in round N.

    Includes:
    - Original proposal + enriched context
    - Previous round outputs from ALL personas
    - Information gathered since last round
    """
    parts = []

    # Round indicator
    round_num = len(round_history) + 1

    if round_num == 1:
        # First round: just enriched proposal
        return enriched_context or proposal

    # Subsequent rounds: show deliberation history
    parts.append("ORIGINAL CONTEXT:")
    parts.append(enriched_context or proposal)
    parts.append("")

    parts.append("=" * 70)
    parts.append("DELIBERATION HISTORY (Previous Rounds)")
    parts.append("=" * 70)
    parts.append("")

    # Show each previous round
    for round_data in round_history:
        r_num = round_data["round"]
        parts.append(f"=== ROUND {r_num} ===\n")

        # Show other personas' outputs
        for other_persona, output in round_data["outputs"].items():
            if other_persona == persona_key:
                continue  # Don't show persona its own previous output

            parts.append(f"{other_persona.upper()}:")
            parts.append(f"  Verdict: {output['verdict']}")
            parts.append(f"  Confidence: {output['confidence']}%")
            parts.append(f"  Reasoning: {output['reasoning'][:200]}...")
            parts.append("")

        # Show info gathered
        if round_data.get("info_gathered"):
            parts.append("INFORMATION GATHERED:")
            for info in round_data["info_gathered"]:
                req_desc = info["request"]["description"]
                data = info["data"]
                source = info.get("source", "unknown")

                parts.append(f"  Q: {req_desc}")
                parts.append(f"  A: {data[:150]}... (source: {source})")
                parts.append("")

    parts.append("=" * 70)
    parts.append(f"YOUR TURN - ROUND {round_num}")
    parts.append("=" * 70)
    parts.append("")
    parts.append("Consider all perspectives above. You may:")
    parts.append("- Maintain your position (if reasoning still holds)")
    parts.append("- Change your position (use CHANGED_POSITION field)")
    parts.append("- Agree/disagree with specific personas (use AGREES_WITH/DISAGREES_WITH)")
    parts.append("- Request additional information (use INFO_NEEDED)")
    parts.append("- Recruit new personas if needed (use RECRUITS)")
    parts.append("")

    return "\n".join(parts)


