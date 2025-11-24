# Prompt-Based Hooks Testing Guide

## Test Cases

### 1. Batch Operation Detection
**Test Prompt:** "write a script to process all files in the directory"

**Expected Output:**
```
⚠️ BATCH OPERATION DETECTED

PERFORMANCE PROTOCOL: Use scripts.lib.parallel for multi-threading.

Example:
  from parallel import run_parallel
  results = run_parallel(process_func, items, max_workers=10, desc='Processing')
```

### 2. API Guessing Prevention  
**Test Prompt:** "write a script to use pandas for data analysis"

**Expected Output:**
```
⚠️ API GUESSING PROHIBITED

STOP. Do not guess method signatures.

MANDATORY:
1. /research 'pandas current docs'
2. /probe pandas.DataFrame

Then code based on ACTUAL runtime API.

See CLAUDE.md § Probe Protocol
```

### 3. Browser Automation
**Test Prompt:** "use requests to login to the website"

**Expected Output:**
```
⚠️ BROWSER AUTOMATION REQUIRED

Do NOT use requests/BeautifulSoup for dynamic sites.

USE: Playwright (Whitebox Browser SDK)

Why:
- CSRF tokens need browser sessions
- JavaScript rendering needs real browser
- Login flows need cookies/localStorage

See CLAUDE.md § Headless Protocol
```

### 4. Bikeshedding Detection
**Test Prompt:** "let's update the prettier config and linting rules"

**Expected Output:**
```
⚖️ VALUE CHECK REQUIRED

This looks like bikeshedding.

MANDATORY: /judge '<proposal>' before proceeding

Ask: Does this ship to production TODAY?

See CLAUDE.md § Judge Protocol
```

### 5. Protocol Enforcer (Meta-Enforcement)
**Test Prompt:** "migrate the database to PostgreSQL"

**Expected Output:**
```
⚠️ PROTOCOL REQUIREMENTS:
- MUST run /council for migration decision
- MUST run /research for current PostgreSQL best practices

These are NON-NEGOTIABLE per CLAUDE.md § Decision Protocol.
```

### 6. Intent Router
**Test Prompt:** "I need to find where the User class is defined"

**Expected Output:**
```
📍 RECOMMENDED: /xray --type class --name User

Why: AST structural search finds class definitions efficiently

See CLAUDE.md § Tool Registry
```

### 7. Knowledge Freshness
**Test Prompt:** "how do I use the latest Next.js app router?"

**Expected Output:**
```
⚠️ KNOWLEDGE CHECK: This may require current information.

RECOMMENDED: /research 'Next.js app router 2025' before coding

Reason: Training data from Jan 2025 - APIs may have changed
```

## PreToolUse Hook Tests

### 8. Shortcut Detector (Task Delegation)
**Test Action:** Delegate to Task agent with >200 char prompt without /think

**Expected:** Should potentially block or warn if complex delegation without decomposition

### 9. Code Intent Validator (Write/Edit)
**Test Action:** Attempt to write a .md file "JUST FOR HUMANS"

**Expected:**
```
🚫 CODE VIOLATION

Creating documentation JUST FOR HUMANS violates CLAUDE.md § Core Philosophy
"NO EXCESSIVE (OR ORPHAN) DOCUMENTATION: ANY DOCUMENTATION MUST ONLY BE FOR ACTUAL LLM USE/CONSUMPTION"

See CLAUDE.md § Core Philosophy
```

## How to Test

1. **Restart Claude Code** (required to load new hooks)
2. **Submit each test prompt** above
3. **Observe systemMessage outputs** in the response
4. **Verify semantic understanding** - do the triggers make sense contextually?

## Success Criteria

✅ All 7 UserPromptSubmit hooks trigger on appropriate prompts  
✅ systemMessages are clear and actionable  
✅ False positive rate is acceptable (<20%)  
✅ Latency impact is acceptable (<2 seconds)  
✅ No JSON parsing errors  

## Monitoring

After testing, monitor:
- **Token usage** via token_tracker.py
- **Latency** via `/home/jinx/.claude/logs`
- **Effectiveness** via user feedback

## Iteration

Based on results, refine prompts in:
`scratch/prompt_templates.json`

Then regenerate config:
`python3 scratch/convert_to_prompt_hooks.py`
`python3 scratch/apply_prompt_hooks.py`
