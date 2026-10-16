"""Unit and property tests for the stamp on US year files.

``create_datasets`` stamps each year file with the identity of the source
dataset it was cut from, the policyengine-core and policyengine-us versions
that calculated it, the register of renamed stored inputs it was cut under
and a year-file format revision (``legacy_inputs.YEAR_FILE_STAMP_H5_DATASET``).
``ensure_datasets`` cuts a year file again, and ``load_datasets`` refuses it,
unless the stamp matches the one a file cut now from the requested dataset
would carry. These tests state the check's invariants over generated stamps,
records, registers, sources and package versions, without a country engine:

- **Exactness.** A year file is current exactly when its stamp has this
  release's format revision and register, the requested source and the
  installed package versions, and its renames record lists only renames in
  that register.
- **Totality.** Whatever the stamp and record hold, the check returns a
  reason or ``None``, and raises only for errors unrelated to the file's
  contents (no permission, a directory, a lock).
- **Round trip.** A stamp reads back as written, and writing again replaces it.
- **Named differences.** The reason names every rename the file's register
  and this release's disagree on, both sources when they differ, and every
  package whose version differs, and nothing that agrees.
- **No partial file is current.** Every truncation of a current year file,
  every save that stops part-way and every save that does not stamp is out
  of date.
- **Ensure agrees with load.** ``ensure_datasets`` cuts the year files again
  exactly when one is missing or ``load_datasets`` would refuse one, and
  decides from the stamps alone: it never reads, downloads or hashes the
  source, and never imports policyengine-us.

``test_dataset_source_identity.py`` tests the source identities themselves,
and ``test_us_legacy_inputs_integration.py`` runs ``create_datasets`` and
``ensure_datasets`` over a real policyengine-us engine.
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
from policyengine.tax_benefit_models.us import datasets as us_datasets
from policyengine.tax_benefit_models.us import legacy_inputs
from policyengine.tax_benefit_models.us.datasets import (
    PolicyEngineUSDataset,
    USYearData,
    _is_policyengine_core_h5,
    ensure_datasets,
    load_datasets,
)
from policyengine.tax_benefit_models.us.legacy_inputs import (
    LEGACY_INPUT_RENAMES,
    RENAMES_H5_DATASET,
    YEAR_FILE_PACKAGES,
    YEAR_FILE_STAMP_H5_DATASET,
    YEAR_FILE_STAMP_REVISION,
    read_renames_record,
    read_year_file_stamp,
    write_renames_record,
    write_year_file_stamp,
    year_file_stamp,
    year_file_stamp_problem,
)
from policyengine.tax_benefit_models.us.legacy_spm import (
    RECORD_H5_DATASET as LEGACY_SPM_RECORD_H5_DATASET,
)

LEGACY = "would_claim_wic"
LIVE = "takes_up_wic_if_eligible"
REVISION = YEAR_FILE_STAMP_REVISION
#: ``hf://`` references are used as they are, and name year files after the
#: file's stem, so no manifest or download is involved. Its identity is the
#: URI as given.
SOURCE = "hf://fixture/repo/tiny.h5"
IDENTITY = {"uri": SOURCE}
STEM = "tiny"
GROUPS = ("household", "tax_unit", "spm_unit", "family", "marital_unit")
#: The installed versions every test in this module sees (see
#: ``_installed_packages``), so no expectation depends on the environment.
PACKAGES = {"policyengine-core": "3.33.0", "policyengine-us": "2.2.1"}
#: The real reader, kept before ``_installed_packages`` replaces it.
REAL_INSTALLED_PACKAGE_VERSIONS = legacy_inputs.installed_package_versions
MALFORMED = "its stamp of what it was cut from and under is malformed"

#: A small alphabet, so generated registers often share names and disagree
#: only on some entries.
NAMES = st.sampled_from(["alpha", "beta", "gamma", "delta"])
REGISTERS = st.dictionaries(NAMES, NAMES, max_size=3)
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
PACKAGE_NAMES = st.sampled_from([*YEAR_FILE_PACKAGES, "extra-package"])
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
            legacy_inputs, "installed_package_versions", lambda: dict(PACKAGES)
        )
        yield


def _frames() -> dict[str, pd.DataFrame]:
    person = pd.DataFrame(
        {
            "person_id": [1, 2],
            **{f"person_{group}_id": [1, 1] for group in GROUPS},
            "person_weight": [1.0, 1.0],
            LIVE: [True, False],
        }
    )
    frames = {"person": person}
    for group in GROUPS:
        frames[group] = pd.DataFrame({f"{group}_id": [1], f"{group}_weight": [1.0]})
    return frames


def _year_dataset(path) -> PolicyEngineUSDataset:
    return PolicyEngineUSDataset(
        name="year-file",
        description="Uncertified two-person year-file fixture",
        filepath=str(path),
        year=2024,
        data=USYearData(
            **{
                entity: MicroDataFrame(frame, weights=f"{entity}_weight")
                for entity, frame in _frames().items()
            }
        ),
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


def _write_year_file(path, *, stamp=_ABSENT, record=_ABSENT):
    """Write a year file's tables, then its record and stamp as given.

    ``stamp`` and ``record`` are JSON values, ``_ABSENT``, or a raw node
    (see :func:`_write_node`).
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    _year_dataset(path).save()
    with h5py.File(path, "a") as file:
        _write_node(file, RENAMES_H5_DATASET, record)
        _write_node(file, YEAR_FILE_STAMP_H5_DATASET, stamp)
    return Path(path)


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


def _is_current(stamp, record, register, source=IDENTITY, packages=PACKAGES) -> bool:
    """The exactness invariant, stated directly on the stored JSON values."""

    def str_map(value):
        return isinstance(value, dict) and all(
            isinstance(key, str) and isinstance(item, str)
            for key, item in value.items()
        )

    return (
        isinstance(stamp, dict)
        and set(stamp) == {"packages", "register", "revision", "source"}
        and type(stamp["revision"]) is int
        and stamp["revision"] == REVISION
        and str_map(stamp["register"])
        and stamp["register"] == register
        and _same_json(stamp["source"], source)
        and _same_json(stamp["packages"], packages)
        and str_map(record)
        and record.items() <= stamp["register"].items()
    )


