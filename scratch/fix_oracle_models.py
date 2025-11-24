#!/usr/bin/env python3
"""Fix oracle.py model defaults to use valid models from council_models.json"""
import json

# Read valid models
with open('.claude/config/council_models.json') as f:
    config = json.load(f)
    valid_models = config['models']

print(f"Valid models from council_models.json: {valid_models}")
print(f"\nRecommendation: Use {valid_models[0]} as new default")

# Check what oracle.py currently uses
with open('scripts/ops/oracle.py') as f:
    content = f.read()
    if 'google/gemini-2.0-flash-thinking-exp' in content:
        print("\nFound hardcoded gemini-2.0-flash-thinking-exp in oracle.py")
        print("This model is invalid (400 Bad Request from OpenRouter)")
    
# Check oracle.py lib
with open('scripts/lib/oracle.py') as f:
    lib_content = f.read()
    if 'google/gemini-2.0-flash-thinking-exp' in lib_content:
        print("Found hardcoded gemini-2.0-flash-thinking-exp in lib/oracle.py")

print(f"\n✅ Replace all instances with: {valid_models[0]}")
