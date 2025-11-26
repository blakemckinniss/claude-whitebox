#!/usr/bin/env python3
"""
Groq: Zero-Dependency Groq API Client

Fast inference via Groq API using stdlib only (urllib, json).
Supports chat completions, streaming, web search, and URL grounding.

Usage:
  # Basic chat completion
  groq.py "Explain quantum computing"

  # With web search (built-in tool)
  groq.py --web-search "Latest AI developments 2025"

  # With URL grounding
  groq.py --url https://example.com "Summarize this article"

  # Streaming response
  groq.py --stream "Write a haiku about code"

  # Custom model (default: moonshotai/kimi-k2-instruct-0905)
  groq.py --model "llama-3.3-70b-versatile" "Debug this error"

  # Custom temperature/max_tokens
  groq.py --temperature 0.9 --max-tokens 8192 "Generate creative code"

Models:
  - moonshotai/kimi-k2-instruct-0905 (default, 128k context)
  - llama-3.3-70b-versatile (128k context)
  - groq/compound (multi-tool support)

Tools:
  - web_search: Real-time web search
  - visit_website: URL content grounding
"""
import sys
import os
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, Dict, Any, List, Iterator

# Add .claude/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
_current = _script_dir
while _current != '/':
    if os.path.exists(os.path.join(_current, '.claude', 'lib', 'core.py')):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with .claude/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, '.claude', 'lib'))
from core import setup_script, finalize, logger, handle_debug  # noqa: E402

# ============================================================
# GROQ API CLIENT (Zero Dependencies)
# ============================================================

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "moonshotai/kimi-k2-instruct-0905"

class GroqAPIError(Exception):
    """Groq API error"""
    pass


def get_api_key() -> str:
    """Get Groq API key from environment or .env file"""
    # Check environment variable first (for Docker/CI)
    if 'GROQ_API_KEY' in os.environ:
        key = os.environ['GROQ_API_KEY'].strip()
        if key:
            return key

    # Fall back to .env file
    env_path = os.path.join(_project_root, '.env')
    if not os.path.exists(env_path):
        raise GroqAPIError("GROQ_API_KEY not found in environment or .env file")

    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('GROQ_API_KEY='):
                    if '=' not in line:
                        continue
                    key = line.split('=', 1)[1].strip()
                    if key:
                        return key
    except (OSError, UnicodeDecodeError) as e:
        raise GroqAPIError(f"Failed to read .env file: {e}")

    raise GroqAPIError("GROQ_API_KEY not found or empty")


