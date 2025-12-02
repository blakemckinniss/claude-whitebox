#!/usr/bin/env python3
"""
State Updater Hook v3: PostToolUse hook that updates session state.

This hook fires AFTER every tool call and:
- Tracks files read/edited/created
- Tracks commands succeeded/failed
- Tracks libraries used
- Detects errors and patterns
- Updates domain detection signals

Silent by default - no output unless debugging.
"""

import _lib_path  # noqa: F401
import sys
import json
import re

# Import the state machine
from session_state import (
    load_state, save_state,
    track_file_read, track_file_edit, track_file_create,
    track_command, track_library_used, track_error,
    resolve_error, add_domain_signal, extract_libraries_from_code,
    track_failure, reset_failures,  # v3.1: Sunk cost tracking
    track_batch_tool, clear_pending_file, clear_pending_search,  # v3.2: Batch enforcement
    extract_function_names, add_pending_integration_grep, clear_integration_grep,  # v3.3: Integration blindness
    create_checkpoint, track_feature_file, complete_feature,  # v3.6: Autonomous agent patterns
    add_work_item,  # v3.6: Auto-feature discovery
)

# =============================================================================
# AUTO-FEATURE DISCOVERY (v3.6)
# =============================================================================

def extract_test_failures(output: str) -> list[dict]:
    """Extract test failure information from pytest/jest/etc output.

    Returns list of {test_name, file, description}
    """
    failures = []

    # Pytest patterns
    pytest_fail = re.findall(
        r'FAILED\s+([\w./]+)::(\w+)',
        output
    )
    for file, test in pytest_fail:
        failures.append({
            "test_name": test,
            "file": file,
            "description": f"Fix failing test: {test} in {file}",
            "priority": 80,
        })

    # Jest patterns
    jest_fail = re.findall(
        r'FAIL\s+([\w./]+)\s*\n.*?✕\s+(.+?)(?:\n|$)',
        output,
        re.MULTILINE
    )
    for file, test in jest_fail:
        failures.append({
            "test_name": test,
            "file": file,
            "description": f"Fix failing test: {test} in {file}",
            "priority": 80,
        })

    # Generic test failure patterns
    generic_fail = re.findall(
        r'(?:Error|FAIL|FAILED):\s*(.+?)(?:\n|$)',
        output
    )
    for msg in generic_fail[:3]:  # Limit to 3
        if msg not in [f.get("description", "") for f in failures]:
            failures.append({
                "test_name": "unknown",
                "file": "unknown",
                "description": f"Fix: {msg[:80]}",
                "priority": 70,
            })

    return failures[:5]  # Limit to 5 failures


def extract_todos_from_content(content: str, filepath: str) -> list[dict]:
    """Extract TODO/FIXME items from code content.

    Returns list of {description, file, priority}
    """
    todos = []

    # Match TODO: or FIXME: with optional description
    patterns = [
        (r'#\s*TODO[:\s]+(.+?)(?:\n|$)', 'TODO'),
        (r'//\s*TODO[:\s]+(.+?)(?:\n|$)', 'TODO'),
        (r'#\s*FIXME[:\s]+(.+?)(?:\n|$)', 'FIXME'),
        (r'//\s*FIXME[:\s]+(.+?)(?:\n|$)', 'FIXME'),
    ]

    for pattern, todo_type in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:3]:  # Limit per pattern
            from pathlib import Path
            filename = Path(filepath).name if filepath else "unknown"
            todos.append({
                "description": f"{todo_type}: {match.strip()[:60]} ({filename})",
                "file": filepath,
                "priority": 60 if todo_type == "FIXME" else 50,
            })

    return todos[:5]  # Limit to 5 TODOs per file


# =============================================================================
# TOOL PROCESSORS
# =============================================================================

def process_read(state, tool_input, result):
    """Process Read tool result."""
    filepath = tool_input.get("file_path", "")
    if filepath:
        track_file_read(state, filepath)
        add_domain_signal(state, filepath)

        # Extract libraries from file content if it's code
        content = result.get("output", "")
        if filepath.endswith(('.py', '.js', '.ts')):
            libs = extract_libraries_from_code(content)
            for lib in libs:
                track_library_used(state, lib)

        # v3.6: AUTO-FEATURE DISCOVERY from TODOs in code
        # Only scan code files, not configs or data
        if filepath.endswith(('.py', '.js', '.ts', '.tsx', '.rs', '.go', '.java')):
            todos = extract_todos_from_content(content, filepath)
            for todo in todos:
                add_work_item(
                    state,
                    item_type="todo",
                    source=filepath,
                    description=todo.get("description", "TODO"),
                    priority=todo.get("priority", 50),
                )