def _stamp(register, revision=REVISION, source=IDENTITY, packages=PACKAGES):
    return {
        "packages": dict(packages),
        "register": dict(register),
        "revision": revision,
        "source": dict(source),
    }


def _current():
    return year_file_stamp(IDENTITY)


# --- The stamp ----------------------------------------------------------


def test_the_stamp_holds_the_source_packages_register_and_revision():
    assert _current() == {
        "packages": PACKAGES,
        "register": {LEGACY: LIVE},
        "revision": 2,
        "source": IDENTITY,
    }
    assert _current()["register"] == LEGACY_INPUT_RENAMES


def test_the_stamp_reads_the_register_and_packages_when_called(monkeypatch):
    """datasets.py must not freeze the register or the versions at import."""
    monkeypatch.setattr(legacy_inputs, "LEGACY_INPUT_RENAMES", {"b": "c", "a": "d"})
    monkeypatch.setattr(
        legacy_inputs, "installed_package_versions", lambda: {"z": None, "y": "1"}
    )

    assert year_file_stamp(IDENTITY) == {
        "packages": {"y": "1", "z": None},
        "register": {"a": "d", "b": "c"},
        "revision": 2,
        "source": IDENTITY,
    }


def test_explicit_packages_override_the_installed_ones():
    assert year_file_stamp(IDENTITY, {"policyengine-us": "9"})["packages"] == {
        "policyengine-us": "9"
    }


def test_the_stamp_is_stored_as_utf8_json(tmp_path):
    path = _write_year_file(tmp_path / "year.h5")

    write_year_file_stamp(path, _current())

    with h5py.File(path, "r") as file:
        assert file[YEAR_FILE_STAMP_H5_DATASET].asstr()[()] == (
            '{"packages": {"policyengine-core": "3.33.0", "policyengine-us": '
            f'"2.2.1"}}, "register": {{"{LEGACY}": "{LIVE}"}}, "revision": 2, '
            f'"source": {{"uri": "{SOURCE}"}}}}'
        )


def test_installed_package_versions_reads_metadata(monkeypatch):
    """The real reader: distribution metadata, ``None`` when absent."""
    monkeypatch.setattr(
        legacy_inputs,
        "YEAR_FILE_PACKAGES",
        ("pytest", "hypothesis", "not-a-distribution-policyengine-test"),
    )

    assert REAL_INSTALLED_PACKAGE_VERSIONS() == {
        "pytest": importlib_metadata.version("pytest"),
        "hypothesis": importlib_metadata.version("hypothesis"),
        "not-a-distribution-policyengine-test": None,
    }


def test_the_stamp_records_policyengine_core_and_policyengine_us():
    assert YEAR_FILE_PACKAGES == ("policyengine-core", "policyengine-us")


STAMPS = st.fixed_dictionaries(
    {
        "packages": PACKAGE_MAPS,
        "register": REGISTERS,
        "revision": st.integers(),
        "source": SOURCES,
    }
)


@settings(max_examples=50, deadline=None)
@given(first=STAMPS, second=STAMPS)
def test_a_year_file_stamp_reads_back_as_written(first, second):
    """Round trip: a stamp reads back exactly, a new one replaces it, and
    the tables and record are left alone."""
    with tempfile.TemporaryDirectory() as directory:
        path = _write_year_file(Path(directory) / "year.h5", record={})
        assert read_year_file_stamp(path) is None

        write_year_file_stamp(path, first)
        assert read_year_file_stamp(path) == first

        write_year_file_stamp(path, second)
        assert read_year_file_stamp(path) == second
        assert read_renames_record(path) == {}
        with pd.HDFStore(path, mode="r") as store:
            assert store["person"]["person_id"].tolist() == [1, 2]


def test_a_missing_or_foreign_file_has_no_stamp(tmp_path):
    assert read_year_file_stamp(tmp_path / "missing.h5") is None
    text = tmp_path / "notes.txt"
    text.write_text("not an H5 file")
    assert read_year_file_stamp(text) is None


def test_the_stamp_does_not_disturb_pandas_or_the_layout_check(tmp_path):
    path = _write_year_file(tmp_path / "year.h5", stamp=_current(), record={})

    with pd.HDFStore(path, mode="r") as store:
        assert sorted(store.keys()) == sorted(f"/{key}" for key in _frames())
    assert not _is_policyengine_core_h5(path)
    loaded = PolicyEngineUSDataset(
        name="year-file", description="reload", filepath=str(path), year=2024
    )
    assert pd.DataFrame(loaded.data.person)[LIVE].tolist() == [True, False]
    assert loaded.metadata["legacy_input_renames"] == {}


# --- Exactness ----------------------------------------------------------


@st.composite
def stamped_files(draw):
    """A current register, source and packages, and a year file's stamp and
    record near them."""
    register = draw(REGISTERS)
    source = draw(SOURCES)
    packages = draw(PACKAGE_MAPS)
    stamped = draw(
        st.one_of(
            st.just(dict(register)),
            REGISTERS,
            # One entry dropped, added or pointed elsewhere.
            st.builds(
                lambda name: {k: v for k, v in register.items() if k != name},
                NAMES,
            ),
            st.builds(lambda k, v: {**register, k: v}, NAMES, NAMES),
        )
    )
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
    revision = draw(st.sampled_from([REVISION, REVISION, 0, 1, 3, -1, 99]))
    record = draw(
        st.one_of(
            st.just(_ABSENT),
            # A subset of the stamped register, as create_datasets writes.
            st.builds(
                lambda keep: {k: v for k, v in stamped.items() if k in keep},
                st.sets(NAMES),
            ),
            REGISTERS,
        )
    )
    stamp = _stamp(stamped, revision, stamped_source, stamped_packages)
    return register, source, packages, stamp, record


