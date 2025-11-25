#!/usr/bin/env python3
"""
Scratch Context Injection Hook (UserPromptSubmit)
Injects relevant past work from scratch/ as associative memory clues
"""
import sys
import json
import os
from pathlib import Path

def load_scratch_index():
    """Load prebuilt scratch index"""
    index_path = Path(".claude/memory/scratch_index.json")
    if not index_path.exists():
        return {}
    
    try:
        with open(index_path) as f:
            return json.load(f)
    except Exception:
        return {}

def find_associations(query, index, top_n=3):
    """Find scratch files associated with query (lightweight version)"""
    import re
    
    query_words = set(re.findall(r'\w+', query.lower()))
    query_words = {w for w in query_words if len(w) > 3}
    
    scores = []
    
    for filepath, metadata in index.items():
        score = 0
        reason = []
        
        # Keyword overlap
        keywords = set(metadata.get('keywords', []))
        overlap = query_words & keywords
        if overlap:
            score += len(overlap) * 2
            reason.append(f"keywords: {'/'.join(list(overlap)[:2])}")
        
        # Function name overlap
        functions = set(f.lower() for f in metadata.get('functions', []))
        func_overlap = functions & query_words
        if func_overlap:
            score += len(func_overlap) * 3
            reason.append(f"function: {list(func_overlap)[0]}")
        
        # Pattern matching
        patterns = metadata.get('patterns', [])
        for pattern in patterns:
            if any(word in pattern.lower() for word in query_words):
                score += 1
                if pattern not in [r[9:] for r in reason if r.startswith('pattern:')]:
                    reason.append(f"pattern: {pattern}")
        
        if score > 0:
            scores.append({
                'file': filepath,
                'score': score,
                'reason': ', '.join(reason[:2])
            })
    
    # Sort by score and recency
    scores.sort(key=lambda x: (x['score'], -index[x['file']].get('modified', 0)), reverse=True)
    return scores[:top_n]

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    
    prompt = data.get("prompt", "").lower()
    
    # Skip if prompt is too short or is a continuation
    if len(prompt) < 20 or prompt.strip() in ["continue", "proceed", "go", "yes", "no"]:
        sys.exit(0)
    
    # Load index
    index = load_scratch_index()
    if not index:
        sys.exit(0)  # No index yet
    
    # Find associations
    associations = find_associations(prompt, index, top_n=3)
    
    if not associations:
        sys.exit(0)  # No matches
    
    # Build context injection
    context_lines = ["📂 SCRATCH CONTEXT (Associative Memory):"]
    for assoc in associations:
        # Format: filename (reason)
        basename = os.path.basename(assoc['file'])
        context_lines.append(f"   • {basename}: {assoc['reason']}")
    
    context = "\n".join(context_lines)
    
    # Inject context
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context
        }
    }))
    sys.exit(0)

if __name__ == "__main__":
    main()
