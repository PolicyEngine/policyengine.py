"""Unit and property tests for the stamp on UK year files.

``create_datasets`` stamps each UK year file, after its tables and data year,
with the identity of the source dataset it was cut from, the
policyengine-core and policyengine-uk versions that projected it and a
year-file format revision (``year_file_stamp.YEAR_FILE_STAMP_H5_DATASET``).
``ensure_datasets`` cuts a year file again, and ``load_datasets`` refuses it,
unless it records its data year and its stamp matches the one a file cut now
from the requested dataset would carry. These tests state the check's
invariants over generated stamps, data-year nodes, sources and package
versions, without a country engine:

- **Exactness.** A year file is current exactly when it records its data
  year and its stamp has this release's format revision, the requested
  source and the installed package versions.
- **Totality.** Whatever the stamp and the data-year node hold, the check
  returns a reason or ``None``, and raises only for errors unrelated to the
  file's contents (no permission, a directory, a lock).
- **Round trip.** A stamp reads back as written, and writing again replaces it.
- **Named differences.** The reason names both sources when they differ and
  every package whose version differs, and nothing that agrees.
- **No partial file is current.** Every truncation of a current year file,
  every save that stops part-way and every save that does not stamp is out
  of date.
- **Ensure agrees with load.** ``ensure_datasets`` cuts the year files again
  exactly when one is missing or ``load_datasets`` would refuse one, and
  decides from the stamps alone: it never opens a table, never reads,
  downloads or hashes the source, and never imports policyengine-uk.
- **Differential.** The UK and US checks name a source or package
  difference with the same clauses, from the shared
  ``year_file_stamp.source_and_package_differences``.

``test_uk_year_file_stamp_integration.py`` runs ``create_datasets`` and
``ensure_datasets`` over a real policyengine-uk engine, and
``test_dataset_source_identity.py`` tests the source identities themselves.
"""

from __future__ import annotations

import builtins
import functools
import io
import json
import os
import tempfile
from importlib import metadata as importlib_metadata
from pathlib import Path
from unittest.mock import MagicMock, patch

import h5py
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from microdf import MicroDataFrame

import policyengine.provenance.dataset_materialization as dataset_materialization
from policyengine.provenance.dataset_materialization import (
    DatasetMaterializationError,
    describe_dataset_source_identity,
    requested_dataset_source_identity,
)
from policyengine.provenance.year_file_stamp import (
    NOT_HDF5,
    YEAR_FILE_STAMP_H5_DATASET,
    read_year_file_stamp,
    write_year_file_stamp,
)
from policyengine.tax_benefit_models.uk import datasets as uk_datasets
from policyengine.tax_benefit_models.uk.datasets import (
    DATA_YEAR_KEY,
    NO_DATA_YEAR,
    YEAR_FILE_PACKAGES,
    YEAR_FILE_STAMP_REVISION,
    PolicyEngineUKDataset,
    UKYearData,
    _records_data_year,
    _year_file_records_data_year,
    ensure_datasets,
    load_datasets,
    year_file_stamp,
    year_file_stamp_problem,
)

REVISION = YEAR_FILE_STAMP_REVISION
DATA_YEAR = 2024
#: ``hf://`` references are used as they are, and name year files after the
#: file's stem, so no manifest or download is involved. Its identity is the
#: URI as given.
SOURCE = "hf://fixture/repo/tiny.h5"
IDENTITY = {"uri": SOURCE}
STEM = "tiny"
#: The installed versions every test in this module sees (see
#: ``_installed_packages``), so no expectation depends on the environment.
PACKAGES = {"policyengine-core": "3.33.0", "policyengine-uk": "2.126.12"}
#: The real reader, kept before ``_installed_packages`` replaces it.
REAL_INSTALLED_PACKAGE_VERSIONS = uk_datasets.installed_package_versions
MALFORMED = "its stamp of what it was cut from and with is malformed"
NO_STAMP = (
    "it has no stamp of the source dataset and package versions it was cut "
    "from and with, so it was cut by an older policyengine.py or not written "
    "completely"
)

#: Small alphabets of source identities in each of their three shapes (see
#: ``dataset_source_identity``), so generated sources often agree.
URIS = st.sampled_from([SOURCE, f"{SOURCE}@r1", f"{SOURCE}@r2"])
SOURCES = st.one_of(
    st.builds(lambda uri: {"uri": uri}, URIS),
    st.builds(
        lambda uri, sha256: {"uri": uri, "sha256": sha256},
        URIS,
        st.sampled_from(["a" * 64, "b" * 64]),
    ),
    st.builds(
        lambda path, size, mtime_ns: {
            "path": path,
            "size": size,
            "mtime_ns": mtime_ns,
        },
        st.sampled_from(["/data/tiny.h5", "/elsewhere/tiny.h5"]),
        st.sampled_from([10, 11]),
        # Before the epoch, at it, and past the year 9999.
        st.sampled_from([-1, 0, 1_760_000_000_123_456_789, 10**20]),
    ),
)
PACKAGE_NAMES = st.sampled_from([*YEAR_FILE_PACKAGES, "policyengine-us", "extra"])
VERSIONS = st.one_of(st.none(), st.sampled_from(["1.0", "1.1"]))
PACKAGE_MAPS = st.dictionaries(PACKAGE_NAMES, VERSIONS, max_size=3)
#: Raw node contents: ``_ABSENT`` for no node, a JSON value, or a node the
#: reader cannot parse as JSON.
_ABSENT = object()
JSON_VALUES = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats() | st.text(max_size=8),
    lambda children: (
        st.lists(children, max_size=3)
        | st.dictionaries(st.text(max_size=8), children, max_size=3)
    ),
    max_leaves=6,
)


@pytest.fixture(autouse=True, scope="module")
def _installed_packages():
    """Pin the installed package versions a stamp records to ``PACKAGES``.

    Module-scoped, so Hypothesis tests can run under it.
    """
    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(
            uk_datasets, "installed_package_versions", lambda: dict(PACKAGES)
        )
        yield


def _frames() -> dict[str, pd.DataFrame]:
    return {
        "person": pd.DataFrame(
            {
                "person_id": [1, 2],
                "person_benunit_id": [1, 1],
                "person_household_id": [1, 1],
                "person_weight": [1.0, 1.0],
                "age": [70, 68],
            }
        ),
        "benunit": pd.DataFrame({"benunit_id": [1], "benunit_weight": [1.0]}),
        "household": pd.DataFrame(
            {"household_id": [1], "household_weight": [1.0], "region": ["LONDON"]}
        ),
    }


def _year_dataset(path, data_year=DATA_YEAR, year=DATA_YEAR) -> PolicyEngineUKDataset:
    """A one-household year file for ``year``, projected from ``data_year``
    (or observed in ``year`` when ``data_year`` is ``None``)."""
    tables = UKYearData(
        **{
            entity: MicroDataFrame(frame, weights=f"{entity}_weight")
            for entity, frame in _frames().items()
        }
    )
    projected = data_year is not None and year > data_year
    return PolicyEngineUKDataset(
        name="year-file",
        description="Uncertified two-person UK year-file fixture",
        filepath=str(path),
        year=year,
        data=tables,
        data_year=data_year,
        data_year_data=tables if projected else None,
    )


