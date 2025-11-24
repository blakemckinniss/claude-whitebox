#!/usr/bin/env python3
"""
Technical Debt Cleanup Script
Removes backup files, compiled Python bytecode, and other remnants.
"""

import os
import sys
from pathlib import Path

def find_and_remove(patterns, dry_run=True):
    """Find and optionally remove files matching patterns."""
    repo_root = Path(__file__).parent.parent

    # Exclusion patterns
    exclude_dirs = {'node_modules', '.git', 'venv', '__pycache__'}

    removed_count = 0
    removed_size = 0

    for pattern in patterns:
        for file_path in repo_root.rglob(pattern):
            # Skip excluded directories
            if any(excluded in file_path.parts for excluded in exclude_dirs):
                continue

            if file_path.is_file():
                size = file_path.stat().st_size
                print(f"{'[DRY RUN] Would remove' if dry_run else 'Removing'}: {file_path.relative_to(repo_root)} ({size} bytes)")

                if not dry_run:
                    file_path.unlink()

                removed_count += 1
                removed_size += size

    return removed_count, removed_size

def remove_pycache_dirs(dry_run=True):
    """Remove __pycache__ directories."""
    repo_root = Path(__file__).parent.parent
    exclude_dirs = {'node_modules', '.git', 'venv'}

    removed_count = 0

    for pycache_dir in repo_root.rglob('__pycache__'):
        # Skip excluded directories
        if any(excluded in pycache_dir.parts for excluded in exclude_dirs):
            continue

        if pycache_dir.is_dir():
            file_count = len(list(pycache_dir.iterdir()))
            print(f"{'[DRY RUN] Would remove' if dry_run else 'Removing'}: {pycache_dir.relative_to(repo_root)} ({file_count} files)")

            if not dry_run:
                import shutil
                try:
                    shutil.rmtree(pycache_dir)
                except OSError as e:
                    # Race condition: dir may be recreated by Python runtime
                    print(f"  Warning: Could not remove {pycache_dir.relative_to(repo_root)}: {e}")
                    continue

            removed_count += 1

    return removed_count

def main():
    dry_run = '--execute' not in sys.argv

    if dry_run:
        print("🔍 DRY RUN MODE - No files will be deleted")
        print("   Run with --execute to perform actual cleanup\n")
    else:
        print("⚠️  EXECUTION MODE - Files will be deleted\n")

    # Cleanup targets
    print("=" * 60)
    print("BACKUP FILES")
    print("=" * 60)
    backup_patterns = ['*.backup', '*.bak', '*.old', '*.tmp', '*~']
    count, size = find_and_remove(backup_patterns, dry_run)
    print(f"\nBackup files: {count} files, {size:,} bytes\n")

    print("=" * 60)
    print("COMPILED PYTHON BYTECODE")
    print("=" * 60)
    bytecode_patterns = ['*.pyc', '*.pyo']
    count, size = find_and_remove(bytecode_patterns, dry_run)
    print(f"\nBytecode files: {count} files, {size:,} bytes\n")

    print("=" * 60)
    print("__pycache__ DIRECTORIES")
    print("=" * 60)
    pycache_count = remove_pycache_dirs(dry_run)
    print(f"\n__pycache__ dirs: {pycache_count} directories\n")

    print("=" * 60)
    print("OS-SPECIFIC FILES")
    print("=" * 60)
    os_patterns = ['.DS_Store', 'Thumbs.db', 'desktop.ini']
    count, size = find_and_remove(os_patterns, dry_run)
    print(f"\nOS temp files: {count} files, {size:,} bytes\n")

    if dry_run:
        print("\n✅ Dry run complete. Run with --execute to perform cleanup.")
    else:
        print("\n✅ Cleanup complete.")

if __name__ == '__main__':
    main()
