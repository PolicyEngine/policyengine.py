"""The versions of packages as they were when this process loaded them.

Installing another version while a process runs changes what the
distribution metadata reports but not the code already imported, so a
receipt that read versions only from the metadata would name code that did
not run. policyengine records its own version when it is imported, and each
country model records its model, core and wrapper versions when it loads
the country package; receipts refuse a run whose installed versions differ.
"""

from __future__ import annotations

from collections.abc import Iterable
from importlib import metadata

_LOADED: dict[str, str] = {}


def record_loaded_versions(names: Iterable[str]) -> None:
    """Record each distribution's installed version, keeping the first seen."""

    for name in names:
        if name in _LOADED:
            continue
        try:
            _LOADED[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue


def loaded_versions() -> dict[str, str]:
    """The versions recorded when each distribution was loaded."""

    return dict(_LOADED)