def _write_node(file, name, content) -> None:
    """Store ``content`` under ``name``: JSON, or a node kind to test."""
    if content is _ABSENT:
        return
    if isinstance(content, tuple):
        kind, value = content
        if kind == "text":
            file.create_dataset(name, data=value, dtype=h5py.string_dtype("utf-8"))
        elif kind == "bytes":
            file.create_dataset(name, data=np.bytes_(value))
        elif kind == "number":
            file.create_dataset(name, data=value)
        elif kind == "array":
            file.create_dataset(name, data=value, dtype=h5py.string_dtype("utf-8"))
        elif kind == "group":
            file.create_group(name)
        else:
            raise AssertionError(kind)
        return
    file.create_dataset(
        name, data=json.dumps(content), dtype=h5py.string_dtype("utf-8")
    )


#: How a year file's data-year node can be stored: ``True`` as pandas writes
#: it (a group), ``False`` for none, or a node that is not a data year.
DATA_YEAR_NODES = ("dataset", "dangling link", "link cycle", "long link chain")


def _write_data_year_node(file, kind) -> None:
    if kind == "dataset":
        file.create_dataset(DATA_YEAR_KEY, data=DATA_YEAR)
    elif kind == "dangling link":
        file[DATA_YEAR_KEY] = h5py.SoftLink("/nowhere")
    elif kind == "link cycle":
        _link_cycle(file, DATA_YEAR_KEY)
    elif kind == "long link chain":
        # A chain too long to follow, to a group that would be a data year.
        file.create_group(f"{DATA_YEAR_KEY}_end")
        _link_chain(file, DATA_YEAR_KEY)
    else:
        raise AssertionError(kind)


def _write_year_file(path, *, stamp=_ABSENT, data_year=True, year=DATA_YEAR):
    """Write a year file's tables and data year, then its stamp, as given.

    ``stamp`` is a JSON value, ``_ABSENT``, or a raw node (see
    :func:`_write_node`). ``data_year`` is ``True`` for the data year as
    ``save()`` writes it, ``False`` for none, or one of
    :data:`DATA_YEAR_NODES`. A file for a ``year`` after the data year holds
    the data year's tables too, as ``create_datasets`` writes it.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    _year_dataset(path, DATA_YEAR if data_year is True else None, year).save()
    with h5py.File(path, "a") as file:
        if data_year not in (True, False):
            _write_data_year_node(file, data_year)
        _write_node(file, YEAR_FILE_STAMP_H5_DATASET, stamp)
    return Path(path)


def _link_cycle(file, name) -> None:
    """Point ``name`` into a cycle of soft links."""
    file[name] = h5py.SoftLink(f"/{name}_loop")
    file[f"{name}_loop"] = h5py.SoftLink(f"/{name}")


def _link_chain(file, name) -> None:
    """Point ``name`` down a chain of soft links too long to follow, to
    ``{name}_end``."""
    file[name] = h5py.SoftLink(f"/{name}_0")
    for index in range(100):
        file[f"{name}_{index}"] = h5py.SoftLink(f"/{name}_{index + 1}")
    file[f"{name}_100"] = h5py.SoftLink(f"/{name}_end")


#: What :func:`_stored` gives for a node no reader can parse as JSON.
_UNREADABLE = object()


def _stored(content):
    """Decode what :func:`_write_node` stores, as the checker reads it back.

    An oracle independent of the checker's reader: raw text is parsed as
    JSON; raw bytes are fixed-length strings, which read back without
    trailing NULs; any other raw node, or text that is not JSON, is
    unreadable. A JSON value reads back as its JSON round trip.
    """
    if content is _ABSENT:
        return _ABSENT
    if isinstance(content, tuple):
        kind, value = content
        try:
            if kind == "text":
                return json.loads(value)
            if kind == "bytes":
                return json.loads(value.rstrip(b"\x00").decode("utf-8"))
        except (RecursionError, ValueError):
            pass
        return _UNREADABLE
    return json.loads(json.dumps(content))


def _same_json(left, right) -> bool:
    """Equal as JSON: ``True`` is not ``1``, and ``1.0`` is not ``1``."""
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def _is_current(stamp, data_year, source=IDENTITY, packages=PACKAGES) -> bool:
    """The exactness invariant, stated directly on the stored values.

    Only a data year written as pandas writes it (a group) counts.
    """
    return (
        data_year is True
        and isinstance(stamp, dict)
        and set(stamp) == {"packages", "revision", "source"}
        and type(stamp["revision"]) is int
        and stamp["revision"] == REVISION
        and _same_json(stamp["source"], source)
        and _same_json(stamp["packages"], packages)
    )


def _stamp(revision=REVISION, source=IDENTITY, packages=PACKAGES):
    return {
        "packages": dict(packages),
        "revision": revision,
        "source": dict(source),
    }


def _current():
    return year_file_stamp(IDENTITY)


# --- The stamp ----------------------------------------------------------


def test_the_stamp_holds_the_source_packages_and_revision():
    assert _current() == {
        "packages": PACKAGES,
        "revision": 1,
        "source": IDENTITY,
    }


def test_the_stamp_reads_the_packages_when_called(monkeypatch):
    """datasets.py must not freeze the versions at import."""
    monkeypatch.setattr(
        uk_datasets, "installed_package_versions", lambda: {"z": None, "y": "1"}
    )

    assert year_file_stamp(IDENTITY) == {
        "packages": {"y": "1", "z": None},
        "revision": 1,
        "source": IDENTITY,
    }


def test_explicit_packages_override_the_installed_ones():
    packages = {"policyengine-uk": "9.9.9"}
    assert year_file_stamp(IDENTITY, packages)["packages"] == packages


def test_the_stamp_is_stored_as_utf8_json(tmp_path):
    path = _write_year_file(tmp_path / "year.h5")
    write_year_file_stamp(path, _current())

    with h5py.File(path, "r") as file:
        node = file[YEAR_FILE_STAMP_H5_DATASET]
        assert node.shape == ()
        assert json.loads(node.asstr()[()]) == _current()


def test_installed_package_versions_reads_metadata(monkeypatch):
    """The real reader: distribution metadata, ``None`` when absent."""
    monkeypatch.setattr(
        uk_datasets,
        "YEAR_FILE_PACKAGES",
        ("pytest", "hypothesis", "not-a-distribution-policyengine-test"),
    )

    assert REAL_INSTALLED_PACKAGE_VERSIONS() == {
        "pytest": importlib_metadata.version("pytest"),
        "hypothesis": importlib_metadata.version("hypothesis"),
        "not-a-distribution-policyengine-test": None,
    }


def test_the_stamp_records_policyengine_core_and_policyengine_uk():
    """policyengine-uk projects each year's tables, uprating by its parameters
    through policyengine-core's parameter tree."""
    assert YEAR_FILE_PACKAGES == ("policyengine-core", "policyengine-uk")
    assert set(REAL_INSTALLED_PACKAGE_VERSIONS()) == set(YEAR_FILE_PACKAGES)


STAMPS = st.fixed_dictionaries(
    {"packages": PACKAGE_MAPS, "revision": st.integers(), "source": SOURCES}
)


@settings(max_examples=50, deadline=None)
@given(first=STAMPS, second=STAMPS)
def test_a_year_file_stamp_reads_back_as_written(first, second):
    with tempfile.TemporaryDirectory() as directory:
        path = _write_year_file(Path(directory) / "year.h5")
        write_year_file_stamp(path, first)
        assert read_year_file_stamp(path) == first
        # Writing again replaces it.
        write_year_file_stamp(path, second)
        assert read_year_file_stamp(path) == second


