# Whitebox SDK Test Suite

Automated tests to ensure alignment, stability, and correctness of the Whitebox SDK.

## Test Categories

### 1. Unit Tests (`unit/`)
Tests individual functions in the core library.

- `test_core.py` - Core library functions (setup_script, logger, etc.)

### 2. Integration Tests (`integration/`)
Tests that components work together correctly.

- `test_scaffolder.py` - Script generation and execution
- `test_indexer.py` - Tool registry generation

### 3. Alignment Tests (`alignment/`)
Tests that enforce Whitebox Engineering principles.

- `test_whitebox_principles.py` - Validates transparency, safety, consistency

### 4. Stability Tests (`stability/`)
Tests for edge cases and robustness.

- `test_path_resolution.py` - Import paths work from any location

## Running Tests

### Run all tests
```bash
python3 .claude/tests/runner.py
```

### Run specific suite
```bash
python3 .claude/tests/runner.py unit
python3 .claude/tests/runner.py integration
python3 .claude/tests/runner.py alignment
python3 .claude/tests/runner.py stability
```

### Run individual test file
```bash
python3 .claude/tests/unit/test_core.py
```

## Test Success Criteria

All tests must pass for the SDK to be considered stable. Tests validate:

✅ **Safety** - All scripts support --dry-run
✅ **Transparency** - All code is readable Python
✅ **Consistency** - All scripts use core library
✅ **Functionality** - Components work as expected
✅ **Robustness** - Path resolution works from any location

## When to Run Tests

- **Before committing SDK changes** - Ensure changes don't break existing functionality
- **After modifying core library** - Validate all dependent scripts still work
- **When adding new features** - Confirm integration with existing system
- **After environment changes** - Verify setup still works correctly

## Adding New Tests

1. Create test file in appropriate category directory
2. Follow naming convention: `test_<feature>.py`
3. Include docstring explaining what is tested
4. Use assertions with clear error messages
5. Add test file to `runner.py` TEST_SUITES dict
6. Run test suite to verify new test works

## Test Output

Tests provide detailed output:
- ✅ Green checkmarks for passing tests
- ❌ Red X marks for failing tests
- Clear assertion messages explaining failures
- Summary statistics at the end

## Philosophy

These tests embody the Whitebox principle: **"If you can't test it transparently, don't build it."**

Every test is readable Python code that validates expected behavior without relying on external tools or services.
