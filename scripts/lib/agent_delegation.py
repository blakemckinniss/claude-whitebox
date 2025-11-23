#!/usr/bin/env python3
"""
Agent Delegation Helper Library

Provides helpers for context offloading and parallel agent management.
Optimizes agent usage for free context bandwidth.

Key functions:
  - parallel_explore(): Spawn multiple Explore agents in parallel
  - summarize_files(): Read files via agents, return summaries
  - batch_analyze(): Parallel analysis of multiple components
"""
from typing import List, Dict, Any
from pathlib import Path


def build_parallel_agent_spec(agents: List[Dict[str, str]]) -> str:
    """
    Build specification for parallel agent invocation.

    Args:
        agents: List of agent specs, each with:
            - subagent_type: Agent type (Explore, Plan, etc.)
            - description: Task description
            - prompt: Full task prompt

    Returns:
        Formatted string showing parallel agent pattern

    Example:
        >>> agents = [
        ...     {"subagent_type": "Explore", "description": "Auth analysis", "prompt": "Analyze auth module"},
        ...     {"subagent_type": "Explore", "description": "API analysis", "prompt": "Analyze API module"},
        ... ]
        >>> spec = build_parallel_agent_spec(agents)
        >>> print(spec)
        PARALLEL AGENT INVOCATION (2 agents):

        <function_calls>
        <invoke name="Task">
          <parameter name="subagent_type">Explore</parameter>
          <parameter name="description">Auth analysis</parameter>
          <parameter name="prompt">Analyze auth module</parameter>
        </invoke>
        <invoke name="Task">
          <parameter name="subagent_type">Explore</parameter>
          <parameter name="description">API analysis</parameter>
          <parameter name="prompt">Analyze API module</parameter>
        </invoke>
        </function_calls>
    """
    if not agents:
        return ""

    spec = f"PARALLEL AGENT INVOCATION ({len(agents)} agents):\n\n"
    spec += "<function_calls>\n"

    for agent in agents:
        spec += "<invoke name=\"Task\">\n"
        spec += f"  <parameter name=\"subagent_type\">{agent['subagent_type']}</parameter>\n"
        spec += f"  <parameter name=\"description\">{agent['description']}</parameter>\n"
        spec += f"  <parameter name=\"prompt\">{agent['prompt']}</parameter>\n"
        spec += "</invoke>\n"

    spec += "</function_calls>\n"

    return spec


def parallel_explore_modules(modules: List[str], focus: str = "architecture") -> str:
    """
    Generate parallel Explore agent spec for multiple modules.

    Args:
        modules: List of module names/paths
        focus: Analysis focus (architecture, security, performance, etc.)

    Returns:
        Parallel agent specification string

    Example:
        >>> spec = parallel_explore_modules(["auth", "api", "database"], focus="security")
    """
    agents = []

    for module in modules:
        agents.append({
            "subagent_type": "Explore",
            "description": f"Analyze {module} module ({focus})",
            "prompt": f"""Analyze the {module} module focusing on {focus}.

Provide:
1. High-level architecture overview
2. Key components and their interactions
3. {focus.capitalize()}-specific observations
4. Potential issues or improvements

Return a concise summary (300-500 words)."""
        })

    return build_parallel_agent_spec(agents)


def summarize_large_files(file_paths: List[str]) -> str:
    """
    Generate parallel agent spec to summarize large files.

    Instead of reading 10×1000 line files (10,000 lines in main context),
    spawn 10 agents to read and summarize (10×50 lines = 500 lines total).

    Args:
        file_paths: List of file paths to summarize

    Returns:
        Parallel agent specification string

    Example:
        >>> files = ["auth.py", "api.py", "database.py"]
        >>> spec = summarize_large_files(files)
    """
    agents = []

    for file_path in file_paths:
        agents.append({
            "subagent_type": "Explore",
            "description": f"Summarize {file_path}",
            "prompt": f"""Read and summarize the file: {file_path}

Provide:
1. Purpose of the file (1-2 sentences)
2. Key classes/functions (list top 5)
3. Dependencies (imports)
4. Notable patterns or issues

Keep summary under 200 words. Focus on WHAT it does, not HOW."""
        })

    return build_parallel_agent_spec(agents)


def batch_code_review(file_pattern: str, focus: str = "security") -> str:
    """
    Generate parallel agent spec for batch code review.

    Args:
        file_pattern: Glob pattern for files to review
        focus: Review focus (security, performance, style, etc.)

    Returns:
        Parallel agent specification string

    Example:
        >>> spec = batch_code_review("src/**/*.py", focus="security")
    """
    return f"""CONTEXT OFFLOADING PATTERN:

Instead of reading all files matching {file_pattern} in main context,
use parallel Explore agents to review and summarize.

Example workflow:
1. Use Glob to find matching files
2. Batch files into groups of 10
3. Spawn 10 parallel agents (one per batch)
4. Each agent reviews 10 files, returns summary
5. Main context receives only summaries (90% savings)

Focus: {focus}
Pattern: {file_pattern}

This pattern is 10× faster and uses 90% less main context.
"""


def agent_swarm_pattern(task_type: str, count: int) -> str:
    """
    Generate pattern for agent swarm operations.

    Args:
        task_type: Type of task (test generation, hypothesis, review, etc.)
        count: Number of agents to spawn

    Returns:
        Pattern description

    Example:
        >>> pattern = agent_swarm_pattern("test generation", 10)
    """
    return f"""AGENT SWARM PATTERN ({count} agents):

Task: {task_type}
Agents: {count} parallel Explore/Plan agents
Strategy: Each agent generates unique output, aggregated at end

Benefits:
- {count}× parallelism (vs sequential)
- Free context (each agent separate window)
- Diverse outputs (different approaches)

Usage:
- Small swarm (3-5): Multi-perspective analysis
- Medium swarm (10-20): Test/hypothesis generation
- Large swarm (50-100): Comprehensive audit/review

For {task_type}, recommend: {min(count, 50)} agents

See: swarm.py for oracle-based swarms (faster for 100+ agents)
"""


# Usage examples
if __name__ == "__main__":
    print("="*70)
    print("AGENT DELEGATION PATTERNS")
    print("="*70)

    print("\n1. Parallel Module Analysis")
    print("-"*70)
    print(parallel_explore_modules(["auth", "api", "database"], focus="security"))

    print("\n2. Large File Summarization")
    print("-"*70)
    print(summarize_large_files(["long_file1.py", "long_file2.py", "long_file3.py"]))

    print("\n3. Batch Code Review")
    print("-"*70)
    print(batch_code_review("src/**/*.py", focus="performance"))

    print("\n4. Agent Swarm")
    print("-"*70)
    print(agent_swarm_pattern("test case generation", 20))
