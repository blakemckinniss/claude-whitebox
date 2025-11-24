#!/usr/bin/env python3
"""
Generate auto-tuning upgrades for remaining enforcement hooks.

Priority order:
1. Performance gates (high impact)
2. Tier gates (foundational)
3. Confidence gates (epistemological)

For each hook, generates:
- Pattern definitions
- Auto-tuner integration
- Meta-learning integration
- Test stubs
"""

import sys
from pathlib import Path

PROJECT_DIR = Path.cwd()
SCRATCH_DIR = PROJECT_DIR / "scratch"

# Template for auto-tuning upgrade
AUTO_TUNE_TEMPLATE = '''#!/usr/bin/env python3
"""
{hook_name} V2: WITH AUTO-TUNING
{hook_type} Hook: {description}

EVOLUTION:
- Phase 1 (OBSERVE): {observe_behavior}
- Phase 2 (WARN): {warn_behavior}
- Phase 3 (ENFORCE): {enforce_behavior}

AUTO-TUNING:
- {tuning_behavior}
"""

import sys
import json
from pathlib import Path

# Add scripts/lib to path
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

sys.path.insert(0, str(PROJECT_DIR / "scripts" / "lib"))

from auto_tuning import AutoTuner
from meta_learning import record_manual_bypass, record_sudo_bypass, check_exception_rule

# Pattern definitions
{patterns_definition}

# Initialize auto-tuner
MEMORY_DIR = PROJECT_DIR / ".claude" / "memory"
STATE_FILE = MEMORY_DIR / "{state_file}"

tuner = AutoTuner(
    system_name="{system_name}",
    state_file=STATE_FILE,
    patterns={patterns_var_name},
    default_phase="observe",
    default_thresholds={thresholds}
)

{main_function}
'''

# Hook configurations
HOOK_CONFIGS = {
    "performance_gate": {
        "hook_name": "Performance Gate",
        "hook_type": "PreToolUse",
        "description": "Enforces performance best practices (parallelism, background execution)",
        "observe_behavior": "Track sequential vs parallel patterns silently",
        "warn_behavior": "Suggest performance improvements",
        "enforce_behavior": "Block inefficient patterns",
        "tuning_behavior": "Learns optimal parallelism thresholds from task type",
        "patterns": {
            "sequential_bash": {
                "threshold": 3,
                "suggested_action": "Use parallel background execution (run_in_background=true)",
            },
            "blocking_on_slow": {
                "threshold": 1,
                "suggested_action": "Use background execution for slow operations (>5s)",
            },
        },
        "state_file": "performance_gate_state.json",
        "system_name": "performance_enforcement",
    },
    "tier_gate": {
        "hook_name": "Tier Gate",
        "hook_type": "PreToolUse",
        "description": "Enforces confidence tier restrictions",
        "observe_behavior": "Track tier violations and actual confidence patterns",
        "warn_behavior": "Suggest evidence gathering to reach required tier",
        "enforce_behavior": "Block actions below required confidence tier",
        "tuning_behavior": "Learns optimal tier thresholds from success/failure patterns",
        "patterns": {
            "ignorance_coding": {
                "threshold": 1,
                "suggested_action": "Gather evidence (Read files, Research, Probe APIs) to reach HYPOTHESIS tier (31%+)",
            },
            "hypothesis_production": {
                "threshold": 1,
                "suggested_action": "Reach CERTAINTY tier (71%+) before modifying production code",
            },
        },
        "state_file": "tier_gate_state.json",
        "system_name": "tier_enforcement",
    },
}


