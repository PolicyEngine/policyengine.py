"""Keep this checkout's directories off the interpreter's import path.

An editable setuptools install leaves ``src/policyengine.egg-info`` in the
checkout, and its ``.pth`` file lists ``src`` after site-packages. If a test
session puts ``src`` ahead of site-packages on ``sys.path``, even as a second
copy, ``importlib.metadata`` reads that egg-info instead of the installed
distribution's metadata for every later test (#623). The scripts under
``scripts/`` import each other by bare module name, as they do when run as
``python scripts/<name>.py``, so tests make ``scripts/`` importable only while
importing one, or only for the length of one test.
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

CHECKOUT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = CHECKOUT / "scripts"

#: Set by the maintenance scripts' entry points; no test may leave it changed.
SKIP_COUNTRY_IMPORTS = "POLICYENGINE_SKIP_COUNTRY_IMPORTS"

#: How collecting the test modules changed ``sys.path``, recorded by
#: ``tests/conftest.py`` when collection finishes.
COLLECTION_IMPORT_PATH_CHANGES = pytest.StashKey[list[str]]()


def _inside_checkout(entry: object) -> bool:
    return isinstance(entry, str) and (
        Path(entry or ".").resolve().is_relative_to(CHECKOUT)
    )


def import_path_changes(before: Iterable[str], after: Iterable[str]) -> list[str]:
    """How ``after`` differs from ``before`` in ways that change what imports find.

    Reported: a new entry inside this checkout, and any change to the number or
    order of the entries ``before`` had, such as a second copy of ``src`` put in
    front of the one an editable install lists after site-packages. Not
    reported: a new entry outside the checkout, which only adds a place to look.
    """

    before, after = list(before), list(after)
    known = set(before)
    changes = [
        f"added {entry!r}"
        for entry in after
        if entry not in known and _inside_checkout(entry)
    ]
    kept = [entry for entry in after if entry in known]
    if kept != before:
        extra = Counter(kept) - Counter(before)
        missing = Counter(before) - Counter(kept)
        changes.extend(f"added another {entry!r}" for entry in extra.elements())
        changes.extend(f"removed {entry!r}" for entry in missing.elements())
        if not extra and not missing:
            changes.append(f"reordered {before} as {kept}")
    return changes


@contextmanager
def scripts_importable() -> Iterator[None]:
    """Put ``scripts/`` on ``sys.path`` for the block, then restore it exactly."""

    saved = list(sys.path)
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        yield
    finally:
        sys.path[:] = saved


@pytest.fixture
def scripts_on_path(monkeypatch):
    """Keep ``scripts/`` importable for one test.

    Script functions import their sibling scripts when called, as the entry
    point does, so a test that calls them needs the directory for its length.
    """

    monkeypatch.syspath_prepend(str(SCRIPTS_DIR))


@pytest.fixture(autouse=True)
def checkout_stays_off_import_path():
    """Fail a test that leaves ``sys.path`` or the country-import switch changed."""

    path, switch = list(sys.path), os.environ.get(SKIP_COUNTRY_IMPORTS)
    yield
    problems = import_path_changes(path, sys.path)
    if os.environ.get(SKIP_COUNTRY_IMPORTS) != switch:
        problems.append(
            f"changed {SKIP_COUNTRY_IMPORTS} from {switch!r} to "
            f"{os.environ.get(SKIP_COUNTRY_IMPORTS)!r}"
        )
    if problems:
        pytest.fail(
            "The test left the interpreter changed for later tests: "
            + "; ".join(problems)
            + ". Import scripts inside tests.fixtures.import_path."
            "scripts_importable() or use the scripts_on_path fixture, and set "
            "environment variables with monkeypatch.",
            pytrace=False,
        )
