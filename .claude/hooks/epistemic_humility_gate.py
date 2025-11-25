#!/usr/bin/env python3
"""
EPISTEMIC HUMILITY GATE - PreToolUse Hook

PREVENTS: Writing code that uses unverified APIs/libraries (hallucination prevention)

DETECTION:
1. Extract imports from code being written
2. Check against verified_knowledge in session state
3. BLOCK if using unverified library with "Research first" message

PHILOSOPHY:
- "I don't know" is the only honest answer for unverified claims
- Guessing that happens to be correct is still reward hacking
- Verification BEFORE code, not "hope it works"

VERIFIED KNOWLEDGE SOURCES:
- research.py results (live docs)
- probe.py results (runtime inspection)
- Read tool (existing codebase patterns)
- User explicit verification ("SUDO VERIFIED")

BYPASS:
- "SUDO VERIFIED" in recent transcript
- EXPERT tier (95%+ confidence)
- Writing to scratch/ (experimental zone)
"""
import sys
import json
import re
import ast
from pathlib import Path
from typing import Set, Dict, List, Tuple

# Standard library modules (don't need verification)
STDLIB_MODULES = frozenset({
    # Built-ins
    "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio", "asyncore",
    "atexit", "audioop", "base64", "bdb", "binascii", "binhex", "bisect",
    "builtins", "bz2", "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd",
    "code", "codecs", "codeop", "collections", "colorsys", "compileall",
    "concurrent", "configparser", "contextlib", "contextvars", "copy", "copyreg",
    "cProfile", "crypt", "csv", "ctypes", "curses", "dataclasses", "datetime",
    "dbm", "decimal", "difflib", "dis", "distutils", "doctest", "email",
    "encodings", "enum", "errno", "faulthandler", "fcntl", "filecmp", "fileinput",
    "fnmatch", "fractions", "ftplib", "functools", "gc", "getopt", "getpass",
    "gettext", "glob", "graphlib", "grp", "gzip", "hashlib", "heapq", "hmac",
    "html", "http", "idlelib", "imaplib", "imghdr", "imp", "importlib", "inspect",
    "io", "ipaddress", "itertools", "json", "keyword", "lib2to3", "linecache",
    "locale", "logging", "lzma", "mailbox", "mailcap", "marshal", "math",
    "mimetypes", "mmap", "modulefinder", "multiprocessing", "netrc", "nis",
    "nntplib", "numbers", "operator", "optparse", "os", "ossaudiodev", "pathlib",
    "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform", "plistlib",
    "poplib", "posix", "posixpath", "pprint", "profile", "pstats", "pty", "pwd",
    "py_compile", "pyclbr", "pydoc", "queue", "quopri", "random", "re",
    "readline", "reprlib", "resource", "rlcompleter", "runpy", "sched", "secrets",
    "select", "selectors", "shelve", "shlex", "shutil", "signal", "site",
    "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd", "sqlite3",
    "ssl", "stat", "statistics", "string", "stringprep", "struct", "subprocess",
    "sunau", "symtable", "sys", "sysconfig", "syslog", "tabnanny", "tarfile",
    "telnetlib", "tempfile", "termios", "test", "textwrap", "threading", "time",
    "timeit", "tkinter", "token", "tokenize", "trace", "traceback", "tracemalloc",
    "tty", "turtle", "turtledemo", "types", "typing", "unicodedata", "unittest",
    "urllib", "uu", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
    "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp",
    "zipfile", "zipimport", "zlib", "_thread",
    # Common typing extensions
    "typing_extensions",
})

# Project-internal modules (verified by being in codebase)
PROJECT_MODULES = frozenset({
    "lib", "core", "epistemology", "pattern_detection", "auto_tuning",
    "meta_learning", "parallel", "batch", "browser", "org_drift",
})

# High-risk libraries that ALWAYS require verification
HIGH_RISK_LIBRARIES = frozenset({
    # Cloud providers
    "boto3", "botocore", "azure", "google.cloud", "gcloud",
    # ML/AI
    "openai", "anthropic", "langchain", "transformers", "torch", "tensorflow",
    # Web frameworks
    "fastapi", "flask", "django", "starlette", "aiohttp",
    # Databases
    "sqlalchemy", "pymongo", "redis", "psycopg2", "mysql",
    # Data science
    "pandas", "numpy", "scipy", "sklearn", "matplotlib", "seaborn",
    # Async/networking
    "httpx", "requests", "aiofiles", "websockets",
    # Browser automation
    "playwright", "selenium", "puppeteer",
})


def extract_imports_from_code(code: str) -> Set[str]:
    """
    Extract top-level module names from Python code.

    Returns set of module names (e.g., {"boto3", "pandas", "requests"})
    """
    imports = set()

    # Try AST parsing first (most accurate)
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Get top-level module (e.g., "os.path" -> "os")
                    top_module = alias.name.split('.')[0]
                    imports.add(top_module)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top_module = node.module.split('.')[0]
                    imports.add(top_module)
    except SyntaxError:
        # Fallback to regex for partial/broken code
        pass

    # Regex fallback for code that doesn't parse
    # Match: import foo, from foo import bar
    import_patterns = [
        r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        r'^from\s+([a-zA-Z_][a-zA-Z0-9_]*)',
    ]
    for pattern in import_patterns:
        for match in re.finditer(pattern, code, re.MULTILINE):
            imports.add(match.group(1))

    return imports


def extract_method_calls(code: str) -> Set[str]:
    """
    Extract method call patterns that indicate library usage.

    Catches patterns like:
    - boto3.client('s3')
    - pd.DataFrame()
    - requests.get()
    """
    patterns = set()

    # Pattern: module.method() or module.Class()
    method_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\.\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
    for match in re.finditer(method_pattern, code):
        module, method = match.groups()
        patterns.add(f"{module}.{method}")

    return patterns


