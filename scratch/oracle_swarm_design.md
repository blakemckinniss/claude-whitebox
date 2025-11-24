# Oracle Swarm Architecture: Massive Parallel Reasoning

## The Vision

**Problem:** LLMs are great at reasoning but limited by sequential thinking.

**Solution:** Spawn 10, 20, 50 external oracles in parallel for massive cognitive throughput.

## Use Cases

### 1. Multi-Angle Analysis (Current council.py)
```bash
# Instead of 5 personas sequentially (15 seconds)
council.py "Migrate to microservices"

# Run 10 perspectives in parallel (3 seconds)
oracle_swarm.py --personas judge,critic,skeptic,innovator,advocate,legal,security,ux,performance,data \
  "Migrate to microservices"
```

**Result:** 10 expert opinions in 3 seconds instead of 30 seconds

### 2. Hypothesis Generation
```bash
# Generate 20 different architectural approaches
oracle_swarm.py --task generate --count 20 \
  "Design a scalable authentication system"

# Returns 20 different approaches:
# 1. JWT with Redis
# 2. Session-based with PostgreSQL
# 3. OAuth2 with third-party
# ... (17 more)
```

**Result:** Explore design space exhaustively in parallel

### 3. Code Review at Scale
```bash
# Review 50 files in parallel
oracle_swarm.py --task review --files "src/**/*.py" \
  "Find security vulnerabilities"

# Each oracle gets 1 file, all run in parallel
```

**Result:** Full codebase security audit in 5 seconds

### 4. Test Case Generation
```bash
# Generate 100 test cases in parallel
oracle_swarm.py --task test-cases --count 100 \
  "scripts/ops/verify.py"

# Returns:
# - 20 happy path tests
# - 30 edge case tests
# - 30 error handling tests
# - 20 integration tests
```

**Result:** Comprehensive test suite from multiple reasoning paths

### 5. Documentation Generation
```bash
# 10 oracles each document 10 functions (100 total)
oracle_swarm.py --task document --parallel 10 \
  "scripts/lib/*.py"
```

**Result:** Full API docs in seconds

### 6. Refactoring Strategies
```bash
# Generate 15 different refactoring approaches
oracle_swarm.py --task refactor --count 15 \
  "legacy_monolith.py"

# Each oracle proposes different strategy:
# 1. Extract service layer
# 2. Apply strategy pattern
# 3. Introduce factory
# ... (12 more)
```

**Result:** Explore refactoring space, pick best approach

## Architecture Design

### Core Components

```
oracle_swarm.py (orchestrator)
├── Task Definition (what to do)
├── Oracle Pool (N parallel workers)
│   ├── Worker 1: OpenRouter API call
│   ├── Worker 2: OpenRouter API call
│   ├── ...
│   └── Worker N: OpenRouter API call
├── Result Aggregation (synthesis)
└── Output Formatting
```

### Implementation Sketch

