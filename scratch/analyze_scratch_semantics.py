#!/usr/bin/env python3
"""Analyze semantic value of scratch/ directory"""
import os
import re

scratch_dir = "scratch"
patterns = {
    "test_scripts": r"test_.*\.py$",
    "analysis_docs": r"(analysis|summary|report|design).*\.md$",
    "prototypes": r"(tmp_|proto_|scratch_|build_).*\.py$",
    "archived": r"archive/",
}

stats = {k: [] for k in patterns}
all_files = []

for root, dirs, files in os.walk(scratch_dir):
    for f in files:
        path = os.path.join(root, f)
        all_files.append(path)
        
        for category, pattern in patterns.items():
            if re.search(pattern, path):
                stats[category].append(path)

print("📊 SCRATCH SEMANTIC ANALYSIS")
print("=" * 60)
print(f"Total files: {len(all_files)}")
print()

for category, files in stats.items():
    print(f"{category}: {len(files)} files")
    if files and len(files) <= 5:
        for f in files[:3]:
            print(f"  - {f}")

# Check for promotion candidates (scripts with main blocks)
promotion_candidates = []
for root, dirs, files in os.walk(scratch_dir):
    for f in files:
        if f.endswith(".py") and not f.startswith("test_"):
            path = os.path.join(root, f)
            try:
                with open(path) as file:
                    content = file.read()
                    # Has main block + helper functions = reusable
                    has_main = '__main__' in content
                    has_functions = len(re.findall(r'^def \w+', content, re.M)) > 1
                    if has_main and has_functions:
                        promotion_candidates.append(path)
            except:
                pass

print()
print(f"🎯 PROMOTION CANDIDATES (reusable scripts): {len(promotion_candidates)}")
for candidate in promotion_candidates[:5]:
    print(f"  - {candidate}")
