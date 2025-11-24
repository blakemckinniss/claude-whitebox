# Oracle Scripts Analysis: Consolidation Opportunity

## Current State

### Existing Oracle Scripts (629 lines total)

| Script | Lines | Purpose | System Prompt |
|--------|-------|---------|---------------|
| judge.py | 159 | Value/ROI assessment | Evaluates necessity, prevents over-engineering |
| critic.py | 157 | Red team / attack assumptions | Pessimistic, exposes blind spots |
| skeptic.py | 186 | Risk analysis / failure modes | Technical risks, edge cases |
| consult.py | 127 | General high-reasoning advice | Expert knowledge consultation |

**Commonality:** All 4 scripts follow identical pattern:
1. Parse arguments (proposal/topic/question)
2. Call OpenRouter API with specific system prompt
3. Return formatted output

**Duplication:** ~80% of code is identical (API call logic, error handling, formatting)

## Comparison with council.py

**council.py:** 800+ lines (complex multi-round deliberation engine)
- N+1 architecture (personas + arbiter)
- Multi-round with convergence detection
- Information gathering
- Dynamic recruitment
- Context sharing
- Structured output parsing

**judge/critic/skeptic/consult:** ~150 lines each (simple single-shot API calls)
- Single prompt → single response
- No multi-round
- No convergence
- No context sharing
- Just: prompt engineering + API call

## The Vestige Problem

**These scripts are SINGLE-PERSONA calls to council.py's multi-persona engine.**

Current workflow:
```bash
# Option 1: Single perspective (vestige scripts)
python3 scripts/ops/judge.py "Migrate to Rust"
python3 scripts/ops/critic.py "Migrate to Rust"
python3 scripts/ops/skeptic.py "Migrate to Rust"

# Option 2: Multi-perspective (council)
python3 scripts/ops/council.py "Migrate to Rust" --personas judge,critic,skeptic
```

**Option 2 is strictly better** (parallel execution, synthesis, convergence).

## Proposed Solution: Generic OpenRouter Runner

### Option A: Purge + Consolidate into council.py

**Action:** Delete judge.py, critic.py, skeptic.py, consult.py

**Replacement:**
```bash
# Instead of: python3 scripts/ops/judge.py "proposal"
# Use: python3 scripts/ops/council.py --personas judge --only judge "proposal"

# Instead of: python3 scripts/ops/critic.py "idea"
# Use: python3 scripts/ops/council.py --personas critic --only critic "idea"
```

**Pros:**
- Eliminates 629 lines of duplication
- Single source of truth (council.py)
- Consistent output format
- Already supports single-persona mode

**Cons:**
- More verbose invocation
- Breaking change for existing scripts/hooks

### Option B: Generic runner.py (Your Proposal)

**Create:** `scripts/ops/oracle.py` (or `runner.py`)

**Design:**
```python
#!/usr/bin/env python3
"""
Generic OpenRouter Oracle - Generalized LLM consultation

Usage:
  oracle.py --persona judge "Should we migrate to Rust?"
  oracle.py --persona critic "Rewrite backend in Go"
  oracle.py --persona skeptic "Use blockchain for auth"
  oracle.py --persona consult "How does async/await work?"
  oracle.py --custom-prompt "You are X" "Do Y"

Replaces: judge.py, critic.py, skeptic.py, consult.py
"""

PERSONA_PROMPTS = {
    "judge": "You are The Judge. Evaluate VALUE and ROI...",
    "critic": "You are The Critic. Attack assumptions...",
    "skeptic": "You are The Skeptic. Find failure modes...",
    "consult": "You are an expert consultant...",
}

def main():
    parser.add_argument("--persona", choices=PERSONA_PROMPTS.keys())
    parser.add_argument("--custom-prompt", help="Custom system prompt")
    parser.add_argument("--model", default="google/gemini-2.0-flash-thinking-exp")
    parser.add_argument("query", help="Question/proposal")

    # Call OpenRouter with selected persona/prompt
    response = call_openrouter(
        system_prompt=PERSONA_PROMPTS[args.persona] or args.custom_prompt,
        user_prompt=args.query,
        model=args.model
    )

    print(response)
```

**Pros:**
- Generic (any persona, any prompt)
- Replaces all 4 vestige scripts
- Simpler than council.py for single-shot queries
- Backward compatible via wrapper scripts

**Cons:**
- Still duplicates council.py's single-persona capability
- Adds another abstraction layer

### Option C: Hybrid (Recommended)

**Keep council.py as primary, add convenience aliases**

**Action:**
1. Keep council.py (multi-round, multi-persona)
2. Add `scripts/lib/oracle.py` (shared OpenRouter API logic)
3. Convert judge.py/critic.py/skeptic.py/consult.py to thin wrappers:

```python
#!/usr/bin/env python3
# scripts/ops/judge.py (30 lines instead of 159)
from scripts.lib.oracle import call_oracle

SYSTEM_PROMPT = "You are The Judge. Evaluate VALUE and ROI..."

def main():
    parser.add_argument("proposal")
    args = parser.parse_args()

    response = call_oracle(SYSTEM_PROMPT, args.proposal)
    print(response)
```

**Pros:**
- Eliminates duplication (shared oracle.py library)
- Backward compatible (scripts still work)
- Flexible (can add new personas easily)
- Clean separation (library vs CLI)

**Cons:**
- Still maintains 4 separate scripts (but thin)

## Recommendation: Option B (Generic oracle.py)

**Rationale:**

1. **council.py is the canonical multi-perspective tool** - designed for complex decisions
2. **Single-shot queries need a simpler interface** - oracle.py fills this gap
3. **Eliminates 4 vestige scripts** - reduces maintenance burden
4. **Generic design** - future-proof (any persona, any prompt)

**Implementation:**

```bash
# Create oracle.py with persona system
python3 scripts/ops/oracle.py --persona judge "Migrate to microservices"
python3 scripts/ops/oracle.py --persona critic "Use GraphQL instead of REST"

# Backward compatibility via slash commands
/judge "proposal" → runs oracle.py --persona judge "proposal"
/critic "idea" → runs oracle.py --persona critic "idea"
```

**Migration Path:**

1. Create `scripts/ops/oracle.py` (generic runner)
2. Test with existing use cases
3. Update slash commands to use oracle.py
4. Deprecate judge.py/critic.py/skeptic.py/consult.py
5. Remove after 1 week

## Alternative: Just Use council.py

**Simplest solution:**

```bash
# Replace judge.py
python3 scripts/ops/council.py --only judge "proposal"

# Replace critic.py
python3 scripts/ops/council.py --only critic "idea"
```

**Update slash commands:**
```bash
# .claude/commands/judge.md
!`python3 scripts/ops/council.py --only judge "$ARGUMENTS"`
```

**This eliminates all 4 vestige scripts with ZERO new code.**

## My Recommendation

**Go with the simplest solution that works:**

1. **Delete:** judge.py, critic.py, skeptic.py, consult.py (629 lines)
2. **Update slash commands** to use `council.py --only <persona>`
3. **If single-persona usage is clunky,** then add oracle.py

**Start simple. Add abstraction only if proven necessary.**
