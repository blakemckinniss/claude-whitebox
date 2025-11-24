#!/usr/bin/env python3
"""
Circuit Status Tool

Shows current state of all circuit breakers and memory usage.

Usage:
    python3 scripts/ops/circuit_status.py [--circuit NAME]
"""

import sys
import argparse
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scratch"))

from circuit_breaker import get_circuit_status
from memory_cleanup import format_memory_report, get_memory_stats


def main():
    parser = argparse.ArgumentParser(
        description="Show circuit breaker and memory status"
    )
    parser.add_argument(
        "--circuit",
        help="Show specific circuit (default: all)",
        default=None,
    )
    parser.add_argument(
        "--memory",
        action="store_true",
        help="Show memory report",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

    if args.json:
        import json

        # JSON output
        from circuit_breaker import load_circuit_state

        state = load_circuit_state()
        stats = get_memory_stats()

        output = {
            "circuits": state.get("circuits", {}),
            "memory": stats,
        }

        print(json.dumps(output, indent=2))
        return 0

    # Human-readable output
    print(get_circuit_status(args.circuit))

    if args.memory or args.circuit is None:
        print()
        print(format_memory_report())

    return 0


if __name__ == "__main__":
    sys.exit(main())
