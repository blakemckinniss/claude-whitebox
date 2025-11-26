#!/usr/bin/env python3
"""
CodeRabbit: AI-powered code review and commit workflow

Modes:
  - Review only (default): Run CodeRabbit review on changes
  - Commit mode (--commit): Review uncommitted changes, commit if clean
"""
import sys
import os
import subprocess  # nosec B404
import re

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


def has_critical_issues(output: str) -> bool:
    """
    Parse CodeRabbit output for critical issues that should block commit.

    Returns True if critical issues found.
    """
    if not output:
        return False

    # Patterns indicating critical issues
    critical_patterns = [
        r"Type:\s*potential_issue",  # CodeRabbit marks issues as potential_issue
        r"Critical\s*bug",
        r"NameError",
        r"undefined\s+variable",
        r"CRITICAL",
    ]

    for pattern in critical_patterns:
        if re.search(pattern, output, re.IGNORECASE):
            return True

    return False


def run_git_commit(message: str, dry_run: bool = False) -> tuple[bool, str]:
    """
    Run git commit with the given message.

    Returns (success, output).
    """
    # First check if there are changes to commit
    status_result = subprocess.run(  # nosec B603 B607
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
    )

    if not status_result.stdout.strip():
        return False, "No changes to commit"

    if dry_run:
        return True, f"Would commit with message: {message}"

    # Stage changes (git add -A)
    subprocess.run(["git", "add", "-A"], check=True)  # nosec B603 B607

    # Commit with message
    commit_result = subprocess.run(  # nosec B603 B607
        ["git", "commit", "-m", message],
        capture_output=True,
        text=True,
    )

    if commit_result.returncode == 0:
        return True, commit_result.stdout
    return False, commit_result.stderr or commit_result.stdout


def build_command(review_type, base_branch, base_commit, config_files, cwd, interactive):
    """Build CodeRabbit CLI command."""
    cmd = ["coderabbit", "review", "--type", review_type]

    if base_branch:
        cmd.extend(["--base", base_branch])
    if base_commit:
        cmd.extend(["--base-commit", base_commit])
    if config_files:
        cmd.extend(["--config"] + config_files)
    if cwd:
        cmd.extend(["--cwd", cwd])
    if not interactive:
        cmd.append("--plain")

    return cmd


def execute_review(cmd, timeout, cwd):
    """Execute CodeRabbit review subprocess."""
    result = subprocess.run(  # nosec B603
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
    )
    return result


def run_coderabbit(
    review_type="all",
    base_branch=None,
    base_commit=None,
    config_files=None,
    interactive=False,
    cwd=None,
    dry_run=False,
    timeout=300,
):
    """
    Run CodeRabbit CLI review.

    Args:
        review_type: Type of review (all, committed, uncommitted)
        base_branch: Base branch for comparison
        base_commit: Base commit for comparison
        config_files: List of additional instruction files
        interactive: Use interactive mode (default is plain text)
        cwd: Working directory
        dry_run: Show command without executing
        timeout: Timeout in seconds (default: 300)

    Returns:
        tuple: (success: bool, output: str)
    """
    cmd = build_command(review_type, base_branch, base_commit, config_files, cwd, interactive)

    logger.info("=" * 70)
    logger.info("🐰 CodeRabbit CLI Review")
    logger.info("=" * 70)
    logger.info(f"Command: {' '.join(cmd)}")
    logger.info("=" * 70)

    if dry_run:
        logger.info("DRY RUN: Would execute the above command")
        return True, ""

    logger.info("Starting CodeRabbit review (this may take several minutes)...")

    try:
        result = execute_review(cmd, timeout, cwd)
        output = result.stdout if result.stdout else result.stderr

        if result.returncode == 0:
            logger.info(output)
            logger.info("=" * 70)
            logger.info("✅ CodeRabbit review completed successfully")
            logger.info("=" * 70)
            return True, output

        logger.error(output)
        logger.error("=" * 70)
        logger.error("❌ CodeRabbit review failed")
        logger.error("=" * 70)
        logger.error(f"CodeRabbit exited with code {result.returncode}")
        return False, output

    except FileNotFoundError:
        install_msg = (
            "CodeRabbit CLI not found. Install with:\n"
            "    curl -fsSL https://install.coderabbit.ai | sh\n\n"
            "After installation, ensure ~/.local/bin is in your PATH."
        )
        logger.error(install_msg)
        return False, install_msg

    except subprocess.TimeoutExpired:
        logger.error(f"CodeRabbit review timed out ({timeout}s limit)")
        return False, f"Timeout after {timeout} seconds"

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False, str(e)


