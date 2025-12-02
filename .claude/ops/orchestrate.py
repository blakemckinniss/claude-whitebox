#!/usr/bin/env python3
# SUDO SECURITY: Reviewed - no eval/exec/compile, shell=False, API key from env
"""
Orchestrate: Claude-powered programmatic tool orchestration.

Uses Claude API's code_execution beta to let Claude write Python code
that orchestrates tool calls - reducing intermediate result pollution.

Usage:
  orchestrate.py "Analyze all Python files in src/ for security issues"
  orchestrate.py "Read all *.md files, extract TODO items, group by priority"

Per Anthropic research: 37% token reduction, 200KB → 1KB for aggregation tasks.
Requires: ANTHROPIC_API_KEY in environment or .env
"""
import sys
import os
import json
import subprocess

_script_dir = os.path.dirname(os.path.abspath(__file__))
_current = _script_dir
while _current != '/':
    if os.path.exists(os.path.join(_current, '.claude', 'lib', 'core.py')):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root")
sys.path.insert(0, os.path.join(_project_root, '.claude', 'lib'))
from core import setup_script, finalize, logger, handle_debug  # noqa: E402

API_URL = "https://api.anthropic.com/v1/messages"  # Public endpoint, not a secret
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
BETA_FLAG = "advanced-tool-use-2025-11-20"

class OrchestrationError(Exception):
    pass

def get_api_key() -> str:
    key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if key:
        return key
    env_path = os.path.join(_project_root, '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.strip().startswith('ANTHROPIC_API_KEY='):
                    return line.split('=', 1)[1].strip()
    raise OrchestrationError("ANTHROPIC_API_KEY not found")

TOOLS = [
    {"name": "read_file", "description": "Read file contents",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
     "allowed_callers": ["code_execution_20250825"]},
    {"name": "list_files", "description": "List files matching glob pattern",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]},
     "allowed_callers": ["code_execution_20250825"]},
    {"name": "search_content", "description": "Search regex in files",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}}, "required": ["pattern"]},
     "allowed_callers": ["code_execution_20250825"]},
    {"name": "run_safe_command", "description": "Run allowed command (git,grep,find,wc,head,tail,sort,cat,ls)",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}, "args": {"type": "array", "items": {"type": "string"}}}, "required": ["command"]},
     "allowed_callers": ["code_execution_20250825"]},
]

ALLOWED_COMMANDS = {"git": ["git"], "grep": ["grep"], "find": ["find"], "wc": ["wc"],
                    "head": ["head"], "tail": ["tail"], "sort": ["sort"], "cat": ["cat"], "ls": ["ls"]}

def execute_tool(name: str, input_data: dict) -> dict:
    import glob as glob_module
    import re

    if name == "read_file":
        path = input_data.get("path", "")
        if ".." in path or path.startswith("/"):
            return {"error": "Path traversal not allowed"}
        full_path = os.path.join(_project_root, path)
        try:
            return {"content": open(full_path).read()[:50000]}
        except Exception as e:
            return {"error": str(e)}

    elif name == "list_files":
        pattern = input_data.get("pattern", "")
        if ".." in pattern:
            return {"error": "Path traversal not allowed"}
        matches = glob_module.glob(os.path.join(_project_root, pattern), recursive=True)
        matches = [os.path.relpath(m, _project_root) for m in matches if '.git' not in m]
        return {"files": matches[:500]}

    elif name == "search_content":
        pattern, path = input_data.get("pattern", ""), input_data.get("path", ".")
        if ".." in path:
            return {"error": "Path traversal not allowed"}
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return {"error": f"Invalid regex: {e}"}
        matches = []
        for root, _, files in os.walk(os.path.join(_project_root, path)):
            if '.git' in root:
                continue
            for fname in files:
                try:
                    for i, line in enumerate(open(os.path.join(root, fname), errors='ignore'), 1):
                        if regex.search(line):
                            matches.append({"file": os.path.relpath(os.path.join(root, fname), _project_root), "line": i, "content": line.strip()[:200]})
                            if len(matches) >= 100:
                                return {"matches": matches}
                except:
                    pass
        return {"matches": matches}

    elif name == "run_safe_command":
        cmd_name, args = input_data.get("command", ""), input_data.get("args", [])
        if cmd_name not in ALLOWED_COMMANDS:
            return {"error": f"Command not allowed. Use: {list(ALLOWED_COMMANDS.keys())}"}
        try:
            result = subprocess.run(ALLOWED_COMMANDS[cmd_name] + list(args), capture_output=True, text=True, timeout=30, cwd=_project_root)
            return {"stdout": result.stdout[:10000], "stderr": result.stderr[:2000], "exit_code": result.returncode}
        except Exception as e:
            return {"error": str(e)}

    return {"error": f"Unknown tool: {name}"}

