#!/usr/bin/env python3
"""
Unit tests for scripts/lib/core.py
Validates core library functions work as expected.
"""
import sys
import os

# Add scripts/lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts', 'lib'))
from core import setup_script, logger, handle_debug, check_dry_run

def test_setup_script_returns_parser():
    """Test that setup_script returns an ArgumentParser"""
    parser = setup_script("Test description")
    assert parser is not None, "setup_script should return a parser"
    assert hasattr(parser, 'parse_args'), "Parser should have parse_args method"
    print("✅ setup_script returns valid parser")

def test_parser_has_standard_flags():
    """Test that parser includes --dry-run and --debug flags"""
    parser = setup_script("Test")

    # Parse with standard flags
    args = parser.parse_args(['--dry-run', '--debug'])

    assert hasattr(args, 'dry_run'), "Parser should have dry_run attribute"
    assert hasattr(args, 'debug'), "Parser should have debug attribute"
    assert args.dry_run == True, "--dry-run flag should set dry_run=True"
    assert args.debug == True, "--debug flag should set debug=True"
    print("✅ Parser includes standard flags (--dry-run, --debug)")

def test_check_dry_run():
    """Test dry-run checking function"""
    parser = setup_script("Test")

    # Test with dry-run enabled
    args = parser.parse_args(['--dry-run'])
    result = check_dry_run(args, "test operation")
    assert result == True, "check_dry_run should return True when dry_run is set"

    # Test with dry-run disabled
    args = parser.parse_args([])
    result = check_dry_run(args, "test operation")
    assert result == False, "check_dry_run should return False when dry_run is not set"

    print("✅ check_dry_run works correctly")

def test_logger_exists():
    """Test that logger is properly configured"""
    assert logger is not None, "Logger should exist"
    assert hasattr(logger, 'info'), "Logger should have info method"
    assert hasattr(logger, 'error'), "Logger should have error method"
    assert hasattr(logger, 'warning'), "Logger should have warning method"
    print("✅ Logger is properly configured")

def test_handle_debug():
    """Test debug mode handler"""
    parser = setup_script("Test")
    args = parser.parse_args(['--debug'])

    # Should not raise exception
    try:
        handle_debug(args)
        print("✅ handle_debug executes without error")
    except Exception as e:
        raise AssertionError(f"handle_debug raised exception: {e}")

def main():
    print("=" * 60)
    print("UNIT TESTS: Core Library (scripts/lib/core.py)")
    print("=" * 60)

    tests = [
        test_setup_script_returns_parser,
        test_parser_has_standard_flags,
        test_check_dry_run,
        test_logger_exists,
        test_handle_debug,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: Unexpected error: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
