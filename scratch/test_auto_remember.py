#!/usr/bin/env python3
"""Test the auto_remember.py hook regex patterns."""
import re


def extract_memory_triggers(text: str) -> list[str]:
    """Extract remember.py commands from Memory Trigger suggestions."""
    # Pattern that handles markdown formatting (**, *, emojis) between "Memory Trigger" and the command
    pattern = r'Memory Trigger.*?`(remember\.py add \w+ ".*?")`'

    commands = []
    matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    for match in matches:
        command = match.group(1)
        if command not in commands:  # Dedup
            commands.append(command)

    return commands


# Test cases
test_cases = [
    # With backticks and bold
    '''**🐘 Memory Trigger:** `remember.py add lessons "Test lesson 1"`''',

    # With emoji and italic
    '''*🐘 Memory Trigger:* `remember.py add decisions "Test decision"`''',

    # Without backticks
    '''Memory Trigger: remember.py add context "Test context"''',

    # Multiple in one message
    '''
    Some response text here.

    **🐘 Memory Trigger:** `remember.py add lessons "Lesson A"`
    **🐘 Memory Trigger:** `remember.py add decisions "Decision B"`
    ''',

    # Real example from actual output
    '''
    ### 🚦 Status & Direction
    *   **Next Steps:** Test the pattern in your next session
    *   **🐘 Memory Trigger:** `remember.py add lessons "Implemented Command Suggestion Mode"`
    ''',
]

print("Testing auto_remember.py regex patterns:\n")

for i, test in enumerate(test_cases, 1):
    print(f"Test case {i}:")
    print(f"Input: {test.strip()[:80]}...")
    commands = extract_memory_triggers(test)
    print(f"Extracted: {commands}")
    print()

# Test real-world example
real_example = '''
**Stats:**
- 52 files changed
- 5,547 insertions, 21 deletions

---

### 🚦 Status & Direction
*   **Next Steps:** Repository is live and ready for collaboration
*   **Priority Gauge:** 100 (Mission complete)
*   **Areas of Concern:** None - all changes committed and pushed
*   **⚖️ Trade-offs:** None
*   **🐘 Memory Trigger:** `remember.py add decisions "Published claude-whitebox as public repository at github.com/blakemckinniss/claude-whitebox"`
*   **🔗 Recommended Protocols:**
    *   *Next:* Consider adding README.md for public visibility
    *   *Quality:* 🛡️ `scripts/ops/audit.py` on critical files before future commits
'''

print("Real-world example:")
commands = extract_memory_triggers(real_example)
print(f"Extracted: {commands}")
print(f"Count: {len(commands)}")
