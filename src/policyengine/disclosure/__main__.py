"""Command line: ``python -m policyengine.disclosure validate <path>...``."""

import argparse
import sys
from collections.abc import Sequence
from typing import Optional

from .validate import validate_public


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m policyengine.disclosure")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser(
        "validate", help="Check the format of published tables."
    )
    validate.add_argument("paths", nargs="+", help="CSV files or directories.")
    validate.add_argument(
        "--reviewed",
        action="append",
        default=[],
        metavar="NAME",
        help="A file in a directory that a person checked. Repeat as needed.",
    )
    arguments = parser.parse_args(argv)

    problems: list[str] = []
    for path in arguments.paths:
        problems.extend(validate_public(path, reviewed=arguments.reviewed))
    for problem in problems:
        print(problem)
    print(f"{len(problems)} problem(s) found.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
