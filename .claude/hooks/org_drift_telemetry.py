#!/usr/bin/env python3
"""
Organizational Drift Telemetry (PostToolUse Hook)
Tracks file operations for drift pattern analysis
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add scripts/lib to path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root / "scripts" / "lib"))

TELEMETRY_FILE = repo_root / ".claude" / "memory" / "org_drift_telemetry.jsonl"


def main():
    # Read hook input from stdin
    hook_input = json.loads(sys.stdin.read())

    tool_name = hook_input.get("toolName")
    tool_params = hook_input.get("toolParams", {})
    tool_result = hook_input.get("result", {})

    # Only track Write and Edit operations
    if tool_name not in ["Write", "Edit"]:
        print("Success")
        return 0

    # Extract file path
    file_path = tool_params.get("file_path")
    if not file_path:
        print("Success")
        return 0

    # Record telemetry
    telemetry_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "file_path": file_path,
        "file_name": Path(file_path).name,
        "directory": str(Path(file_path).parent),
        "depth": len(Path(file_path).parts),
        "success": not tool_result.get("error"),
    }

    # Append to telemetry file
    TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TELEMETRY_FILE, 'a') as f:
        f.write(json.dumps(telemetry_entry) + '\n')

    print("Success")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        # On error, just log and continue
        print(f"Success (telemetry error: {e})", file=sys.stderr)
        sys.exit(0)