def load_verified_knowledge(session_id: str) -> Dict:
    """Load verified knowledge from session state."""
    # Find project root
    project_dir = Path(__file__).resolve().parent.parent
    while not (project_dir / "scripts" / "lib").exists() and project_dir != project_dir.parent:
        project_dir = project_dir.parent

    state_file = project_dir / ".claude" / "memory" / f"session_{session_id}_state.json"

    if not state_file.exists():
        return {}

    try:
        with open(state_file) as f:
            state = json.load(f)
            return state.get("verified_knowledge", {})
    except (json.JSONDecodeError, IOError):
        return {}


def check_sudo_verified(data: dict) -> bool:
    """Check if SUDO VERIFIED in recent transcript."""
    transcript_path = data.get("transcript_path", "")
    if not transcript_path:
        return False
    try:
        import os
        if os.path.exists(transcript_path):
            with open(transcript_path, 'r') as tf:
                transcript = tf.read()
                last_chunk = transcript[-5000:] if len(transcript) > 5000 else transcript
                return "SUDO VERIFIED" in last_chunk
    except Exception:
        pass
    return False


def get_confidence(session_id: str) -> int:
    """Get current confidence from session state."""
    project_dir = Path(__file__).resolve().parent.parent
    while not (project_dir / "scripts" / "lib").exists() and project_dir != project_dir.parent:
        project_dir = project_dir.parent

    state_file = project_dir / ".claude" / "memory" / f"session_{session_id}_state.json"

    if not state_file.exists():
        return 0

    try:
        with open(state_file) as f:
            state = json.load(f)
            return state.get("confidence", 0)
    except (json.JSONDecodeError, IOError):
        return 0


def check_library_verification(
    imports: Set[str],
    verified: Dict,
    file_path: str
) -> List[Tuple[str, str]]:
    """
    Check which imports are unverified.

    Returns list of (library, reason) tuples for unverified libs.
    """
    unverified = []
    verified_libs = verified.get("libraries", {})

    for lib in imports:
        # Skip stdlib
        if lib in STDLIB_MODULES:
            continue

        # Skip project modules
        if lib in PROJECT_MODULES:
            continue

        # Skip if verified
        if lib in verified_libs:
            continue

        # Determine severity
        if lib in HIGH_RISK_LIBRARIES:
            reason = f"HIGH-RISK library '{lib}' requires verification (API changes frequently)"
        else:
            reason = f"Library '{lib}' not verified in this session"

        unverified.append((lib, reason))

    return unverified


def main():
    # Read hook input
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Can't parse input, allow through
        print(json.dumps({"decision": "allow"}))
        return 0

    tool_name = hook_input.get("tool_name")
    tool_params = hook_input.get("tool_input", {})
    session_id = hook_input.get("session_id", "")

    # Only check Write and Edit tools
    if tool_name not in ["Write", "Edit"]:
        print(json.dumps({"decision": "allow"}))
        return 0

    # Get file path and content
    file_path = tool_params.get("file_path", "")
    content = tool_params.get("content", tool_params.get("new_string", ""))

    # BYPASS: scratch/ is experimental zone
    if "scratch/" in file_path or "/scratch/" in file_path:
        print(json.dumps({"decision": "allow"}))
        return 0

    # BYPASS: Non-Python files
    if not file_path.endswith(".py"):
        print(json.dumps({"decision": "allow"}))
        return 0

    # BYPASS: SUDO VERIFIED
    if check_sudo_verified(hook_input):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": "⚠️ SUDO VERIFIED - epistemic humility check bypassed"
            }
        }))
        return 0

    # BYPASS: EXPERT tier (95%+)
    confidence = get_confidence(session_id)
    if confidence >= 95:
        print(json.dumps({"decision": "allow"}))
        return 0

    # Extract imports from code
    imports = extract_imports_from_code(content)

    if not imports:
        # No imports, allow
        print(json.dumps({"decision": "allow"}))
        return 0

    # Load verified knowledge
    verified = load_verified_knowledge(session_id)

    # Check for unverified libraries
    unverified = check_library_verification(imports, verified, file_path)

    if not unverified:
        # All imports verified
        print(json.dumps({"decision": "allow"}))
        return 0

    # BUILD BLOCK MESSAGE
    lib_list = "\n".join([f"  • {lib}: {reason}" for lib, reason in unverified])
    research_cmds = "\n".join([
        f'  python3 scripts/ops/research.py "{lib} python usage 2025"'
        for lib, _ in unverified[:3]  # Top 3
    ])
    probe_cmds = "\n".join([
        f'  python3 scripts/ops/probe.py {lib}'
        for lib, _ in unverified[:3]
    ])

    block_message = f"""🛑 EPISTEMIC HUMILITY GATE - UNVERIFIED API USAGE

You are writing code that uses libraries you have NOT verified.

UNVERIFIED LIBRARIES:
{lib_list}

WHY THIS MATTERS:
- "I think this API works like X" is a GUESS
- Guessing that happens to be correct is still REWARD HACKING
- Your training data is from January 2025 - APIs change

REQUIRED: Say "I don't know" and verify FIRST

Option 1 - Research (live docs):
{research_cmds}

Option 2 - Probe (runtime inspection):
{probe_cmds}

Option 3 - Read existing code using this library:
  Use Grep/Read to find existing patterns in codebase

AFTER verification, your code will be allowed.

Current Confidence: {confidence}%
Bypass: Say "SUDO VERIFIED" if you are certain (tracked for review)
"""

    result = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": block_message
        }
    }

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
