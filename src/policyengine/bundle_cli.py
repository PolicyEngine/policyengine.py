from __future__ import annotations

import argparse
import shlex
from typing import Optional, Sequence

from policyengine.bundle import (
    constraints_url,
    current_python_version,
    default_target_python,
    get_bundle_version,
    install_profile,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="policyengine-bundle",
        description="Install PolicyEngine profiles from the vendored bundle.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    constraints = subparsers.add_parser(
        "constraints-url",
        help="Print the constraints URL for a bundle profile and Python version.",
    )
    _add_profile_argument(constraints)
    _add_python_version_argument(constraints)

    install = subparsers.add_parser(
        "install",
        help="Install a certified PolicyEngine profile with bundle constraints.",
    )
    _add_profile_argument(install)
    _add_python_version_argument(install)
    install.add_argument(
        "--target-python",
        default=None,
        help=(
            "Interpreter to install into. Defaults to the active virtualenv "
            "interpreter when VIRTUAL_ENV is set, otherwise this command's "
            "Python interpreter."
        ),
    )
    install.add_argument(
        "--installer",
        choices=("pip", "uv"),
        default="pip",
        help="Installer backend to run. Defaults to pip.",
    )
    install.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the install command without running it.",
    )

    return parser


def _add_profile_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "profile",
        choices=("us", "uk", "all"),
        help="Bundle profile to install.",
    )


def _add_python_version_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--python-version",
        default=current_python_version(),
        help=(
            "Bundle Python major.minor target. Defaults to the Python version "
            "running this command."
        ),
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "constraints-url":
        print(constraints_url(args.profile, args.python_version))
        return 0
    if args.command == "install":
        target_python = args.target_python or default_target_python()
        command = install_profile(
            args.profile,
            args.python_version,
            installer=args.installer,
            target_python=target_python,
            dry_run=args.dry_run,
        )
        if args.dry_run:
            print(shlex.join(command))
        else:
            print(
                "Installed PolicyEngine bundle "
                f"{get_bundle_version()} profile {args.profile!r} into "
                f"{target_python}."
            )
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