def test_a_missing_or_foreign_file_has_no_stamp(tmp_path):
    assert read_year_file_stamp(tmp_path / "missing.h5") is None
    (tmp_path / "text.h5").write_text("not an H5 file")
    assert read_year_file_stamp(tmp_path / "text.h5") is None
    assert read_year_file_stamp(_write_year_file(tmp_path / "year.h5")) is None


def test_the_stamp_does_not_disturb_pandas_or_loading(tmp_path):
    path = _write_year_file(tmp_path / "year.h5", stamp=_current())

    with pd.HDFStore(path, mode="r") as store:
        assert sorted(store.keys()) == sorted(
            [f"/{key}" for key in _frames()] + [f"/{DATA_YEAR_KEY}"]
        )
    loaded = PolicyEngineUKDataset(
        name="year-file", description="reload", filepath=str(path), year=DATA_YEAR
    )
    assert loaded.data_year == DATA_YEAR
    assert pd.DataFrame(loaded.data.person)["age"].tolist() == [70, 68]


# --- The data year ------------------------------------------------------


@pytest.mark.parametrize("data_year", [True, False, "dataset"])
def test_the_data_year_check_agrees_with_pandas(tmp_path, data_year):
    """The check reads the data year's presence with h5py, as pandas lists
    its keys, without opening the file with PyTables."""
    path = _write_year_file(tmp_path / "year.h5", data_year=data_year)

    with h5py.File(path, "r") as file:
        assert _records_data_year(file) == _year_file_records_data_year(path)
        assert _records_data_year(file) == (data_year is True)


def test_a_year_file_of_a_later_year_records_its_data_year(tmp_path):
    """A projected file, with the data year's tables under their prefix."""
    tables = _year_dataset(tmp_path / "x.h5").data
    path = tmp_path / "year.h5"
    PolicyEngineUKDataset(
        name="projected",
        description="projected",
        filepath=str(path),
        year=DATA_YEAR + 2,
        data=tables,
        data_year=DATA_YEAR,
        data_year_data=tables,
    ).save()
    write_year_file_stamp(path, _current())

    assert year_file_stamp_problem(path, IDENTITY) is None


def test_files_without_a_stamp_are_out_of_date_with_distinct_reasons(tmp_path):
    """policyengine.py before #556 wrote neither; after it, the data year."""
    oldest = _write_year_file(tmp_path / "oldest.h5", data_year=False)
    data_year_only = _write_year_file(tmp_path / "data_year_only.h5")

    assert year_file_stamp_problem(oldest, IDENTITY) == NO_DATA_YEAR
    assert year_file_stamp_problem(data_year_only, IDENTITY) == NO_STAMP
    assert NO_DATA_YEAR == (
        "it has no recorded data year, so it was written before policyengine.py "
        "kept the observed year its tables were projected from, or not written "
        "completely; policyengine-uk would take its projected tables as observed "
        "data and uprate the State Pension by CPI rather than the triple lock"
    )


@pytest.mark.parametrize("data_year", [False, *DATA_YEAR_NODES])
def test_a_stamped_file_without_a_data_year_is_out_of_date(tmp_path, data_year):
    """A stamp alone is not enough: the run needs the data year. A data-year
    node that is not a group, or a link that cannot be followed, is none."""
    path = _write_year_file(tmp_path / "year.h5", stamp=_current(), data_year=data_year)

    assert year_file_stamp_problem(path, IDENTITY) == NO_DATA_YEAR


# --- Exactness ----------------------------------------------------------


@st.composite
def stamped_files(draw):
    """A current source and packages, and a year file's stamp and data year
    near them."""
    source = draw(SOURCES)
    packages = draw(PACKAGE_MAPS)
    stamped_source = draw(st.one_of(st.just(dict(source)), SOURCES))
    stamped_packages = draw(
        st.one_of(
            st.just(dict(packages)),
            PACKAGE_MAPS,
            # One version changed, dropped or added.
            st.builds(lambda k, v: {**packages, k: v}, PACKAGE_NAMES, VERSIONS),
            st.builds(
                lambda name: {k: v for k, v in packages.items() if k != name},
                PACKAGE_NAMES,
            ),
        )
    )
    revision = draw(st.sampled_from([REVISION, REVISION, 0, 2, -1, 99]))
    stamp = draw(
        st.one_of(
            st.just(_stamp(revision, stamped_source, stamped_packages)),
            st.just(_stamp(revision, stamped_source, stamped_packages)),
            st.just(_ABSENT),
        )
    )
    data_year = draw(st.sampled_from([True, True, True, False, *DATA_YEAR_NODES]))
    return source, packages, stamp, data_year


@settings(max_examples=300, deadline=None)
@given(case=stamped_files())
def test_a_year_file_is_current_only_under_the_exact_stamp_requested(case):
    source, packages, stamp, data_year = case
    with tempfile.TemporaryDirectory() as directory:
        path = _write_year_file(
            Path(directory) / "year.h5", stamp=stamp, data_year=data_year
        )
        problem = year_file_stamp_problem(path, source, packages)

    assert (problem is None) == _is_current(_stored(stamp), data_year, source, packages)
    assert problem is None or (isinstance(problem, str) and problem)


#: Text stored as it is, not as JSON. HDF5 variable-length strings cannot
#: hold a NUL character, and a lone surrogate cannot be encoded as UTF-8.
RAW_TEXT = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    max_size=12,
)

NODES = st.one_of(
    st.just(_ABSENT),
    JSON_VALUES,
    st.fixed_dictionaries(
        {
            "packages": st.one_of(PACKAGE_MAPS, JSON_VALUES),
            "revision": st.one_of(
                st.just(REVISION), st.booleans(), st.floats(), JSON_VALUES
            ),
            "source": st.one_of(
                SOURCES,
                JSON_VALUES,
                # Well-formed keys holding values of the wrong type.
                st.fixed_dictionaries(
                    {"path": JSON_VALUES, "size": JSON_VALUES, "mtime_ns": JSON_VALUES}
                ),
                st.fixed_dictionaries({"uri": JSON_VALUES, "sha256": JSON_VALUES}),
            ),
        }
    ),
    st.tuples(st.just("text"), RAW_TEXT),
    st.tuples(st.just("bytes"), st.binary(min_size=1, max_size=12)),
    st.tuples(st.just("number"), st.integers(-5, 5)),
    st.tuples(st.just("array"), st.lists(RAW_TEXT, min_size=1, max_size=3)),
    st.tuples(st.just("group"), st.none()),
)


@settings(max_examples=400, deadline=None)
@given(
    stamp=NODES,
    data_year=st.sampled_from([True, False, *DATA_YEAR_NODES]),
    source=SOURCES,
    packages=PACKAGE_MAPS,
)
def test_the_year_file_problem_is_total_and_exact_for_any_content(
    stamp, data_year, source, packages
):
    """Totality: any stamp and data-year node give a reason or ``None``,
    never an error, and ``None`` exactly for the stamp requested, however it
    is stored (``_stored`` decodes raw nodes independently of the checker)."""
    with tempfile.TemporaryDirectory() as directory:
        path = _write_year_file(
            Path(directory) / "year.h5", stamp=stamp, data_year=data_year
        )
        problem = year_file_stamp_problem(path, source, packages)

    assert problem is None or (isinstance(problem, str) and problem)
    assert (problem is None) == _is_current(_stored(stamp), data_year, source, packages)


