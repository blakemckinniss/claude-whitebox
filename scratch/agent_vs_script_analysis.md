# Agent vs Script Analysis: Purge, Refactor, or Keep?

## Current State

### Agents (.claude/agents/*.md)
7 agents total:
- **council-advisor** - Multi-perspective decision making (runs judge/critic/skeptic/thinker/oracle)
- **researcher** - Context firewall for docs/API research
- **script-smith** - Code writer with quality gates
- **sherlock** - Read-only debugger, anti-gaslighting
- **critic** - Red team/attack assumptions
- **macgyver** - Living off the Land improvisation
- **runner** - Execute scripts without modifying (minimal, uses haiku)

### Scripts (scripts/ops/*.py)
26 scripts total, including:
- **council.py** - Multi-round deliberation with N+1 architecture
- **critic.py** - Oracle-powered assumption attack
- **research.py** - Tavily API web search
- **audit.py, void.py, drift_check.py** - Quality gates
- **verify.py, probe.py, xray.py** - Investigation tools
- etc.

### Overlap Analysis

**Name Overlap:** Only `critic` exists as BOTH agent AND script
- `critic.py` (script): Oracle-powered assumption attack tool
- `critic.md` (agent): Agent that CALLS critic.py + skeptic.py + gathers code evidence

**Functional Overlap:**
- **council-advisor (agent)** runs `council.py` (script) → WRAPPER PATTERN
- **researcher (agent)** runs `research.py` + `probe.py` + `xray.py` → WRAPPER PATTERN
- **critic (agent)** runs `critic.py` + `skeptic.py` → WRAPPER PATTERN

## The Core Question: Why Have Both?

### Agents Provide:
1. **Context Isolation** - Separate conversation thread (prevents main context pollution)
2. **Tool Scoping** - Restricted tool access (e.g., sherlock is read-only)
3. **Behavioral Framing** - Agent system prompt shapes HOW the tool is used
4. **Batch Orchestration** - Agents run MULTIPLE scripts in sequence
5. **Return Synthesis** - Agents digest large outputs → concise summaries

### Scripts Provide:
1. **Direct Execution** - Can be called from bash, agents, hooks
2. **Composability** - Can be chained in bash pipelines
3. **Testability** - Easier to unit test vs agent behavior
4. **Reusability** - Used by agents, hooks, and main assistant
5. **Determinism** - Scripts have deterministic I/O

## Pattern Detection: Agents as Orchestrators

Looking at the agents:

**council-advisor.md:**
```markdown
python3 scripts/ops/council.py "<proposal>"
```
→ Agent wraps the script with advisory protocol

**researcher.md:**
```markdown
python3 scripts/ops/research.py "<query>"
python3 scripts/ops/probe.py "<object>"
python3 scripts/ops/xray.py --type <type> --name <Name>
```
→ Agent orchestrates multiple investigation scripts

**critic.md:**
```markdown
python3 scripts/ops/critic.py "<idea>"
python3 scripts/ops/skeptic.py "<proposal>"
```
→ Agent combines adversarial perspectives

**sherlock.md:**
→ Agent enforces read-only tool scoping for anti-gaslighting

**script-smith.md:**
→ Agent enforces quality gates (audit/void/drift) during code writing

**macgyver.md:**
→ Agent enforces "Living off the Land" mindset

**runner.md:**
→ Minimal agent (uses haiku) for executing scripts without modification

## Value Assessment

### High-Value Agents (KEEP)
1. **sherlock** - Tool scoping (read-only) prevents modification during debugging
2. **script-smith** - Quality gate enforcement + write permission scoping
3. **macgyver** - Mindset enforcement (improvisation over installation)
4. **researcher** - Context firewall (500→50 lines) prevents pollution

### Questionable-Value Agents (ANALYZE)
5. **council-advisor** - Just calls `council.py` (but adds advisory formatting?)
6. **critic** - Just calls `critic.py` + `skeptic.py` (but adds code evidence gathering?)
7. **runner** - Minimal wrapper, but enforces read-only execution

## Official Anthropic Doc Guidance

From the official agent documentation you provided:

**Key Benefits:**
- **Context preservation** - Separate context window
- **Specialized expertise** - Domain-specific prompts
- **Tool access control** - Limit powerful tools
- **Reusability** - Share across projects

**Best Practices:**
- "Design focused subagents" - Single responsibility
- "Write detailed prompts" - Behavioral guidance
- "Limit tool access" - Security and focus
- "Chain subagents" - Complex workflows

## Recommendations

### Option 1: PURGE (Minimalist)
Delete all agents, rely only on scripts + main assistant behavioral prompts.

**Pros:**
- Simpler mental model
- Fewer moving parts
- Scripts are more testable

**Cons:**
- Lose context isolation
- Lose tool scoping (sherlock, script-smith)
- Main context gets polluted by large outputs

**Verdict:** ❌ TOO AGGRESSIVE - Loses valuable capabilities

---

