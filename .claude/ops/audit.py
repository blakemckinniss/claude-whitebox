#!/usr/bin/env python3
"""
The Sentinel: Runs static analysis and anti-pattern detection on target files
"""
import sys
import os
import subprocess
import re

# Add .claude/lib to path (minimal bootstrap)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
from core import setup_script, finalize, logger, handle_debug, get_project_root  # noqa: E402


def check_ruff(filepath):
    """Run Ruff linter on the file."""
    print("\n" + "=" * 70)
    print("🔍 [SENTINEL] Running Ruff Linter...")
    print("=" * 70)

    try:
        result = subprocess.run(
            ["ruff", "check", filepath], capture_output=True, text=True
        ,
        timeout=10)

        if result.returncode == 0:
            print("  ✅ Ruff: No linting errors")
            return True
        else:
            print("  ❌ Ruff found issues:")
            print(result.stdout)
            return False

    except FileNotFoundError:
        logger.warning("  ⚠️  Ruff not installed - skipping")
        return True
    except Exception as e:
        logger.warning(f"  ⚠️  Ruff check failed: {e}")
        return True


def check_bandit(filepath):
    """Run Bandit security scanner on the file."""
    print("\n" + "=" * 70)
    print("🛡️  [SENTINEL] Running Bandit Security Scanner...")
    print("=" * 70)

    try:
        result = subprocess.run(
            ["bandit", "-r", filepath, "-f", "txt"], capture_output=True, text=True
        ,
        timeout=10)

        # Bandit returns 0 if no issues, 1 if issues found
        if result.returncode == 0:
            print("  ✅ Bandit: No security issues")
            return True
        else:
            print("  ❌ Bandit found security issues:")
            print(result.stdout)
            return False

    except FileNotFoundError:
        logger.warning("  ⚠️  Bandit not installed - skipping")
        return True
    except Exception as e:
        logger.warning(f"  ⚠️  Bandit check failed: {e}")
        return True


def check_complexity(filepath):
    """Check cyclomatic complexity using Radon."""
    print("\n" + "=" * 70)
    print("📊 [SENTINEL] Checking Cyclomatic Complexity...")
    print("=" * 70)

    try:
        # Import radon here to avoid hard dependency
        from radon.complexity import cc_visit

        with open(filepath, "r") as f:
            code = f.read()

        complexity_scores = cc_visit(code)
        max_complexity = 10
        violations = []

        for block in complexity_scores:
            if block.complexity > max_complexity:
                violations.append((block.name, block.complexity, block.lineno))

        if violations:
            print(f"  ❌ Complexity violations (max allowed: {max_complexity}):")
            for name, score, lineno in violations:
                print(f"     Line {lineno}: {name} has complexity {score}")
            return False
        else:
            print(f"  ✅ All functions have complexity ≤ {max_complexity}")
            return True

    except ImportError:
        logger.warning("  ⚠️  Radon not installed - skipping")
        return True
    except Exception as e:
        logger.warning(f"  ⚠️  Complexity check failed: {e}")
        return True


def check_custom_anti_patterns(filepath, strict=False):
    """Check for custom anti-patterns defined in anti_patterns.md."""
    print("\n" + "=" * 70)
    print("🚫 [SENTINEL] Checking Custom Anti-Patterns...")
    print("=" * 70)

    # Define anti-patterns with severity levels
    anti_patterns = [
        # Critical security issues
        (
            r'sk-proj-|ghp_|AWS_SECRET|api[_-]?key\s*=\s*["\'](?!.*getenv)',
            "🔴 CRITICAL: Hardcoded secret detected",
            True,
        ),
        (r"shell\s*=\s*True", "🔴 CRITICAL: Shell injection risk (shell=True)", True),
        (
            r'cursor\.execute\([^?]*f["\']',
            "🔴 CRITICAL: SQL injection risk (f-string in query)",
            True,
        ),
        # Warning-level issues
        (r"except\s*:", "🟡 WARNING: Blind exception catching", False),
        (r"except\s+Exception\s*:", "🟡 WARNING: Catching Exception too broad", False),
        (r"global\s+\w+", "🟡 WARNING: Global variable mutation", False),
        (r"print\s*\(", "🟡 WARNING: Use logger.info instead of print", False),
        (
            r"pdb\.set_trace\(\)|breakpoint\(\)",
            "🟡 WARNING: Debug breakpoint left in code",
            False,
        ),
        (
            r"from\s+\w+\s+import\s+\*",
            "🟡 WARNING: Wildcard import (from X import *)",
            False,
        ),
        # Info-level issues
        (r"TODO:", "🔵 INFO: TODO comment found", False),
        (r"#\s*[^#\n]{50,}\n\s*#", "🔵 INFO: Large commented-out code block", False),
    ]

    try:
        with open(filepath, "r") as f:
            content = f.read()

        violations = []
        critical_found = False

        for pattern, message, is_critical in anti_patterns:
            matches = list(re.finditer(pattern, content, re.MULTILINE))
            if matches:
                for match in matches:
                    # Find line number
                    lineno = content[: match.start()].count("\n") + 1
                    violations.append((lineno, message, is_critical))
                    if is_critical:
                        critical_found = True

        if violations:
            print(f"  Found {len(violations)} anti-pattern(s):")
            for lineno, message, is_critical in sorted(violations):
                print(f"     Line {lineno}: {message}")

            if critical_found:
                print("\n  🔴 CRITICAL issues must be fixed immediately!")
                return False
            else:
                print("\n  ⚠️  Warnings should be addressed")
                if strict:
                    print("  ⚠️  STRICT MODE: Warnings cause failure")
                    return False
                return True  # Warnings don't fail the audit in normal mode
        else:
            print("  ✅ No anti-patterns detected")
            return True

    except Exception as e:
        logger.error(f"  ❌ Anti-pattern check failed: {e}")
        return False


