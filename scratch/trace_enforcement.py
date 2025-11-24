#!/usr/bin/env python3
"""Trace enforcement hook execution"""
import sys
import json

# Wrap print to add tracer
original_print = print
call_count = [0]

def traced_print(*args, **kwargs):
    call_count[0] += 1
    original_print(f"[PRINT CALL {call_count[0]}]", file=sys.stderr)
    import traceback
    traceback.print_stack(limit=3, file=sys.stderr)
    original_print(*args, **kwargs)

# Monkey-patch print
__builtins__.print = traced_print

# Now import and run the hook
exec(open('scratch/enforce_reasoning_rigor.py').read())