### Option 2: REFACTOR (Pragmatic)
Keep only agents that provide UNIQUE VALUE beyond script execution:

**KEEP:**
1. **sherlock** - Read-only tool scoping (prevents modification loops)
2. **script-smith** - Write permission + quality gate enforcement
3. **researcher** - Context firewall (prevents large doc dumps)
4. **macgyver** - Mindset enforcement (LotL philosophy)

**DELETE:**
5. **council-advisor** - Redundant with `council.py` + main assistant
6. **critic** - Redundant with `critic.py` + `skeptic.py`
7. **runner** - Questionable value (just calls bash?)

**Refactor CLAUDE.md:**
- Update agent list to reflect survivors
- Emphasize scripts as primary tools
- Reserve agents for context/tool scoping only

**Pros:**
- Keeps high-value capabilities
- Reduces redundancy
- Clearer separation: scripts=tools, agents=specialized contexts

**Cons:**
- Still need to maintain 4 agents
- Council/critic lose agent framing

**Verdict:** ✅ STRONG CANDIDATE - Balances value vs complexity

---

### Option 3: KEEP + CLARIFY (Conservative)
Keep all agents but clarify roles more explicitly in CLAUDE.md.

**Changes:**
- Reframe agents as "Orchestration Layer" vs "Tool Layer"
- Update CLAUDE.md to show agent→script relationships
- Add decision tree: "When to use agent vs script?"

**Example Decision Tree:**
```
Need to run council.py?
├─ Main context has room? → Run `python3 scripts/ops/council.py` directly
└─ Need context isolation? → Delegate to council-advisor agent
```

**Pros:**
- No deletion risk
- Preserves all current capabilities
- Documentation improvement clarifies usage

**Cons:**
- Maintains redundancy
- Doesn't solve confusion

**Verdict:** ⚠️ SAFE BUT DOESN'T FIX CORE ISSUE

---

### Option 4: HYBRID (Experimental)
Delete redundant agents BUT promote scripts to auto-spawn agents when context gets large.

**Implementation:**
- Delete: council-advisor, critic, runner
- Keep: sherlock, script-smith, researcher, macgyver
- Add hook: If script output >1000 tokens → automatically spawn researcher agent for synthesis

**Pros:**
- Automatic context management
- Reduces manual agent count
- Preserves context firewall benefits

**Cons:**
- More complex (hook-based routing)
- Less explicit control

**Verdict:** 🔬 INTERESTING BUT COMPLEX

---

## My Recommendation: Option 2 (Refactor)

**Rationale:**

1. **Tool Scoping Value (sherlock, script-smith):**
   - sherlock's read-only restriction prevents gaslighting loops
   - script-smith's write permission + quality gates prevent bad code

2. **Context Firewall Value (researcher):**
   - Large doc dumps (500 lines) pollute main context
   - Researcher compresses to 50 words + code snippet

3. **Mindset Enforcement Value (macgyver):**
   - LotL philosophy requires behavioral framing
   - Script alone doesn't enforce "don't install" mindset

4. **Redundancy Problem (council-advisor, critic, runner):**
   - council-advisor just runs `council.py` (main assistant can do this)
   - critic just runs `critic.py` + `skeptic.py` (main assistant can do this)
   - runner just runs bash (main assistant can do this)

**Action Plan:**

1. DELETE these agents:
   - `.claude/agents/council-advisor.md`
   - `.claude/agents/critic.md`
   - `.claude/agents/runner.md`

2. UPDATE CLAUDE.md:
   - Remove references to deleted agents
   - Clarify when to use remaining agents vs scripts
   - Add decision tree

3. UPDATE epistemology.py:
   - Remove reward bonuses for deleted agents
   - Keep bonuses for sherlock, script-smith, researcher

4. VERIFY hooks don't reference deleted agents

## Final Decision Tree (Post-Refactor)

```
┌─────────────────────────────────────────┐
│ SCRIPTS (scripts/ops/*.py)              │
│ Direct execution, composable, testable  │
├─────────────────────────────────────────┤
│ council.py, critic.py, judge.py,        │
│ skeptic.py, research.py, probe.py,      │
│ verify.py, audit.py, void.py, etc.      │
└─────────────────────────────────────────┘
           ↑
           │ Called by
           │
┌──────────┴──────────────────────────────┐
│ AGENTS (.claude/agents/*.md)            │
│ Context isolation, tool scoping         │
├─────────────────────────────────────────┤
│ researcher  - Context firewall          │
│ sherlock    - Read-only debugging       │
│ script-smith - Write permission + gates │
│ macgyver    - LotL mindset enforcement  │
└─────────────────────────────────────────┘
```

**When to use agents:**
- **researcher:** Fetching large docs (>500 lines) that would pollute context
- **sherlock:** Debugging loops where you suspect gaslighting
- **script-smith:** Writing production code (enforces audit/void/drift)
- **macgyver:** Tool failures requiring improvisation

**When to use scripts directly:**
- Everything else (council, critic, verify, probe, etc.)
