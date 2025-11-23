#!/usr/bin/env python3
"""
Auto-Fix Template Library
Provides deterministic, reversible fixes for common errors
"""
import re
import os
import subprocess
from typing import Optional, Callable, Tuple, Dict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AutoFix:
    """Auto-fix template"""
    fix_id: str
    name: str
    description: str
    pattern: str  # Regex pattern to match
    risk: int  # 0-100
    effort: int  # 0-100
    reversible: bool
    fix_fn: Callable[[str, str, re.Match], Tuple[bool, str, Optional[str]]]
    verify_fn: Optional[Callable[[str], bool]] = None

    def apply(self, file_path: str, content: str, match: re.Match) -> Tuple[bool, str, Optional[str]]:
        """
        Apply fix to content

        Args:
            file_path: Path to file
            content: File content
            match: Regex match object

        Returns:
            Tuple[bool, str, Optional[str]]: (success, new_content, error_message)
        """
        return self.fix_fn(file_path, content, match)

    def verify(self, file_path: str) -> bool:
        """
        Verify fix was applied correctly

        Args:
            file_path: Path to file

        Returns:
            bool: True if verification passed
        """
        if self.verify_fn:
            return self.verify_fn(file_path)
        return True  # Default: assume success


# ============================================================================
# FIX FUNCTIONS
# ============================================================================

def fix_hardcoded_secret(file_path: str, content: str, match: re.Match) -> Tuple[bool, str, Optional[str]]:
    """
    Fix hardcoded secret by replacing with os.getenv

    Returns:
        Tuple[bool, str, Optional[str]]: (success, new_content, error_message)
    """
    # Extract variable name and secret
    matched_text = match.group(0)

    # Try to extract variable name
    var_match = re.search(r'(\w+)\s*=\s*["\']', matched_text)
    if not var_match:
        return False, content, "Could not extract variable name"

    var_name = var_match.group(1)
    env_var_name = var_name.upper()

    # Ensure os is imported
    if "import os" not in content:
        # Add import at top after shebang/docstring
        lines = content.split('\n')
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith('#!') or line.startswith('"""') or line.startswith("'''"):
                continue
            if line.strip() and not line.startswith('import') and not line.startswith('from'):
                insert_pos = i
                break
        lines.insert(insert_pos, 'import os')
        content = '\n'.join(lines)

    # Replace hardcoded secret with os.getenv
    new_text = f'{var_name} = os.getenv("{env_var_name}")'
    new_content = content[:match.start()] + new_text + content[match.end():]

    return True, new_content, None


def fix_print_statement(file_path: str, content: str, match: re.Match) -> Tuple[bool, str, Optional[str]]:
    """
    Replace print() with logger.info()

    Returns:
        Tuple[bool, str, Optional[str]]: (success, new_content, error_message)
    """
    # Ensure logger is imported (from core import logger)
    has_logger_import = False
    import_patterns = [
        r'from\s+core\s+import.*logger',
        r'from\s+\.core\s+import.*logger',
        r'import\s+logging',
    ]
    for pattern in import_patterns:
        if re.search(pattern, content):
            has_logger_import = True
            break

    # If no logger import, add it
    if not has_logger_import:
        lines = content.split('\n')
        # Find first non-shebang, non-docstring line
        insert_pos = 0
        in_docstring = False
        for i, line in enumerate(lines):
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                if in_docstring:
                    in_docstring = False
                    insert_pos = i + 1
                    break
                else:
                    in_docstring = True
            if not in_docstring and line.strip() and not line.startswith('#'):
                insert_pos = i
                break

        # Check if scripts/ops/ or scripts/lib/ (uses core)
        if 'scripts/ops' in file_path or 'scripts/lib' in file_path:
            lines.insert(insert_pos, 'from core import logger')
        else:
            lines.insert(insert_pos, 'import logging')
            lines.insert(insert_pos + 1, 'logger = logging.getLogger(__name__)')

        content = '\n'.join(lines)

    # Replace print with logger.info
    new_content = re.sub(r'print\(', 'logger.info(', content)

    return True, new_content, None