@settings(max_examples=400, deadline=None)
@given(case=stamped_files())
def test_a_year_file_is_current_only_under_the_exact_stamp_requested(case):
    """Exactness, and refinement of the record check a year file had before.

    A subset rule would accept a file cut by a newer release under a larger
    register, which stores live names this release's engine may not define.
    """
    register, source, packages, stamp, record = case
    with tempfile.TemporaryDirectory() as directory:
        path = _write_year_file(Path(directory) / "year.h5", stamp=stamp, record=record)
        with patch.object(legacy_inputs, "LEGACY_INPUT_RENAMES", register):
            problem = year_file_stamp_problem(path, source, packages)

        assert (problem is None) == _is_current(
            _stored(stamp), _stored(record), register, source, packages
        )
        assert problem is None or (isinstance(problem, str) and problem)
        if problem is None:
            # Every file the stamp accepts, the record check accepted too.
            assert read_renames_record(path) == record


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
            "register": st.one_of(REGISTERS, JSON_VALUES),
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
    record=NODES,
    register=REGISTERS,
    source=SOURCES,
    packages=PACKAGE_MAPS,
)
def test_the_year_file_problem_is_total_and_exact_for_any_content(
    stamp, record, register, source, packages
):
    """Totality: any stamp and record give a reason or ``None``, never an
    error, and ``None`` exactly for the stamp requested, however it is
    stored (``_stored`` decodes raw nodes independently of the checker)."""
    with tempfile.TemporaryDirectory() as directory:
        path = _write_year_file(Path(directory) / "year.h5", stamp=stamp, record=record)
        with patch.object(legacy_inputs, "LEGACY_INPUT_RENAMES", register):
            problem = year_file_stamp_problem(path, source, packages)

    assert problem is None or (isinstance(problem, str) and problem)
    assert (problem is None) == _is_current(
        _stored(stamp), _stored(record), register, source, packages
    )


@pytest.mark.parametrize(
    "record",
    [("text", "{}"), ("bytes", b"{}"), ("bytes", b"{}\x00\x00")],
)
def test_a_record_stored_raw_is_read_as_its_json(tmp_path, monkeypatch, record):
    """The case a one-directional totality check missed: raw text or bytes
    that hold an empty record, under an empty register."""
    monkeypatch.setattr(legacy_inputs, "LEGACY_INPUT_RENAMES", {})
    path = _write_year_file(tmp_path / "year.h5", stamp=_current(), record=record)

    assert year_file_stamp_problem(path, IDENTITY) is None
    assert _is_current(_stored(_current()), _stored(record), {})


@pytest.mark.parametrize(
    "stamp",
    [
        {**_stamp({LEGACY: LIVE}), "revision": True},
        {**_stamp({LEGACY: LIVE}), "revision": 2.0},
        {**_stamp({LEGACY: LIVE}), "revision": "2"},
        {"register": {LEGACY: LIVE}, "revision": 2},
        {k: v for k, v in _stamp({LEGACY: LIVE}).items() if k != "source"},
        {k: v for k, v in _stamp({LEGACY: LIVE}).items() if k != "packages"},
        {**_stamp({LEGACY: LIVE}), "extra": None},
        {**_stamp({LEGACY: LIVE}), "register": {LEGACY: 5}},
        {**_stamp({LEGACY: LIVE}), "register": [[LEGACY, LIVE]]},
        {**_stamp({LEGACY: LIVE}), "packages": {"policyengine-us": 2.2}},
        {**_stamp({LEGACY: LIVE}), "packages": [["policyengine-us", "2.2.1"]]},
        {**_stamp({LEGACY: LIVE}), "source": SOURCE},
        {**_stamp({LEGACY: LIVE}), "source": {}},
        {**_stamp({LEGACY: LIVE}), "source": {"uri": 5}},
        {**_stamp({LEGACY: LIVE}), "source": {"uri": SOURCE, "sha256": None}},
        {**_stamp({LEGACY: LIVE}), "source": {"uri": SOURCE, "revision": "r1"}},
        {
            **_stamp({LEGACY: LIVE}),
            "source": {"path": "/a", "size": True, "mtime_ns": 1},
        },
        {
            **_stamp({LEGACY: LIVE}),
            "source": {"path": "/a", "size": 1, "mtime_ns": 1.0},
        },
        {**_stamp({LEGACY: LIVE}), "source": {"path": "/a", "size": 1}},
        [_stamp({LEGACY: LIVE})],
        ("text", "not json"),
        ("text", ""),
        ("bytes", b"\xff\xfe"),
        ("number", 2),
        ("array", ["{}"]),
        ("group", None),
    ],
)
def test_a_malformed_stamp_is_out_of_date(tmp_path, stamp):
    path = _write_year_file(tmp_path / "year.h5", stamp=stamp, record={})

    assert year_file_stamp_problem(path, IDENTITY) == MALFORMED


@pytest.mark.parametrize("revision", [0, 1, 3, -1])
def test_a_year_file_from_another_format_revision_is_out_of_date(tmp_path, revision):
    # Another revision may shape the rest of its stamp and record differently,
    # and is still reported by revision rather than as malformed.
    stamp = {"revision": revision, "registers": [[LEGACY, LIVE]]}
    path = _write_year_file(tmp_path / "year.h5", stamp=stamp)

    assert year_file_stamp_problem(path, IDENTITY) == (
        f"it was cut with year-file format revision {revision}, and this "
        "version of policyengine.py reads only revision 2"
    )


def test_a_year_file_stamped_by_revision_1_is_cut_again_once(tmp_path):
    """The stamp #590 wrote holds no source or package versions."""
    path = _write_year_file(
        tmp_path / "year.h5",
        stamp={"register": dict(LEGACY_INPUT_RENAMES), "revision": 1},
        record={},
    )

    assert year_file_stamp_problem(path, IDENTITY) == (
        "it was cut with year-file format revision 1, and this version of "
        "policyengine.py reads only revision 2"
    )


def test_files_without_a_stamp_are_out_of_date_with_distinct_reasons(tmp_path):
    """policyengine.py 6.1.1 and earlier wrote neither; #531 wrote the record."""
    oldest = _write_year_file(tmp_path / "oldest.h5")
    record_only = _write_year_file(tmp_path / "record_only.h5", record={LEGACY: LIVE})

    assert year_file_stamp_problem(oldest, IDENTITY) == (
        "it has no record of the renamed stored inputs mapped when it was cut, "
        "so it was cut by an older policyengine.py or not written completely, "
        f"and may have lost any of: {LEGACY} -> {LIVE}"
    )
    assert year_file_stamp_problem(record_only, IDENTITY) == (
        "it has no stamp of the register of renamed inputs it was cut under, so "
        f"it may have lost any of: {LEGACY} -> {LIVE}"
    )


