#!/usr/bin/env python3
"""
EXPANDED Epistemology Library: Confidence & Risk with Engineering Best Practices
Adds nuanced rewards for good practices and penalties for anti-patterns
"""

# NEW CONFIDENCE GAINS - Engineering Best Practices
CONFIDENCE_GAINS_EXPANDED = {
    # Existing high-value actions
    "user_question": 25,
    "web_search": 20,
    "use_script": 20,
    # Existing medium-value actions
    "probe_api": 15,
    "verify_success": 15,
    "use_script_smith": 15,
    "run_audit": 15,
    # Existing low-value actions
    "read_file_first": 10,
    "read_file_repeat": 2,
    "grep_glob": 5,
    # Existing meta-actions
    "use_researcher": 25,
    "use_council": 10,
    "run_tests": 30,

    # NEW: Git operations (state awareness)
    "git_commit": 10,        # Shows task completion, adds finality
    "git_status": 5,         # State awareness, checking before acting
    "git_log": 5,            # Historical context
    "git_diff": 10,          # Understanding changes before committing
    "git_add": 5,            # Staging changes deliberately

    # NEW: Documentation reading (explicit knowledge)
    "read_md_first": 15,     # First time reading any .md file
    "read_md_repeat": 5,     # Re-reading .md (higher than code re-read)
    "read_claude_md": 20,    # Reading project constitution (CLAUDE.md)
    "read_readme": 15,       # Reading project overview (README.md)

    # NEW: Technical debt cleanup (proactive quality)
    "fix_todo": 10,          # Fixing TODO/FIXME comments
    "remove_stub": 15,       # Completing incomplete code (pass, ..., NotImplementedError)
    "reduce_complexity": 10, # Reducing cyclomatic complexity (detected by audit.py)

    # NEW: Testing (quality assurance)
    "write_tests": 15,       # Creating new test files
    "add_test_coverage": 20, # Adding tests to existing test file
}

# NEW CONFIDENCE PENALTIES - Anti-Patterns
CONFIDENCE_PENALTIES_EXPANDED = {
    # Existing pattern violations
    "hallucination": -20,
    "falsehood": -25,
    "insanity": -15,
    "loop": -15,
    # Existing tier violations
    "tier_violation": -10,
    # Existing failures
    "tool_failure": -10,
    "user_correction": -20,

    # NEW: Context blindness (severe)
    "edit_before_read": -20,      # Editing file without reading it first
    "modify_unexamined": -25,     # Production write without prior Read (CRITICAL)

    # NEW: User context ignorance
    "repeat_instruction": -15,    # Telling user to do something already done
    # ignore_correction already exists as "user_correction"

    # NEW: Testing negligence
    "skip_test_easy": -15,        # Not testing when feature is easily testable
    "claim_done_no_test": -20,    # Claiming "done" without test verification

    # NEW: Security/quality shortcuts (critical)
    "modify_no_audit": -25,       # Production modification without audit.py
    "commit_no_upkeep": -15,      # Git commit without upkeep.py
    "write_stub": -10,            # Writing stub code (already blocked by ban_stubs.py)
}


# DETECTION LOGIC EXAMPLES
# These would be integrated into update_confidence() function

def detect_git_operation(command: str) -> tuple[str, int]:
    """Detect git operations and return boost key and amount"""
    command = command.strip()

    if command.startswith("git commit"):
        return ("git_commit", CONFIDENCE_GAINS_EXPANDED["git_commit"])
    elif command.startswith("git status"):
        return ("git_status", CONFIDENCE_GAINS_EXPANDED["git_status"])
    elif command.startswith("git diff"):
        return ("git_diff", CONFIDENCE_GAINS_EXPANDED["git_diff"])
    elif command.startswith("git log"):
        return ("git_log", CONFIDENCE_GAINS_EXPANDED["git_log"])
    elif command.startswith("git add"):
        return ("git_add", CONFIDENCE_GAINS_EXPANDED["git_add"])

    return (None, 0)


def detect_documentation_read(file_path: str, read_files: dict) -> tuple[str, int]:
    """Detect documentation file reads and return boost key and amount"""
    if not file_path.endswith(".md"):
        return (None, 0)

    # Check if already read (diminishing returns)
    if file_path in read_files:
        return ("read_md_repeat", CONFIDENCE_GAINS_EXPANDED["read_md_repeat"])

    # Special cases for important docs
    if file_path.endswith("CLAUDE.md"):
        return ("read_claude_md", CONFIDENCE_GAINS_EXPANDED["read_claude_md"])
    elif file_path.endswith("README.md"):
        return ("read_readme", CONFIDENCE_GAINS_EXPANDED["read_readme"])
    else:
        # Generic .md file
        return ("read_md_first", CONFIDENCE_GAINS_EXPANDED["read_md_first"])