```python
#!/usr/bin/env python3
"""
Oracle Swarm: Massive Parallel External Reasoning

Usage:
  # Multi-perspective analysis (10 oracles)
  oracle_swarm.py --personas judge,critic,skeptic,... "proposal"

  # Hypothesis generation (20 oracles)
  oracle_swarm.py --generate 20 "Design auth system"

  # Code review (1 oracle per file)
  oracle_swarm.py --review "src/**/*.py"

  # Test generation (100 oracles)
  oracle_swarm.py --test-cases 100 "module.py"
"""

from concurrent.futures import ThreadPoolExecutor
from scripts.lib.parallel import run_parallel

TASKS = {
    "analyze": {
        "prompt": "Analyze this proposal from the {perspective} perspective: {input}",
        "default_count": 10,
    },
    "generate": {
        "prompt": "Generate a unique approach to: {input}. Be creative and different from common solutions.",
        "default_count": 20,
    },
    "review": {
        "prompt": "Review this code for {focus}: {input}",
        "default_count": "auto",  # 1 per file
    },
    "test-cases": {
        "prompt": "Generate a unique test case for: {input}. Focus on {category}.",
        "default_count": 100,
    },
}

def oracle_call(prompt, model="google/gemini-2.0-flash-thinking-exp"):
    """Single oracle invocation"""
    # Call OpenRouter API
    response = call_openrouter(prompt, model)
    return response

def oracle_swarm(task, input_data, count=None, personas=None):
    """Spawn N oracles in parallel"""

    if task == "analyze":
        # Multi-perspective analysis
        personas = personas or ["judge", "critic", "skeptic", "innovator", "advocate"]
        prompts = [
            TASKS["analyze"]["prompt"].format(perspective=p, input=input_data)
            for p in personas
        ]

    elif task == "generate":
        # Hypothesis generation
        count = count or TASKS["generate"]["default_count"]
        prompts = [
            TASKS["generate"]["prompt"].format(input=input_data)
            for _ in range(count)
        ]

    elif task == "review":
        # Code review (1 oracle per file)
        files = glob.glob(input_data)
        prompts = [
            TASKS["review"]["prompt"].format(focus="security", input=read_file(f))
            for f in files
        ]

    elif task == "test-cases":
        # Test case generation
        count = count or TASKS["test-cases"]["default_count"]
        categories = ["happy-path", "edge-case", "error-handling", "integration"]
        prompts = [
            TASKS["test-cases"]["prompt"].format(
                input=input_data,
                category=categories[i % len(categories)]
            )
            for i in range(count)
        ]

    # Execute all prompts in parallel (max 50 workers)
    results = run_parallel(
        oracle_call,
        prompts,
        max_workers=min(50, len(prompts)),
        desc=f"Oracle swarm ({task})"
    )

    return results

def synthesize_results(results, task):
    """Aggregate oracle outputs into actionable summary"""

    if task == "analyze":
        # Group by verdict (PROCEED/STOP/etc)
        verdicts = extract_verdicts(results)
        return format_multi_perspective_summary(verdicts)

    elif task == "generate":
        # Deduplicate and rank by novelty
        unique = deduplicate_approaches(results)
        return format_ranked_approaches(unique)

    elif task == "review":
        # Group findings by severity
        findings = extract_findings(results)
        return format_security_report(findings)

    elif task == "test-cases":
        # Deduplicate and categorize
        tests = deduplicate_tests(results)
        return format_test_suite(tests)
```

## Advanced Patterns

### 1. Recursive Swarms (Swarm spawns swarms)

```python
# Level 1: High-level design (5 oracles)
architectures = oracle_swarm.py --generate 5 "Design auth system"

# Level 2: Detail each architecture (5 oracles per architecture = 25 total)
for arch in architectures:
    details = oracle_swarm.py --generate 5 f"Detail implementation: {arch}"
```

**Result:** 5 architectures × 5 implementation details = 25 complete designs

### 2. Consensus Detection

```python
# Run 20 oracles on same question
results = oracle_swarm.py --generate 20 "Best database for analytics"

# Find consensus
consensus = find_consensus(results)
# Output: "18/20 recommend PostgreSQL with TimescaleDB"
```

**Result:** Statistical confidence from parallel reasoning

### 3. Adversarial Pairs

```python
# Spawn 10 architect oracles + 10 critic oracles
architects = oracle_swarm.py --persona architect --count 10 "Design X"
critics = oracle_swarm.py --persona critic --input architectures

# Each critic attacks one architecture
```

**Result:** Designs pre-validated by adversarial review

### 4. Iterative Refinement

```python
# Round 1: Generate 20 ideas
ideas = oracle_swarm.py --generate 20 "Solve problem X"

# Round 2: Refine top 5 (5 oracles per idea = 25 total)
top_5 = rank_ideas(ideas)[:5]
refined = [oracle_swarm.py --refine idea for idea in top_5]

# Round 3: Critique refined ideas
final = [oracle_swarm.py --critique idea for idea in refined]
```