def test_an_unstamped_file_is_out_of_date_even_with_an_empty_register(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(legacy_inputs, "LEGACY_INPUT_RENAMES", {})
    oldest = _write_year_file(tmp_path / "oldest.h5")
    record_only = _write_year_file(tmp_path / "record_only.h5", record={})

    assert year_file_stamp_problem(oldest, IDENTITY) == (
        "it has no record of the renamed stored inputs mapped when it was cut, "
        "so it was cut by an older policyengine.py or not written completely"
    )
    assert year_file_stamp_problem(record_only, IDENTITY) == (
        "it has no stamp of the register of renamed inputs it was cut under"
    )


@pytest.mark.parametrize(
    "record, reason",
    [
        (
            _ABSENT,
            "it has no record of the renamed stored inputs mapped when it was cut",
        ),
        (
            [],
            "its record of the renamed stored inputs mapped when it was cut is malformed",
        ),
        (
            [[LEGACY, LIVE]],
            "its record of the renamed stored inputs mapped when it was cut is malformed",
        ),
        (
            5,
            "its record of the renamed stored inputs mapped when it was cut is malformed",
        ),
        (
            {LEGACY: 1},
            "its record of the renamed stored inputs mapped when it was cut is malformed",
        ),
        (
            ("text", "{"),
            "its record of the renamed stored inputs mapped when it was cut is malformed",
        ),
        (
            ("group", None),
            "its record of the renamed stored inputs mapped when it was cut is malformed",
        ),
        (
            {"retired": "replacement"},
            "its record lists renames outside the register it was stamped with: "
            "retired -> replacement",
        ),
        (
            {LEGACY: "elsewhere"},
            "its record lists renames outside the register it was stamped with: "
            f"{LEGACY} -> elsewhere",
        ),
    ],
)
def test_a_stamped_file_needs_a_record_within_its_register(tmp_path, record, reason):
    path = _write_year_file(tmp_path / "year.h5", stamp=_current(), record=record)

    assert year_file_stamp_problem(path, IDENTITY) == reason


def test_a_stamp_and_record_stored_as_fixed_length_strings_are_read(tmp_path):
    stamp = json.dumps(_current()).encode()
    record = json.dumps({LEGACY: LIVE}).encode()
    path = _write_year_file(
        tmp_path / "year.h5", stamp=("bytes", stamp), record=("bytes", record)
    )

    assert year_file_stamp_problem(path, IDENTITY) is None
    assert read_year_file_stamp(path) == _current()
    assert read_renames_record(path) == {LEGACY: LIVE}


def test_raising_the_format_revision_makes_older_files_out_of_date(
    tmp_path, monkeypatch
):
    older = _write_year_file(tmp_path / "older.h5", stamp=_current(), record={})
    monkeypatch.setattr(legacy_inputs, "YEAR_FILE_STAMP_REVISION", 7)
    newer = _write_year_file(tmp_path / "newer.h5", stamp=_current(), record={})

    assert _current()["revision"] == 7
    assert year_file_stamp_problem(newer, IDENTITY) is None
    assert year_file_stamp_problem(older, IDENTITY) == (
        "it was cut with year-file format revision 2, and this version of "
        "policyengine.py reads only revision 7"
    )


#: JSON nested very deeply. Whether the parser reaches its limit depends on
#: the interpreter and the platform: CPython 3.14 checks the native stack, so
#: it varies with stack size, architecture and build. In our runs, CPython
#: 3.11-3.13, and 3.14 on macOS, raised RecursionError, while 3.14 on CI's
#: Linux runners parsed it into nested lists. Either way the stamp or record
#: is not well formed.
DEEP_JSON = "[" * 100_000 + "0" + "]" * 100_000


@pytest.mark.parametrize(
    "stamp, record, reason",
    [
        (("text", DEEP_JSON), {}, MALFORMED),
        (
            _current(),
            ("text", DEEP_JSON),
            "its record of the renamed stored inputs mapped when it was cut is "
            "malformed",
        ),
        (
            {"revision": 3},
            ("text", DEEP_JSON),
            "it was cut with year-file format revision 3, and this version of "
            "policyengine.py reads only revision 2",
        ),
    ],
)
def test_json_nested_too_deeply_is_out_of_date_not_an_error(
    tmp_path, stamp, record, reason
):
    path = _write_year_file(tmp_path / "year.h5", stamp=stamp, record=record)

    assert year_file_stamp_problem(path, IDENTITY) == reason
    if isinstance(stamp, tuple):
        # Unreadable (None) or parsed into nested lists, but never a stamp.
        assert not isinstance(read_year_file_stamp(path), dict)
    else:
        assert read_year_file_stamp(path) == stamp
    assert read_renames_record(path) == (None if isinstance(record, tuple) else record)


@pytest.mark.parametrize("name", [YEAR_FILE_STAMP_H5_DATASET, RENAMES_H5_DATASET])
def test_a_recursion_error_while_parsing_is_unreadable_content(
    tmp_path, monkeypatch, name
):
    """The RecursionError path, on every platform (see ``DEEP_JSON``)."""
    path = _write_year_file(tmp_path / "year.h5", stamp=_current(), record={})
    loads = json.loads

    def deep(text, *args, **kwargs):
        with h5py.File(path, "r") as file:
            if text == file[name].asstr()[()]:
                raise RecursionError("maximum recursion depth exceeded")
        return loads(text, *args, **kwargs)

    monkeypatch.setattr(legacy_inputs.json, "loads", deep)

    assert year_file_stamp_problem(path, IDENTITY) == (
        MALFORMED
        if name == YEAR_FILE_STAMP_H5_DATASET
        else "its record of the renamed stored inputs mapped when it was cut is "
        "malformed"
    )


def test_dangling_links_in_place_of_the_stamp_and_record_read_as_absent(tmp_path):
    path = _write_year_file(tmp_path / "year.h5")
    with h5py.File(path, "a") as file:
        file[YEAR_FILE_STAMP_H5_DATASET] = h5py.SoftLink("/nowhere")
        file[RENAMES_H5_DATASET] = h5py.ExternalLink(
            str(tmp_path / "missing.h5"), "/record"
        )

    assert year_file_stamp_problem(path, IDENTITY).startswith(
        "it has no record of the renamed stored inputs mapped when it was cut"
    )
    assert read_year_file_stamp(path) is None
    assert read_renames_record(path) is None


def _link_cycle(file, name) -> None:
    """Point ``name`` into a cycle of soft links."""
    file[name] = h5py.SoftLink(f"/{name}_loop")
    file[f"{name}_loop"] = h5py.SoftLink(f"/{name}")


def _long_link_chain(file, name) -> None:
    """Point ``name`` down a chain of soft links too long to follow, to a
    node that would be well formed if reached."""
    content = _current() if name == YEAR_FILE_STAMP_H5_DATASET else {}
    _write_node(file, f"{name}_end", content)
    file[name] = h5py.SoftLink(f"/{name}_0")
    for index in range(100):
        file[f"{name}_{index}"] = h5py.SoftLink(f"/{name}_{index + 1}")
    file[f"{name}_100"] = h5py.SoftLink(f"/{name}_end")


@pytest.mark.parametrize("links", [_link_cycle, _long_link_chain])
@pytest.mark.parametrize("name", [YEAR_FILE_STAMP_H5_DATASET, RENAMES_H5_DATASET])
def test_links_that_cannot_be_followed_are_unreadable_content(tmp_path, links, name):
    """Totality: h5py raises RuntimeError for these, which reads as
    unreadable content rather than escaping."""
    path = _write_year_file(
        tmp_path / "year.h5",
        **{"stamp": _current(), "record": {}, **{_NODE_ARGUMENT[name]: _ABSENT}},
    )
    with h5py.File(path, "a") as file:
        links(file, name)

    assert year_file_stamp_problem(path, IDENTITY) == (
        MALFORMED
        if name == YEAR_FILE_STAMP_H5_DATASET
        else "its record of the renamed stored inputs mapped when it was cut is "
        "malformed"
    )
    if name == YEAR_FILE_STAMP_H5_DATASET:
        assert read_year_file_stamp(path) is None
    else:
        assert read_renames_record(path) is None


#: Which ``_write_year_file`` argument writes each node.
_NODE_ARGUMENT = {YEAR_FILE_STAMP_H5_DATASET: "stamp", RENAMES_H5_DATASET: "record"}


@pytest.mark.parametrize("record", [{}, {LEGACY: LIVE}])
def test_a_file_stamped_for_the_requested_source_is_current(tmp_path, record):
    path = _write_year_file(tmp_path / "year.h5", stamp=_current(), record=record)

    assert year_file_stamp_problem(path, IDENTITY) is None


# --- Named differences --------------------------------------------------


@settings(max_examples=200, deadline=None)
@given(register=REGISTERS, stamped=REGISTERS)
def test_a_stale_year_file_names_each_rename_it_may_lack(register, stamped):
    """The reason names every entry the registers disagree on, as
    ``old -> new`` from the register that has it, and no other."""
    with tempfile.TemporaryDirectory() as directory:
        path = _write_year_file(
            Path(directory) / "year.h5", stamp=_stamp(stamped), record={}
        )
        with patch.object(legacy_inputs, "LEGACY_INPUT_RENAMES", register):
            problem = year_file_stamp_problem(path, IDENTITY)

    if stamped == register:
        assert problem is None
        return
    missing = {k: v for k, v in register.items() if stamped.get(k) != v}
    unknown = {k: v for k, v in stamped.items() if register.get(k) != v}
    clauses = problem.split("; ")
    for legacy, live in missing.items():
        assert f"{legacy} -> {live}" in clauses[0]
    for legacy, live in unknown.items():
        assert f"{legacy} -> {live}" in clauses[-1]
    assert ("cut before these renames were registered" in problem) == bool(missing)
    assert ("does not register" in problem) == bool(unknown)
    for legacy, live in register.items() & stamped.items():
        assert f"{legacy} -> {live}" not in problem


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
            stamp=_stamp(
                LEGACY_INPUT_RENAMES, REVISION, stamped_source, stamped_packages
            ),
            record={},
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
            {"uri": "hf://org/repo/acs.h5@old", "sha256": "a" * 64},
            {"uri": "hf://org/repo/acs.h5@new", "sha256": "b" * 64},
            f"hf://org/repo/acs.h5@old (sha256 {'a' * 64}), and the requested "
            f"source is hf://org/repo/acs.h5@new (sha256 {'b' * 64})",
        ),
        (
            # A re-upload under the same revision name.
            {"uri": "hf://org/repo/acs.h5@r", "sha256": "a" * 64},
            {"uri": "hf://org/repo/acs.h5@r", "sha256": "b" * 64},
            f"hf://org/repo/acs.h5@r (sha256 {'a' * 64}), and the requested "
            f"source is hf://org/repo/acs.h5@r (sha256 {'b' * 64})",
        ),
        (
            {"uri": "hf://org/repo/acs.h5@r", "sha256": "a" * 64},
            {"uri": "hf://org/repo/acs.h5@r"},
            f"hf://org/repo/acs.h5@r (sha256 {'a' * 64}), and the requested "
            "source is hf://org/repo/acs.h5@r",
        ),
        (
            {
                "path": "/data/tiny.h5",
                "size": 10,
                "mtime_ns": 1_760_000_000_000_000_001,
            },
            {
                "path": "/data/tiny.h5",
                "size": 12,
                "mtime_ns": 1_760_000_060_000_000_000,
            },
            "/data/tiny.h5 (10 bytes, modified 2025-10-09T08:53:20.000000001Z), "
            "and the requested source is /data/tiny.h5 (12 bytes, modified "
            "2025-10-09T08:54:20.000000000Z)",
        ),
        (
            {"path": "/a/tiny.h5", "size": 10, "mtime_ns": 0},
            {"path": "/b/tiny.h5", "size": 10, "mtime_ns": 0},
            "/a/tiny.h5 (10 bytes, modified 1970-01-01T00:00:00.000000000Z), and "
            "the requested source is /b/tiny.h5 (10 bytes, modified "
            "1970-01-01T00:00:00.000000000Z)",
        ),
    ],
)
def test_a_year_file_cut_from_another_source_names_both(
    tmp_path, stamped_source, source, described
):
    path = _write_year_file(
        tmp_path / "year.h5",
        stamp=_stamp(LEGACY_INPUT_RENAMES, source=stamped_source),
        record={},
    )

    assert year_file_stamp_problem(path, source) == f"it was cut from {described}"