@pytest.mark.parametrize(
    "stamp",
    [
        {**_stamp(), "revision": True},
        {**_stamp(), "revision": 1.0},
        {**_stamp(), "revision": "1"},
        {"revision": 1},
        {k: v for k, v in _stamp().items() if k != "source"},
        {k: v for k, v in _stamp().items() if k != "packages"},
        {**_stamp(), "extra": None},
        # A US stamp's shape, with its register.
        {**_stamp(), "register": {}},
        {**_stamp(), "packages": {"policyengine-uk": 2.126}},
        {**_stamp(), "packages": [["policyengine-uk", "2.126.12"]]},
        {**_stamp(), "source": SOURCE},
        {**_stamp(), "source": {}},
        {**_stamp(), "source": {"uri": 5}},
        {**_stamp(), "source": {"uri": SOURCE, "sha256": None}},
        {**_stamp(), "source": {"uri": SOURCE, "revision": "r1"}},
        {**_stamp(), "source": {"path": "/a", "size": True, "mtime_ns": 1}},
        {**_stamp(), "source": {"path": "/a", "size": 1, "mtime_ns": 1.0}},
        {**_stamp(), "source": {"path": "/a", "size": 1}},
        [_stamp()],
        ("text", "not json"),
        ("text", ""),
        ("bytes", b"\xff\xfe"),
        ("number", 1),
        ("array", ["{}"]),
        ("group", None),
    ],
)
def test_a_malformed_stamp_is_out_of_date(tmp_path, stamp):
    path = _write_year_file(tmp_path / "year.h5", stamp=stamp)

    assert year_file_stamp_problem(path, IDENTITY) == MALFORMED


@pytest.mark.parametrize("revision", [0, 2, 3, -1])
def test_a_year_file_from_another_format_revision_is_out_of_date(tmp_path, revision):
    # Another revision may shape the rest of its stamp, or keep its data year,
    # differently, and is still reported by revision rather than as malformed
    # or as lacking a data year.
    stamp = {"revision": revision, "sources": [SOURCE]}
    path = _write_year_file(tmp_path / "year.h5", stamp=stamp, data_year=False)

    assert year_file_stamp_problem(path, IDENTITY) == (
        f"it was cut with year-file format revision {revision}, and this "
        "version of policyengine.py reads only revision 1"
    )


def test_a_stamp_stored_as_a_fixed_length_string_is_read(tmp_path):
    stamp = json.dumps(_current()).encode()
    path = _write_year_file(tmp_path / "year.h5", stamp=("bytes", stamp))

    assert year_file_stamp_problem(path, IDENTITY) is None
    assert read_year_file_stamp(path) == _current()


def test_raising_the_format_revision_makes_older_files_out_of_date(
    tmp_path, monkeypatch
):
    older = _write_year_file(tmp_path / "older.h5", stamp=_current())
    monkeypatch.setattr(uk_datasets, "YEAR_FILE_STAMP_REVISION", 7)
    newer = _write_year_file(tmp_path / "newer.h5", stamp=_current())

    assert _current()["revision"] == 7
    assert year_file_stamp_problem(newer, IDENTITY) is None
    assert year_file_stamp_problem(older, IDENTITY) == (
        "it was cut with year-file format revision 1, and this version of "
        "policyengine.py reads only revision 7"
    )


#: JSON nested very deeply. Whether the parser reaches its limit depends on
#: the interpreter and the platform (see the same constant in
#: ``test_us_year_file_stamp.py``). Either way the stamp is not well formed.
DEEP_JSON = "[" * 100_000 + "0" + "]" * 100_000


def test_json_nested_too_deeply_is_out_of_date_not_an_error(tmp_path):
    path = _write_year_file(tmp_path / "year.h5", stamp=("text", DEEP_JSON))

    assert year_file_stamp_problem(path, IDENTITY) == MALFORMED
    # Unreadable (None) or parsed into nested lists, but never a stamp.
    assert not isinstance(read_year_file_stamp(path), dict)


def test_a_recursion_error_while_parsing_is_unreadable_content(tmp_path, monkeypatch):
    """The RecursionError path, on every platform (see ``DEEP_JSON``)."""
    path = _write_year_file(tmp_path / "year.h5", stamp=_current())
    loads = json.loads

    def deep(text, *args, **kwargs):
        with h5py.File(path, "r") as file:
            if text == file[YEAR_FILE_STAMP_H5_DATASET].asstr()[()]:
                raise RecursionError("maximum recursion depth exceeded")
        return loads(text, *args, **kwargs)

    monkeypatch.setattr(json, "loads", deep)

    assert year_file_stamp_problem(path, IDENTITY) == MALFORMED


def test_a_dangling_link_in_place_of_the_stamp_reads_as_absent(tmp_path):
    path = _write_year_file(tmp_path / "year.h5")
    with h5py.File(path, "a") as file:
        file[YEAR_FILE_STAMP_H5_DATASET] = h5py.ExternalLink(
            str(tmp_path / "missing.h5"), "/stamp"
        )

    assert year_file_stamp_problem(path, IDENTITY) == NO_STAMP
    assert read_year_file_stamp(path) is None


@pytest.mark.parametrize("links", ["cycle", "chain"])
def test_stamp_links_that_cannot_be_followed_are_unreadable_content(tmp_path, links):
    """Totality: h5py raises RuntimeError for these, which reads as
    unreadable content rather than escaping."""
    path = _write_year_file(tmp_path / "year.h5")
    with h5py.File(path, "a") as file:
        if links == "cycle":
            _link_cycle(file, YEAR_FILE_STAMP_H5_DATASET)
        else:
            _write_node(file, f"{YEAR_FILE_STAMP_H5_DATASET}_end", _current())
            _link_chain(file, YEAR_FILE_STAMP_H5_DATASET)

    assert year_file_stamp_problem(path, IDENTITY) == MALFORMED
    assert read_year_file_stamp(path) is None


def test_a_file_stamped_for_the_requested_source_is_current(tmp_path):
    path = _write_year_file(tmp_path / "year.h5", stamp=_current())

    assert year_file_stamp_problem(path, IDENTITY) is None


# --- Named differences --------------------------------------------------


@settings(max_examples=300, deadline=None)
@given(
    source=SOURCES,
    stamped_source=SOURCES,
    packages=PACKAGE_MAPS,
    stamped_packages=PACKAGE_MAPS,
)
def test_a_stale_year_file_names_each_source_and_version_that_differs(
    source, stamped_source, packages, stamped_packages
):
    """The reason has a source clause exactly when the sources differ, naming
    both, and one clause for each package whose version differs or that only
    one side records, naming it; nothing that agrees is mentioned."""
    with tempfile.TemporaryDirectory() as directory:
        path = _write_year_file(
            Path(directory) / "year.h5",
            stamp=_stamp(REVISION, stamped_source, stamped_packages),
        )
        problem = year_file_stamp_problem(path, source, packages)

    differing = {
        name
        for name in stamped_packages.keys() | packages.keys()
        if name not in stamped_packages
        or name not in packages
        or stamped_packages[name] != packages[name]
    }
    if stamped_source == source and not differing:
        assert problem is None
        return
    clauses = problem.split("; ")
    source_clauses = [c for c in clauses if c.startswith("it was cut from ")]
    if stamped_source == source:
        assert source_clauses == []
    else:
        assert source_clauses == [
            f"it was cut from {describe_dataset_source_identity(stamped_source)}, "
            "and the requested source is "
            f"{describe_dataset_source_identity(source)}"
        ]
    package_clauses = [c for c in clauses if c not in source_clauses]
    assert len(package_clauses) == len(differing)
    for name, clause in zip(sorted(differing), package_clauses):
        assert name in clause
        for other in (stamped_packages.keys() | packages.keys()) - {name}:
            assert other not in clause