**Result:** Multi-stage evolutionary design process

## Performance Characteristics

### Throughput

**Single oracle:** 1 query per 3 seconds = 20 queries/minute

**Oracle swarm (50 workers):** 50 queries per 3 seconds = 1000 queries/minute

**50x throughput increase**

### Cost

**OpenRouter pricing:** ~$0.001 per query (Gemini Flash)

**100 oracles:** $0.10 per swarm invocation

**1000 oracles:** $1.00 per massive batch

**Cost is negligible compared to human time savings**

## Integration with Existing System

### Option 1: Extend council.py

```python
# Add swarm mode to council.py
council.py --swarm --count 20 "proposal"
```

**Pros:** Single tool for all oracle usage
**Cons:** Mixes multi-round (council) with parallel-batch (swarm)

### Option 2: Separate oracle_swarm.py

```python
# Keep council.py for multi-round deliberation
# Add oracle_swarm.py for parallel batch processing
```

**Pros:** Clear separation of concerns
**Cons:** Two tools instead of one

### Option 3: Unified oracle.py with modes

```python
# Single oracle call
oracle.py --persona judge "proposal"

# Multi-round deliberation
oracle.py --council --personas judge,critic,skeptic "proposal"

# Parallel swarm
oracle.py --swarm --count 20 --task generate "proposal"
```

**Pros:** Single tool, multiple modes
**Cons:** Complex interface

## Recommendation: Three-Tier Architecture

```
Layer 1: oracle.py (single-shot API call)
├── Simplest: one prompt → one response
└── Use: Quick consultation, slash commands

Layer 2: council.py (multi-round deliberation)
├── Complex: N personas × M rounds with convergence
└── Use: Strategic decisions requiring synthesis

Layer 3: swarm.py (massive parallel batch)
├── Powerful: N oracles in parallel (10-1000+)
└── Use: Hypothesis generation, code review at scale, test generation
```

**Each layer builds on the previous:**
- oracle.py = primitive (1 API call)
- council.py = multi-round coordination (uses oracle.py internally)
- swarm.py = parallel batch (uses oracle.py internally)

## Implementation Priority

### Phase 1: Create oracle.py (replaces judge/critic/skeptic/consult)
- Single-shot API wrapper
- Support personas + custom prompts
- ~150 lines

### Phase 2: Refactor council.py to use oracle.py
- Extract API logic to oracle.py
- Council becomes orchestrator only
- Reduces council.py complexity

### Phase 3: Create swarm.py
- Parallel batch processing
- Task-based modes (analyze, generate, review, test)
- Result aggregation and synthesis
- ~300 lines

## Expected Impact

**Code Reduction:**
- Delete: judge.py (159), critic.py (157), skeptic.py (186), consult.py (127) = 629 lines
- Add: oracle.py (~150), swarm.py (~300) = 450 lines
- **Net: -179 lines while adding swarm capability**

**Capability Increase:**
- Before: Sequential single-oracle calls
- After: Parallel swarm (10-50x throughput)

**Use Cases Unlocked:**
- Hypothesis generation (20+ approaches)
- Code review at scale (50+ files in parallel)
- Test generation (100+ test cases)
- Multi-perspective analysis (10+ perspectives)
- Consensus detection (statistical confidence)

## Next Steps

1. ✅ Create oracle.py (generic single-shot wrapper)
2. ⏳ Test oracle.py with all existing personas
3. ⏳ Update slash commands (/judge, /critic, etc) to use oracle.py
4. ⏳ Delete vestige scripts (judge.py, critic.py, skeptic.py, consult.py)
5. ⏳ Refactor council.py to use oracle.py internally
6. ⏳ Create swarm.py for parallel batch processing
7. ⏳ Add swarm use cases (hypothesis gen, code review, test gen)

**Start with Phase 1 (oracle.py), prove it works, then expand to swarm.**