def process_edit(state, tool_input, result):
    """Process Edit tool result."""
    filepath = tool_input.get("file_path", "")
    if filepath:
        track_file_edit(state, filepath)

        # v3.6: Track file as part of current feature work
        track_feature_file(state, filepath)

        # Extract libraries from new code
        new_code = tool_input.get("new_string", "")
        if new_code:
            libs = extract_libraries_from_code(new_code)
            for lib in libs:
                track_library_used(state, lib)

            # v3.3: Detect function edits for integration blindness prevention
            # Extract from OLD_STRING (what's being changed), not new_string
            # new_string may contain unrelated functions that appear in replacement text
            if filepath.endswith(('.py', '.js', '.ts', '.tsx', '.rs', '.go')):
                old_code = tool_input.get("old_string", "")
                functions = extract_function_names(old_code)
                for func in functions:
                    add_pending_integration_grep(state, func, filepath)


def detect_stubs_in_content(content: str) -> list[str]:
    """Detect stub patterns in code content."""
    STUB_PATTERNS = [
        ('TODO', 'TODO'),
        ('FIXME', 'FIXME'),
        ('NotImplementedError', 'NotImplementedError'),
        ('raise NotImplementedError', 'NotImplementedError'),
        ('pass  #', 'stub pass'),
        ('...  #', 'ellipsis stub'),
    ]
    found = []
    for pattern, label in STUB_PATTERNS:
        if pattern in content:
            found.append(label)
    return list(set(found))[:3]


def process_write(state, tool_input, result) -> str | None:
    """Process Write tool result. Returns warning message if stubs detected."""
    filepath = tool_input.get("file_path", "")
    warning = None

    if filepath:
        # Check if file existed before (would have been read)
        is_new_file = filepath not in state.files_read
        if is_new_file:
            track_file_create(state, filepath)
        else:
            track_file_edit(state, filepath)

        # v3.6: Track file as part of current feature work
        track_feature_file(state, filepath)

        # Extract libraries
        content = tool_input.get("content", "")
        if content:
            libs = extract_libraries_from_code(content)
            for lib in libs:
                track_library_used(state, lib)

            # Detect stubs in NEW files only (flag for memory)
            if is_new_file:
                stubs = detect_stubs_in_content(content)
                if stubs:
                    from pathlib import Path
                    fname = Path(filepath).name
                    warning = f"⚠️ STUB DETECTED in new file `{fname}`: {', '.join(stubs)}\n   Remember to complete before session ends!"

    return warning


def process_bash(state, tool_input, result):
    """Process Bash tool result."""
    command = tool_input.get("command", "")
    output = result.get("output", "")
    exit_code = result.get("exit_code", 0)
    success = exit_code == 0

    track_command(state, command, success, output)

    # v3.3.1: Track files read via cat/head/tail so gap_detector doesn't false-positive
    if success:
        read_cmds = ["cat ", "head ", "tail ", "less ", "more "]
        if any(command.startswith(cmd) or f" {cmd}" in command for cmd in read_cmds):
            # Extract file paths from command (simple heuristic)
            parts = command.split()
            for part in parts[1:]:  # Skip command name
                if not part.startswith("-") and "/" in part or "." in part:
                    # Looks like a file path
                    track_file_read(state, part)

    # v3.6: AUTONOMOUS CHECKPOINT CREATION after successful git commit
    # This implements the Anthropic pattern for recovery points:
    # https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
    if success and re.search(r'\bgit\s+commit\b', command, re.IGNORECASE):
        # Extract commit hash from output (typically shown after commit)
        commit_hash = ""
        hash_match = re.search(r'\[[\w-]+\s+([a-f0-9]{7,})\]', output)
        if hash_match:
            commit_hash = hash_match.group(1)

        # Extract commit message for checkpoint notes
        msg_match = re.search(r'-m\s+["\']([^"\']+)["\']', command)
        notes = msg_match.group(1)[:50] if msg_match else "commit"

        # Create checkpoint
        create_checkpoint(state, commit_hash=commit_hash, notes=notes)

        # Only complete feature if commit message indicates completion
        # Avoids fragmenting multi-commit features
        completion_keywords = ['fix', 'complete', 'done', 'finish', 'implement', 'resolve', 'close']
        msg_lower = notes.lower()
        is_completion_commit = any(kw in msg_lower for kw in completion_keywords)

        if state.current_feature and is_completion_commit:
            complete_feature(state, status="completed")

    # v3.1: Track failures for sunk cost detection
    approach_sig = f"Bash:{command.split()[0][:20]}" if command.split() else "Bash:unknown"

    # Check for errors in output
    if not success or "error" in output.lower() or "failed" in output.lower():
        # Extract error type
        error_patterns = [
            (r"(\d{3})\s*(Unauthorized|Forbidden|Not Found)", "HTTP error"),
            (r"(ModuleNotFoundError|ImportError)", "Import error"),
            (r"(SyntaxError|TypeError|ValueError)", "Python error"),
            (r"(ENOENT|EACCES|EPERM)", "Filesystem error"),
            (r"(connection refused|timeout)", "Network error"),
        ]

        error_type = "Command error"
        for pattern, etype in error_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                error_type = etype
                break

        if not success:
            track_error(state, error_type, output[:500])
            track_failure(state, approach_sig)  # v3.1

    # Check if error was resolved (success after previous failure)
    if success and state.errors_unresolved:
        reset_failures(state)  # v3.1: Reset on success
        # If similar command succeeded, might have resolved the error
        for error in state.errors_unresolved[:]:
            if any(word in command.lower() for word in error.get("type", "").lower().split()):
                resolve_error(state, error.get("type", ""))

    # v3.6: AUTO-FEATURE DISCOVERY from test failures
    # Extract failing tests and add them to work queue
    if "pytest" in command or "npm test" in command or "jest" in command or "cargo test" in command:
        failures = extract_test_failures(output)
        for failure in failures:
            add_work_item(
                state,
                item_type="test_failure",
                source=failure.get("file", "tests"),
                description=failure.get("description", "Fix test failure"),
                priority=failure.get("priority", 80),
            )