@pytest.mark.parametrize(
    "stamped_packages, packages, reason",
    [
        (
            {**PACKAGES, "policyengine-us": "2.2.0"},
            PACKAGES,
            "it was cut with policyengine-us 2.2.0, and policyengine-us 2.2.1 is "
            "installed",
        ),
        (
            PACKAGES,
            {**PACKAGES, "policyengine-us": None},
            "it was cut with policyengine-us 2.2.1, and policyengine-us is not "
            "installed",
        ),
        (
            {**PACKAGES, "policyengine-core": None},
            PACKAGES,
            "it was cut with no recorded policyengine-core version, and "
            "policyengine-core 3.33.0 is installed",
        ),
        (
            {"policyengine-us": "2.2.1"},
            PACKAGES,
            "it was cut with no recorded policyengine-core version, and "
            "policyengine-core 3.33.0 is installed",
        ),
        (
            {**PACKAGES, "extra-package": "1.0"},
            PACKAGES,
            "it records the extra-package version it was cut with, which this "
            "version of policyengine.py does not check",
        ),
        (
            {"policyengine-core": "3.32.0", "policyengine-us": "2.2.0"},
            PACKAGES,
            "it was cut with policyengine-core 3.32.0, and policyengine-core "
            "3.33.0 is installed; it was cut with policyengine-us 2.2.0, and "
            "policyengine-us 2.2.1 is installed",
        ),
    ],
)
def test_a_year_file_cut_with_other_versions_names_them(
    tmp_path, stamped_packages, packages, reason
):
    path = _write_year_file(
        tmp_path / "year.h5",
        stamp=_stamp(LEGACY_INPUT_RENAMES, packages=stamped_packages),
        record={},
    )

    assert year_file_stamp_problem(path, IDENTITY, packages) == reason