def main():
    parser = setup_script("Wrapper for CodeRabbit CLI code review tool")

    parser.add_argument(
        "-t",
        "--type",
        choices=["all", "committed", "uncommitted"],
        default="all",
        help="Review type (default: all)",
    )
    parser.add_argument(
        "-b", "--base", help="Base branch for comparison"
    )
    parser.add_argument(
        "--base-commit", help="Base commit on current branch for comparison"
    )
    parser.add_argument(
        "-c",
        "--config",
        nargs="+",
        help="Additional instruction files for CodeRabbit AI",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Use interactive mode (default is plain text)",
    )
    parser.add_argument(
        "--cwd", help="Working directory path"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Review uncommitted changes, then commit if no critical issues",
    )
    parser.add_argument(
        "-m",
        "--message",
        help="Commit message (used with --commit)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Commit even if CodeRabbit finds issues (with --commit)",
    )

    args = parser.parse_args()
    handle_debug(args)

    if args.dry_run:
        logger.info("🔍 DRY RUN MODE: Showing command preview only")

    # Commit mode: review uncommitted, then commit if clean
    if args.commit:
        logger.info("=" * 70)
        logger.info("🐰 CodeRabbit Commit Mode")
        logger.info("=" * 70)

        # Force uncommitted review type
        review_type = "uncommitted"

        try:
            success, output = run_coderabbit(
                review_type=review_type,
                base_branch=args.base,
                base_commit=args.base_commit,
                config_files=args.config,
                interactive=False,  # Need plain output for parsing
                cwd=args.cwd,
                dry_run=args.dry_run,
                timeout=args.timeout,
            )

            if not success:
                logger.error("CodeRabbit review failed - cannot commit")
                finalize(success=False)

            # Check for critical issues
            found_issues = has_critical_issues(output)

            if found_issues and not args.force:
                logger.error("=" * 70)
                logger.error("🚫 COMMIT BLOCKED: Critical issues found")
                logger.error("=" * 70)
                logger.error("Fix the issues above, or use --force to commit anyway")
                finalize(success=False)

            if found_issues and args.force:
                logger.warning("⚠️ Committing despite issues (--force used)")

            # Generate commit message
            commit_msg = args.message
            if not commit_msg:
                commit_msg = "chore: changes reviewed by CodeRabbit"
                if not found_issues:
                    commit_msg = "feat: changes (CodeRabbit review passed)"

            # Perform commit
            commit_success, commit_output = run_git_commit(commit_msg, dry_run=args.dry_run)

            if commit_success:
                logger.info("=" * 70)
                logger.info("✅ Commit successful")
                logger.info("=" * 70)
                logger.info(commit_output)
                finalize(success=True)
            else:
                logger.error(f"Commit failed: {commit_output}")
                finalize(success=False)

        except Exception as e:
            logger.error(f"Commit workflow failed: {e}")
            import traceback
            traceback.print_exc()
            finalize(success=False)

        return  # Exit after commit mode

    # Standard review mode
    try:
        success, output = run_coderabbit(
            review_type=args.type,
            base_branch=args.base,
            base_commit=args.base_commit,
            config_files=args.config,
            interactive=args.interactive,
            cwd=args.cwd,
            dry_run=args.dry_run,
            timeout=args.timeout,
        )

        if success:
            finalize(success=True)
        else:
            finalize(success=False)

    except Exception as e:
        logger.error(f"CodeRabbit wrapper failed: {e}")
        import traceback
        traceback.print_exc()
        finalize(success=False)


if __name__ == "__main__":
    main()
