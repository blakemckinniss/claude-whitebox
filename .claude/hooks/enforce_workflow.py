import sys
import json

try:
    data = json.load(sys.stdin)
except:
    sys.exit(0)

# Get user prompt
prompt = data.get("prompt", "").lower()

# Check for complex task indicators
complex_triggers = [
    "architect",
    "architecture",
    "design",
    "refactor",
    "refactoring",
    "optimize",
    "optimization",
    "strategy",
    "pattern",
    "schema",
    "restructure",
    "migration",
    "scale",
    "performance",
    "security design",
]

oracle_triggered = any(trigger in prompt for trigger in complex_triggers)

# Build context message
base_context = "(System Reminder: Prefer writing scratch scripts over manual actions. Check `scratch/` before starting.)"

if oracle_triggered:
    context = (
        base_context
        + "\n\n"
        + (
            "⚠️ COMPLEXITY DETECTED: This looks like an architectural/design task.\n"
            "ORACLE PROTOCOL: Consider consulting The Oracle before implementation:\n"
            '  python3 scripts/ops/consult.py "<your problem description>"\n'
            "This provides external reasoning to catch edge cases you might miss."
        )
    )
else:
    context = base_context

# Inject context reminder
print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context,
            }
        }
    )
)
sys.exit(0)