def test_every_difference_is_named_in_order(tmp_path):
    path = _write_year_file(
        tmp_path / "year.h5",
        stamp=_stamp(
            {},
            source={"uri": f"{SOURCE}@old"},
            packages={**PACKAGES, "policyengine-us": "2.2.0"},
        ),
        record={},
    )

    assert year_file_stamp_problem(path, IDENTITY) == (
        "it was cut before these renames were registered, so it may have lost "
        f"them: {LEGACY} -> {LIVE}; it was cut from {SOURCE}@old, and the "
        f"requested source is {SOURCE}; it was cut with policyengine-us 2.2.0, "
        "and policyengine-us 2.2.1 is installed"
    )


def test_a_future_register_entry_makes_a_stamped_file_out_of_date(
    tmp_path, monkeypatch
):
    path = _write_year_file(tmp_path / "year.h5", stamp=_current(), record={})
    monkeypatch.setattr(
        legacy_inputs,
        "LEGACY_INPUT_RENAMES",
        {**LEGACY_INPUT_RENAMES, "old_input": "new_input"},
    )

    assert year_file_stamp_problem(path, IDENTITY) == (
        "it was cut before these renames were registered, so it may have lost "
        "them: old_input -> new_input"
    )


@pytest.mark.parametrize(
    "register, reason",
    [
        (
            {},
            "it was cut under renames this version of policyengine.py does not "
            f"register: {LEGACY} -> {LIVE}",
        ),
        (
            {LEGACY: "elsewhere"},
            "it was cut before these renames were registered, so it may have lost "
            f"them: {LEGACY} -> elsewhere; it was cut under renames this version "
            f"of policyengine.py does not register: {LEGACY} -> {LIVE}",
        ),
    ],
)
def test_retiring_or_retargeting_an_entry_makes_a_stamped_file_out_of_date(
    tmp_path, monkeypatch, register, reason
):
    path = _write_year_file(
        tmp_path / "year.h5", stamp=_current(), record={LEGACY: LIVE}
    )
    monkeypatch.setattr(legacy_inputs, "LEGACY_INPUT_RENAMES", register)

    # The record of a file cut under the old register lies within that
    # register, so the register is what makes it out of date.
    assert year_file_stamp_problem(path, IDENTITY) == reason


# --- No partial file is current -----------------------------------------


@functools.cache
def _current_year_file_bytes() -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        path = _write_year_file(
            Path(directory) / "year.h5", stamp=_current(), record={}
        )
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

    assert year_file_stamp_problem(path, IDENTITY) == (
        "it cannot be read as an HDF5 file (it may be half-written or corrupt)"
    )


def test_saving_a_year_file_again_drops_its_stamp(tmp_path):
    path = _write_year_file(tmp_path / "year.h5", stamp=_current(), record={})

    dataset = PolicyEngineUSDataset(
        name="year-file", description="reload", filepath=str(path), year=2024
    )
    dataset.save()

    # ``save()`` rewrites the tables and the record it loaded, but not the
    # stamp, which only ``create_datasets`` writes.
    assert read_renames_record(path) == {}
    assert read_year_file_stamp(path) is None
    assert year_file_stamp_problem(path, IDENTITY).startswith("it has no stamp")


def test_a_save_that_stops_part_way_leaves_no_stamp(tmp_path, monkeypatch):
    path = _write_year_file(tmp_path / "year.h5", stamp=_current(), record={})
    put = pd.HDFStore.put

    def put_until_family(self, key, value, *args, **kwargs):
        if key == "family":
            raise RuntimeError("stopped part-way")
        return put(self, key, value, *args, **kwargs)

    monkeypatch.setattr(pd.HDFStore, "put", put_until_family)
    with pytest.raises(RuntimeError, match="stopped part-way"):
        _year_dataset(path).save()

    assert read_year_file_stamp(path) is None
    assert year_file_stamp_problem(path, IDENTITY) is not None


# --- Errors unrelated to the file's contents ----------------------------


def _unreadable_by_permission(path) -> Path:
    path = _write_year_file(path, stamp=_current(), record={})
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
        with patch.object(us_datasets, "create_datasets", create):
            with pytest.raises(error):
                ensure_datasets(
                    datasets=[SOURCE], years=[2024], data_folder=str(data_folder)
                )
    finally:
        if path.is_file():
            os.chmod(path, 0o644)
    create.assert_not_called()


def test_a_locked_file_is_raised_not_cut_again(tmp_path, monkeypatch):
    path = _write_year_file(tmp_path / "year.h5", stamp=_current(), record={})

    def locked(*args, **kwargs):
        raise BlockingIOError(35, "Unable to lock file")

    monkeypatch.setattr(h5py, "File", locked)
    with pytest.raises(BlockingIOError):
        year_file_stamp_problem(path, IDENTITY)


