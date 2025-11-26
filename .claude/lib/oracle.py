#!/usr/bin/env python3
"""
Oracle Library: Shared OpenRouter API Interface

Provides unified OpenRouter API calling logic for all oracle-based scripts.
Used by: oracle.py, council.py, and future swarm.py

Functions:
  - call_openrouter(): Generic OpenRouter API wrapper
  - call_oracle_single(): Single-shot oracle consultation (from oracle.py pattern)
  - call_arbiter(): Arbiter synthesis (from council.py pattern)
"""
import os
import json
import requests
from typing import Dict, List, Optional, Tuple


class OracleAPIError(Exception):
    """Raised when OpenRouter API call fails"""
    pass


def call_openrouter(
    messages: List[Dict[str, str]],
    model: str = "openai/gpt-5.1",
    timeout: int = 120,
    enable_reasoning: bool = True
) -> Dict:
    """
    Generic OpenRouter API wrapper.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: OpenRouter model identifier
        timeout: Request timeout in seconds
        enable_reasoning: Enable reasoning extraction (if model supports it)

    Returns:
        Dict with 'content', 'reasoning', and 'raw_response' keys

    Raises:
        OracleAPIError: If API key missing or request fails
    """
    # Get API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise OracleAPIError("Missing OPENROUTER_API_KEY environment variable")

    # Prepare headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/claude-code/whitebox",
    }

    # Prepare request body
    data = {
        "model": model,
        "messages": messages,
    }

    # Enable reasoning if requested
    if enable_reasoning:
        data["extra_body"] = {"reasoning": {"enabled": True}}

    # Call API
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json()

    except requests.exceptions.Timeout:
        raise OracleAPIError(f"Request timed out after {timeout}s")
    except requests.exceptions.RequestException as e:
        raise OracleAPIError(f"API request failed: {e}")
    except json.JSONDecodeError as e:
        raise OracleAPIError(f"Invalid JSON response: {e}")

    # Extract content and reasoning
    try:
        choice = result["choices"][0]["message"]
        content = choice.get("content", "")
        reasoning = choice.get("reasoning", "") or result.get("reasoning", "")

        return {
            "content": content,
            "reasoning": reasoning,
            "raw_response": result
        }

    except (KeyError, IndexError) as e:
        raise OracleAPIError(f"Unexpected response structure: {e}")


def call_oracle_single(
    query: str,
    persona: Optional[str] = None,
    custom_prompt: Optional[str] = None,
    model: str = "openai/gpt-5.1",
    timeout: int = 120
) -> Tuple[str, str, str]:
    """
    Single-shot oracle consultation (oracle.py pattern).

    Args:
        query: User's question/proposal
        persona: Persona name (if using PERSONAS from caller)
        custom_prompt: Custom system prompt (if not using persona)
        model: OpenRouter model to use
        timeout: Request timeout in seconds

    Returns:
        tuple: (content, reasoning, title)

    Raises:
        OracleAPIError: If API call fails

    Note: This function does NOT define personas. Caller must pass
    either custom_prompt (system prompt string) or persona (name only).
    The caller is responsible for mapping persona -> system prompt.
    """
    # Build messages
    messages = []

    if custom_prompt:
        messages.append({"role": "system", "content": custom_prompt})
        title = "🔮 ORACLE RESPONSE"
    elif persona:
        # Caller must handle persona lookup, we just mark it
        # This function expects custom_prompt for persona system prompts
        raise ValueError("Use custom_prompt for persona system prompts, not persona name")
    else:
        # No system prompt (consult mode)
        title = "🧠 ORACLE CONSULTATION"

    messages.append({"role": "user", "content": query})

    # Call OpenRouter
    result = call_openrouter(messages, model=model, timeout=timeout)

    return result["content"], result["reasoning"], title


def call_arbiter(
    proposal: str,
    deliberation_context: str,
    model: str = "openai/gpt-5.1",
    timeout: int = 60
) -> Dict:
    """
    Arbiter synthesis (council.py pattern).

    Args:
        proposal: Original proposal being deliberated
        deliberation_context: Full deliberation history as formatted string
        model: OpenRouter model to use
        timeout: Request timeout in seconds

    Returns:
        Dict with 'content', 'reasoning', 'parsed_verdict' keys

    Raises:
        OracleAPIError: If API call fails

    Note: This function handles arbiter-specific prompt building.
    Caller should prepare deliberation_context as a formatted string.
    """
    # Build arbiter prompt
    arbiter_prompt = f"""You are the Arbiter in a multi-round deliberative council.

{deliberation_context}

ARBITER TASK:
1. Review all rounds of deliberation
2. Synthesize the discussion into a final verdict using CONVICTION-WEIGHTED voting
3. Explain the reasoning that led to consensus or majority
4. If bikeshedding was detected, note which concerns were substantive vs trivial

CONVICTION-WEIGHTED VOTING:
- High confidence + high conviction votes carry maximum weight
- Low conviction reduces voting power even with high confidence
- The dominant verdict is determined by weighted scores, not simple majority

Return your synthesis in this format:
VERDICT: [PROCEED | CONDITIONAL_GO | STOP | ESCALATE]
CONFIDENCE: [0-100]
REASONING: [Your synthesis of the multi-round deliberation, noting conviction patterns]
"""

    messages = [{"role": "user", "content": arbiter_prompt}]

    # Call OpenRouter
    result = call_openrouter(messages, model=model, timeout=timeout)

    # Parse arbiter output (basic parsing, caller can enhance)
    content = result["content"]
    parsed = {
        "verdict": None,
        "confidence": None,
        "reasoning": ""
    }

    # Extract VERDICT
    import re
    verdict_match = re.search(r'VERDICT:\s*(PROCEED|CONDITIONAL_GO|STOP|ESCALATE|ABSTAIN)', content, re.IGNORECASE)
    if verdict_match:
        parsed["verdict"] = verdict_match.group(1).upper()

    # Extract CONFIDENCE
    confidence_match = re.search(r'CONFIDENCE:\s*(\d+)', content)
    if confidence_match:
        parsed["confidence"] = int(confidence_match.group(1))

    # Extract REASONING (everything after REASONING:)
    reasoning_match = re.search(r'REASONING:\s*(.+)', content, re.DOTALL)
    if reasoning_match:
        parsed["reasoning"] = reasoning_match.group(1).strip()

    return {
        "content": content,
        "reasoning": result["reasoning"],
        "parsed_verdict": parsed
    }


# Convenience functions for common use cases
def oracle_judge(query: str, persona_prompt: str, model: str = "openai/gpt-5.1") -> str:
    """Quick judge consultation"""
    content, _, _ = call_oracle_single(query, custom_prompt=persona_prompt, model=model)
    return content


def oracle_critic(query: str, persona_prompt: str, model: str = "openai/gpt-5.1") -> str:
    """Quick critic consultation"""
    content, _, _ = call_oracle_single(query, custom_prompt=persona_prompt, model=model)
    return content


def oracle_skeptic(query: str, persona_prompt: str, model: str = "openai/gpt-5.1") -> str:
    """Quick skeptic consultation"""
    content, _, _ = call_oracle_single(query, custom_prompt=persona_prompt, model=model)
    return content


def oracle_consult(query: str, model: str = "openai/gpt-5.1") -> str:
    """Quick general consultation (no system prompt)"""
    content, _, _ = call_oracle_single(query, model=model)
    return content
