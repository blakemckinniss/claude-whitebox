#!/usr/bin/env python3
"""
Lesson Consolidation: Merges duplicate auto-learned patterns
Part of Reflexion Memory Protocol - called by upkeep.py before commits
"""
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Find project root
script_path = Path(__file__).resolve()
current = script_path.parent
while current != current.parent:
    if (current / "scripts" / "lib" / "core.py").exists():
        PROJECT_ROOT = current
        break
    current = current.parent
else:
    print("ERROR: Could not find project root", file=stderr)
    sys.exit(1)

sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "lib"))

LESSONS_FILE = PROJECT_ROOT / ".claude" / "memory" / "lessons.md"


def parse_lessons(content):
    """Parse lessons.md into structured entries"""
    entries = []
    current_entry = None

    for line in content.split('\n'):
        # Detect auto-learned entries
        if line.startswith('### '):
            # Save previous entry
            if current_entry:
                entries.append(current_entry)

            # Start new entry
            timestamp = line.replace('### ', '').strip()
            current_entry = {
                'timestamp': timestamp,
                'content': '',
                'is_auto': False,
                'tag': None,
                'raw': line + '\n'
            }
        elif current_entry:
            current_entry['raw'] += line + '\n'
            current_entry['content'] += line + '\n'

            # Detect tags
            if '[AUTO-LEARNED-FAILURE]' in line:
                current_entry['is_auto'] = True
                current_entry['tag'] = 'FAILURE'
            elif '[AUTO-LEARNED-SUCCESS]' in line:
                current_entry['is_auto'] = True
                current_entry['tag'] = 'SUCCESS'

    # Save last entry
    if current_entry:
        entries.append(current_entry)

    return entries


def extract_pattern_key(content):
    """Extract pattern key for duplicate detection"""
    # Remove tags
    clean = content.replace('[AUTO-LEARNED-FAILURE]', '').replace('[AUTO-LEARNED-SUCCESS]', '').strip()

    # Extract core pattern
    # "Verification failed: file_exists check for 'foo.txt'"
    # → "file_exists:foo.txt"
    if 'Verification failed:' in clean or 'Verify success after' in clean:
        match = re.search(r'(file_exists|grep_text|port_open|command_success).*?[\'"]([^\'"]+)', clean)
        if match:
            return f"verify:{match.group(1)}:{match.group(2)}"

    # "Bash command failed: `command` → error"
    # → "bash:command"
    if 'Bash command failed:' in clean:
        match = re.search(r'`([^`]+)`', clean)
        if match:
            cmd = match.group(1)[:50]  # First 50 chars
            return f"bash:{cmd}"

    # "Edit rejected: Attempted to edit foo.py"
    # → "edit:foo.py"
    if 'Edit rejected:' in clean:
        match = re.search(r'edit ([^\s]+)', clean)
        if match:
            return f"edit:{match.group(1)}"

    # "Agent X failed"
    # → "agent:X"
    if 'Agent' in clean and 'failed' in clean:
        match = re.search(r'Agent (\w+)', clean)
        if match:
            return f"agent:{match.group(1)}"

    # Default: first 50 chars
    return clean[:50]


def consolidate_duplicates(entries):
    """Merge duplicate auto-learned patterns"""
    # Group by pattern
    patterns = defaultdict(list)

    for entry in entries:
        if entry['is_auto']:
            key = extract_pattern_key(entry['content'])
            patterns[key].append(entry)

    # Consolidate each pattern
    consolidated = []
    seen_keys = set()

    for entry in entries:
        if not entry['is_auto']:
            # Keep manual entries as-is
            consolidated.append(entry)
        else:
            key = extract_pattern_key(entry['content'])
            if key in seen_keys:
                # Skip duplicates
                continue

            seen_keys.add(key)
            group = patterns[key]

            if len(group) == 1:
                # Single entry - remove tag, promote to permanent
                entry['content'] = entry['content'].replace('[AUTO-LEARNED-FAILURE] ', '').replace('[AUTO-LEARNED-SUCCESS] ', '')
                entry['raw'] = f"### {entry['timestamp']}\n{entry['content']}\n"
                consolidated.append(entry)
            else:
                # Multiple entries - merge
                first = group[0]
                count = len(group)
                tag = first['tag']

                # Create merged lesson
                merged_content = first['content'].replace(f'[AUTO-LEARNED-{tag}] ', '')
                merged_content = f"{merged_content.strip()} (occurred {count} times)\n"

                merged_entry = {
                    'timestamp': first['timestamp'],
                    'content': merged_content,
                    'is_auto': False,  # Promoted to permanent
                    'tag': None,
                    'raw': f"### {first['timestamp']}\n{merged_content}\n"
                }
                consolidated.append(merged_entry)

    return consolidated


def rebuild_lessons_file(entries):
    """Rebuild lessons.md from consolidated entries"""
    # Extract header (everything before first ###)
    with open(LESSONS_FILE, 'r') as f:
        content = f.read()

    header_match = re.match(r'(.*?)(?=### )', content, re.DOTALL)
    header = header_match.group(1) if header_match else "# The Pain Log (Lessons Learned)\n\n"

    # Rebuild file
    output = header
    for entry in entries:
        output += entry['raw']

    return output


def main():
    """Consolidate auto-learned lessons"""
    if not LESSONS_FILE.exists():
        print("No lessons.md file found")
        return

    # Load lessons
    with open(LESSONS_FILE, 'r') as f:
        content = f.read()

    # Parse entries
    entries = parse_lessons(content)

    # Count auto-learned entries before
    auto_count_before = sum(1 for e in entries if e['is_auto'])

    # Consolidate duplicates
    consolidated = consolidate_duplicates(entries)

    # Count auto-learned entries after
    auto_count_after = sum(1 for e in consolidated if e['is_auto'])

    # Rebuild file
    new_content = rebuild_lessons_file(consolidated)

    # Write back
    with open(LESSONS_FILE, 'w') as f:
        f.write(new_content)

    # Report
    merged_count = auto_count_before - auto_count_after
    if merged_count > 0:
        print(f"✅ Consolidated {merged_count} duplicate auto-learned lessons")
    else:
        print("✅ No duplicate lessons to consolidate")

    return 0


if __name__ == "__main__":
    sys.exit(main())