def call_groq_api(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.6,
    max_tokens: int = 4096,
    stream: bool = False,
    tools: Optional[List[str]] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Call Groq API with stdlib only (no external dependencies).

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Groq model identifier
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum completion tokens
        stream: Enable streaming responses
        tools: List of built-in tool names (web_search, visit_website)
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'choices', 'usage', etc.

    Raises:
        GroqAPIError: On API errors
    """
    api_key = get_api_key()

    # Build request payload
    payload = {
        "messages": messages,
        "model": model,
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
        "top_p": 1,
        "stream": stream,
        "stop": None
    }

    # Add tools if specified
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    if tools:
        # For compound model with built-in tools
        if "compound" in model:
            headers["Groq-Model-Version"] = "latest"
            payload["compound_custom"] = {
                "tools": {
                    "enabled_tools": tools
                }
            }
        else:
            # Map tool names to correct types
            tool_type_map = {
                "web_search": "browser_search",
                "visit_website": "browser_search"
            }
            payload["tools"] = [{"type": tool_type_map.get(tool, tool)} for tool in tools]

    # Make HTTP request
    try:
        logger.debug(f"Calling Groq API: {model} (stream={stream})")

        req = urllib.request.Request(
            GROQ_API_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )

        if stream:
            # For streaming, we cannot use context manager
            # Read all chunks into list before closing connection
            response = urllib.request.urlopen(req, timeout=timeout)  # nosec B310 - HTTPS POST to hardcoded API URL
            try:
                chunks = list(_handle_streaming_response(response))
                return iter(chunks)
            finally:
                response.close()
        else:
            # For non-streaming, use context manager
            with urllib.request.urlopen(req, timeout=timeout) as response:  # nosec B310 - HTTPS POST to hardcoded API URL
                response_data = response.read().decode('utf-8')
                result = json.loads(response_data)
                return result

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_data = json.loads(error_body)
            error_msg = error_data.get('error', {}).get('message', error_body)
        except json.JSONDecodeError:
            error_msg = error_body

        raise GroqAPIError(f"HTTP {e.code}: {error_msg}")

    except urllib.error.URLError as e:
        raise GroqAPIError(f"Network error: {e.reason}")

    except json.JSONDecodeError as e:
        raise GroqAPIError(f"Invalid JSON response: {e}")

    except Exception as e:
        raise GroqAPIError(f"Unexpected error: {e}")


def _handle_streaming_response(response) -> Iterator[str]:
    """
    Handle SSE streaming response.

    Yields:
        Content chunks from streaming response
    """
    for line in response:
        line = line.decode('utf-8').strip()

        if not line:
            continue

        if line.startswith('data: '):
            data_str = line[6:]  # Remove 'data: ' prefix

            if data_str == '[DONE]':
                break

            try:
                chunk = json.loads(data_str)
                choices = chunk.get('choices', [])

                if not choices:
                    logger.debug("Empty choices in streaming chunk")
                    continue

                delta = choices[0].get('delta', {})
                content = delta.get('content', '')

                if content:
                    yield content

            except json.JSONDecodeError as e:
                logger.warning(f"Malformed streaming chunk: {e}")
                continue
            except (KeyError, IndexError) as e:
                logger.warning(f"Unexpected chunk structure: {e}")
                continue


def groq_chat(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.6,
    max_tokens: int = 4096,
    stream: bool = False,
    web_search: bool = False,
    url: Optional[str] = None,
    system_prompt: Optional[str] = None
) -> str:
    """
    Send chat completion to Groq API.

    Args:
        prompt: User prompt
        model: Groq model identifier
        temperature: Sampling temperature
        max_tokens: Maximum completion tokens
        stream: Enable streaming (prints chunks to stdout)
        web_search: Enable web search tool
        url: URL to ground response with (visit_website tool)
        system_prompt: Optional system prompt

    Returns:
        Response content (or empty string if streaming)
    """
    # Build messages
    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    # Add URL context if provided
    if url:
        prompt = f"Visit {url} and then: {prompt}"

    messages.append({"role": "user", "content": prompt})

    # Build tools list
    tools = []
    if web_search:
        tools.append("web_search")
    if url:
        tools.append("visit_website")

    # Auto-switch to compound model if tools requested and not already using compound
    if tools and "compound" not in model:
        logger.info("Auto-switching to groq/compound (tools require compound model)")
        model = "groq/compound"

    # Call API
    result = call_groq_api(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
        tools=tools if tools else None
    )

    # Handle response
    if stream:
        # Print streaming chunks
        full_content = []
        try:
            for chunk in result:
                print(chunk, end='', flush=True)
                full_content.append(chunk)
            print()  # Final newline
        except BrokenPipeError:
            # Pipe closed (e.g., piped to head), exit gracefully
            pass
        return ''.join(full_content)
    else:
        # Extract content from response
        if 'choices' not in result or not result['choices']:
            raise GroqAPIError("No response from API (empty choices)")

        try:
            content = result['choices'][0]['message']['content']
        except (KeyError, IndexError) as e:
            raise GroqAPIError(f"Malformed API response: {e}")

        # Log usage stats
        usage = result.get('usage', {})
        if usage:
            logger.debug(
                f"Usage: {usage.get('prompt_tokens', 0)} prompt + "
                f"{usage.get('completion_tokens', 0)} completion = "
                f"{usage.get('total_tokens', 0)} total tokens"
            )

        return content


# ============================================================
# CLI INTERFACE
# ============================================================

def main():
    parser = setup_script("Groq: Zero-dependency Groq API client")

    # Query
    parser.add_argument(
        "query",
        nargs="?",
        help="Prompt to send to Groq"
    )

    # Model selection
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Groq model (default: {DEFAULT_MODEL})"
    )

    # Generation parameters
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.6,
        help="Sampling temperature 0-2 (default: 0.6)"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Maximum completion tokens (default: 4096)"
    )

    # Tools
    parser.add_argument(
        "--web-search",
        action="store_true",
        help="Enable web search tool"
    )
    parser.add_argument(
        "--url",
        help="URL to ground response with (visit_website tool)"
    )

    # Streaming
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Enable streaming response"
    )

    # System prompt
    parser.add_argument(
        "--system",
        help="Custom system prompt"
    )

    args = parser.parse_args()
    handle_debug(args)

    # Validate arguments
    if not args.query:
        parser.error("Query required")

    # Validate temperature range
    if not 0 <= args.temperature <= 2:
        parser.error("Temperature must be between 0 and 2")

    # Validate max_tokens
    if args.max_tokens <= 0:
        parser.error("Max tokens must be positive")

    # Dry run check
    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would send the following to Groq:")
        logger.info(f"Query: {args.query}")
        logger.info(f"Model: {args.model}")
        logger.info(f"Temperature: {args.temperature}")
        logger.info(f"Max tokens: {args.max_tokens}")
        logger.info(f"Stream: {args.stream}")
        logger.info(f"Web search: {args.web_search}")
        logger.info(f"URL: {args.url or 'None'}")
        logger.info(f"System: {args.system or 'None'}")
        finalize(success=True)

    try:
        # Log invocation
        tools_enabled = []
        if args.web_search:
            tools_enabled.append("web_search")
        if args.url:
            tools_enabled.append("visit_website")

        tools_label = f" +tools({','.join(tools_enabled)})" if tools_enabled else ""
        logger.info(f"Calling Groq ({args.model}{tools_label})...")

        # Call Groq API
        response = groq_chat(
            prompt=args.query,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            stream=args.stream,
            web_search=args.web_search,
            url=args.url,
            system_prompt=args.system
        )

        # Display results (if not streaming)
        if not args.stream:
            print("\n" + "=" * 70)
            print("🚀 GROQ RESPONSE")
            print("=" * 70)
            print("\n" + response)
            print("\n" + "=" * 70 + "\n")

    except GroqAPIError as e:
        logger.error(f"API call failed: {e}")
        finalize(success=False)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