@pytest.mark.parametrize(
    "error",
    [
        PermissionError(13, "Permission denied"),
        IsADirectoryError(21, "Is a directory"),
        BlockingIOError(35, "Unable to lock file"),
    ],
)
def test_errors_unrelated_to_the_contents_are_raised_while_reading(
    tmp_path, monkeypatch, error
):
    path = _write_year_file(tmp_path / "year.h5", stamp=_current(), record={})

    def fail(self, *args, **kwargs):
        raise error

    monkeypatch.setattr(h5py.Dataset, "asstr", fail)
    with pytest.raises(type(error)):
        year_file_stamp_problem(path, IDENTITY)


# --- read_renames_record reads only well-formed records -----------------


@pytest.mark.parametrize(
    "record",
    [[], [[LEGACY, LIVE]], 5, {LEGACY: 1}, ("text", "{"), ("group", None)],
)
def test_a_malformed_renames_record_reads_as_none(tmp_path, record):
    path = _write_year_file(tmp_path / "year.h5", record=record)

    assert read_renames_record(path) is None


def test_a_well_formed_renames_record_still_reads_back(tmp_path):
    path = _write_year_file(tmp_path / "year.h5")
    write_renames_record(path, {LEGACY: LIVE})

    assert read_renames_record(path) == {LEGACY: LIVE}


# --- ensure_datasets agrees with load_datasets --------------------------

#: Each year file state, and whether it is current.
STATES = {
    "current": (dict(stamp=_current(), record={}), True),
    "current, mapped": (
        dict(stamp=_current(), record=dict(LEGACY_INPUT_RENAMES)),
        True,
    ),
    "6.1.1 and earlier": (dict(), False),
    "record only": (dict(record={}), False),
    "revision 1": (
        dict(stamp={"register": dict(LEGACY_INPUT_RENAMES), "revision": 1}, record={}),
        False,
    ),
    "missing entry": (dict(stamp=_stamp({}), record={}), False),
    "extra entry": (
        dict(stamp=_stamp({**LEGACY_INPUT_RENAMES, "old": "new"}), record={}),
        False,
    ),
    "retargeted": (dict(stamp=_stamp({LEGACY: "elsewhere"}), record={}), False),
    "older revision": (dict(stamp=_stamp(LEGACY_INPUT_RENAMES, 0), record={}), False),
    "newer revision": (dict(stamp={"revision": 3}, record={}), False),
    "other source revision": (
        dict(
            stamp=_stamp(LEGACY_INPUT_RENAMES, source={"uri": f"{SOURCE}@old"}),
            record={},
        ),
        False,
    ),
    "verified source": (
        dict(
            stamp=_stamp(
                LEGACY_INPUT_RENAMES, source={"uri": SOURCE, "sha256": "a" * 64}
            ),
            record={},
        ),
        False,
    ),
    "other policyengine-us": (
        dict(
            stamp=_stamp(
                LEGACY_INPUT_RENAMES,
                packages={**PACKAGES, "policyengine-us": "2.2.0"},
            ),
            record={},
        ),
        False,
    ),
    "other policyengine-core": (
        dict(
            stamp=_stamp(
                LEGACY_INPUT_RENAMES,
                packages={**PACKAGES, "policyengine-core": "3.34.0"},
            ),
            record={},
        ),
        False,
    ),
    "malformed stamp": (dict(stamp=("text", "not json"), record={}), False),
    "no record": (dict(stamp=_current()), False),
    "record outside": (dict(stamp=_current(), record={"x": "y"}), False),
    "not HDF5": (None, False),
    "missing": (None, None),
}


def _make_state(path: Path, state: str) -> None:
    written, _ = STATES[state]
    if state == "missing":
        return
    if state == "not HDF5":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not an H5 file")
        return
    _write_year_file(path, **written)


def _create_current_files(datasets, years, data_folder, allow_unmanaged=False):
    """Stand in for ``create_datasets``: write current year files."""
    for year in years:
        _write_year_file(
            Path(data_folder) / f"{STEM}_year_{year}.h5",
            stamp=_current(),
            record={},
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
            _make_state(data_folder / f"{STEM}_year_{year}.h5", state)

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
            patch.object(us_datasets, "create_datasets", create),
            patch.object(us_datasets.logger, "warning") as warning,
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
                    "US year file %s is out of date: %s. Creating the year files again."
                )

            # The year files are now current, so they are reused.
            create.reset_mock()
            loaded = ensure_datasets(
                datasets=[SOURCE], years=years, data_folder=str(data_folder)
            )
            create.assert_not_called()
        assert sorted(loaded) == [f"{STEM}_{year}" for year in years]


