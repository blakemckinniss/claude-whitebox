# ADR (Architectural Decision Records)

## Core Philosophy Decisions

### 2025-11-20: Whitebox-Only Architecture
**Decision:** Do not use MCP (Model Context Protocol) tools. All functionality must be transparent, executable code.
**Reason:** Transparency and auditability are non-negotiable. If we cannot read the code that performs an action, we do not run it.
**Consequences:** Requires writing more scripts, but provides full control and visibility.

### 2025-11-20: Script-First Development
**Decision:** Use scaffolder (`scripts/scaffold.py`) to generate all new tools with SDK compliance built-in.
**Reason:** Ensures consistency (logging, dry-run, error handling) across all scripts.
**Consequences:** Slightly slower initial development, but eliminates technical debt.

### 2025-11-20: Parallel Execution Standard
**Decision:** Use `scripts/lib/parallel.py` for any operation processing 3+ items.
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