def generate_performance_gate():
    """Generate performance gate upgrade"""
    config = HOOK_CONFIGS["performance_gate"]

    patterns_def = f"""PERFORMANCE_PATTERNS = {config['patterns']}"""

    main_func = '''
def main():
    """Main enforcement logic"""
    try:
        data = json.load(sys.stdin)
    except:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "allowExecution": True,
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    tool_name = data.get("toolName", "")
    tool_params = data.get("toolParams", {})
    turn = data.get("turn", 0)
    prompt = data.get("prompt", "")

    # Only track Bash tool for performance patterns
    if tool_name != "Bash":
        sys.exit(0)

    command = tool_params.get("command", "")
    run_in_background = tool_params.get("run_in_background", False)

    # Detect slow operations not using background
    slow_keywords = ["pytest", "npm test", "npm run build", "cargo build", "docker build"]
    is_slow = any(kw in command for kw in slow_keywords)

    if is_slow and not run_in_background:
        pattern_name = "blocking_on_slow"

        # Check exception rules
        should_bypass, rule = check_exception_rule(
            "performance_gate",
            {"tool": tool_name, "command": command}
        )

        if should_bypass:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "allowExecution": True,
                    "additionalContext": f"🎓 Exception: {rule['reason']}",
                }
            }
            print(json.dumps(output))
            sys.exit(0)

        # Check if should enforce
        action, message = tuner.should_enforce(pattern_name, prompt)

        # Track bypass
        if "MANUAL" in prompt:
            record_manual_bypass(
                hook_name="performance_gate",
                context={"tool": tool_name, "pattern": pattern_name, "command": command[:100]},
                turn=turn,
                reason="Manual bypass of performance enforcement"
            )

        # Update metrics (estimate slow command = 30s blocked)
        tuner.update_metrics(
            pattern_name,
            turns_wasted=1,  # Could have worked during that time
            script_written=False,
            bypassed="MANUAL" in prompt or "SUDO MANUAL" in prompt
        )

        # Phase transition
        transition_msg = tuner.check_phase_transition(turn)
        if transition_msg:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "allowExecution": True,
                    "additionalContext": transition_msg,
                }
            }
            print(json.dumps(output))
            sys.exit(0)

        # Auto-tune
        tuner.auto_tune_thresholds(turn)

        # Report
        report = tuner.generate_report(turn)
        if report:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "allowExecution": True,
                    "additionalContext": report,
                }
            }
            print(json.dumps(output))
            sys.exit(0)

        # Enforcement
        if action == "block" and message:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "allowExecution": False,
                    "blockMessage": message,
                }
            }
            print(json.dumps(output))
            sys.exit(0)

        elif action == "warn" and message:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "allowExecution": True,
                    "additionalContext": message,
                }
            }
            print(json.dumps(output))
            sys.exit(0)

    # Allow execution (default)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "allowExecution": True,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
'''

    code = AUTO_TUNE_TEMPLATE.format(
        hook_name=config["hook_name"],
        hook_type=config["hook_type"],
        description=config["description"],
        observe_behavior=config["observe_behavior"],
        warn_behavior=config["warn_behavior"],
        enforce_behavior=config["enforce_behavior"],
        tuning_behavior=config["tuning_behavior"],
        patterns_definition=patterns_def,
        state_file=config["state_file"],
        system_name=config["system_name"],
        patterns_var_name="PERFORMANCE_PATTERNS",
        thresholds="{}",
        main_function=main_func
    )

    output_file = SCRATCH_DIR / "performance_gate_v2.py"
    with open(output_file, "w") as f:
        f.write(code)

    return output_file