def detect_test_file_write(file_path: str, operation: str) -> tuple[str, int]:
    """Detect test file creation/modification and return boost key and amount"""
    import os

    filename = os.path.basename(file_path)

    # Check if test file
    is_test = (
        filename.startswith("test_") or
        filename.endswith("_test.py") or
        "/tests/" in file_path
    )

    if not is_test:
        return (None, 0)

    if operation == "Write":  # New test file
        return ("write_tests", CONFIDENCE_GAINS_EXPANDED["write_tests"])
    elif operation == "Edit":  # Adding to existing test file
        return ("add_test_coverage", CONFIDENCE_GAINS_EXPANDED["add_test_coverage"])

    return (None, 0)


def detect_debt_cleanup(old_content: str, new_content: str) -> list[tuple[str, int]]:
    """
    Compare old vs new file content to detect debt cleanup
    Returns list of (boost_key, boost_amount) tuples
    """
    import re

    boosts = []

    # Count TODOs/FIXMEs removed
    old_todos = len(re.findall(r'#\s*(TODO|FIXME|HACK|XXX)', old_content))
    new_todos = len(re.findall(r'#\s*(TODO|FIXME|HACK|XXX)', new_content))

    if new_todos < old_todos:
        todos_fixed = old_todos - new_todos
        # +10% per TODO fixed (cap at 3 TODOs = 30%)
        for _ in range(min(todos_fixed, 3)):
            boosts.append(("fix_todo", CONFIDENCE_GAINS_EXPANDED["fix_todo"]))

    # Count stubs removed
    stub_patterns = [r'\bpass\b', r'\.\.\.', r'NotImplementedError']
    old_stubs = sum(len(re.findall(p, old_content)) for p in stub_patterns)
    new_stubs = sum(len(re.findall(p, new_content)) for p in stub_patterns)

    if new_stubs < old_stubs:
        stubs_removed = old_stubs - new_stubs
        # +15% per stub removed (cap at 2 stubs = 30%)
        for _ in range(min(stubs_removed, 2)):
            boosts.append(("remove_stub", CONFIDENCE_GAINS_EXPANDED["remove_stub"]))

    return boosts


# EXPANDED update_confidence() LOGIC
# This shows how the existing function would be modified

def update_confidence_EXPANDED_LOGIC(session_id, tool_name, tool_input, turn, reason, state):
    """
    PSEUDO-CODE showing expanded detection logic
    This would replace the existing update_confidence() function
    """
    boost = 0
    boost_reasons = []

    # === EXISTING LOGIC ===
    if tool_name == "Read":
        file_path = tool_input.get("file_path", "")

        # NEW: Check if .md file first
        doc_key, doc_boost = detect_documentation_read(file_path, state.get("read_files", {}))
        if doc_key:
            boost = doc_boost
            boost_reasons.append(doc_key)
        else:
            # Existing code file logic
            if file_path in state.get("read_files", {}):
                boost = CONFIDENCE_GAINS_EXPANDED["read_file_repeat"]
                boost_reasons.append("read_file_repeat")
            else:
                boost = CONFIDENCE_GAINS_EXPANDED["read_file_first"]
                boost_reasons.append("read_file_first")

        # Track file read
        if "read_files" not in state:
            state["read_files"] = {}
        state["read_files"][file_path] = state["read_files"].get(file_path, 0) + 1

    elif tool_name == "Bash":
        command = tool_input.get("command", "")

        # NEW: Check git operations first
        git_key, git_boost = detect_git_operation(command)
        if git_key:
            boost = git_boost
            boost_reasons.append(git_key)
        # Existing verification/research/probe detection
        elif "scripts/ops/verify.py" in command or "/verify " in command:
            boost = CONFIDENCE_GAINS_EXPANDED["verify_success"]
            boost_reasons.append("verify_success")
        elif "scripts/ops/research.py" in command or "/research" in command:
            boost = CONFIDENCE_GAINS_EXPANDED["web_search"]
            boost_reasons.append("web_search")
        elif "scripts/ops/probe.py" in command or "/probe" in command:
            boost = CONFIDENCE_GAINS_EXPANDED["probe_api"]
            boost_reasons.append("probe_api")
        elif "scripts/ops/audit.py" in command:
            boost = CONFIDENCE_GAINS_EXPANDED["run_audit"]
            boost_reasons.append("run_audit")
        elif "pytest" in command or "python -m pytest" in command:
            boost = CONFIDENCE_GAINS_EXPANDED["run_tests"]
            boost_reasons.append("run_tests")
        elif "scripts/ops/council.py" in command:
            boost = CONFIDENCE_GAINS_EXPANDED["use_council"]
            boost_reasons.append("use_council")
        else:
            boost = CONFIDENCE_GAINS_EXPANDED["use_script"]
            boost_reasons.append("use_script")

    elif tool_name == "Write":
        file_path = tool_input.get("file_path", "")

        # NEW: Check if writing test file
        test_key, test_boost = detect_test_file_write(file_path, "Write")
        if test_key:
            boost = test_boost
            boost_reasons.append(test_key)

    elif tool_name == "Edit":
        file_path = tool_input.get("file_path", "")

        # NEW: Check if editing test file
        test_key, test_boost = detect_test_file_write(file_path, "Edit")
        if test_key:
            boost = test_boost
            boost_reasons.append(test_key)

        # NEW: Check for debt cleanup (requires old/new content comparison)
        # This would need to be done in a PostToolUse hook that has access to file diffs
        # For now, just note the location for future implementation

    elif tool_name == "Task":
        subagent_type = tool_input.get("subagent_type", "")
        if subagent_type == "researcher":
            boost = CONFIDENCE_GAINS_EXPANDED["use_researcher"]
            boost_reasons.append("use_researcher")
        elif subagent_type == "script-smith":
            boost = CONFIDENCE_GAINS_EXPANDED["use_script_smith"]
            boost_reasons.append("use_script_smith")
        else:
            boost = 10  # Generic delegation
            boost_reasons.append("delegation")

    elif tool_name in ["Grep", "Glob"]:
        boost = CONFIDENCE_GAINS_EXPANDED["grep_glob"]
        boost_reasons.append("grep_glob")

    elif tool_name == "WebSearch":
        boost = CONFIDENCE_GAINS_EXPANDED["web_search"]
        boost_reasons.append("web_search")

    # Update confidence (cap at 100)
    old_confidence = state["confidence"]
    new_confidence = min(100, old_confidence + boost)
    state["confidence"] = new_confidence

    # Record evidence with detailed reasons
    evidence_entry = {
        "turn": turn,
        "tool": tool_name,
        "target": str(tool_input.get("file_path") or tool_input.get("query") or tool_input.get("command", ""))[:100],
        "boost": boost,
        "reasons": boost_reasons,  # NEW: Track specific boost reasons
        "timestamp": "...",
    }

    return new_confidence, boost