def check_sdk_compliance(filepath):
    """Check if the script follows Whitebox SDK standards."""
    print("\n" + "=" * 70)
    print("📋 [SENTINEL] Checking SDK Compliance...")
    print("=" * 70)

    try:
        with open(filepath, "r") as f:
            content = f.read()

        violations = []

        # Check for required imports
        if "from core import" not in content:
            violations.append("Missing SDK imports (from core import ...)")

        if "setup_script" not in content:
            violations.append("Missing setup_script() call")

        if "finalize" not in content:
            violations.append("Missing finalize() call")

        if "--dry-run" not in content and "dry_run" not in content:
            violations.append("Missing dry-run support")

        # Check for docstring
        if not content.strip().startswith('#!/usr/bin/env python3\n"""'):
            violations.append("Missing module docstring")

        if violations:
            print("  ⚠️  SDK compliance issues:")
            for violation in violations:
                print(f"     - {violation}")
            return False
        else:
            print("  ✅ SDK compliant")
            return True

    except Exception as e:
        logger.error(f"  ❌ SDK compliance check failed: {e}")
        return True  # Don't fail on check error


def main():
    parser = setup_script(
        "The Sentinel: Runs static analysis and anti-pattern detection on target files"
    )

    parser.add_argument("target", help="Python file to audit")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings (not just critical issues)",
    )

    args = parser.parse_args()
    handle_debug(args)

    target_path = os.path.abspath(args.target)

    if not os.path.exists(target_path):
        logger.error(f"File not found: {target_path}")
        finalize(success=False)

    if not target_path.endswith(".py"):
        logger.error("Target must be a Python file (.py)")
        finalize(success=False)

    print("\n" + "=" * 70)
    print("🛡️  THE SENTINEL: Code Quality Gate")
    print("=" * 70)
    print(f"  Target: {target_path}")
    print(f"  Strict Mode: {args.strict}")
    print("=" * 70)

    if args.dry_run:
        logger.info("Dry-run mode: Would run audits but not fail")
        finalize(success=True)

    try:
        results = {
            "ruff": check_ruff(target_path),
            "bandit": check_bandit(target_path),
            "complexity": check_complexity(target_path),
            "anti_patterns": check_custom_anti_patterns(
                target_path, strict=args.strict
            ),
            "sdk_compliance": check_sdk_compliance(target_path),
        }

        # Summary
        print("\n" + "=" * 70)
        print("📊 AUDIT SUMMARY")
        print("=" * 70)

        passed = sum(1 for v in results.values() if v)
        failed = len(results) - passed

        for check, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status}: {check}")

        print("=" * 70)

        # Determine overall result
        # Critical failure = bandit failed (always critical)
        # Anti-patterns can fail due to critical issues OR strict mode warnings
        critical_failed = not results["bandit"]

        if critical_failed:
            print("🔴 CRITICAL FAILURE: Security issues detected")
            print("   Fix these issues immediately before committing!")
            logger.error("Audit failed with critical security issues")
            finalize(success=False)
        elif failed > 0 and args.strict:
            print(f"⚠️  STRICT MODE FAILURE: {failed} check(s) failed")
            logger.warning(f"Audit failed in strict mode ({failed} issues)")
            finalize(success=False)
        elif failed > 0:
            # Check if anti_patterns failed due to critical patterns (not strict mode)
            # If anti_patterns failed in non-strict mode, it must be critical patterns
            if not results["anti_patterns"] and not args.strict:
                print("🔴 CRITICAL FAILURE: Critical anti-patterns detected")
                print("   Fix these issues immediately before committing!")
                logger.error("Audit failed with critical anti-patterns")
                finalize(success=False)
            else:
                print(f"⚠️  {failed} warning(s) - consider fixing")
                logger.warning(f"Audit passed with {failed} warnings")
                finalize(success=True)
        else:
            print("✅ ALL CHECKS PASSED")
            logger.info("Audit passed successfully")
            finalize(success=True)

    except Exception as e:
        logger.error(f"Audit failed: {e}")
        import traceback

        traceback.print_exc()
        finalize(success=False)


if __name__ == "__main__":
    main()
