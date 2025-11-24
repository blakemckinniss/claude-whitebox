#!/usr/bin/env python3
"""
Prototype: Scratch Indexer (AST + Regex)
Extract semantic signatures from scratch/ for associative retrieval
"""
import os
import ast
import re
import json
from pathlib import Path
from collections import defaultdict

def extract_python_signatures(filepath):
    """Extract AST signatures from Python file"""
    signatures = {
        'functions': [],
        'classes': [],
        'imports': [],
        'patterns': []
    }
    
    try:
        with open(filepath) as f:
            content = f.read()
            tree = ast.parse(content)
        
        # Extract functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                signatures['functions'].append(node.name)
            elif isinstance(node, ast.ClassDef):
                signatures['classes'].append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    signatures['imports'].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    signatures['imports'].append(node.module)
        
        # Extract semantic patterns via regex
        patterns = {
            'oracle_usage': r'oracle\.py|call_oracle|PERSONAS',
            'parallel_usage': r'parallel\.py|run_parallel|max_workers',
            'verification': r'verify\.py|assert|pytest|test_',
            'hooks': r'UserPromptSubmit|PostToolUse|PreToolUse',
            'decisions': r'VERDICT|RECOMMENDATION|CONCLUSION',
        }
        
        for pattern_name, pattern in patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                signatures['patterns'].append(pattern_name)
                
    except Exception as e:
        pass
    
    return signatures

def extract_markdown_decisions(filepath):
    """Extract key decisions/verdicts from markdown files"""
    decisions = []
    
    try:
        with open(filepath) as f:
            content = f.read()
        
        # Extract sections with decisions
        decision_patterns = [
            r'##\s*(VERDICT|RECOMMENDATION|CONCLUSION|DECISION)[:\s]*(.+?)(?=\n##|\Z)',
            r'\*\*VERDICT:\*\*\s*(.+)',
            r'\*\*RECOMMENDATION:\*\*\s*(.+)',
        ]
        
        for pattern in decision_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    decisions.append(' '.join(match).strip()[:200])
                else:
                    decisions.append(match.strip()[:200])
                    
    except Exception as e:
        pass
    
    return decisions

def build_scratch_index():
    """Build index of all scratch/ files"""
    scratch_dir = Path("scratch")
    index = {}

    for filepath in scratch_dir.rglob("*"):
        if not filepath.is_file():
            continue

        rel_path = str(filepath)
        
        # Get file metadata
        stat = filepath.stat()
        metadata = {
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'type': filepath.suffix,
        }
        
        # Extract semantic content
        if filepath.suffix == '.py':
            signatures = extract_python_signatures(filepath)
            metadata.update(signatures)
            
            # Extract keywords from filename
            keywords = re.findall(r'\w+', filepath.stem)
            metadata['keywords'] = [k.lower() for k in keywords if len(k) > 3]
            
        elif filepath.suffix == '.md':
            decisions = extract_markdown_decisions(filepath)
            metadata['decisions'] = decisions
            
            # Extract keywords from filename
            keywords = re.findall(r'\w+', filepath.stem)
            metadata['keywords'] = [k.lower() for k in keywords if len(k) > 3]
        
        index[rel_path] = metadata
    
    return index

def find_associations(query, index, top_n=5):
    """Find scratch files associated with query keywords"""
    query_words = set(re.findall(r'\w+', query.lower()))
    query_words = {w for w in query_words if len(w) > 3}
    
    scores = []
    
    for filepath, metadata in index.items():
        score = 0
        matches = []
        
        # Keyword overlap
        keywords = set(metadata.get('keywords', []))
        overlap = query_words & keywords
        if overlap:
            score += len(overlap) * 2
            matches.append(f"keywords: {', '.join(overlap)}")
        
        # Function name overlap
        functions = set(metadata.get('functions', []))
        func_overlap = {f.lower() for f in functions} & query_words
        if func_overlap:
            score += len(func_overlap) * 3
            matches.append(f"functions: {', '.join(func_overlap)}")
        
        # Pattern matching
        patterns = metadata.get('patterns', [])
        for pattern in patterns:
            if any(word in pattern.lower() for word in query_words):
                score += 1
                matches.append(f"pattern: {pattern}")
        
        if score > 0:
            scores.append({
                'file': filepath,
                'score': score,
                'matches': matches,
                'type': metadata['type']
            })
    
    # Sort by score
    scores.sort(key=lambda x: x['score'], reverse=True)
    return scores[:top_n]

if __name__ == "__main__":
    print("🔍 Building scratch/ index...")
    index = build_scratch_index()
    
    print(f"✅ Indexed {len(index)} files")
    print()
    
    # Test queries
    test_queries = [
        "oracle external reasoning",
        "parallel execution performance",
        "hook enforcement testing",
        "epistemology confidence tracking"
    ]
    
    for query in test_queries:
        print(f"Query: '{query}'")
        results = find_associations(query, index, top_n=3)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['file']} (score: {result['score']})")
                print(f"     Matches: {', '.join(result['matches'])}")
        else:
            print("  No associations found")
        print()
    
    # Save index
    output_path = ".claude/memory/scratch_index.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(index, f, indent=2)
    
    print(f"💾 Index saved to {output_path}")