@pytest.mark.parametrize(
    "stamped_source, source, described",
    [
        (
            {
                "uri": "hf://policyengine/uk-data/enhanced_frs_2024_25.h5@1.58.0",
                "sha256": "a" * 64,
            },
            {
                "uri": "hf://policyengine/uk-data/enhanced_frs_2024_25.h5@1.59.0",
                "sha256": "b" * 64,
            },
            "hf://policyengine/uk-data/enhanced_frs_2024_25.h5@1.58.0 (sha256 "
            f"{'a' * 64}), and the requested source is "
            "hf://policyengine/uk-data/enhanced_frs_2024_25.h5@1.59.0 (sha256 "
            f"{'b' * 64})",
        ),
        (
            # A re-upload under the same revision name.
            {"uri": "hf://org/repo/populace_uk_2023.h5@r", "sha256": "a" * 64},
            {"uri": "hf://org/repo/populace_uk_2023.h5@r", "sha256": "b" * 64},
            f"hf://org/repo/populace_uk_2023.h5@r (sha256 {'a' * 64}), and the "
            "requested source is hf://org/repo/populace_uk_2023.h5@r (sha256 "
            f"{'b' * 64})",
        ),
        (
            {"path": "/data/frs.h5", "size": 10, "mtime_ns": 1_760_000_000_000_000_001},
            {"path": "/data/frs.h5", "size": 12, "mtime_ns": 1_760_000_060_000_000_000},
            "/data/frs.h5 (10 bytes, modified 2025-10-09T08:53:20.000000001Z), "
            "and the requested source is /data/frs.h5 (12 bytes, modified "
            "2025-10-09T08:54:20.000000000Z)",
        ),
    ],
)
def test_a_year_file_cut_from_another_source_names_both(
    tmp_path, stamped_source, source, described
):
    path = _write_year_file(tmp_path / "year.h5", stamp=_stamp(source=stamped_source))

    assert year_file_stamp_problem(path, source) == f"it was cut from {described}"


@pytest.mark.parametrize(
    "stamped_packages, packages, reason",
    [
        (
            {**PACKAGES, "policyengine-uk": "2.126.11"},
            PACKAGES,
            "it was cut with policyengine-uk 2.126.11, and policyengine-uk "
            "2.126.12 is installed",
        ),
        (
            PACKAGES,
            {**PACKAGES, "policyengine-uk": None},
            "it was cut with policyengine-uk 2.126.12, and policyengine-uk is "
            "not installed",
        ),
        (
            {"policyengine-uk": "2.126.12"},
            PACKAGES,
            "it was cut with no recorded policyengine-core version, and "
            "policyengine-core 3.33.0 is installed",
        ),
        (
            {**PACKAGES, "policyengine-us": "2.2.1"},
            PACKAGES,
            "it records the policyengine-us version it was cut with, which this "
            "version of policyengine.py does not check",
        ),
        (
            {"policyengine-core": "3.32.0", "policyengine-uk": "2.126.11"},
            PACKAGES,
            "it was cut with policyengine-core 3.32.0, and policyengine-core "
            "3.33.0 is installed; it was cut with policyengine-uk 2.126.11, and "
            "policyengine-uk 2.126.12 is installed",
        ),
    ],
)
def test_a_year_file_cut_with_other_versions_names_them(
    tmp_path, stamped_packages, packages, reason
):
    path = _write_year_file(
        tmp_path / "year.h5", stamp=_stamp(packages=stamped_packages)
    )

    assert year_file_stamp_problem(path, IDENTITY, packages) == reason


def test_every_difference_is_named_in_order(tmp_path):
    path = _write_year_file(
        tmp_path / "year.h5",
        stamp=_stamp(
            source={"uri": f"{SOURCE}@old"},
            packages={**PACKAGES, "policyengine-uk": "2.126.11"},
        ),
    )

    assert year_file_stamp_problem(path, IDENTITY) == (
        f"it was cut from {SOURCE}@old, and the requested source is {SOURCE}; "
        "it was cut with policyengine-uk 2.126.11, and policyengine-uk "
        "2.126.12 is installed"
    )


# --- Differential: the US check names differences the same way -----------


@settings(max_examples=150, deadline=None)
@given(
    source=SOURCES,
    stamped_source=SOURCES,
    packages=PACKAGE_MAPS,
    stamped_packages=PACKAGE_MAPS,
)
def test_the_uk_and_us_checks_name_source_and_package_differences_alike(
    source, stamped_source, packages, stamped_packages
):
    """Two implementations of one semantics: a UK and a US year file that
    differ from the request only in source and packages get the same
    reason."""
    from policyengine.tax_benefit_models.us import legacy_inputs
    from policyengine.tax_benefit_models.us.datasets import (
        PolicyEngineUSDataset,
        USYearData,
    )

    groups = ("household", "tax_unit", "spm_unit", "family", "marital_unit")
    person = pd.DataFrame(
        {
            "person_id": [1],
            **{f"person_{group}_id": [1] for group in groups},
            "person_weight": [1.0],
        }
    )
    frames = {"person": person} | {
        group: pd.DataFrame({f"{group}_id": [1], f"{group}_weight": [1.0]})
        for group in groups
    }
    with tempfile.TemporaryDirectory() as directory:
        uk_path = _write_year_file(
            Path(directory) / "uk.h5",
            stamp=_stamp(REVISION, stamped_source, stamped_packages),
        )
        us_path = Path(directory) / "us.h5"
        PolicyEngineUSDataset(
            name="us",
            description="us",
            filepath=str(us_path),
            year=DATA_YEAR,
            data=USYearData(
                **{
                    entity: MicroDataFrame(frame, weights=f"{entity}_weight")
                    for entity, frame in frames.items()
                }
            ),
            metadata={legacy_inputs.RENAMES_RECORD_KEY: {}},
        ).save()
        us_stamp = legacy_inputs.year_file_stamp(stamped_source, stamped_packages)
        legacy_inputs.write_year_file_stamp(us_path, us_stamp)

        uk = year_file_stamp_problem(uk_path, source, packages)
        us = legacy_inputs.year_file_stamp_problem(us_path, source, packages)

    assert uk == us


# --- Partial files ------------------------------------------------------


@functools.cache
def _current_year_file_bytes() -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        path = _write_year_file(Path(directory) / "year.h5", stamp=_current())
        assert year_file_stamp_problem(path, IDENTITY) is None
        return path.read_bytes()


@settings(max_examples=100, deadline=None)
@given(data=st.data())
def test_a_truncated_year_file_is_never_current(data):
    content = _current_year_file_bytes()
    length = data.draw(st.integers(0, len(content) - 1))
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "year.h5"
        path.write_bytes(content[:length])

        assert year_file_stamp_problem(path, IDENTITY) is not None


