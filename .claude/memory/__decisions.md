# ADR (Architectural Decision Records)

## Core Philosophy Decisions

### 2025-11-20: Whitebox-Only Architecture
**Decision:** Do not use MCP (Model Context Protocol) tools. All functionality must be transparent, executable code.
**Reason:** Transparency and auditability are non-negotiable. If we cannot read the code that performs an action, we do not run it.
**Consequences:** Requires writing more scripts, but provides full control and visibility.

### 2025-11-20: Script-First Development
**Decision:** Use scaffolder (`.claude/ops/scaffold.py`) to generate all new tools with SDK compliance built-in.
**Reason:** Ensures consistency (logging, dry-run, error handling) across all scripts.
**Consequences:** Slightly slower initial development, but eliminates technical debt.

### 2025-11-20: Parallel Execution Standard
**Decision:** Use `.claude/lib/parallel.py` for any operation processing 3+ items.
**Reason:** Significant performance improvement for I/O-bound operations, with progress visibility.
**Consequences:** Requires understanding of concurrent execution patterns.

## Technology Choices

### 2025-11-20: Python as Primary Language
**Decision:** Use Python for all SDK scripts.
**Reason:** Available in environment, excellent library ecosystem, readable.
**Consequences:** Path resolution complexity across different script locations (solved).

### 2025-11-20: Tavily for Web Search
**Decision:** Use Tavily API for real-time research instead of embedding/vector search.
**Reason:** Provides current documentation with source URLs for verification.
**Consequences:** Requires API key, subject to rate limits.

### 2025-11-20: OpenRouter for External Reasoning
**Decision:** Use OpenRouter to access reasoning models (Gemini, DeepSeek) instead of direct APIs.
**Reason:** Single API for multiple models, transparent pricing.
**Consequences:** Dependency on third-party service, but code remains inspectable.

### 2025-11-20: tqdm for Progress Bars
**Decision:** Use tqdm for batch operation progress tracking (with graceful fallback).
**Reason:** Industry standard, excellent UX for long-running operations.
**Consequences:** Optional dependency, but significantly improves user experience.

## Rejected Alternatives

### MCP Servers (Rejected)
**Why:** Blackbox abstractions that hide implementation details.
**Instead:** Write transparent Python scripts for all external interactions.

### Vector Databases for Memory (Rejected)
**Why:** Opaque storage, difficult to audit, requires external service.
**Instead:** Use markdown files in `.claude/memory/` for persistent storage.

---
*Architectural decisions are binding until explicitly revised with new ADR entry.*

### 2025-11-20 17:04
The Probe Protocol: Runtime Introspection. Decision: Force runtime API verification before coding. Reason: LLMs hallucinate library methods based on probability, not truth. Solution: Dynamic module inspection via probe.py reveals actual runtime state. Consequences: Eliminates guesswork, but requires discipline to run probe before coding. Philosophy: Completes the Knowledge Pyramid (Oracle=concept, Researcher=docs, Probe=syntax).

### 2025-11-20 17:10
The Upkeep Protocol: Automated Maintenance. Decision: Force continuous synchronization between code and documentation via automation. Reason: LLMs cannot be trusted to remember to update indexes and requirements - drift (bitrot) is inevitable without enforcement. Solution: upkeep.py scans project, pre_commit.py blocks stale commits, SessionEnd hook runs maintenance automatically. Consequences: Requires discipline but eliminates technical debt accumulation. Philosophy: Whitebox automation - all maintenance is transparent, auditable Python code.

### 2025-11-20 17:14
The X-Ray Protocol: AST-Based Structural Search. Decision: Build semantic code search using Python's ast module instead of text-based grep. Reason: grep is blind to code structure - cannot distinguish definitions from usages, see inheritance, or understand decorators. Solution: xray.py parses AST and provides semantic queries (find class definitions, track imports, find decorators, see inheritance). Consequences: Only works for Python code, but provides precise structural understanding. No external dependencies. Philosophy: Whitebox semantic search - transparent stdlib-based analysis.

### 2025-11-20 17:20
The Headless Protocol: Browser Automation SDK. Decision: Wrap Playwright in clean SDK to make browser automation the path of least resistance. Reason: LLMs avoid Playwright due to boilerplate and friction, defaulting to requests+BS4 which fails on dynamic sites. Solution: browser.py provides context managers, smart_dump for LLM-readable content, auto-screenshots on error, safe helpers. Scaffolder supports --template playwright for zero-boilerplate generation. Hook blocks requests+BS4 for UI tasks. Consequences: Requires playwright installation but eliminates friction. Philosophy: Whitebox automation - transparent Python wrapping Playwright sync API.

### 2025-11-20 17:41
Adopted The Cartesian Protocol for meta-cognition. Rationale: LLMs are people-pleasers and rush to execution. We need forced adversarial reasoning to catch XY problems, sunk cost fallacy, and premature optimization. The Thinker decomposes problems sequentially. The Skeptic performs hostile review. Both use OpenRouter for external reasoning. Hook system warns before risky operations.

### 2025-11-20 17:46
Adopted The MacGyver Protocol for improvisation and resilience. Rationale: LLMs give up when tools are missing ('please install X'). MacGyver Protocol enforces Living off the Land (LotL) - use ONLY what's available. inventory.py scans system capabilities. macgyver agent has LotL mindset baked in. Fallback chain: stdlib → binaries → raw I/O → creative workarounds. Never surrender, always find a solution.

### 2025-11-23 21:32
Memory directory split: .claude/memory/ now contains only SDK configuration (lessons, decisions, synapses, configs) in git. Runtime state (session_*_state.json, telemetry.jsonl, enforcement state) is gitignored as it's per-user and grows unbounded. Rationale: SDK config defines system behavior (shareable), runtime state is transient per-user data.