def process_glob(state, tool_input, result):
    """Process Glob tool result."""
    pattern = tool_input.get("pattern", "")
    add_domain_signal(state, pattern)


def process_grep(state, tool_input, result):
    """Process Grep tool result."""
    pattern = tool_input.get("pattern", "")
    add_domain_signal(state, pattern)


def process_task(state, tool_input, result):
    """Process Task tool result."""
    prompt = tool_input.get("prompt", "")
    add_domain_signal(state, prompt[:200])


# =============================================================================
# MAIN
# =============================================================================

PROCESSORS = {
    "Read": process_read,
    "Edit": process_edit,
    "Write": process_write,
    "Bash": process_bash,
    "Glob": process_glob,
    "Grep": process_grep,
    "Task": process_task,
}


def main():
    """PostToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    result = input_data.get("tool_result", {})

    if not tool_name:
        print(json.dumps({}))
        sys.exit(0)

    # Load state
    state = load_state()

    # Update tool count
    state.tool_counts[tool_name] = state.tool_counts.get(tool_name, 0) + 1

    # v3.2: Track batch tool usage
    # Note: tools_in_message would ideally come from hook context
    # For now, we track single vs batched based on tool frequency patterns
    # The PreToolUse hook (batch_intercept) handles the actual blocking
    track_batch_tool(state, tool_name, tools_in_message=1)  # Conservative: assume 1

    # Clear pending items when they're addressed
    if tool_name == "Read":
        filepath = tool_input.get("file_path", "")
        if filepath:
            clear_pending_file(state, filepath)
    elif tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        if pattern:
            clear_pending_search(state, pattern)
            clear_integration_grep(state, pattern)  # v3.3: Clear integration blindness
    elif tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        if pattern:
            clear_pending_search(state, pattern)
    elif tool_name == "Bash":
        # v3.3.1: Clear state when equivalent commands run via Bash
        command = tool_input.get("command", "")

        # Clear integration greps when grep/rg run via Bash
        if "grep " in command or command.startswith("grep") or "rg " in command:
            # Extract patterns from grep command - look for quoted or unquoted patterns
            patterns = re.findall(r'grep[^\|]*?["\']([^"\']+)["\']', command)
            patterns += re.findall(r"grep\s+(?:-\w+\s+)*(\w+)", command)
            for pattern in patterns:
                if len(pattern) > 3:  # Skip short patterns like -r, -n
                    clear_integration_grep(state, pattern)
                    clear_pending_search(state, pattern)

        # Clear pending_files when cat/head/tail/less run via Bash
        read_cmds = ["cat ", "head ", "tail ", "less ", "more "]
        if any(cmd in command for cmd in read_cmds):
            parts = command.split()
            for part in parts:
                if not part.startswith("-") and ("/" in part or "." in part):
                    clear_pending_file(state, part)

        # Clear pending_searches when find/fd run via Bash
        if "find " in command or command.startswith("find") or "fd " in command:
            # Extract patterns from find -name "pattern"
            name_patterns = re.findall(r'-name\s+["\']?([^"\']+)["\']?', command)
            for pattern in name_patterns:
                clear_pending_search(state, pattern)

    # Process tool-specific updates
    processor = PROCESSORS.get(tool_name)
    warning_message = None
    if processor:
        try:
            result_val = processor(state, tool_input, result)
            # process_write returns a warning string if stubs detected
            if isinstance(result_val, str):
                warning_message = result_val
        except Exception as e:
            # Log error to stderr and state for debugging (don't break the hook)
            import sys as _sys
            print(f"[state_updater] Processor error for {tool_name}: {e}", file=_sys.stderr)
            track_error(state, "hook_processor_error", f"{tool_name}: {str(e)[:200]}")

    # Save state
    save_state(state)

    # Output warning if stubs detected in new file
    if warning_message:
        print(json.dumps({"additionalContext": warning_message}))
    else:
        print(json.dumps({}))
    sys.exit(0)


if __name__ == "__main__":
    main()