def test_a_file_that_is_not_hdf5_is_out_of_date(tmp_path):
    path = tmp_path / "year.h5"
    path.write_text("not an H5 file")

    assert year_file_stamp_problem(path, IDENTITY) == NOT_HDF5
    assert NOT_HDF5 == (
        "it cannot be read as an HDF5 file (it may be half-written or corrupt)"
    )


def test_saving_a_year_file_again_drops_its_stamp(tmp_path):
    path = _write_year_file(tmp_path / "year.h5", stamp=_current())

    dataset = PolicyEngineUKDataset(
        name="year-file", description="reload", filepath=str(path), year=DATA_YEAR
    )
    dataset.save()

    # ``save()`` rewrites the tables and the data year it loaded, but not the
    # stamp, which only ``create_datasets`` writes.
    assert dataset.data_year == DATA_YEAR
    assert read_year_file_stamp(path) is None
    assert year_file_stamp_problem(path, IDENTITY) == NO_STAMP


def test_a_save_that_stops_part_way_leaves_no_stamp(tmp_path, monkeypatch):
    path = _write_year_file(tmp_path / "year.h5", stamp=_current())
    put = pd.HDFStore.put

    def put_until_household(self, key, value, *args, **kwargs):
        if key == "household":
            raise RuntimeError("stopped part-way")
        return put(self, key, value, *args, **kwargs)

    monkeypatch.setattr(pd.HDFStore, "put", put_until_household)
    with pytest.raises(RuntimeError, match="stopped part-way"):
        _year_dataset(path).save()

    assert read_year_file_stamp(path) is None
    # The data year is written after the tables, so it is missing too.
    assert year_file_stamp_problem(path, IDENTITY) == NO_DATA_YEAR


# --- Errors unrelated to the file's contents ----------------------------


def _unreadable_by_permission(path) -> Path:
    path = _write_year_file(path, stamp=_current())
    os.chmod(path, 0)
    return path


def _a_directory(path) -> Path:
    path.mkdir()
    return path


@pytest.mark.parametrize(
    "make, error",
    [
        (_unreadable_by_permission, PermissionError),
        (_a_directory, IsADirectoryError),
    ],
)
def test_errors_unrelated_to_the_contents_are_raised(tmp_path, make, error):
    if error is PermissionError and hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root can read a file without permission bits")
    data_folder = tmp_path / "data"
    data_folder.mkdir()
    path = make(data_folder / f"{STEM}_year_2024.h5")
    create = MagicMock()
    try:
        with pytest.raises(error):
            year_file_stamp_problem(path, IDENTITY)
        with pytest.raises(error):
            load_datasets(datasets=[SOURCE], years=[2024], data_folder=str(data_folder))
        with patch.object(uk_datasets, "create_datasets", create):
            with pytest.raises(error):
                ensure_datasets(
                    datasets=[SOURCE], years=[2024], data_folder=str(data_folder)
                )
    finally:
        if path.is_file():
            os.chmod(path, 0o644)
    create.assert_not_called()


def test_a_locked_file_is_raised_not_cut_again(tmp_path, monkeypatch):
    path = _write_year_file(tmp_path / "year.h5", stamp=_current())

    def locked(*args, **kwargs):
        raise BlockingIOError(35, "Unable to lock file")

    monkeypatch.setattr(h5py, "File", locked)
    with pytest.raises(BlockingIOError):
        year_file_stamp_problem(path, IDENTITY)


ERRORS = [
    PermissionError(13, "Permission denied"),
    IsADirectoryError(21, "Is a directory"),
    BlockingIOError(35, "Unable to lock file"),
]


@pytest.mark.parametrize("error", ERRORS)
def test_errors_unrelated_to_the_contents_are_raised_while_reading_the_stamp(
    tmp_path, monkeypatch, error
):
    path = _write_year_file(tmp_path / "year.h5", stamp=_current())

    def fail(self, *args, **kwargs):
        raise error

    monkeypatch.setattr(h5py.Dataset, "asstr", fail)
    with pytest.raises(type(error)):
        year_file_stamp_problem(path, IDENTITY)


@pytest.mark.parametrize("error", ERRORS)
def test_errors_unrelated_to_the_contents_are_raised_while_finding_the_data_year(
    tmp_path, monkeypatch, error
):
    path = _write_year_file(tmp_path / "year.h5", stamp=_current())
    get = h5py.Group.get

    def fail_for_the_data_year(self, name, *args, **kwargs):
        if name == DATA_YEAR_KEY:
            raise error
        return get(self, name, *args, **kwargs)

    monkeypatch.setattr(h5py.Group, "get", fail_for_the_data_year)
    with pytest.raises(type(error)):
        year_file_stamp_problem(path, IDENTITY)


# --- ensure_datasets and load_datasets ----------------------------------

#: Year-file states: what is written, and whether the file is current
#: (``None``: the file is missing).
STATES = {
    "current": (dict(stamp=_current()), True),
    "before #556": (dict(data_year=False), False),
    "data year only": (dict(), False),
    "stamped, no data year": (dict(stamp=_current(), data_year=False), False),
    "older revision": (dict(stamp=_stamp(0)), False),
    "newer revision": (dict(stamp={"revision": 2}), False),
    "other source revision": (
        dict(stamp=_stamp(source={"uri": f"{SOURCE}@old"})),
        False,
    ),
    "verified source": (
        dict(stamp=_stamp(source={"uri": SOURCE, "sha256": "a" * 64})),
        False,
    ),
    "other policyengine-uk": (
        dict(stamp=_stamp(packages={**PACKAGES, "policyengine-uk": "2.126.11"})),
        False,
    ),
    "other policyengine-core": (
        dict(stamp=_stamp(packages={**PACKAGES, "policyengine-core": "3.34.0"})),
        False,
    ),
    "malformed stamp": (dict(stamp=("text", "not json")), False),
    "data year link cycle": (dict(stamp=_current(), data_year="link cycle"), False),
    "not HDF5": (None, False),
    "missing": (None, None),
}


def _make_state(path: Path, state: str, year: int) -> None:
    written, _ = STATES[state]
    if state == "missing":
        return
    if state == "not HDF5":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not an H5 file")
        return
    _write_year_file(path, **written, year=year)


def _create_current_files(datasets, years, data_folder, allow_unmanaged=False):
    """Stand in for ``create_datasets``: write current year files."""
    for year in years:
        _write_year_file(
            Path(data_folder) / f"{STEM}_year_{year}.h5", stamp=_current(), year=year
        )
    return {"created": True}


