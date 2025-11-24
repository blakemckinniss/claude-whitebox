#!/usr/bin/env python3
"""
Batch fix all malformed test arguments in integration tests
"""
import sys
from pathlib import Path

sys.path.insert(0, '/home/jinx/workspace/claude-whitebox/scripts/lib')
from core import setup_script, finalize, logger

# Map of test file to correct test args
TEST_FIXES = {
    "test_reality_check.py": {
        "dry_run_args": '["python3", str(self.script_path), "file_exists", "scripts/ops/verify.py", "--dry-run"]',
        "basic_args": '["python3", str(self.script_path), "file_exists", "scripts/ops/verify.py"]',
    },
    "test_macgyver.py": {
        "dry_run_args": '["python3", str(self.script_path), "--compact", "--dry-run"]',
        "basic_args": '["python3", str(self.script_path), "--compact"]',
    },
    "test_xray.py": {
        "dry_run_args": '["python3", str(self.script_path), "scripts/ops", "--type", "function", "--name", "main", "--dry-run"]',
        "basic_args": '["python3", str(self.script_path), "scripts/ops", "--type", "function", "--name", "main"]',
    },
    "test_void_hunter.py": {
        "dry_run_args": '["python3", str(self.script_path), "scripts/ops/void.py", "--stub-only", "--dry-run"]',
        "basic_args": '["python3", str(self.script_path), "scripts/ops/void.py", "--stub-only"]',
    },
    "test_upkeep.py": {
        "dry_run_args": '["python3", str(self.script_path), "--dry-run"]',
        "basic_args": '["python3", str(self.script_path)]',
    },
    "test_oracle.py": {
        "dry_run_args": '["python3", str(self.script_path), "How do I design a REST API?", "--dry-run"]',
        "basic_args": '["python3", str(self.script_path), "How do I design a REST API?"]',
    },
    "test_judge.py": {
        "dry_run_args": '["python3", str(self.script_path), "Build a custom framework from scratch", "--dry-run"]',
        "basic_args": '["python3", str(self.script_path), "Build a custom framework from scratch"]',
    },
    "test_critic.py": {
        "dry_run_args": '["python3", str(self.script_path), "Migrate to microservices architecture", "--dry-run"]',
        "basic_args": '["python3", str(self.script_path), "Migrate to microservices architecture"]',
    },
    "test_cartesian.py": {
        "dry_run_args": '["python3", str(self.script_path), "Refactor authentication system", "--dry-run"]',
        "basic_args": '["python3", str(self.script_path), "Refactor authentication system"]',
    },
    "test_research.py": {
        "dry_run_args": '["python3", str(self.script_path), "python unittest best practices", "--dry-run"]',
        "basic_args": '["python3", str(self.script_path), "python unittest best practices"]',
    },
    "test_sentinel.py": {
        "dry_run_args": '["python3", str(self.script_path), "scripts/ops/audit.py", "--dry-run"]',
        "basic_args": '["python3", str(self.script_path), "scripts/ops/audit.py"]',
    },
    "test_finish_line.py": {
        "dry_run_args": '["python3", str(self.script_path), "status", "--dry-run"]',
        "basic_args": '["python3", str(self.script_path), "status"]',
    },
    "test_scripting.py": {
        "dry_run_args": '["python3", str(self.script_path), str(output_path), "Test description", "--dry-run"]',
        "basic_args": '["python3", str(self.script_path), str(output_path), "Test description"]',
    },
}

def fix_test_file(test_path: Path, fixes: dict) -> bool:
    """Fix test args in a test file"""
    content = test_path.read_text()

    # Find and replace the malformed subprocess.run calls
    # Pattern 1: test_dry_run_mode
    dry_run_start = '        result = subprocess.run(\n            ["python3", str(self.script_path)'
    basic_start = '        result = subprocess.run(\n            ["python3", str(self.script_path)'

    lines = content.split('\n')
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is a subprocess.run line
        if 'result = subprocess.run(' in line and i + 1 < len(lines):
            # Look ahead to see the actual command
            next_line = lines[i + 1]

            # Find if it's in dry_run_mode or basic_functionality
            # Look backwards for function definition
            func_name = None
            for j in range(i-1, max(0, i-20), -1):
                if 'def test_dry_run_mode' in lines[j]:
                    func_name = 'dry_run'
                    break
                elif 'def test_basic_functionality' in lines[j]:
                    func_name = 'basic'
                    break

            if func_name and '["python3"' in next_line:
                # This is a line we need to fix
                # Skip old command lines until we hit the next key line
                new_lines.append(line)  # Keep "result = subprocess.run("

                if func_name == 'dry_run':
                    new_lines.append(f'            {fixes["dry_run_args"]},')
                else:
                    new_lines.append(f'            {fixes["basic_args"]},')

                # Skip lines until we find "capture_output"
                i += 1
                while i < len(lines) and 'capture_output' not in lines[i]:
                    i += 1
                i -= 1  # Back up one so we don't skip the capture_output line
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

        i += 1

    test_path.write_text('\n'.join(new_lines))
    return True

def main():
    parser = setup_script("Batch fix malformed test arguments")
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()

    test_dir = Path('/home/jinx/workspace/claude-whitebox/.claude/tests/integration')
    fixed_count = 0

    logger.info(f"Fixing {len(TEST_FIXES)} test files...")

    for test_file, fixes in TEST_FIXES.items():
        test_path = test_dir / test_file

        if not test_path.exists():
            logger.warning(f"⚠️  Test file not found: {test_file}")
            continue

        if args.execute:
            try:
                fix_test_file(test_path, fixes)
                logger.info(f"✅ FIXED: {test_file}")
                fixed_count += 1
            except Exception as e:
                logger.error(f"❌ FAILED: {test_file} - {e}")
        else:
            logger.warning(f"⚠️  DRY-RUN: Would fix {test_file}")

    if not args.execute:
        logger.warning("\nRun with --execute to apply fixes:")
        logger.warning("  python3 scratch/batch_fix_tests.py --execute")
    else:
        logger.info(f"\n✅ Fixed {fixed_count}/{len(TEST_FIXES)} test files")

    finalize(success=True)

if __name__ == "__main__":
    main()
