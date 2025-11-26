#!/usr/bin/env python3
"""Path setup for importing from .claude/lib/. Import this first in hooks."""
import sys
from pathlib import Path

_lib_dir = str(Path(__file__).parent.parent / "lib")
if _lib_dir not in sys.path:
    sys.path.insert(0, _lib_dir)
