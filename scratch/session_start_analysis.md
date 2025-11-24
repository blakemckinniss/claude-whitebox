# Session Start Spawn Loop Analysis

## Problem
50 test_hooks.py processes spawned in 10 seconds, all parented by PID 14 (/init)

## Root Cause Hypothesis
`test_hooks_background.py` is registered ONCE in SessionStart, but:

### Possible Triggers:
1. **Claude Code spawning multiple sessions**
   - Each new message/tool call might be triggering SessionStart
   - SessionStart should only fire ONCE per actual session, not per turn

2. **Hook recursion**
   - A hook might be spawning subprocess that triggers new session detection
   - Background processes (Popen with start_new_session=True) may be seen as new sessions

3. **Multiple Claude processes**
   - VS Code extension or multiple terminals triggering parallel sessions

## Evidence
- test_hooks_background.py uses `subprocess.Popen(..., start_new_session=True)`
- This detaches the process, parenting to PID 1/init
- **50 spawns in 10s = 5 per second** = extremely high rate

## Likely Culprit
The `start_new_session=True` flag in test_hooks_background.py may be causing Claude Code
to detect each background test as a NEW session, triggering SessionStart again recursively.

## Fix Strategy
1. **Remove start_new_session=True** - keep process attached to parent
2. **Add spawn guard** - track if test already running, skip if so
3. **Add cooldown** - prevent spawns within N seconds of last spawn
4. **Disable background testing** - run synchronously or only on explicit command

## Immediate Action
Kill all running test_hooks.py processes and disable test_hooks_background.py temporarily
to confirm diagnosis.
