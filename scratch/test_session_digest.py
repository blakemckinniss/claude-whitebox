#!/usr/bin/env python3
"""Test session_digest.py hook with synthetic transcript."""
import json
import subprocess
import tempfile
from pathlib import Path

# Create synthetic transcript with realistic conversation
transcript = [
    {
        "type": "user",
        "message": {
            "content": "I need to migrate our authentication system from JWT to OAuth2. What do you recommend?"
        }
    },
    {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "text",
                    "text": "OAuth2 is a good choice for improved security. Let me help you plan the migration. First, let's use the council to evaluate this decision."
                }
            ]
        }
    },
    {
        "type": "user",
        "message": {
            "content": "Yes, but I'm worried about breaking existing API clients. Can we do this incrementally?"
        }
    },
    {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "text",
                    "text": "Absolutely. We can implement a dual-authentication strategy. Here's the plan: 1) Add OAuth2 support alongside JWT, 2) Deprecate JWT with a 6-month notice, 3) Migrate clients incrementally."
                },
                {
                    "type": "tool_use",
                    "name": "Write",
                    "input": {
                        "file_path": "/tmp/auth_migration_plan.md",
                        "content": "# OAuth2 Migration Plan\n## Phase 1: Dual Authentication\n## Phase 2: Client Migration"
                    }
                }
            ]
        }
    },
    {
        "type": "user",
        "message": {
            "content": "Good plan. Let's start with implementing OAuth2 in the auth module."
        }
    },
    {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "text",
                    "text": "I'll create the OAuth2 authentication handler with support for authorization code flow and client credentials."
                }
            ]
        }
    }
]

# Write transcript to temp file
with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, prefix='test_session_') as f:
    for entry in transcript:
        f.write(json.dumps(entry) + '\n')
    transcript_path = f.name

print(f"Test transcript: {transcript_path}")

# Create hook input
hook_input = {
    "transcript_path": transcript_path,
    "cwd": str(Path.cwd()),
    "stop_hook_active": False
}

# Run hook
print("\n=== RUNNING SESSION DIGEST HOOK ===")
result = subprocess.run(
    ["python3", ".claude/hooks/session_digest.py"],
    input=json.dumps(hook_input),
    capture_output=True,
    text=True,
    timeout=45
)

print("=== HOOK OUTPUT ===")
print(result.stdout)

if result.stderr:
    print("\n=== ERRORS ===")
    print(result.stderr)

print(f"\n=== EXIT CODE: {result.returncode} ===")

# Check digest file
session_id = Path(transcript_path).stem
digest_path = Path(f".claude/memory/session_digests/{session_id}.json")

if digest_path.exists():
    print(f"\n=== DIGEST FILE: {digest_path} ===")
    with open(digest_path) as f:
        digest = json.load(f)
        print(json.dumps(digest, indent=2))
else:
    print(f"\n⚠️  Digest file not created at {digest_path}")
    print("This is expected if OPENROUTER_API_KEY is not set")

# Cleanup
Path(transcript_path).unlink()
print(f"\n✓ Cleaned up test transcript")