@settings(max_examples=80, deadline=None)
@given(states=st.lists(st.sampled_from(sorted(STATES)), min_size=1, max_size=3))
def test_ensure_cuts_again_exactly_when_load_would_refuse(states):
    years = [2024 + index for index in range(len(states))]
    stale = [state for state in states if STATES[state][1] is False]
    # load_datasets stops at the first year file it cannot use.
    first_unusable = next((s for s in states if STATES[s][1] is not True), None)
    with tempfile.TemporaryDirectory() as directory:
        data_folder = Path(directory) / "data"
        for year, state in zip(years, states):
            _make_state(data_folder / f"{STEM}_year_{year}.h5", state, year)

        if first_unusable is not None and STATES[first_unusable][1] is False:
            with pytest.raises(ValueError, match="is out of date: "):
                load_datasets(
                    datasets=[SOURCE], years=years, data_folder=str(data_folder)
                )

        expected_warnings = sorted(
            (str(path), problem)
            for year in years
            if (path := data_folder / f"{STEM}_year_{year}.h5").exists()
            and (problem := year_file_stamp_problem(path, IDENTITY)) is not None
        )
        create = MagicMock(side_effect=_create_current_files)
        with (
            patch.object(uk_datasets, "create_datasets", create),
            patch.object(uk_datasets.logger, "warning") as warning,
        ):
            ensure_datasets(
                datasets=[SOURCE], years=years, data_folder=str(data_folder)
            )

            assert create.called == (bool(stale) or "missing" in states)
            # One warning per out-of-date file, naming it and its reason.
            assert warning.call_count == len(stale)
            assert (
                sorted(
                    (str(call.args[1]), call.args[2]) for call in warning.call_args_list
                )
                == expected_warnings
            )
            for call in warning.call_args_list:
                assert call.args[0] == (
                    "UK year file %s is out of date: %s. Creating the year files again."
                )

            # The year files are now current, so they are reused.
            create.reset_mock()
            loaded = ensure_datasets(
                datasets=[SOURCE], years=years, data_folder=str(data_folder)
            )
            create.assert_not_called()
        assert sorted(loaded) == [f"{STEM}_{year}" for year in years]
        for year in years:
            assert loaded[f"{STEM}_{year}"].data_year == DATA_YEAR