@pytest.mark.parametrize("local_source", [False, True])
@pytest.mark.parametrize(
    "states",
    [
        ["current", "current, mapped"],
        ["current", "record only"],
        ["current", "other source revision"],
        ["current", "other policyengine-us"],
    ],
)
def test_ensure_decides_from_the_stamps_alone(tmp_path, states, local_source):
    """Deciding never opens a year file's tables, and never reads, hashes or
    downloads the source dataset or imports policyengine-us. A local source
    is only ``stat()``-ed."""
    data_folder = tmp_path / "data"
    years = [2024, 2025]
    dataset, identity = SOURCE, IDENTITY
    if local_source:
        source_file = tmp_path / "sources" / f"{STEM}.h5"
        source_file.parent.mkdir()
        source_file.write_bytes(b"the source is never read")
        dataset, identity = (
            str(source_file),
            requested_dataset_source_identity("us", str(source_file)),
        )
    for year, state in zip(years, states):
        written, _ = STATES[state]
        stamp = written.get("stamp", _ABSENT)
        if isinstance(stamp, dict) and stamp.get("source") == IDENTITY:
            stamp = {**stamp, "source": identity}
        _write_year_file(
            data_folder / f"{STEM}_year_{year}.h5",
            **{**written, "stamp": stamp},
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

    class StampAndRecordOnly:
        """An H5 file that lets the decision read only the stamp and record."""

        def __init__(self, path, mode="r", **kwargs):
            assert mode == "r"
            assert source_path is None or Path(path).resolve() != source_path
            self._file = real_file(path, mode, **kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self._file.close()

        def get(self, name, default=None):
            # The legacy SPM declarations record is a small JSON node like the
            # stamp, read to tell a legacy source's year file is current.
            assert name in (
                YEAR_FILE_STAMP_H5_DATASET,
                RENAMES_H5_DATASET,
                LEGACY_SPM_RECORD_H5_DATASET,
            ), name
            return self._file.get(name, default)

    real_open, real_import = builtins.open, builtins.__import__

    def open_anything_but_the_source(file, *args, **kwargs):
        if (
            source_path is not None
            and isinstance(file, (str, os.PathLike))
            and Path(file).resolve() == source_path
        ):
            refuse()
        return real_open(file, *args, **kwargs)

    def import_anything_but_policyengine_us(name, *args, **kwargs):
        if name == "policyengine_us" or name.startswith("policyengine_us."):
            raise AssertionError("deciding imported policyengine-us")
        return real_import(name, *args, **kwargs)

    with (
        patch.object(h5py, "File", StampAndRecordOnly),
        patch.object(pd, "HDFStore", RefusedStore),
        # ``pd.read_hdf`` looks HDFStore up in its own module, and PyTables
        # opens files without h5py.
        patch("pandas.io.pytables.HDFStore", RefusedStore),
        patch("tables.open_file", refuse),
        patch.object(builtins, "open", open_anything_but_the_source),
        patch.object(io, "open", open_anything_but_the_source),
        patch.object(builtins, "__import__", import_anything_but_policyengine_us),
        patch.object(dataset_materialization, "sha256_file", refuse),
        patch.object(dataset_materialization.requests, "get", refuse),
        patch.object(us_datasets, "materialize_dataset", refuse),
        patch.object(us_datasets, "load_datasets", load),
        patch.object(us_datasets, "create_datasets", create),
    ):
        result = ensure_datasets(
            datasets=[dataset], years=years, data_folder=str(data_folder)
        )

    stale = any(STATES[state][1] is False for state in states)
    assert result == ("created" if stale else "loaded")


def test_the_refusal_names_the_file_and_what_it_may_lack(tmp_path):
    data_folder = tmp_path / "data"
    path = data_folder / f"{STEM}_year_2024.h5"
    _write_year_file(path, stamp=_stamp({}), record={})

    with pytest.raises(ValueError) as refused:
        load_datasets(datasets=[SOURCE], years=[2024], data_folder=str(data_folder))

    assert str(refused.value) == (
        f"US year file {path} is out of date: it was cut before these renames "
        f"were registered, so it may have lost them: {LEGACY} -> {LIVE}. "
        "Regenerate it with ensure_datasets() or create_datasets()."
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
            patch.object(us_datasets, "materialize_dataset", refuse),
            patch.object(us_datasets, "year_file_stamp_problem", refuse),
            patch.object(us_datasets, "PolicyEngineUSDataset", refuse),
        ):
            for call in (
                lambda: load_datasets(
                    datasets=requests, years=[2024], data_folder=directory
                ),
                lambda: us_datasets.create_datasets(
                    datasets=requests,
                    years=[2024],
                    data_folder=directory,
                    allow_unmanaged=True,
                ),
            ):
                if collide:
                    with pytest.raises(ValueError, match="would share the US year"):
                        call()
        with patch.object(us_datasets, "create_datasets", create):
            if collide:
                with pytest.raises(ValueError, match="would share the US year"):
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
        f"Datasets {first!r} and {second!r} would share the US year files "
        f"pop_year_{{year}}.h5, but are different sources: {first} and {second}. "
        "Request them in separate calls with separate data folders."
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
        patch.object(us_datasets, "materialize_dataset", refuse),
        patch("requests.get", refuse),
    ):
        with pytest.raises(ValueError, match=error):
            us_datasets.create_datasets(
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

    with patch.object(us_datasets, "materialize_dataset", refuse):
        with pytest.raises(DatasetMaterializationError, match=error):
            us_datasets.create_datasets(
                datasets=[SOURCE, request_],
                years=[2024],
                data_folder=str(tmp_path),
                allow_unmanaged=True,
            )


def test_one_source_requested_by_two_names_is_not_a_collision(tmp_path):
    """The default's logical name and its own URI are one source."""
    from policyengine.provenance.manifest import get_release_manifest

    manifest = get_release_manifest("us")
    requests = [manifest.default_dataset, manifest.default_dataset_uri]
    create = MagicMock(return_value="created")

    with patch.object(us_datasets, "create_datasets", create):
        assert (
            ensure_datasets(datasets=requests, years=[2024], data_folder=str(tmp_path))
            == "created"
        )


def test_the_refusal_names_the_source_it_was_cut_from(tmp_path):
    data_folder = tmp_path / "data"
    path = data_folder / f"{STEM}_year_2024.h5"
    _write_year_file(
        path,
        stamp=_stamp(LEGACY_INPUT_RENAMES, source={"uri": f"{SOURCE}@old"}),
        record={},
    )

    with pytest.raises(ValueError) as refused:
        load_datasets(datasets=[SOURCE], years=[2024], data_folder=str(data_folder))

    assert str(refused.value) == (
        f"US year file {path} is out of date: it was cut from {SOURCE}@old, and "
        f"the requested source is {SOURCE}. Regenerate it with ensure_datasets() "
        "or create_datasets()."
    )


def test_load_and_ensure_compare_with_the_installed_versions(tmp_path, monkeypatch):
    """Both read the versions when called, not at import."""
    data_folder = tmp_path / "data"
    _write_year_file(data_folder / f"{STEM}_year_2024.h5", stamp=_current(), record={})
    load_datasets(datasets=[SOURCE], years=[2024], data_folder=str(data_folder))

    monkeypatch.setattr(
        legacy_inputs,
        "installed_package_versions",
        lambda: {**PACKAGES, "policyengine-us": "2.3.0"},
    )
    with pytest.raises(ValueError, match="policyengine-us 2.3.0 is installed"):
        load_datasets(datasets=[SOURCE], years=[2024], data_folder=str(data_folder))
    create = MagicMock(return_value="created")
    with patch.object(us_datasets, "create_datasets", create):
        assert (
            ensure_datasets(
                datasets=[SOURCE], years=[2024], data_folder=str(data_folder)
            )
            == "created"
        )
