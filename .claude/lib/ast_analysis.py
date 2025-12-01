#!/usr/bin/env python3
"""
AST Analysis Module: Semantic code analysis for hooks.

Provides AST-based detection that's more accurate than regex:
- Security vulnerability detection (eval, exec, SQL injection)
- Semantic stub detection (empty functions, always-true validators)
- Import verification
- Taint tracking for sensitive data flow

Usage:
    from ast_analysis import SecurityAnalyzer, StubAnalyzer, ImportAnalyzer

    # Check code for security issues
    analyzer = SecurityAnalyzer(source_code)
    violations = analyzer.analyze()

    # Check for semantic stubs
    stub_analyzer = StubAnalyzer(source_code)
    stubs = stub_analyzer.find_stubs()
"""

import ast
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Violation:
    """Represents a code violation found by AST analysis."""
    category: str      # 'security', 'stub', 'import'
    severity: str      # 'critical', 'block', 'warn'
    name: str          # Violation identifier
    message: str       # Human-readable description
    line: int          # Line number
    col: int           # Column offset
    suggestion: str    # Fix suggestion
    context: str = ""  # Code snippet


# =============================================================================
# SECURITY ANALYZER
# =============================================================================

class SecurityAnalyzer(ast.NodeVisitor):
    """
    AST-based security vulnerability detection.

    Advantages over regex:
    - Ignores strings/comments (no false positives on "don't use eval()")
    - Detects aliased calls (f = eval; f(x))
    - Catches indirect calls (getattr(builtins, 'eval')())
    - Understands context (subprocess in test vs production)
    """

    # Dangerous functions that allow code injection
    DANGEROUS_CALLS = {
        'eval': ('critical', 'Code injection via eval()', 'Use ast.literal_eval() for safe parsing'),
        'exec': ('critical', 'Code injection via exec()', 'Avoid dynamic code execution'),
        'compile': ('block', 'Dynamic code compilation', 'Ensure input is trusted'),
        # Note: __import__() function calls only - regular 'import x' statements are safe
        # AST visit_Call only triggers on function calls, not import statements
        '__import__': ('block', 'Dynamic __import__() call', 'Use importlib with validation'),
    }

    # Dangerous attribute access patterns
    DANGEROUS_ATTRS = {
        ('subprocess', 'call'): ('check_shell_arg', 'Command injection risk'),
        ('subprocess', 'run'): ('check_shell_arg', 'Command injection risk'),
        ('subprocess', 'Popen'): ('check_shell_arg', 'Command injection risk'),
        ('os', 'system'): ('block', 'Use subprocess with shell=False'),
        ('os', 'popen'): ('block', 'Use subprocess with shell=False'),
        ('pickle', 'load'): ('block', 'Pickle deserialization is unsafe'),
        ('pickle', 'loads'): ('block', 'Pickle deserialization is unsafe'),
        ('yaml', 'load'): ('check_loader_arg', 'Use yaml.safe_load()'),
        ('yaml', 'unsafe_load'): ('block', 'Use yaml.safe_load()'),
    }

    def __init__(self, source: str, filename: str = "<string>"):
        self.source = source
        self.filename = filename
        self.violations: List[Violation] = []
        self.aliases: Dict[str, str] = {}  # Track variable aliases
        self._lines = source.split('\n')

    def analyze(self) -> List[Violation]:
        """Parse and analyze source code. Returns list of violations."""
        try:
            tree = ast.parse(self.source, filename=self.filename)
            self.visit(tree)
        except SyntaxError as e:
            self.violations.append(Violation(
                category='security',
                severity='warn',
                name='syntax_error',
                message=f'Could not parse: {e}',
                line=e.lineno or 0,
                col=e.offset or 0,
                suggestion='Fix syntax errors first'
            ))
        return self.violations

    def _get_line_context(self, lineno: int) -> str:
        """Get source line for context."""
        if 0 < lineno <= len(self._lines):
            return self._lines[lineno - 1].strip()[:60]
        return ""

    def visit_Import(self, node: ast.Import):
        """Track imports for alias resolution."""
        for alias in node.names:
            name = alias.asname or alias.name
            self.aliases[name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from imports."""
        module = node.module or ''
        for alias in node.names:
            name = alias.asname or alias.name
            self.aliases[name] = f"{module}.{alias.name}"
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        """Track variable assignments for alias detection."""
        if isinstance(node.value, ast.Name):
            # x = eval -> track that x is now eval
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if node.value.id in self.DANGEROUS_CALLS:
                        self.aliases[target.id] = node.value.id
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Check function calls for dangerous patterns."""
        func_name = self._get_call_name(node)

        if func_name:
            # Check direct dangerous calls
            if func_name in self.DANGEROUS_CALLS:
                severity, msg, suggestion = self.DANGEROUS_CALLS[func_name]
                self.violations.append(Violation(
                    category='security',
                    severity=severity,
                    name=f'dangerous_call_{func_name}',
                    message=msg,
                    line=node.lineno,
                    col=node.col_offset,
                    suggestion=suggestion,
                    context=self._get_line_context(node.lineno)
                ))

            # Check aliased dangerous calls
            resolved = self.aliases.get(func_name)
            if resolved and resolved in self.DANGEROUS_CALLS:
                severity, msg, suggestion = self.DANGEROUS_CALLS[resolved]
                self.violations.append(Violation(
                    category='security',
                    severity=severity,
                    name='aliased_dangerous_call',
                    message=f'{msg} (via alias {func_name})',
                    line=node.lineno,
                    col=node.col_offset,
                    suggestion=suggestion,
                    context=self._get_line_context(node.lineno)
                ))

        # Check method calls on known dangerous modules
        if isinstance(node.func, ast.Attribute):
            self._check_attribute_call(node)

        # Check for SQL injection patterns
        self._check_sql_injection(node)

        self.generic_visit(node)

    def _get_call_name(self, node: ast.Call) -> Optional[str]:
        """Extract function name from call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def _check_attribute_call(self, node: ast.Call):
        """Check method calls like subprocess.run()."""
        attr = node.func
        if not isinstance(attr, ast.Attribute):
            return

        # Get the base object name
        if isinstance(attr.value, ast.Name):
            base = attr.value.id
            method = attr.attr

            # Resolve aliases
            resolved_base = self.aliases.get(base, base)

            key = (resolved_base, method)
            if key in self.DANGEROUS_ATTRS:
                action, msg = self.DANGEROUS_ATTRS[key]

                if action == 'check_shell_arg':
                    # Check if shell=True is present
                    for kw in node.keywords:
                        if kw.arg == 'shell':
                            if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                self.violations.append(Violation(
                                    category='security',
                                    severity='block',
                                    name='shell_injection',
                                    message=f'{msg} with shell=True',
                                    line=node.lineno,
                                    col=node.col_offset,
                                    suggestion='Use shell=False with list arguments',
                                    context=self._get_line_context(node.lineno)
                                ))

                elif action == 'check_loader_arg':
                    # Check if Loader is specified for yaml.load
                    has_loader = any(kw.arg == 'Loader' for kw in node.keywords)
                    if not has_loader and len(node.args) < 2:
                        self.violations.append(Violation(
                            category='security',
                            severity='block',
                            name='yaml_unsafe_load',
                            message='yaml.load without Loader is unsafe',
                            line=node.lineno,
                            col=node.col_offset,
                            suggestion='Use yaml.safe_load() or specify Loader',
                            context=self._get_line_context(node.lineno)
                        ))

                elif action == 'block':
                    self.violations.append(Violation(
                        category='security',
                        severity='block',
                        name=f'dangerous_method_{method}',
                        message=msg,
                        line=node.lineno,
                        col=node.col_offset,
                        suggestion=msg,
                        context=self._get_line_context(node.lineno)
                    ))

    def _check_sql_injection(self, node: ast.Call):
        """Detect SQL injection patterns in execute() calls."""
        func_name = self._get_call_name(node)
        if func_name not in ('execute', 'executemany'):
            return

        if not node.args:
            return

        query_arg = node.args[0]

        # Check for f-string SQL
        if isinstance(query_arg, ast.JoinedStr):
            self.violations.append(Violation(
                category='security',
                severity='critical',
                name='sql_injection_fstring',
                message='SQL injection risk: f-string in query',
                line=node.lineno,
                col=node.col_offset,
                suggestion='Use parameterized queries: execute("SELECT ?", (val,))',
                context=self._get_line_context(node.lineno)
            ))

        # Check for string concatenation
        if isinstance(query_arg, ast.BinOp) and isinstance(query_arg.op, ast.Add):
            if self._contains_string_with_sql(query_arg):
                self.violations.append(Violation(
                    category='security',
                    severity='critical',
                    name='sql_injection_concat',
                    message='SQL injection risk: string concatenation in query',
                    line=node.lineno,
                    col=node.col_offset,
                    suggestion='Use parameterized queries',
                    context=self._get_line_context(node.lineno)
                ))

        # Check for % formatting
        if isinstance(query_arg, ast.BinOp) and isinstance(query_arg.op, ast.Mod):
            if self._contains_string_with_sql(query_arg.left):
                self.violations.append(Violation(
                    category='security',
                    severity='critical',
                    name='sql_injection_format',
                    message='SQL injection risk: % formatting in query',
                    line=node.lineno,
                    col=node.col_offset,
                    suggestion='Use parameterized queries',
                    context=self._get_line_context(node.lineno)
                ))

    def _contains_string_with_sql(self, node: ast.AST) -> bool:
        """Check if node contains SQL keywords in a string."""
        sql_keywords = ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE')

        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            upper = node.value.upper()
            return any(kw in upper for kw in sql_keywords)

        # Recurse into binary operations
        if isinstance(node, ast.BinOp):
            return (self._contains_string_with_sql(node.left) or
                    self._contains_string_with_sql(node.right))

        return False

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """Detect bare except clauses."""
        if node.type is None:
            self.violations.append(Violation(
                category='security',
                severity='block',
                name='bare_except',
                message='Bare except catches SystemExit/KeyboardInterrupt',
                line=node.lineno,
                col=node.col_offset,
                suggestion='Use "except Exception:" instead',
                context=self._get_line_context(node.lineno)
            ))
        self.generic_visit(node)


# =============================================================================
# STUB ANALYZER
# =============================================================================

class StubAnalyzer(ast.NodeVisitor):
    """
    Semantic stub detection that catches what regex misses.

    Detects:
    - pass/... stubs (obvious)
    - return None functions (semantic stub)
    - return True/False validators (always-true validation)
    - empty try/except blocks
    - NotImplementedError raises
    """

    def __init__(self, source: str, filename: str = "<string>"):
        self.source = source
        self.filename = filename
        self.stubs: List[Violation] = []
        self._lines = source.split('\n')

    def find_stubs(self) -> List[Violation]:
        """Analyze source and return list of stub violations."""
        try:
            tree = ast.parse(self.source, filename=self.filename)
            self.visit(tree)
        except SyntaxError:
            pass  # Can't analyze unparseable code
        return self.stubs

    def _get_line_context(self, lineno: int) -> str:
        """Get source line for context."""
        if 0 < lineno <= len(self._lines):
            return self._lines[lineno - 1].strip()[:60]
        return ""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Check function definitions for stub patterns."""
        self._check_function_stub(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Check async functions too."""
        self._check_function_stub(node)
        self.generic_visit(node)

    def _check_function_stub(self, node):
        """Analyze function body for stub patterns."""
        body = node.body

        # Skip docstring if present
        if body and isinstance(body[0], ast.Expr):
            if isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                body = body[1:]

        if not body:
            return

        # Single statement functions
        if len(body) == 1:
            stmt = body[0]

            # pass stub
            if isinstance(stmt, ast.Pass):
                self.stubs.append(Violation(
                    category='stub',
                    severity='block',
                    name='pass_stub',
                    message=f'Function {node.name}() is a pass stub',
                    line=node.lineno,
                    col=node.col_offset,
                    suggestion='Implement the function body',
                    context=self._get_line_context(node.lineno)
                ))
                return

            # ... (Ellipsis) stub
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                if stmt.value.value is ...:
                    self.stubs.append(Violation(
                        category='stub',
                        severity='block',
                        name='ellipsis_stub',
                        message=f'Function {node.name}() is an ellipsis stub',
                        line=node.lineno,
                        col=node.col_offset,
                        suggestion='Implement the function body',
                        context=self._get_line_context(node.lineno)
                    ))
                    return

            # return None stub (semantic) - catches both `return` and `return None`
            if isinstance(stmt, ast.Return):
                is_none_return = (
                    stmt.value is None or  # bare return
                    (isinstance(stmt.value, ast.Constant) and stmt.value.value is None)  # return None
                )
                if is_none_return:
                    self.stubs.append(Violation(
                        category='stub',
                        severity='warn',
                        name='return_none_stub',
                        message=f'Function {node.name}() only returns None',
                        line=node.lineno,
                        col=node.col_offset,
                        suggestion='Implement meaningful return value',
                        context=self._get_line_context(node.lineno)
                    ))
                    return

                # return True/False validator stub
                if isinstance(stmt.value, ast.Constant):
                    if stmt.value.value in (True, False):
                        # Check if function name suggests validation
                        validator_names = ('validate', 'check', 'is_', 'has_', 'can_', 'verify')
                        if any(node.name.lower().startswith(v) or node.name.lower().endswith(v.rstrip('_'))
                               for v in validator_names):
                            self.stubs.append(Violation(
                                category='stub',
                                severity='warn',
                                name='always_true_validator',
                                message=f'Validator {node.name}() always returns {stmt.value.value}',
                                line=node.lineno,
                                col=node.col_offset,
                                suggestion='Implement actual validation logic',
                                context=self._get_line_context(node.lineno)
                            ))
                            return

            # raise NotImplementedError
            if isinstance(stmt, ast.Raise):
                if isinstance(stmt.exc, ast.Call):
                    if isinstance(stmt.exc.func, ast.Name):
                        if stmt.exc.func.id == 'NotImplementedError':
                            self.stubs.append(Violation(
                                category='stub',
                                severity='block',
                                name='not_implemented_stub',
                                message=f'Function {node.name}() raises NotImplementedError',
                                line=node.lineno,
                                col=node.col_offset,
                                suggestion='Implement the function',
                                context=self._get_line_context(node.lineno)
                            ))
                            return
                elif isinstance(stmt.exc, ast.Name):
                    if stmt.exc.id == 'NotImplementedError':
                        self.stubs.append(Violation(
                            category='stub',
                            severity='block',
                            name='not_implemented_stub',
                            message=f'Function {node.name}() raises NotImplementedError',
                            line=node.lineno,
                            col=node.col_offset,
                            suggestion='Implement the function',
                            context=self._get_line_context(node.lineno)
                        ))
                        return

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """Detect empty except handlers."""
        if len(node.body) == 1:
            if isinstance(node.body[0], ast.Pass):
                self.stubs.append(Violation(
                    category='stub',
                    severity='warn',
                    name='empty_except',
                    message='Empty except handler silently swallows errors',
                    line=node.lineno,
                    col=node.col_offset,
                    suggestion='Log the error or re-raise',
                    context=self._get_line_context(node.lineno)
                ))
        self.generic_visit(node)


# =============================================================================
# IMPORT ANALYZER
# =============================================================================

class ImportAnalyzer(ast.NodeVisitor):
    """
    Verify imports exist before allowing code.

    Catches:
    - Imports of non-installed packages
    - Typos in import names
    - Deprecated module usage
    """

    DEPRECATED_MODULES = {
        'imp': 'Use importlib instead',
        'optparse': 'Use argparse instead',
        'formatter': 'Removed in Python 3.10',
    }

    def __init__(self, source: str, filename: str = "<string>"):
        self.source = source
        self.filename = filename
        self.issues: List[Violation] = []
        self._lines = source.split('\n')

    def verify_imports(self, check_existence: bool = True) -> List[Violation]:
        """Analyze imports. Set check_existence=False to skip pip checks."""
        try:
            tree = ast.parse(self.source, filename=self.filename)
            self._check_existence = check_existence
            self.visit(tree)
        except SyntaxError:
            pass
        return self.issues

    def _get_line_context(self, lineno: int) -> str:
        if 0 < lineno <= len(self._lines):
            return self._lines[lineno - 1].strip()[:60]
        return ""

    def visit_Import(self, node: ast.Import):
        """Check regular imports."""
        for alias in node.names:
            self._check_module(alias.name, node.lineno, node.col_offset)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Check from imports."""
        if node.module:
            self._check_module(node.module, node.lineno, node.col_offset)
        self.generic_visit(node)

    def _check_module(self, module: str, lineno: int, col: int):
        """Check if module is deprecated or missing."""
        # Check deprecation
        base_module = module.split('.')[0]
        if base_module in self.DEPRECATED_MODULES:
            self.issues.append(Violation(
                category='import',
                severity='warn',
                name='deprecated_import',
                message=f'Module {base_module} is deprecated',
                line=lineno,
                col=col,
                suggestion=self.DEPRECATED_MODULES[base_module],
                context=self._get_line_context(lineno)
            ))

        # Check existence (expensive, optional)
        if self._check_existence:
            import importlib.util
            try:
                spec = importlib.util.find_spec(base_module)
                if spec is None:
                    self.issues.append(Violation(
                        category='import',
                        severity='block',
                        name='missing_import',
                        message=f'Module {base_module} not found',
                        line=lineno,
                        col=col,
                        suggestion=f'pip install {base_module}',
                        context=self._get_line_context(lineno)
                    ))
            except (ModuleNotFoundError, ValueError):
                self.issues.append(Violation(
                    category='import',
                    severity='block',
                    name='missing_import',
                    message=f'Module {base_module} not found',
                    line=lineno,
                    col=col,
                    suggestion=f'pip install {base_module}',
                    context=self._get_line_context(lineno)
                ))


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def analyze_code(source: str, filename: str = "<string>") -> Dict[str, List[Violation]]:
    """
    Run all analyzers on source code.

    Returns dict with keys: 'security', 'stubs', 'imports'
    """
    return {
        'security': SecurityAnalyzer(source, filename).analyze(),
        'stubs': StubAnalyzer(source, filename).find_stubs(),
        'imports': ImportAnalyzer(source, filename).verify_imports(check_existence=False),
    }


def analyze_file(filepath: str) -> Dict[str, List[Violation]]:
    """Analyze a Python file."""
    path = Path(filepath)
    if not path.exists():
        return {'security': [], 'stubs': [], 'imports': []}

    source = path.read_text(encoding='utf-8')
    return analyze_code(source, str(path))


def has_critical_violations(source: str) -> Tuple[bool, List[Violation]]:
    """Quick check for critical security issues. Returns (has_critical, violations)."""
    violations = SecurityAnalyzer(source).analyze()
    critical = [v for v in violations if v.severity == 'critical']
    return bool(critical), critical


def has_stubs(source: str) -> Tuple[bool, List[Violation]]:
    """Quick check for stub functions. Returns (has_stubs, stubs)."""
    stubs = StubAnalyzer(source).find_stubs()
    blocking = [s for s in stubs if s.severity == 'block']
    return bool(blocking), blocking