def call_api(task: str, model: str = DEFAULT_MODEL, max_tokens: int = 8192) -> str:
    import urllib.request, urllib.error

    system = """You orchestrate tools via Python code. Return ONLY final consolidated results.
Tools: read_file(path), list_files(pattern), search_content(pattern,path), run_safe_command(command,args)"""

    # Format tools for API - code_execution needs name field
    tools = [{"type": "code_execution_20250825", "name": "code_execution"}]
    for t in TOOLS:
        tools.append({"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]})

    payload = {"model": model, "max_tokens": max_tokens, "system": system,
               "messages": [{"role": "user", "content": task}],
               "tools": tools}

    headers = {"Content-Type": "application/json", "x-api-key": get_api_key(),
               "anthropic-version": "2023-06-01", "anthropic-beta": BETA_FLAG}

    req = urllib.request.Request(API_URL, json.dumps(payload).encode(), headers, method='POST')
    logger.info(f"Calling Claude API ({model}) with code_execution...")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return process_response(json.loads(resp.read()), headers, model, max_tokens, system)
    except urllib.error.HTTPError as e:
        raise OrchestrationError(f"HTTP {e.code}: {e.read().decode()[:500]}")

def process_response(result: dict, headers: dict, model: str, max_tokens: int, system: str, messages: list = None, depth: int = 0) -> str:
    import urllib.request
    if depth > 10:
        raise OrchestrationError("Max depth exceeded")

    messages = messages or []
    content_blocks = result.get("content", [])
    text_parts = [b.get("text", "") for b in content_blocks if b.get("type") == "text"]
    tool_uses = [b for b in content_blocks if b.get("type") == "tool_use"]

    if not tool_uses or result.get("stop_reason") == "end_turn":
        return "\n".join(text_parts)

    tool_results = []
    for tu in tool_uses:
        logger.debug(f"  Tool: {tu.get('name')}")
        tool_results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": json.dumps(execute_tool(tu["name"], tu.get("input", {})))})

    messages.append({"role": "assistant", "content": content_blocks})
    messages.append({"role": "user", "content": tool_results})

    # Rebuild tools list (same format as initial call)
    tools = [{"type": "code_execution_20250825", "name": "code_execution"}]
    for t in TOOLS:
        tools.append({"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]})

    payload = {"model": model, "max_tokens": max_tokens, "system": system, "messages": messages, "tools": tools}

    req = urllib.request.Request(API_URL, json.dumps(payload).encode(), headers, method='POST')
    with urllib.request.urlopen(req, timeout=120) as resp:
        return process_response(json.loads(resp.read()), headers, model, max_tokens, system, messages, depth + 1)

def main():
    parser = setup_script("Orchestrate: Claude-powered tool orchestration")
    parser.add_argument("task", nargs="?", help="Task to orchestrate")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=8192)
    args = parser.parse_args()
    handle_debug(args)

    if not args.task:
        parser.error("Task required")
    if args.dry_run:
        logger.info(f"DRY RUN: {args.task}")
        finalize(success=True)

    try:
        result = call_api(args.task, args.model, args.max_tokens)
        print(f"\n{'='*70}\n🎯 ORCHESTRATION RESULT\n{'='*70}\n\n{result}\n\n{'='*70}\n")
    except OrchestrationError as e:
        logger.error(f"Failed: {e}")
        finalize(success=False)
    finalize(success=True)

if __name__ == "__main__":
    main()
