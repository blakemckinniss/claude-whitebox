# Logical Fallacy Detection System - Architecture

## Overview
Meta-cognitive system to detect and prevent logical fallacies in AI reasoning using three-layer enforcement: detection, intervention, and reinforcement learning.

## Core Problem
LLMs are pattern-matching engines that can produce logically invalid reasoning:
- **Correlation ≠ Causation** (post hoc fallacies)
- **Circular reasoning** (begging the question)
- **False dichotomies** (black-and-white thinking)
- **Hasty generalizations** (insufficient evidence)
- **Strawman arguments** (misrepresenting position)
- **Appeal to authority** (without verification)
- **Slippery slope** (chain of unjustified inferences)
- **Confirmation bias** (cherry-picking evidence)
- **Ad hominem** (attacking source, not argument)
- **Sunk cost fallacy** (commitment escalation)

## Architecture: Three-Layer Defense

### Layer 1: Pattern Detection (PreToolUse Hook)
**Hook:** `detect_logical_fallacy.py`
**Trigger:** UserPromptSubmit + PostToolUse (analyzing Claude's responses)
**Action:** SOFT WARN (log patterns, inject warning)

**Detection Patterns:**
1. **Post Hoc Ergo Propter Hoc** (correlation → causation)
   - Pattern: "X happened, then Y happened, therefore X caused Y"
   - Regex: `(?:since|after|because).*(?:therefore|thus|so)`

2. **Circular Reasoning**
   - Pattern: Conclusion appears in premises
   - Detection: Semantic similarity between premise and conclusion

3. **False Dichotomy**
   - Pattern: "either X or Y" without justification
   - Regex: `(?:either|only).*(?:or|alternative)`

4. **Hasty Generalization**
   - Pattern: Universal claims from limited samples
   - Regex: `(?:always|never|all|none).*(?:based on|from|in this case)`

5. **Appeal to Authority** (without verification)
   - Pattern: "X says Y, therefore Y is true"
   - Regex: `(?:expert|authority|documentation).*(?:says|claims).*(?:therefore|so)`

6. **Slippery Slope**
   - Pattern: A → B → C → D without justification
   - Detection: Chain of 3+ implications without evidence

7. **Confirmation Bias**
   - Pattern: Cherry-picking files/data that support hypothesis
   - Detection: Grep with narrow patterns, ignoring contradictory evidence

8. **Sunk Cost Fallacy**
   - Pattern: "I already spent X time/tokens, must continue"
   - Regex: `(?:already|spent|invested).*(?:continue|finish|complete)`

### Layer 2: Reasoning Enforcement (PreToolUse Hook)
**Hook:** `enforce_reasoning_rigor.py`
**Trigger:** PreToolUse on Write/Edit/Task (production actions)
**Action:** HARD BLOCK if reasoning incomplete

**Requirements:**
- Universal claims require QUANTITATIVE EVIDENCE (not "many", but "73% of 156 files")
- Causal claims require MECHANISM ("X causes Y via Z pathway")
- Generalizations require SAMPLE SIZE (minimum N=3 for code patterns)
- Predictions require CONFIDENCE BOUNDS ("80% confident" not "will definitely")

**Enforcement Rules:**
1. **No Universal Claims Without Evidence**
   - Block: "All X are Y" without verification
   - Require: Exhaustive search OR explicit sample size

2. **No Causal Claims Without Mechanism**
   - Block: "X causes Y" without explanation
   - Require: "X causes Y via [mechanism Z]"

3. **No Generalizations From Single Example**
   - Block: Refactoring based on one file
   - Require: Pattern detection across N≥3 files

4. **No Certainty Without Verification**
   - Block: "This will work" without /verify
   - Require: Probabilistic language OR evidence

### Layer 3: Metacognitive Intervention (PostToolUse Hook)
**Hook:** `trigger_metacognition.py`
**Trigger:** PostToolUse when fallacy detected OR complex decision
**Action:** FORCE oracle consultation before proceeding

**Trigger Conditions:**
- Fallacy detected in Layer 1 (2+ patterns in single turn)
- Architectural decision (affecting 5+ files)
- Failed verification (3-strike rule)
- Contradiction with previous evidence

**Oracle Consultation:**
```bash
oracle.py --persona skeptic "Evaluate this reasoning: [Claude's claim]"
```

**Meta-Questions:**
1. "What evidence would DISPROVE this hypothesis?"
2. "What alternative explanations exist?"
3. "What assumptions am I making?"
4. "What would change my conclusion?"

## Detection Logic

### Semantic Analysis (requires NLP)
For detecting circular reasoning and strawman arguments:
- Use lightweight semantic similarity (sentence-transformers)
- Compare premise vectors with conclusion vectors
- Threshold: >0.85 similarity = likely circular

### Confidence Calibration
Track prediction accuracy over time:
- Store: (claim, confidence, outcome)
- Calculate: Brier score (measure of probabilistic accuracy)
- Penalty: -15% confidence for overconfident false claims

### Telemetry
Track fallacy occurrences:
```json
{
  "fallacy_type": "hasty_generalization",
  "turn": 42,
  "context": "Claiming all error handling follows pattern X after seeing 1 file",
  "blocked": true,
  "override": false
}
```

## Implementation Strategy

### Phase 1: Pattern Detection (Regex-Based)
**File:** `detect_logical_fallacy.py`
- Implement 8 regex patterns
- Inject warnings (not blocking)
- Log to `.claude/memory/fallacy_telemetry.jsonl`

### Phase 2: Reasoning Enforcement (Rule-Based)
**File:** `enforce_reasoning_rigor.py`
- Hard-block universal claims without evidence
- Hard-block causal claims without mechanism
- Require confidence bounds (not certainty)

### Phase 3: Metacognitive Intervention (Oracle-Powered)
**File:** `trigger_metacognition.py`
- Auto-trigger oracle on fallacy detection
- Force "steelman" (opposite of strawman) exercise
- Require evidence of falsifiability

### Phase 4: Reinforcement Learning (Telemetry)
**File:** `fallacy_telemetry.py`
- Track fallacy rate over time
- Penalize repeated fallacies (-10% confidence)
- Reward falsifiable reasoning (+5% confidence)

## Integration with Existing Systems

### Epistemological Protocol
- Fallacy detection → -20% confidence (similar to hallucination)
- Rigorous reasoning → +10% confidence
- False certainty → -15% confidence

### Evidence Tracking
- Universal claims require evidence count
- Causal claims require mechanism documentation
- Generalizations require sample size

### Oracle Protocol
- Auto-invoke on complex reasoning
- Skeptic persona for fallacy checking
- Judge persona for YAGNI violations

## Testing Strategy

### Unit Tests
```python
test_post_hoc_detection()  # "X then Y therefore X caused Y"
test_circular_reasoning()  # Premise = Conclusion
test_false_dichotomy()     # "Either X or nothing"
test_hasty_generalization() # Universal from N=1
test_appeal_to_authority() # "Docs say X therefore X" (without verify)
```

### Integration Tests
```python
test_blocks_unchecked_universal_claim()
test_requires_mechanism_for_causation()
test_triggers_oracle_on_complex_decision()
test_telemetry_tracks_fallacy_rate()
```

### Stress Tests
- Give Claude intentionally fallacious prompts
- Verify detection rate >90%
- Verify false positive rate <10%

## Philosophy

**Core Insight:** LLMs optimize for linguistic coherence, not logical validity.

**Solution:** External logic checker that:
1. Detects invalid inference patterns (regex)
2. Enforces evidence requirements (rules)
3. Forces adversarial review (oracle)
4. Tracks calibration over time (telemetry)

**Result:** LLM that says "I don't know" instead of rationalizing.

## Open Questions

1. **Semantic Analysis:** Do we need lightweight NLP for circular reasoning detection, or can regex suffice?
2. **Threshold Tuning:** What similarity threshold for circular reasoning? (0.85? 0.90?)
3. **Override Mechanism:** Should user be able to say "SUDO ALLOW_FALLACY"?
4. **Oracle Budget:** How to prevent infinite recursion (oracle calls oracle)?
5. **False Positives:** How to handle legitimate uses of "all" or "always" (e.g., "all files in this directory")?

## Next Steps

1. Implement Phase 1 (detection patterns)
2. Test against historical session logs
3. Tune thresholds for false positives
4. Implement Phase 2 (enforcement)
5. Integrate with epistemological protocol
