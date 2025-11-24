#!/usr/bin/env python3
"""Extract clean function definitions from patches"""
import re

with open("scratch/epistemology_patches.py") as f:
    content = f.read()

# Find the section with actual code (after the usage notes)
start_marker = "# ===================================================================\n# NEW FUNCTIONS TO ADD"
sections = content.split(start_marker)

if len(sections) > 1:
    code_section = sections[1]
    
    # Remove the usage notes section
    usage_marker = "# ===================================================================\n# USAGE NOTES"
    if usage_marker in code_section:
        code_section = code_section.split(usage_marker)[0]
    
    # Clean up - remove the end marker comment
    code_section = code_section.replace("# ===================================================================", "")
    
    print(code_section.strip())
else:
    print("ERROR: Could not find code section")