# SUMMARY OF CHANGES TO PRODUCTION FILES

"""
FILES TO MODIFY:

1. scripts/lib/epistemology.py
   - Replace CONFIDENCE_GAINS with CONFIDENCE_GAINS_EXPANDED
   - Replace CONFIDENCE_PENALTIES with CONFIDENCE_PENALTIES_EXPANDED
   - Add helper functions: detect_git_operation(), detect_documentation_read(), detect_test_file_write()
   - Update update_confidence() function with expanded logic above

2. .claude/hooks/evidence_tracker.py
   - No changes needed (already calls update_confidence())
   - Will automatically pick up new patterns

3. .claude/hooks/tier_gate.py (EXPAND)
   - When blocking Edit due to file not read, also apply "edit_before_read" penalty
   - When blocking production Write without audit, apply "modify_no_audit" penalty

4. .claude/hooks/debt_cleanup_detector.py (NEW)
   - PostToolUse hook for Edit/Write tools
   - Reads old + new file content
   - Calls detect_debt_cleanup()
   - Applies multiple boosts for debt cleanup

5. .claude/hooks/command_prerequisite_gate.py (EXPAND)
   - When blocking git commit without upkeep, apply "commit_no_upkeep" penalty
   - When blocking production write without audit, apply "modify_no_audit" penalty

6. CLAUDE.md
   - Update § Epistemological Protocol with new confidence values
   - Add table of all gains/penalties with examples
"""


if __name__ == "__main__":
    # Test detection functions
    print("=== Git Operation Detection ===")
    for cmd in ["git commit -m 'test'", "git status", "git diff", "git log", "git add .", "ls"]:
        key, boost = detect_git_operation(cmd)
        key_str = key if key else "no_match"
        print(f"{cmd:30} -> {key_str:20} (+{boost}%)")

    print("\n=== Documentation Read Detection ===")
    for path in ["CLAUDE.md", "README.md", "docs/guide.md", "src/main.py"]:
        key, boost = detect_documentation_read(path, {})
        key_str = key if key else "no_match"
        print(f"{path:30} -> {key_str:20} (+{boost}%)")

    print("\n=== Test File Write Detection ===")
    for path in ["test_auth.py", "tests/test_api.py", "auth_test.py", "src/auth.py"]:
        for op in ["Write", "Edit"]:
            key, boost = detect_test_file_write(path, op)
            key_str = key if key else "no_match"
            print(f"{path:30} ({op:5}) -> {key_str:20} (+{boost}%)")

    print("\n=== Debt Cleanup Detection ===")
    old = """
# TODO: Fix this
def foo():
    pass  # Stub

# FIXME: Handle error
def bar():
    ...
"""
    new = """
def foo():
    return 42  # Implemented

def bar():
    try:
        return process()
    except Exception as e:
        log_error(e)
"""
    boosts = detect_debt_cleanup(old, new)
    print(f"Boosts detected: {boosts}")
    print(f"Total boost: +{sum(b[1] for b in boosts)}%")
