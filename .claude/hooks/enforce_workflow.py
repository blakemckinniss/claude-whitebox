import sys
import json

try:
    data = json.load(sys.stdin)
except:
    sys.exit(0)

# Inject context reminder
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": "(System Reminder: Prefer writing scratch scripts over manual actions. Check `scratch/` before starting.)"
    }
}))
sys.exit(0)
