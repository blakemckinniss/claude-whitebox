#!/bin/bash

# Create test transcript
TRANSCRIPT=$(mktemp --suffix=.jsonl)
cat > "$TRANSCRIPT" << 'INNER_EOF'
{"type":"user","message":{"content":"I need to migrate our authentication system from JWT to OAuth2. What do you recommend?"}}
{"type":"assistant","message":{"content":[{"type":"text","text":"OAuth2 is a good choice for improved security. Let me help you plan the migration."}]}}
{"type":"user","message":{"content":"Can we do this incrementally?"}}
{"type":"assistant","message":{"content":[{"type":"text","text":"Yes, we can implement a dual-authentication strategy."}]}}
INNER_EOF

echo "Test transcript: $TRANSCRIPT"

# Create hook input
HOOK_INPUT=$(cat << INNER_EOF2
{
  "transcript_path": "$TRANSCRIPT",
  "cwd": "$(pwd)",
  "stop_hook_active": false
}
INNER_EOF2
)

echo "$HOOK_INPUT" | python3 -u .claude/hooks/session_digest.py 2>&1

echo "Exit code: $?"

# Check if digest was created
SESSION_ID=$(basename "$TRANSCRIPT" .jsonl)
DIGEST_PATH=".claude/memory/session_digests/${SESSION_ID}.json"

if [ -f "$DIGEST_PATH" ]; then
    echo "✓ Digest created at $DIGEST_PATH"
    cat "$DIGEST_PATH"
else
    echo "✗ No digest created"
fi

rm "$TRANSCRIPT"
