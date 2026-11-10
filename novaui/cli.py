"""Command-line utilities for Yuktara UI."""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="yuktara-ui")
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser(
        "setup", help="download and verify the native runtime dependencies"
    )
    setup.add_argument(
        "--include-dev", action="store_true",
        help="also install the pinned development test runner",
    )
    args = parser.parse_args(argv)

    if args.command == "setup":
        from .native.dependencies import DependencyError, setup_all
        try:
            result = setup_all(include_dev=args.include_dev)
        except (DependencyError, OSError) as exc:
            print(f"Yuktara UI setup failed: {exc}", file=sys.stderr)
            return 1
        print("Yuktara UI dependencies are ready:")
        for name, value in result.items():
            print(f"  {name}: {value}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
