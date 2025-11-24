#!/usr/bin/env python3
"""
Reset Circuit Breaker Tool

Manually reset circuit breakers (admin override).

Usage:
    python3 scripts/ops/reset_circuit.py [--all | --circuit NAME]
"""

import sys
import argparse
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scratch"))

from circuit_breaker import reset_circuit, reset_all_circuits, get_circuit_status


def main():
    parser = argparse.ArgumentParser(description="Reset circuit breakers")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--circuit",
        help="Reset specific circuit",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Reset all circuits",
    )

    args = parser.parse_args()

    if args.all:
        print(reset_all_circuits())
    else:
        print(reset_circuit(args.circuit))

    print("\nCurrent Status:")
    print(get_circuit_status())

    return 0


if __name__ == "__main__":
    sys.exit(main())