@pytest.mark.parametrize("local_source", [False, True])
@pytest.mark.parametrize(
    "states",
    [
        ["current", "current"],
        ["current", "data year only"],
        ["current", "before #556"],
        ["current", "other source revision"],
        ["current", "other policyengine-uk"],
    ],
)
def test_ensure_decides_from_the_stamps_alone(tmp_path, states, local_source):
    """Deciding never opens a year file's tables (only its stamp and whether
    its data year exists), and never reads, hashes or downloads the source
    dataset or imports policyengine-uk. A local source is only
    ``stat()``-ed."""
    data_folder = tmp_path / "data"
    years = [2024, 2025]
    dataset, identity = SOURCE, IDENTITY
    if local_source:
        source_file = tmp_path / "sources" / f"{STEM}.h5"
        source_file.parent.mkdir()
        source_file.write_bytes(b"the source is never read")
        dataset, identity = (
            str(source_file),
            requested_dataset_source_identity("uk", str(source_file)),
        )
    for year, state in zip(years, states):
        written, _ = STATES[state]
        stamp = written.get("stamp", _ABSENT)
        if isinstance(stamp, dict) and stamp.get("source") == IDENTITY:
            stamp = {**stamp, "source": identity}
        _write_year_file(
            data_folder / f"{STEM}_year_{year}.h5",
            **{**written, "stamp": stamp},
            year=year,
        )
    load, create = MagicMock(return_value="loaded"), MagicMock(return_value="created")
    source_path = Path(dataset).resolve() if local_source else None

    def refuse(*args, **kwargs):
        raise AssertionError("deciding opened a table or the source dataset")

    class RefusedStore:
        """A class, so pandas' ``isinstance(..., HDFStore)`` checks still work."""

        def __init__(self, *args, **kwargs):
            refuse()

    real_file = h5py.File

    class StampAndDataYearOnly:
        """An H5 file that lets the decision read only the stamp and find the
        data year."""

        def __init__(self, path, mode="r", **kwargs):
            assert mode == "r"
            assert source_path is None or Path(path).resolve() != source_path
            self._file = real_file(path, mode, **kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self._file.close()

        def get(self, name, default=None):
            assert name in (YEAR_FILE_STAMP_H5_DATASET, DATA_YEAR_KEY), name
            node = self._file.get(name, default)
            if name == DATA_YEAR_KEY:
                # Its presence only: the group's contents are not handed over.
                return h5py.Group.__new__(h5py.Group) if node is not None else None
            return node

    real_open, real_import = builtins.open, builtins.__import__

    def open_anything_but_the_source(file, *args, **kwargs):
        if (
            source_path is not None
            and isinstance(file, str | os.PathLike)
            and Path(file).resolve() == source_path
        ):
            refuse()
        return real_open(file, *args, **kwargs)

    def import_anything_but_policyengine_uk(name, *args, **kwargs):
        if name == "policyengine_uk" or name.startswith("policyengine_uk."):
            raise AssertionError("deciding imported policyengine-uk")
        return real_import(name, *args, **kwargs)

    with (
        patch.object(h5py, "File", StampAndDataYearOnly),
        patch.object(pd, "HDFStore", RefusedStore),
        # ``pd.read_hdf`` looks HDFStore up in its own module, and PyTables
        # opens files without h5py.
        patch("pandas.io.pytables.HDFStore", RefusedStore),
        patch("tables.open_file", refuse),
        patch.object(builtins, "open", open_anything_but_the_source),
        patch.object(io, "open", open_anything_but_the_source),
        patch.object(builtins, "__import__", import_anything_but_policyengine_uk),
        patch.object(dataset_materialization, "sha256_file", refuse),
        patch.object(dataset_materialization.requests, "get", refuse),
        patch.object(uk_datasets, "materialize_dataset", refuse),
        patch.object(uk_datasets, "load_datasets", load),
        patch.object(uk_datasets, "create_datasets", create),
    ):
        result = ensure_datasets(
            datasets=[dataset], years=years, data_folder=str(data_folder)
        )

    stale = any(STATES[state][1] is False for state in states)
    assert result == ("created" if stale else "loaded")


def test_the_refusal_names_the_file_and_why(tmp_path):
    data_folder = tmp_path / "data"
    path = data_folder / f"{STEM}_year_2024.h5"
    _write_year_file(
        path, stamp=_stamp(packages={**PACKAGES, "policyengine-uk": "2.126.11"})
    )

    with pytest.raises(ValueError) as refused:
        load_datasets(datasets=[SOURCE], years=[2024], data_folder=str(data_folder))

    assert str(refused.value) == (
        f"UK year file {path} is out of date: it was cut with policyengine-uk "
        "2.126.11, and policyengine-uk 2.126.12 is installed. Regenerate it with "
        "ensure_datasets() or create_datasets()."
    )


def test_the_refusal_names_the_source_it_was_cut_from(tmp_path):
    data_folder = tmp_path / "data"
    path = data_folder / f"{STEM}_year_2024.h5"
    _write_year_file(path, stamp=_stamp(source={"uri": f"{SOURCE}@old"}))

    with pytest.raises(ValueError) as refused:
        load_datasets(datasets=[SOURCE], years=[2024], data_folder=str(data_folder))

    assert str(refused.value) == (
        f"UK year file {path} is out of date: it was cut from {SOURCE}@old, and "
        f"the requested source is {SOURCE}. Regenerate it with ensure_datasets() "
        "or create_datasets()."
    )


def test_a_year_file_without_a_data_year_is_refused_as_before(tmp_path):
    data_folder = tmp_path / "data"
    path = data_folder / f"{STEM}_year_2024.h5"
    _write_year_file(path, data_year=False)

    with pytest.raises(ValueError) as refused:
        load_datasets(datasets=[SOURCE], years=[2024], data_folder=str(data_folder))

    assert str(refused.value) == (
        f"UK year file {path} is out of date: {NO_DATA_YEAR}. Regenerate it "
        "with ensure_datasets() or create_datasets()."
    )


def test_load_and_ensure_compare_with_the_installed_versions(tmp_path, monkeypatch):
    """Both read the versions when called, not at import."""
    data_folder = tmp_path / "data"
    _write_year_file(data_folder / f"{STEM}_year_2024.h5", stamp=_current())
    load_datasets(datasets=[SOURCE], years=[2024], data_folder=str(data_folder))

    monkeypatch.setattr(
        uk_datasets,
        "installed_package_versions",
        lambda: {**PACKAGES, "policyengine-uk": "2.127.0"},
    )
    with pytest.raises(ValueError, match="policyengine-uk 2.127.0 is installed"):
        load_datasets(datasets=[SOURCE], years=[2024], data_folder=str(data_folder))
    create = MagicMock(return_value="created")
    with patch.object(uk_datasets, "create_datasets", create):
        assert (
            ensure_datasets(
                datasets=[SOURCE], years=[2024], data_folder=str(data_folder)
            )
            == "created"
        )


# --- Two sources never share year files --------------------------------

#: Requests whose stems (``pop`` or ``other``) collide in different ways.
COLLIDING = [
    "hf://fixture/repo/pop.h5@r1",
    "hf://fixture/repo/pop.h5@r2",
    "hf://elsewhere/repo/pop.h5@r1",
    "hf://fixture/repo/other.h5@r1",
]


def _stem_of(uri: str) -> str:
    return uri.rsplit("/", 1)[-1].split(".")[0]


@settings(max_examples=60, deadline=None)
@given(requests=st.lists(st.sampled_from(COLLIDING), min_size=1, max_size=4))
def test_two_sources_with_one_stem_are_refused_before_anything_is_cut(requests):
    """Requests that would share year files are refused by all three
    functions, before reading a year file or cutting one; requests of one
    source repeated, or of sources with different stems, are not."""
    stems = {}
    for request in requests:
        stems.setdefault(_stem_of(request), set()).add(request)
    collide = any(len(sources) > 1 for sources in stems.values())
    create = MagicMock(side_effect=lambda *a, **k: {})

    def refuse(*args, **kwargs):
        raise AssertionError("a year file was read or cut")

    with tempfile.TemporaryDirectory() as directory:
        with (
            patch.object(uk_datasets, "materialize_dataset", refuse),
            patch.object(uk_datasets, "year_file_stamp_problem", refuse),
            patch.object(uk_datasets, "PolicyEngineUKDataset", refuse),
        ):
            for call in (
                lambda: load_datasets(
                    datasets=requests, years=[2024], data_folder=directory
                ),
                lambda: uk_datasets.create_datasets(
                    datasets=requests,
                    years=[2024],
                    data_folder=directory,
                    allow_unmanaged=True,
                ),
            ):
                if collide:
                    with pytest.raises(ValueError, match="would share the UK year"):
                        call()
        with patch.object(uk_datasets, "create_datasets", create):
            if collide:
                with pytest.raises(ValueError, match="would share the UK year"):
                    ensure_datasets(
                        datasets=requests, years=[2024], data_folder=directory
                    )
                create.assert_not_called()
            else:
                ensure_datasets(datasets=requests, years=[2024], data_folder=directory)
                create.assert_called_once()


def test_the_collision_refusal_names_both_requests_and_sources(tmp_path):
    first, second = "hf://fixture/repo/pop.h5@r1", "hf://fixture/repo/pop.h5@r2"

    with pytest.raises(ValueError) as refused:
        ensure_datasets(
            datasets=[first, second], years=[2024], data_folder=str(tmp_path)
        )

    assert str(refused.value) == (
        f"Datasets {first!r} and {second!r} would share the UK year files "
        f"pop_year_{{year}}.h5, but are different sources: {first} and {second}. "
        "Request them in separate calls with separate data folders."
    )


def test_two_local_files_with_one_name_are_refused(tmp_path):
    """The usual smoke-test collision: ``pop.h5`` in two folders."""
    first, second = tmp_path / "a" / "pop.h5", tmp_path / "b" / "pop.h5"
    for path in (first, second):
        path.parent.mkdir()
        path.write_bytes(b"source")

    with pytest.raises(ValueError, match="would share the UK year files pop_year_"):
        ensure_datasets(
            datasets=[str(first), str(second)],
            years=[2024],
            data_folder=str(tmp_path / "data"),
            allow_unmanaged=True,
        )


@pytest.mark.parametrize(
    "requests, error",
    [
        (["not_a_bundle_dataset", SOURCE], "Unknown managed dataset"),
        ([SOURCE, "hf://fixture/repo/other.h5"], "Explicit dataset URIs bypass"),
    ],
)
def test_create_refuses_what_materialize_would_with_its_error(
    tmp_path, requests, error
):
    """With several datasets, ``create_datasets`` checks them all for shared
    year files first. A request ``materialize_dataset`` would refuse is
    refused there with the same error, and nothing is downloaded."""

    def refuse(*args, **kwargs):
        raise AssertionError("a dataset was materialized or downloaded")

    with (
        patch.object(uk_datasets, "materialize_dataset", refuse),
        patch("requests.get", refuse),
    ):
        with pytest.raises(ValueError, match=error):
            uk_datasets.create_datasets(
                datasets=requests, years=[2024], data_folder=str(tmp_path)
            )


@pytest.mark.parametrize(
    "request_, error",
    [
        ("s3://bucket/tiny.h5", "Unsupported explicit dataset URI"),
        ("hf://owner/repo", "Invalid Hugging Face dataset URI"),
    ],
)
def test_create_refuses_a_uri_materialize_would_before_cutting_anything(
    tmp_path, request_, error
):
    """Even with ``allow_unmanaged``, with ``materialize_dataset``'s error."""

    def refuse(*args, **kwargs):
        raise AssertionError("a dataset was materialized or downloaded")

    with patch.object(uk_datasets, "materialize_dataset", refuse):
        with pytest.raises(DatasetMaterializationError, match=error):
            uk_datasets.create_datasets(
                datasets=[SOURCE, request_],
                years=[2024],
                data_folder=str(tmp_path),
                allow_unmanaged=True,
            )


def test_one_source_requested_by_two_names_is_not_a_collision(tmp_path):
    """The default's logical name and its own URI are one source."""
    from policyengine.provenance.manifest import get_release_manifest

    manifest = get_release_manifest("uk")
    requests = [manifest.default_dataset, manifest.default_dataset_uri]
    create = MagicMock(return_value="created")

    with patch.object(uk_datasets, "create_datasets", create):
        assert (
            ensure_datasets(datasets=requests, years=[2024], data_folder=str(tmp_path))
            == "created"
        )


def test_the_default_is_checked_against_its_bundle_pin(tmp_path):
    """``datasets=None`` checks the certified default, by its manifest entry."""
    from policyengine.provenance.manifest import get_release_manifest

    manifest = get_release_manifest("uk")
    default = requested_dataset_source_identity("uk", None)
    stem = manifest.default_dataset
    data_folder = tmp_path / "data"
    _write_year_file(data_folder / f"{stem}_year_2026.h5", stamp=_stamp(source=default))
    load = MagicMock(return_value="loaded")

    with patch.object(uk_datasets, "load_datasets", load):
        assert ensure_datasets(years=[2026], data_folder=str(data_folder)) == "loaded"
    assert default["sha256"] == manifest.datasets[stem].sha256
    assert (
        year_file_stamp_problem(
            data_folder / f"{stem}_year_2026.h5",
            requested_dataset_source_identity("uk", manifest.default_dataset_uri),
        )
        is None
    )
