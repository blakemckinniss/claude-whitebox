# Claude Code Hooks Reference

## Hook Lifecycle Events (6 Total)

| Event | When | Latency | Use Case |
|-------|------|---------|----------|
| **SessionStart** | Once at session start | <200ms | Init state, load memory, display stats |
| **UserPromptSubmit** | After user prompt, before Claude responds | <100ms | Context injection (NO network calls) |
| **PreToolUse** | Before ANY tool executes | ~350ms | Gating, authorization, security (Groq OK) |
| **PostToolUse** | After tool completes | <50ms | Telemetry, evidence gathering |
| **Stop** | User interrupts (Ctrl+C) | <100ms | Cleanup, warnings |
| **SessionEnd** | End of session | <1000ms | Final cleanup, auto-commit |

## Input Format (JSON via stdin)

```json
{
  "session_id": "uuid",
  "hook_event": "PreToolUse",
  "timestamp": "2025-11-25T10:30:45.123Z",
  "turn_number": 5,

  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "file_contents": "..."
  },

  "transcript_path": "/path/to/transcript.txt",
  "user_message": "user's question"
}
```

### Key Fields by Event

| Field | Events | Purpose |
|-------|--------|---------|
| `tool_name` | PreToolUse, PostToolUse | Tool being called |
| `tool_input` | PreToolUse | Tool parameters |
| `transcript_path` | Most | Session transcript file |
| `exit_code` | PostToolUse | 0=success, >0=failure |
| `user_message` | UserPromptSubmit | User's actual prompt |

## Output Format (JSON to stdout)

### ALLOW (default - proceed silently)
```json
{"hookSpecificOutput": {"hookEventName": "PreToolUse"}}
```

### BLOCK (deny execution)
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "decision": "block",
    "reason": "Production write requires 71% confidence",
    "additionalContext": "Build confidence with /research, /probe, /verify"
  }
}
```

### WARN (proceed with warning)
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "decision": "warn",
    "additionalContext": "File not read yet. Consider opening first."
  }
}
```

## Environment Variables

Claude Code provides:
```bash
CLAUDE_SESSION_ID=uuid
CLAUDE_PROJECT_DIR=/path/to/project
CLAUDE_TURN_NUMBER=5
CLAUDE_HOOK_EVENT=PreToolUse
```

**CRITICAL:** Claude Code does NOT auto-load `.env` into hook processes.
- If you need secrets, read `.env` explicitly in hook code
- Priority: `.env` file > `os.environ` (shell may have stale values)

## Configuration (settings.json)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/my_hook.py",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

### Matcher Patterns
- `"Write"` - exact match
- `"(Read|Write|Edit)"` - regex OR
- `".*"` - all tools
- `"mcp__.*"` - all MCP tools

## Best Practices

### 1. Input Validation
```python
try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, EOFError):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "Unknown"}}))
    return
```

### 2. Fail Open (graceful degradation)
```python
try:
    # Your logic
except Exception as e:
    logging.error(f"Hook error: {e}")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
```

### 3. File-Based State (no in-process memory)
```python
STATE_FILE = Path(__file__).parent.parent / "memory" / "my_state.json"

def load_state():
    if STATE_FILE.exists():
        return json.load(open(STATE_FILE))
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)
```

### 4. Reading Secrets from .env (correct priority)
```python
def get_secret(key_name: str) -> str:
    """Read secret from .env file first, fall back to os.environ.

    Why .env first? Shell environment may have stale values from old sessions.
    Claude Code loads env at startup and they persist. The .env file is
    the source of truth since users update it directly.
    """
    # Walk up to find .env (source of truth)
    current = Path(__file__).resolve().parent
    while current != current.parent:
        env_path = current / '.env'
        if env_path.exists():
            for line in open(env_path):
                line = line.strip()
                if line.startswith(f'{key_name}='):
                    return line.split('=', 1)[1].strip().strip('"\'')
        current = current.parent

    # Fall back to os.environ (CI/Docker scenarios)
    return os.environ.get(key_name, '')
```

### 5. SUDO Bypass Pattern
```python
def has_sudo(transcript_path):
    if not transcript_path or not Path(transcript_path).exists():
        return False
    content = open(transcript_path).read()
    return "SUDO" in content[-5000:]

if has_sudo(data.get("transcript_path")):
    # Skip check, allow with warning
    pass
```

### 6. Debug Logging (to file, NOT stdout)
```python
import logging
logging.basicConfig(filename=Path.home() / ".claude_hook_debug.log", level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug(f"Input: {data}")  # OK
# print(f"Debug: {data}")       # WRONG - breaks JSON protocol
```

## Testing Hooks Locally

```bash
# Create test input
cat > /tmp/test.json << 'EOF'
{"tool_name": "Write", "tool_input": {"file_path": "/tmp/x.py"}}
EOF

# Run hook
python3 .claude/hooks/my_hook.py < /tmp/test.json

# Validate JSON output
python3 .claude/hooks/my_hook.py < /tmp/test.json | jq .
```

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| 401 API errors | Shell has stale key | Read `.env` first, not `os.environ` |
| Hook times out | Slow network call | Use caching, <350ms budget |
| State doesn't persist | Wrong file path | Use absolute paths |
| SUDO not detected | Wrong transcript chunk | Check last 5000 chars |
| Invalid output | Debug prints | Never print to stdout except final JSON |

## File Locations

- Hooks: `.claude/hooks/*.py`
- State: `.claude/memory/*.json`
- Config: `settings.json` (project root or `.claude/`)
- Debug log: `~/.claude_hook_debug.log`
- Cache: `/tmp/claude_hook_cache/`
