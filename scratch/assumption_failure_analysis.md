# CRITICAL FAILURE: Assumption-Based Implementation

## What Happened
I implemented Context7 integration based on **research results about MCP servers** instead of **verifying the actual API**.

## The Failure Chain
1. User provided clear API example: `curl -X GET "https://context7.com/api/v1/..."`
2. I ran web research and found MCP server documentation
3. I **assumed** MCP was the only way to use Context7
4. I **ignored** the user's explicit curl example showing REST API
5. I wrote an entire implementation based on wrong assumptions
6. I only discovered the truth when attempting to run it

## Why This Is Catastrophic
- **User had the answer** in their original message
- **I ignored ground truth** (the curl command) in favor of search results
- **I wasted tokens** implementing wrong approach
- **I spread misinformation** ("Context7 is MCP-only")
- **This pattern scales** - if I do this on every task, the system is useless

## Root Cause Analysis
### Violated Protocols
1. **Constitution #9**: "No Hallucinations: Verify reality (probe) before claiming facts"
2. **Reality Check Protocol**: Should have tested the curl command FIRST
3. **Epistemological Protocol**: Built implementation at 20% confidence (IGNORANCE tier)
4. **Research Before Code**: Found docs but didn't verify against user's example

### Cognitive Bias
- **Confirmation Bias**: Research found MCP docs, so I stopped looking
- **Recency Bias**: Latest research results overrode user's original input
- **Authority Bias**: Trusted "official documentation" over user's working example
- **Complexity Bias**: Assumed complex MCP protocol instead of simple REST

## The Pattern
```
User provides working example
  ↓
I research topic
  ↓
Research returns tangential information
  ↓
I assume research is complete picture
  ↓
I implement based on incomplete understanding
  ↓
Implementation fails
  ↓
User corrects me
```

## What Should Have Happened
```
User provides working example
  ↓
I TEST the example immediately (verify.py command_success)
  ↓
Working? → Use it directly
  ↓
Not working? → THEN research alternatives
  ↓
Research yields different approach?
  ↓
ASK USER which is correct (AskUserQuestion)
  ↓
Implement verified approach
```

## Prevention Strategies

### 1. User Input Primacy Rule
**RULE**: If user provides working code/commands, TEST THEM FIRST before researching.
- User's curl example = ground truth
- Research = supplementary context
- Never let research override user's explicit examples

### 2. Verify Before Theorize
**RULE**: Run actual tests before building mental models.
```bash
# Should have done this IMMEDIATELY:
curl -X GET "https://context7.com/api/v1/vercel/next.js?type=txt&topic=ssr&tokens=5000" \
  -H "Authorization: Bearer $CONTEXT7_API_KEY"
```
- Exit code 0 = API works, use it
- Exit code non-0 = API broken, research alternatives

### 3. Confidence Gating for Assumptions
**RULE**: Cannot make architectural decisions at <71% confidence.
- I was at 20% confidence (IGNORANCE tier)
- Should have been BLOCKED from writing production code
- Should have been forced to gather evidence first

### 4. Cross-Reference Detection
**RULE**: When research contradicts user input, HALT and ask.
- User said: "REST API with curl"
- Research said: "MCP server with stdio"
- **I should have stopped and asked which is correct**

## Proposed Protocol: Assumption Firewall

### Hook: PreToolUse (Write/Edit)
**Check**: Does session state contain user-provided examples for current task?
- YES → Have I tested them?
  - NO → BLOCK: "Test user's example first"
  - YES, failed → Proceed with alternative
  - YES, worked → Must use user's approach

### Hook: PostResearch
**Check**: Do research results contradict user input?
- YES → Flag for AskUserQuestion
- NO → Proceed

### Tool: assumption_check.py
**Function**: Compare implementation plan against user's original input
- Extract code/commands from user messages
- Compare against proposed implementation
- Report divergence score

## Testing the Fix
1. Re-read user's original message
2. Extract the curl command
3. Test it immediately
4. If it works → implement based on THAT, not research
5. Document the correct API in docs.py

## Meta-Lesson
**The user is the ground truth.**
- User examples > Research results
- Testing > Theorizing
- Asking > Assuming
- Verify > Believe

This failure pattern is not just "oops I made a mistake."
This is **systematic epistemic failure** that undermines the entire protocol system.

## Action Items
1. Test user's curl command immediately
2. Rewrite docs.py based on ACTUAL API
3. Create assumption_firewall hook to prevent this pattern
4. Add to lessons.md with HIGH priority
5. Update epistemological protocol with "User Input Primacy" rule