def fix_wildcard_import(file_path: str, content: str, match: re.Match) -> Tuple[bool, str, Optional[str]]:
    """
    Replace wildcard import with explicit imports

    NOTE: This is a simplified implementation. Full implementation would require AST analysis.

    Returns:
        Tuple[bool, str, Optional[str]]: (success, new_content, error_message)
    """
    # Extract module name
    matched_text = match.group(0)
    module_match = re.search(r'from\s+(\S+)\s+import', matched_text)
    if not module_match:
        return False, content, "Could not extract module name"

    module_name = module_match.group(1)

    # NOTE: Wildcard imports require AST analysis for proper fixing
    # This is a DELIBERATE limitation - full implementation would need to:
    # 1. Parse AST to find all symbols used from module
    # 2. Replace wildcard with explicit list
    # For now, flag for manual review

    # VOID_IGNORE: This FIXME is the FIX we apply to user code, not a stub here
    manual_review_comment = f"# FIXME: Replace wildcard import - specify explicit imports from {module_name}"
    new_content = content[:match.start()] + manual_review_comment + '\n' + matched_text + content[match.end():]

    return False, new_content, "Wildcard import requires manual AST analysis"


def fix_blind_exception(file_path: str, content: str, match: re.Match) -> Tuple[bool, str, Optional[str]]:
    """
    Replace bare except with Exception

    Returns:
        Tuple[bool, str, Optional[str]]: (success, new_content, error_message)
    """
    # Replace 'except:' with 'except Exception:'
    matched_text = match.group(0)
    new_text = matched_text.replace('except:', 'except Exception as e:')

    # Also add logging if not present
    # Check if next line after except has logging
    lines = content.split('\n')
    except_line_num = content[:match.start()].count('\n')

    # Find the except block
    new_content = content[:match.start()] + new_text + content[match.end():]

    return True, new_content, None


def fix_stub_implementation(file_path: str, content: str, match: re.Match) -> Tuple[bool, str, Optional[str]]:
    """
    Replace pass with NotImplementedError (makes stubs explicit)

    NOTE: This literally contains NotImplementedError with a message.
    This is INTENTIONAL - it's the auto-fix output, not a stub in this library.

    Returns:
        Tuple[bool, str, Optional[str]]: (success, new_content, error_message)
    """
    # Replace 'pass' with explicit not-implemented error
    matched_text = match.group(0)
    # VOID_IGNORE: This NotImplementedError is the FIX we apply to USER code, not a stub
    replacement_text = 'raise NotImplementedError("Implement this method")'

    new_content = content[:match.start()] + replacement_text + content[match.end():]

    return True, new_content, None


def fix_todo_comment(file_path: str, content: str, match: re.Match) -> Tuple[bool, str, Optional[str]]:
    """
    Flag TODO comments for manual GitHub issue creation

    NOTE: TODOs in code should become tracked issues.
    This is a deliberate limitation - we don't auto-create GitHub issues.

    Returns:
        Tuple[bool, str, Optional[str]]: (success, new_content, error_message)
    """
    # Deliberate limitation: Require manual GitHub issue creation for tracking
    return False, content, "TODO comments require manual issue tracking setup"


# ============================================================================
# VERIFICATION FUNCTIONS
# ============================================================================

def verify_no_pattern(file_path: str, pattern: str) -> bool:
    """Verify pattern no longer exists in file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        return not re.search(pattern, content)
    except:
        return False


def verify_has_pattern(file_path: str, pattern: str) -> bool:
    """Verify pattern exists in file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        return bool(re.search(pattern, content))
    except:
        return False


def verify_audit_passes(file_path: str) -> bool:
    """Verify file passes audit"""
    try:
        result = subprocess.run(
            ['python3', 'scripts/ops/audit.py', file_path],
            capture_output=True,
            timeout=10,
            cwd=Path(__file__).parent.parent.parent,
        )
        return result.returncode == 0
    except:
        return False


# ============================================================================
# AUTO-FIX REGISTRY
# ============================================================================