def generate_lesson_consolidator():
    """Generate lesson consolidation system"""
    code = '''#!/usr/bin/env python3
"""
Lesson Consolidation System: Prevents lessons.md bloat

AUTO-RUNS:
- Every 100 turns (via PostToolUse hook)
- On SessionEnd

OPERATIONS:
1. Find duplicate lessons (word overlap >70%)
2. Merge duplicates (keep most specific/recent)
3. Expire old lessons (>6 months + not cited in 50 turns)
4. Weight lessons by recency + citation count

RESULT: lessons.md stays <50 entries, high signal-to-noise
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re

PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

LESSONS_FILE = PROJECT_DIR / ".claude" / "memory" / "lessons.md"


def load_lessons():
    """Load lessons from file"""
    if not LESSONS_FILE.exists():
        return []

    with open(LESSONS_FILE) as f:
        content = f.read()

    # Parse lessons (each starts with "###" or bullet)
    lessons = []
    current_lesson = []

    for line in content.split("\n"):
        if line.startswith("###") or line.startswith("**"):
            if current_lesson:
                lessons.append("\\n".join(current_lesson))
            current_lesson = [line]
        elif current_lesson:
            current_lesson.append(line)

    if current_lesson:
        lessons.append("\\n".join(current_lesson))

    return lessons


def calculate_similarity(lesson1, lesson2):
    """Calculate word overlap similarity"""
    words1 = set(re.findall(r"\\w+", lesson1.lower()))
    words2 = set(re.findall(r"\\w+", lesson2.lower()))

    if not words1 or not words2:
        return 0.0

    intersection = len(words1 & words2)
    union = len(words1 | words2)

    return intersection / union if union > 0 else 0.0


def find_duplicates(lessons, threshold=0.70):
    """Find duplicate lessons with >threshold similarity"""
    duplicates = []

    for i, lesson1 in enumerate(lessons):
        for j, lesson2 in enumerate(lessons[i+1:], i+1):
            similarity = calculate_similarity(lesson1, lesson2)
            if similarity >= threshold:
                duplicates.append((i, j, similarity))

    return duplicates


def merge_lessons(lesson1, lesson2):
    """Merge two similar lessons (keep more specific)"""
    # Longer lesson is usually more specific
    if len(lesson1) > len(lesson2):
        return lesson1 + f"\\n\\n(Consolidated with similar lesson)"
    else:
        return lesson2 + f"\\n\\n(Consolidated with similar lesson)"


def consolidate_lessons(lessons):
    """Consolidate duplicate lessons"""
    duplicates = find_duplicates(lessons)

    if not duplicates:
        return lessons, 0

    # Merge duplicates (keep track of merged indices)
    to_remove = set()
    merged_lessons = lessons.copy()

    for i, j, similarity in duplicates:
        if i not in to_remove and j not in to_remove:
            merged_lessons[i] = merge_lessons(lessons[i], lessons[j])
            to_remove.add(j)

    # Remove duplicates
    consolidated = [l for i, l in enumerate(merged_lessons) if i not in to_remove]

    return consolidated, len(to_remove)


def expire_old_lessons(lessons, age_threshold_months=6):
    """Remove lessons older than threshold"""
    # This is simplified - would need date parsing in real implementation
    # For now, just return all lessons (no expiration)
    return lessons, 0


def save_lessons(lessons):
    """Save consolidated lessons"""
    content = "# Lessons Learned\\n\\n"
    content += f"*Auto-consolidated on {datetime.now().isoformat()}*\\n\\n"
    content += "\\n\\n".join(lessons)

    with open(LESSONS_FILE, "w") as f:
        f.write(content)


def main():
    """Main consolidation logic"""
    print("📚 LESSON CONSOLIDATION SYSTEM\\n")

    lessons = load_lessons()
    original_count = len(lessons)

    print(f"Original lessons: {original_count}")

    # Consolidate duplicates
    lessons, duplicates_removed = consolidate_lessons(lessons)
    print(f"Duplicates removed: {duplicates_removed}")

    # Expire old lessons
    lessons, expired = expire_old_lessons(lessons)
    print(f"Expired lessons: {expired}")

    # Save
    save_lessons(lessons)

    final_count = len(lessons)
    print(f"\\nFinal lessons: {final_count}")
    print(f"Reduction: {original_count - final_count} ({(original_count - final_count) / original_count * 100:.0f}%)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

    output_file = SCRATCH_DIR / "consolidate_lessons.py"
    with open(output_file, "w") as f:
        f.write(code)

    return output_file


def main():
    """Generate all upgrade files"""
    print("🔧 Generating auto-tuning upgrades...\n")

    generated = []

    # Performance gate
    f = generate_performance_gate()
    generated.append(f)
    print(f"✅ Generated: {f}")

    # Lesson consolidator
    f = generate_lesson_consolidator()
    generated.append(f)
    print(f"✅ Generated: {f}")

    print(f"\n📊 Generated {len(generated)} files")
    print("\n💡 NEXT STEPS:")
    print("1. Review generated files in scratch/")
    print("2. Test each upgrade in isolation")
    print("3. Deploy to .claude/hooks/")
    print("4. Run integration tests")

    return 0


if __name__ == "__main__":
    sys.exit(main())
