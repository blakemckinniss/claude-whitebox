# Organizational Drift Detection Analysis

## Catastrophic Anti-Patterns (Must Block)

### 1. **Infinite Recursion** (CRITICAL)
- **Pattern:** Directory contains subdirectory with same name
- **Example:** `scripts/scripts/ops/` or `.claude/hooks/.claude/hooks/`
- **Detection:** Path contains repeated segments
- **Severity:** CATASTROPHIC - breaks all tooling

### 2. **Catastrophic Duplication** (CRITICAL)
- **Pattern:** Same functional file exists in multiple locations
- **Example:**
  - `audit.py` in both `scripts/ops/` and `scratch/`
  - `epistemology.py` in both `scripts/lib/` and `.claude/hooks/`
- **Detection:** Filename collision across production zones
- **Severity:** HIGH - creates maintenance nightmare

### 3. **Hook Explosion** (HIGH)
- **Pattern:** >30 hooks in `.claude/hooks/`
- **Rationale:** Each hook adds overhead; >30 suggests lack of consolidation
- **Detection:** File count in hooks directory
- **Severity:** HIGH - performance degradation

### 4. **Scratch Bloat** (MEDIUM)
- **Pattern:** >500 files in `scratch/` (excluding archive/)
- **Rationale:** Scratch is temp zone; massive accumulation suggests poor hygiene
- **Detection:** File count excluding archive subdirs
- **Severity:** MEDIUM - context pollution

### 5. **Production Zone Pollution** (HIGH)
- **Pattern:** Test files, scratch files, or temp data in `scripts/ops/`
- **Example:** `test_*.py`, `*.tmp`, `debug_*.py` in production
- **Detection:** Filename patterns in wrong zones
- **Severity:** HIGH - violates separation of concerns

### 6. **Deep Nesting** (MEDIUM)
- **Pattern:** Directory depth >6 levels
- **Example:** `projects/foo/src/components/auth/providers/oauth/google/handlers/`
- **Detection:** Path depth count
- **Severity:** MEDIUM - maintainability issue

### 7. **Memory Fragmentation** (MEDIUM)
- **Pattern:** >100 session state files in `.claude/memory/`
- **Rationale:** Old sessions accumulate; should be pruned
- **Detection:** File count matching `session_*_state.json`
- **Severity:** MEDIUM - disk waste

### 8. **Root Pollution** (CRITICAL)
- **Pattern:** New files created in repository root
- **Example:** `test.py`, `foo.json`, `temp.md` in `/`
- **Detection:** New file in root outside allowlist
- **Severity:** CRITICAL - violates constitution (Hard Block #1)

## Legitimate Overrides (Must Allow)

### 1. **Archive Growth**
- `scratch/archive/` can grow unbounded (it's intentional)
- Override: Exclude archive directories from scratch bloat check

### 2. **Projects Zone Independence**
- `projects/` can have ANY structure (user owns it)
- Override: Exclude `projects/` from depth/pattern checks

### 3. **External Dependencies**
- `node_modules/`, `venv/`, `__pycache__/` are system-managed
- Override: Exclude from ALL checks

### 4. **Multi-Turn Operations**
- Large refactors may temporarily violate limits
- Override: "SUDO" keyword bypasses all checks

### 5. **Intentional Duplication**
- Templates in `projects/.template/` may mirror real structures
- Override: Exclude `.template/` directories

## Detection Strategy

### Phase 1: Static Analysis (Fast)
1. Path recursion check (regex)
2. File count checks (stat)
3. Depth calculation (path.split('/'))
4. Zone violation check (pattern matching)

### Phase 2: Content Analysis (Slow - only if Phase 1 passes)
1. Filename collision check (cross-zone comparison)
2. Duplicate detection (hash comparison for same names)

### Phase 3: Auto-Tuning
- Track false positives by pattern type
- Adjust thresholds every 100 turns
- Auto-generate exception rules from "SUDO" overrides

## Proposed Thresholds (Initial)

| Pattern | Initial Threshold | Auto-Tune Range |
|---------|------------------|-----------------|
| Hook Count | 30 | 25-40 |
| Scratch Files | 500 | 300-700 |
| Memory Sessions | 100 | 75-150 |
| Max Depth | 6 | 5-8 |
| Duplicate Zones | 0 (hard block) | N/A |
| Recursion | 0 (hard block) | N/A |
| Root Pollution | 0 (hard block) | N/A |

## Implementation Notes

1. **Fail Fast:** Recursion/Root checks first (cheap, catastrophic)
2. **Progressive:** Only run expensive checks if fast ones pass
3. **Transparent:** Show which rule triggered + current vs threshold
4. **Escapable:** "SUDO" keyword overrides (logged as evidence)
5. **Self-Tuning:** Track FP rate per rule, adjust thresholds
