#!/usr/bin/env python3
"""
Cached Hook Template
Add this to hooks that read files repeatedly
"""

import json
import sys
from pathlib import Path
import hashlib
import time

# Simple file-based cache
class HookCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    def get(self, key: str) -> dict | None:
        """Get cached value"""
        cache_file = self.cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.json"

        if cache_file.exists():
            # Check if cache is fresh (< 5 minutes old)
            if time.time() - cache_file.stat().st_mtime < 300:
                with open(cache_file) as f:
                    return json.load(f)
        return None

    def set(self, key: str, value: dict):
        """Set cached value"""
        cache_file = self.cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.json"
        with open(cache_file, 'w') as f:
            json.dump(value, f)

# Usage in hook:
cache = HookCache(Path("/tmp/claude_hook_cache"))
session_id = input_data.get("session_id")

# Try cache first
cached = cache.get(session_id)
if cached:
    print(json.dumps(cached))
    sys.exit(0)

# Compute result (expensive operation)
result = expensive_file_reading_operation()

# Cache for next time
cache.set(session_id, result)
print(json.dumps(result))
