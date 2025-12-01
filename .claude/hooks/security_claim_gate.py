#!/usr/bin/env python3
"""
Security Claim Gate Hook: Require audit for security-sensitive code.

Hook Type: PreToolUse (matcher: Edit|Write)
Enforces CLAUDE.md Auto-Invoke Rule: "Claiming security-sensitive code is safe -> audit <file>"

BLOCKS edits to security-sensitive files without prior audit.

Security-sensitive patterns:
- auth, login, password, credential, token, secret, key
- encrypt, decrypt, hash, sign, verify
- permission, role, access, grant

Note: Code injection patterns (eval/exec) are handled by content_gate.py

Bypass: Include 'SUDO SECURITY' or run audit first.
"""

import _lib_path  # noqa: F401
import sys
import json
import re

from session_state import load_state
from synapse_core import output_hook_result, check_sudo_in_transcript  # SUDO SECURITY

# Security-sensitive file patterns
SECURITY_FILE_PATTERNS = [
    r'auth',
    r'login',
    r'password',
    r'credential',
    r'token',
    r'secret',
    r'key',
    r'permission',
    r'role',
    r'access',
    r'security',
    r'crypto',
    r'encrypt',
    r'session',
    r'jwt',
    r'oauth',
    r'saml',
]

# Security-sensitive content patterns
# Note: injection patterns handled by content_gate.py
SECURITY_CONTENT_PATTERNS = [
    r'password\s*=',
    r'secret\s*=',
    r'api_key\s*=',
    r'token\s*=',
    r'\.hash\(',
    r'\.encrypt\(',
    r'\.decrypt\(',
    r'\.sign\(',
    r'\.verify\(',
    r'subprocess\.(call|run|Popen)',
    r'\.execute\(',
]


def is_security_sensitive(file_path: str, content: str) -> list[str]:
    """Check if this is security-sensitive code. Returns list of indicators."""
    indicators = []

    # Check file path
    path_lower = file_path.lower()
    for pattern in SECURITY_FILE_PATTERNS:
        if pattern in path_lower:
            indicators.append(f"security file: {pattern}")
            break

    # Check content
    for pattern in SECURITY_CONTENT_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            indicators.append(f"security pattern detected")
            if len(indicators) >= 2:
                break

    return indicators


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name not in ("Edit", "Write", "MultiEdit"):
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    transcript_path = data.get("transcript_path", "")
    file_path = tool_input.get("file_path", "")

    # Get content
    content = ""
    if tool_name == "Write":
        content = tool_input.get("content", "")
    elif tool_name == "Edit":
        content = tool_input.get("new_string", "")

    # Bypass check - content, transcript, or existing file comment
    if "SUDO SECURITY" in content.upper() or check_sudo_in_transcript(transcript_path):
        sys.exit(0)

    # Check if target file already has SUDO SECURITY comment
    try:
        from pathlib import Path
        if Path(file_path).exists():
            existing_content = Path(file_path).read_text()
            if "SUDO SECURITY" in existing_content.upper():
                sys.exit(0)
    except (IOError, OSError):
        pass

    indicators = is_security_sensitive(file_path, content)
    if not indicators:
        sys.exit(0)

    # Check if audit was run on this file
    state = load_state()
    audited_files = getattr(state, 'audited_files', [])

    if file_path in audited_files:
        sys.exit(0)

    # BLOCK - security-sensitive edit without audit
    output_hook_result(
        "PreToolUse",
        decision="deny",
        reason=(
            f"**SECURITY GATE BLOCKED** (Auto-Invoke Rule)\n\n"
            f"Detected: {', '.join(indicators[:2])}\n\n"
            f"Security-sensitive code requires audit before edit.\n\n"
            f"```bash\n"
            f"audit {file_path}\n"
            f"```\n\n"
            f"Bypass: Add 'SUDO SECURITY' to content if audit already done."
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