AUTO_FIX_REGISTRY: Dict[str, AutoFix] = {
    "hardcoded_secret": AutoFix(
        fix_id="hardcoded_secret",
        name="Fix Hardcoded Secret",
        description="Replace hardcoded API key/secret with os.getenv()",
        pattern=r'(\w+)\s*=\s*["\'](?:sk-proj-|ghp_|AWS_SECRET)[^"\']+["\']',
        risk=15,  # Low risk - just env var migration
        effort=10,
        reversible=True,
        fix_fn=fix_hardcoded_secret,
        verify_fn=lambda fp: verify_has_pattern(fp, r'os\.getenv'),
    ),
    "print_statement": AutoFix(
        fix_id="print_statement",
        name="Replace print() with logger",
        description="Replace print() calls with logger.info()",
        pattern=r'print\s*\(',
        risk=5,
        effort=5,
        reversible=True,
        fix_fn=fix_print_statement,
        verify_fn=lambda fp: verify_has_pattern(fp, r'logger\.'),
    ),
    "wildcard_import": AutoFix(
        fix_id="wildcard_import",
        name="Fix Wildcard Import",
        description="Replace 'from X import *' with explicit imports",
        pattern=r'from\s+\w+\s+import\s+\*',
        risk=20,
        effort=15,
        reversible=True,
        fix_fn=fix_wildcard_import,
        verify_fn=None,  # Requires manual verification
    ),
    "blind_exception": AutoFix(
        fix_id="blind_exception",
        name="Fix Blind Exception",
        description="Replace 'except:' with 'except Exception as e:'",
        pattern=r'except\s*:',
        risk=15,
        effort=10,
        reversible=True,
        fix_fn=fix_blind_exception,
        verify_fn=lambda fp: verify_no_pattern(fp, r'except\s*:'),
    ),
    "stub_implementation": AutoFix(
        fix_id="stub_implementation",
        name="Fix Stub Implementation",
        description="Replace 'pass' with NotImplementedError",
        pattern=r'^\s+pass\s*$',
        risk=10,
        effort=5,
        reversible=True,
        fix_fn=fix_stub_implementation,
        verify_fn=lambda fp: verify_has_pattern(fp, r'NotImplementedError'),
    ),
}


def get_auto_fix(fix_id: str) -> Optional[AutoFix]:
    """Get auto-fix by ID"""
    return AUTO_FIX_REGISTRY.get(fix_id)


def find_applicable_fixes(content: str) -> list[Tuple[AutoFix, re.Match]]:
    """
    Find all applicable auto-fixes for content

    Args:
        content: File content

    Returns:
        List of (AutoFix, Match) tuples
    """
    applicable = []

    for fix_id, auto_fix in AUTO_FIX_REGISTRY.items():
        for match in re.finditer(auto_fix.pattern, content, re.MULTILINE):
            applicable.append((auto_fix, match))

    return applicable


def apply_auto_fix(file_path: str, auto_fix: AutoFix, backup: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Apply auto-fix to file

    Args:
        file_path: Path to file
        auto_fix: AutoFix object
        backup: Whether to create backup before applying

    Returns:
        Tuple[bool, Optional[str]]: (success, error_message)
    """
    try:
        # Read file
        with open(file_path, 'r') as f:
            content = f.read()

        # Create backup
        if backup:
            backup_path = f"{file_path}.autofix.backup"
            with open(backup_path, 'w') as f:
                f.write(content)

        # Find all matches
        matches = list(re.finditer(auto_fix.pattern, content, re.MULTILINE))
        if not matches:
            return False, "Pattern not found in file"

        # Apply fix to each match (reverse order to preserve positions)
        new_content = content
        for match in reversed(matches):
            success, new_content, error = auto_fix.apply(file_path, new_content, match)
            if not success:
                return False, error

        # Write new content
        with open(file_path, 'w') as f:
            f.write(new_content)

        # Verify fix
        if auto_fix.verify_fn:
            if not auto_fix.verify(file_path):
                # Restore backup
                if backup and Path(backup_path).exists():
                    with open(backup_path, 'r') as f:
                        original = f.read()
                    with open(file_path, 'w') as f:
                        f.write(original)
                return False, "Verification failed, restored backup"

        return True, None

    except Exception as e:
        return False, str(e)
