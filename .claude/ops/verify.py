#!/usr/bin/env python3
"""
The Fact-Checker: Validates system state assertions. Returns True/False. Use this BEFORE claiming something is true.
"""
import sys
import os
import socket
import subprocess

# Add .claude/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
# Find project root by looking for '.claude' directory
_current = _script_dir
while _current != "/":
    if os.path.exists(os.path.join(_current, ".claude", "lib", "core.py")):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with .claude/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, ".claude", "lib"))
from core import setup_script, finalize, logger, handle_debug  # noqa: E402


def check_file_exists(target):
    """Check if a file or directory exists."""
    return os.path.exists(target)


def check_grep_text(target, expected):
    """Check if expected text exists in file."""
    try:
        with open(target, "r") as f:
            content = f.read()
            return expected in content
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.debug(f"Error reading file: {e}")
        return False


def check_port_open(target, host="localhost"):
    """Check if a port is open on localhost."""
    try:
        port = int(target)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except ValueError:
        logger.error(f"Invalid port number: {target}")
        return False
    except Exception as e:
        logger.debug(f"Error checking port: {e}")
        return False


def check_command_success(target, timeout=10):
    """Check if a command exits with code 0."""
    try:
        result = subprocess.run(
            target, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.debug(f"Command timed out after {timeout}s")
        return False
    except Exception as e:
        logger.debug(f"Error running command: {e}")
        return False


def main():
    parser = setup_script(
        "The Fact-Checker: Validates system state assertions. Returns True/False. Use this BEFORE claiming something is true."
    )

    # Custom arguments
    parser.add_argument(
        "check",
        choices=["file_exists", "grep_text", "port_open", "command_success"],
        help="Type of check to perform",
    )
    parser.add_argument("target", help="The file, port, or command to check")
    parser.add_argument("--expected", help="Expected text for grep_text check")
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host for port_open check (default: localhost)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout for command_success check (default: 10s)",
    )

    args = parser.parse_args()
    handle_debug(args)

    # Validation
    if args.check == "grep_text" and not args.expected:
        logger.error("grep_text check requires --expected argument")
        finalize(success=False)

    logger.info(f"Verifying: {args.check} on '{args.target}'")

    if args.dry_run:
        logger.warning("⚠️  DRY RUN: Would perform check but not enforce result")
        finalize(success=True)

    try:
        # Perform the check
        verified = False

        if args.check == "file_exists":
            verified = check_file_exists(args.target)
            claim = f"File/directory exists: {args.target}"

        elif args.check == "grep_text":
            verified = check_grep_text(args.target, args.expected)
            claim = f"File '{args.target}' contains '{args.expected}'"

        elif args.check == "port_open":
            verified = check_port_open(args.target, args.host)
            claim = f"Port {args.target} is open on {args.host}"

        elif args.check == "command_success":
            verified = check_command_success(args.target, args.timeout)
            claim = f"Command '{args.target}' exits with code 0"

        # Report result
        if verified:
            print("\n" + "=" * 70)
            print("✅ VERIFIED")
            print("=" * 70)
            print(f"CLAIM: {claim}")
            print("RESULT: TRUE")
            print("=" * 70 + "\n")
            logger.info("Verification PASSED")
            finalize(success=True)
        else:
            print("\n" + "=" * 70)
            print("❌ FALSE CLAIM")
            print("=" * 70)
            print(f"CLAIM: {claim}")
            print("RESULT: FALSE")
            print("=" * 70 + "\n")
            logger.error("Verification FAILED")
            finalize(success=False)

    except Exception as e:
        logger.error(f"Verification error: {e}")
        print("\n" + "=" * 70)
        print("❌ VERIFICATION ERROR")
        print("=" * 70)
        print(f"ERROR: {e}")
        print("=" * 70 + "\n")
        finalize(success=False)


if __name__ == "__main__":
    main()
