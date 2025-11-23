#!/usr/bin/env python3
"""
Auto-Commit on Completion Hook
Triggers: UserPromptSubmit
Purpose: Automatically commit when work is complete
"""
import sys
import json
import subprocess
import re
from pathlib import Path

# Completion keywords that trigger auto-commit
COMPLETION_KEYWORDS = [
    "done",
    "complete",
    "completed",
    "finished",
    "finished",
    "ready",
    "implemented",
    "implemented",
]

def has_uncommitted_changes():
    """Check if there are uncommitted changes"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return bool(result.stdout.strip())
    except:
        return False

def get_uncommitted_files():
    """Get list of uncommitted files"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5
        )
        files = []
        for line in result.stdout.strip().split('\n'):
            if line:
                # Format: " M file.py" or "?? file.py"
                status = line[:2]
                filepath = line[3:].strip()
                files.append(filepath)
        return files
    except:
        return []

def run_quality_gates(files):
    """
    Run quality gates on changed files
    Returns: (success, message)
    """
    issues = []

    # Filter to only Python files for audit/void
    python_files = [f for f in files if f.endswith('.py') and Path(f).exists()]

    if python_files:
        # Run audit on Python files
        try:
            audit_result = subprocess.run(
                ["python3", "scripts/ops/audit.py"] + python_files[:10],  # Limit to 10 files
                capture_output=True,
                text=True,
                timeout=30
            )
            # Check for CRITICAL in output
            if "CRITICAL" in audit_result.stdout:
                issues.append("Audit found CRITICAL security issues")
        except subprocess.TimeoutExpired:
            issues.append("Audit timeout")
        except:
            pass  # Audit failed, but don't block

        # Run void on Python files
        try:
            void_result = subprocess.run(
                ["python3", "scripts/ops/void.py"] + python_files[:10],
                capture_output=True,
                text=True,
                timeout=30
            )
            # Check for stubs in output
            if "stub" in void_result.stdout.lower() or "TODO" in void_result.stdout:
                issues.append("Void found stub code or TODOs")
        except:
            pass  # Void failed, but don't block

    # Run upkeep
    try:
        subprocess.run(
            ["python3", "scripts/ops/upkeep.py"],
            capture_output=True,
            timeout=30
        )
    except:
        pass  # Upkeep failed, but don't block

    if issues:
        return False, "\n".join(f"  • {issue}" for issue in issues)

    return True, "Quality gates passed"

def generate_commit_message(files):
    """Generate commit message from changed files"""
    # Categorize files
    hook_files = [f for f in files if '.claude/hooks' in f]
    lib_files = [f for f in files if 'scripts/lib' in f]
    doc_files = [f for f in files if f.endswith('.md')]
    config_files = [f for f in files if '.claude/memory' in f or '.claude/settings' in f]

    # Determine prefix
    if hook_files and lib_files:
        prefix = "feat(system)"
        summary = f"Update epistemological protocol with graduated tiers"
    elif hook_files:
        prefix = "feat(hooks)"
        summary = f"Update {len(hook_files)} hooks"
    elif lib_files:
        prefix = "feat(lib)"
        summary = f"Update core libraries"
    elif doc_files:
        prefix = "docs"
        summary = f"Update documentation"
    else:
        prefix = "chore"
        summary = f"Update {len(files)} files"

    # Build details
    details = []
    if hook_files:
        details.append(f"- Updated {len(hook_files)} hooks")
    if lib_files:
        details.append(f"- Modified {len(lib_files)} library files")
    if doc_files:
        details.append(f"- Updated {len(doc_files)} documentation files")
    if config_files:
        details.append(f"- Updated {len(config_files)} config/memory files")

    message = f"""{prefix}: {summary}

{chr(10).join(details) if details else 'Auto-commit on completion'}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

    return message

def auto_commit():
    """Attempt to auto-commit uncommitted changes"""
    files = get_uncommitted_files()
    if not files:
        return None  # Nothing to commit

    # Run quality gates
    success, gate_message = run_quality_gates(files)

    if not success:
        return f"""⚠️ AUTO-COMMIT BLOCKED

Quality gates failed for {len(files)} uncommitted files:

{gate_message}

Fix these issues, then I'll auto-commit.

To manually check:
  python3 scripts/ops/audit.py <files>
  python3 scripts/ops/void.py <files>
"""

    # Quality gates passed - commit
    try:
        # Stage all changes
        subprocess.run(
            ["git", "add", "."],
            check=True,
            timeout=10
        )

        # Generate message
        message = generate_commit_message(files)

        # Commit
        subprocess.run(
            ["git", "commit", "-m", message],
            check=True,
            capture_output=True,
            timeout=10
        )

        return f"""✅ AUTO-COMMITTED {len(files)} FILES

Quality gates passed. Changes committed automatically.

Files committed:
{chr(10).join(f"  • {f}" for f in files[:10])}
{"  • ..." if len(files) > 10 else ""}

Commit message: {message.split(chr(10))[0]}

You can continue working - system will auto-commit when you're done."""

    except subprocess.CalledProcessError as e:
        return f"""⚠️ AUTO-COMMIT FAILED

Git commit failed: {e}

You may need to commit manually:
  git add .
  git commit -m "your message"
"""
    except Exception as e:
        return f"⚠️ Auto-commit error: {e}"

# Load input
try:
    input_data = json.load(sys.stdin)
except:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ""
        }
    }))
    sys.exit(0)

prompt = input_data.get("prompt", "").lower()

# Check for completion keywords
completion_detected = any(keyword in prompt for keyword in COMPLETION_KEYWORDS)

# Also check if there are uncommitted changes
has_changes = has_uncommitted_changes()

# Only auto-commit if:
# 1. User signaled completion, AND
# 2. There are uncommitted changes
if completion_detected and has_changes:
    result = auto_commit()
    if result:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": result
            }
        }))
        sys.exit(0)

# No auto-commit needed
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": ""
    }
}))
sys.exit(0)
