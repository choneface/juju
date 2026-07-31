from __future__ import annotations

import argparse
import asyncio
import sys

from .runner import run_files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="be-the-cowboy")
    subparsers = parser.add_subparsers(dest="command", required=True)

    test_parser = subparsers.add_parser("test", help="run be-the-cowboy tests")
    test_parser.add_argument("paths", nargs="+", help="test files to run")
    test_parser.add_argument("--jobs", type=int, default=None, help="max concurrent tests")

    args = parser.parse_args(argv)
    if args.command == "test":
        return asyncio.run(run_files(args.paths, jobs=args.jobs))

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
