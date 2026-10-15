"""Keep this checkout's directories off the interpreter's import path.

An editable setuptools install leaves ``src/policyengine.egg-info`` in the
checkout. If a test session puts ``src`` ahead of site-packages on
``sys.path``, ``importlib.metadata`` reads that egg-info instead of the
installed distribution's metadata for every later test (#623). The scripts
under ``scripts/`` import each other by bare module name, as they do when run
as ``python scripts/<name>.py``, so tests make ``scripts/`` importable only
while importing one, or only for the length of one test.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

CHECKOUT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = CHECKOUT / "scripts"

#: Entries inside this checkout that collecting the test modules added to
#: ``sys.path``, recorded by ``tests/conftest.py`` when collection finishes.
ADDED_BY_COLLECTION = pytest.StashKey[list[str]]()


def checkout_entries_added(before: Iterable[str], after: Iterable[str]) -> list[str]:
    """Entries of ``after`` that ``before`` lacks and that point into this checkout."""

    known = set(before)
    added = []
    for entry in after:
        if entry in known or not isinstance(entry, str):
            continue
        if Path(entry or ".").resolve().is_relative_to(CHECKOUT):
            added.append(entry)
    return added


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
    """Fail a test that leaves a checkout directory on ``sys.path``."""

    before = list(sys.path)
    yield
    added = checkout_entries_added(before, sys.path)
    if added:
        pytest.fail(
            f"The test left {added} on sys.path. Import scripts inside "
            "tests.fixtures.import_path.scripts_importable() or use the "
            "scripts_on_path fixture, which restore the import path.",
            pytrace=False,
        )
