#!/usr/bin/env python3
"""Test debt_tracker.py hook with synthetic transcript."""
import json
import subprocess
import tempfile
from pathlib import Path

# Create synthetic transcript with Write calls containing debt
transcript = [
    {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Write",
                    "input": {
                        "file_path": "/tmp/test_auth.py",
                        "content": """def authenticate(user):
    # TODO: Add proper password validation
    # FIXME: This is vulnerable to timing attacks
    pass

def verify_token(token):
    # HACK: Temporary workaround for JWT validation
    ...

def logout(session_id):
    # XXX: Need to implement session cleanup
    raise NotImplementedError("Session cleanup not yet implemented")
"""
                    }
                },
                {
                    "type": "tool_use",
                    "name": "Edit",
                    "input": {
                        "file_path": "/tmp/test_database.py",
                        "old_string": "pass",
                        "new_string": """# TODO: Add connection pooling
conn = create_connection()"""
                    }
                }
            ]
        }
    }
]

# Write transcript to temp file
with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
    for entry in transcript:
        f.write(json.dumps(entry) + '\n')
    transcript_path = f.name

# Create hook input
hook_input = {
    "transcript_path": transcript_path,
    "cwd": str(Path.cwd()),
    "stop_hook_active": False
}

# Run hook
result = subprocess.run(
    ["python3", ".claude/hooks/debt_tracker.py"],
    input=json.dumps(hook_input),
    capture_output=True,
    text=True
)

print("=== HOOK OUTPUT ===")
print(result.stdout)

if result.stderr:
    print("\n=== ERRORS ===")
    print(result.stderr)

print(f"\n=== EXIT CODE: {result.returncode} ===")

# Check ledger
ledger_path = Path(".claude/memory/debt_ledger.jsonl")
if ledger_path.exists():
    print("\n=== LEDGER CONTENTS (last 10 entries) ===")
    with open(ledger_path) as f:
        lines = f.readlines()
        for line in lines[-10:]:
            entry = json.loads(line)
            print(f"  {entry['type']:15} | {entry['file']:30} | {entry['context'][:50]}")
else:
    print("\n⚠️  Ledger file not created")

# Cleanup
Path(transcript_path).unlink()
