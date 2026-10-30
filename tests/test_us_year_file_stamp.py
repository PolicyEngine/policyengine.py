"""Unit and property tests for the stamp on US year files.

``create_datasets`` stamps each year file with the register of renamed stored
inputs it was cut under and a year-file format revision
(``legacy_inputs.YEAR_FILE_STAMP_H5_DATASET``). ``ensure_datasets`` cuts a
year file again, and ``load_datasets`` refuses it, unless the stamp matches
this release's. These tests state the check's invariants over generated
stamps, records and registers, without a country engine:

- **Exactness.** A year file is current exactly when its stamp has this
  release's format revision and register, and its renames record lists only
  renames in that register.
- **Totality.** Whatever the stamp and record hold, the check returns a
  reason or ``None``, and raises only for errors unrelated to the file's
  contents (no permission, a directory, a lock).
- **Round trip.** A stamp reads back as written, and writing again replaces it.
- **Named renames.** The reason names every rename the file's register and
  this release's disagree on, from the register alone.
- **No partial file is current.** Every truncation of a current year file,
  every save that stops part-way and every save that does not stamp is out
  of date.
- **Ensure agrees with load.** ``ensure_datasets`` cuts the year files again
  exactly when one is missing or ``load_datasets`` would refuse one, and
  decides from the stamps alone.

``test_us_legacy_inputs_integration.py`` runs ``create_datasets`` and
``ensure_datasets`` over a real policyengine-us engine.
"""

from __future__ import annotations

import functools
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import h5py
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from microdf import MicroDataFrame

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
#: file's stem, so no manifest or download is involved.
SOURCE = "hf://fixture/tiny.h5"
STEM = "tiny"
GROUPS = ("household", "tax_unit", "spm_unit", "family", "marital_unit")

#: A small alphabet, so generated registers often share names and disagree
#: only on some entries.
NAMES = st.sampled_from(["alpha", "beta", "gamma", "delta"])
REGISTERS = st.dictionaries(NAMES, NAMES, max_size=3)
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


def _is_current(stamp, record, register) -> bool:
    """The exactness invariant, stated directly on the stored JSON values."""

    def str_map(value):
        return isinstance(value, dict) and all(
            isinstance(key, str) and isinstance(item, str)
            for key, item in value.items()
        )

    return (
        isinstance(stamp, dict)
        and set(stamp) == {"register", "revision"}
        and type(stamp["revision"]) is int
        and stamp["revision"] == REVISION
        and str_map(stamp["register"])
        and stamp["register"] == register
        and str_map(record)
        and record.items() <= stamp["register"].items()
    )


def _stamp(register, revision=REVISION):
    return {"register": dict(register), "revision": revision}


# --- The stamp ----------------------------------------------------------


def test_the_stamp_holds_the_whole_register_and_the_format_revision():
    assert year_file_stamp() == {
        "register": {LEGACY: LIVE},
        "revision": 1,
    }
    assert year_file_stamp()["register"] == LEGACY_INPUT_RENAMES


def test_the_stamp_reads_the_register_when_called(monkeypatch):
    """datasets.py must not freeze the register at import."""
    monkeypatch.setattr(legacy_inputs, "LEGACY_INPUT_RENAMES", {"b": "c", "a": "d"})

    assert year_file_stamp() == {"register": {"a": "d", "b": "c"}, "revision": 1}


def test_the_stamp_is_stored_as_utf8_json(tmp_path):
    path = _write_year_file(tmp_path / "year.h5")

    write_year_file_stamp(path, year_file_stamp())

    with h5py.File(path, "r") as file:
        assert file[YEAR_FILE_STAMP_H5_DATASET].asstr()[()] == (
            f'{{"register": {{"{LEGACY}": "{LIVE}"}}, "revision": 1}}'
        )


@settings(max_examples=50, deadline=None)
@given(
    first=st.fixed_dictionaries({"register": REGISTERS, "revision": st.integers()}),
    second=st.fixed_dictionaries({"register": REGISTERS, "revision": st.integers()}),
)
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
    path = _write_year_file(tmp_path / "year.h5", stamp=year_file_stamp(), record={})

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
    """A current register, and a year file's stamp and record near it."""
    register = draw(REGISTERS)
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
    revision = draw(st.sampled_from([REVISION, REVISION, 0, 2, -1, 99]))
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
    return register, _stamp(stamped, revision), record


@settings(max_examples=300, deadline=None)
@given(case=stamped_files())
def test_a_year_file_is_current_only_under_this_releases_exact_stamp(case):
    """Exactness, and refinement of the record check a year file had before.

    A subset rule would accept a file cut by a newer release under a larger
    register, which stores live names this release's engine may not define.
    """
    register, stamp, record = case
    with tempfile.TemporaryDirectory() as directory:
        path = _write_year_file(Path(directory) / "year.h5", stamp=stamp, record=record)
        with patch.object(legacy_inputs, "LEGACY_INPUT_RENAMES", register):
            problem = year_file_stamp_problem(path)

        assert (problem is None) == _is_current(stamp, record, register)
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
            "register": st.one_of(REGISTERS, JSON_VALUES),
            "revision": st.one_of(
                st.just(REVISION), st.booleans(), st.floats(), JSON_VALUES
            ),
        }
    ),
    st.tuples(st.just("text"), RAW_TEXT),
    st.tuples(st.just("bytes"), st.binary(min_size=1, max_size=12)),
    st.tuples(st.just("number"), st.integers(-5, 5)),
    st.tuples(st.just("array"), st.lists(RAW_TEXT, min_size=1, max_size=3)),
    st.tuples(st.just("group"), st.none()),
)


@settings(max_examples=300, deadline=None)
@given(stamp=NODES, record=NODES, register=REGISTERS)
def test_the_year_file_problem_is_total_and_exact_for_any_content(
    stamp, record, register
):
    """Totality: any stamp and record give a reason or ``None``, never an
    error, and ``None`` only for this release's exact stamp."""
    with tempfile.TemporaryDirectory() as directory:
        path = _write_year_file(Path(directory) / "year.h5", stamp=stamp, record=record)
        with patch.object(legacy_inputs, "LEGACY_INPUT_RENAMES", register):
            problem = year_file_stamp_problem(path)

    assert problem is None or (isinstance(problem, str) and problem)
    if problem is None:
        assert _is_current(stamp, record, register)


@pytest.mark.parametrize(
    "stamp",
    [
        {"register": {LEGACY: LIVE}, "revision": True},
        {"register": {LEGACY: LIVE}, "revision": 1.0},
        {"register": {LEGACY: LIVE}, "revision": "1"},
        {"register": {LEGACY: LIVE}},
        {"register": {LEGACY: LIVE}, "revision": 1, "extra": None},
        {"register": {LEGACY: 5}, "revision": 1},
        {"register": [[LEGACY, LIVE]], "revision": 1},
        [{"register": {LEGACY: LIVE}, "revision": 1}],
        ("text", "not json"),
        ("text", ""),
        ("bytes", b"\xff\xfe"),
        ("number", 1),
        ("array", ["{}"]),
        ("group", None),
    ],
)
def test_a_malformed_stamp_is_out_of_date(tmp_path, stamp):
    path = _write_year_file(tmp_path / "year.h5", stamp=stamp, record={})

    assert year_file_stamp_problem(path) == (
        "its stamp of the register of renamed inputs it was cut under is malformed"
    )


@pytest.mark.parametrize("revision", [0, 2, -1])
def test_a_year_file_from_another_format_revision_is_out_of_date(tmp_path, revision):
    # A later revision may shape the rest of its stamp and record differently,
    # and is still reported by revision rather than as malformed.
    stamp = {"revision": revision, "registers": [[LEGACY, LIVE]]}
    path = _write_year_file(tmp_path / "year.h5", stamp=stamp)

    assert year_file_stamp_problem(path) == (
        f"it was cut with year-file format revision {revision}, and this "
        "version of policyengine.py reads only revision 1"
    )


def test_files_without_a_stamp_are_out_of_date_with_distinct_reasons(tmp_path):
    """policyengine.py 6.1.1 and earlier wrote neither; #531 wrote the record."""
    oldest = _write_year_file(tmp_path / "oldest.h5")
    record_only = _write_year_file(tmp_path / "record_only.h5", record={LEGACY: LIVE})

    assert year_file_stamp_problem(oldest) == (
        "it has no record of the renamed stored inputs mapped when it was cut, "
        "so it was cut by an older policyengine.py or not written completely, "
        f"and may have lost any of: {LEGACY} -> {LIVE}"
    )
    assert year_file_stamp_problem(record_only) == (
        "it has no stamp of the register of renamed inputs it was cut under, so "
        f"it may have lost any of: {LEGACY} -> {LIVE}"
    )


def test_an_unstamped_file_is_out_of_date_even_with_an_empty_register(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(legacy_inputs, "LEGACY_INPUT_RENAMES", {})
    oldest = _write_year_file(tmp_path / "oldest.h5")
    record_only = _write_year_file(tmp_path / "record_only.h5", record={})

    assert year_file_stamp_problem(oldest) == (
        "it has no record of the renamed stored inputs mapped when it was cut, "
        "so it was cut by an older policyengine.py or not written completely"
    )
    assert year_file_stamp_problem(record_only) == (
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
    path = _write_year_file(
        tmp_path / "year.h5", stamp=year_file_stamp(), record=record
    )

    assert year_file_stamp_problem(path) == reason


def test_a_stamp_and_record_stored_as_fixed_length_strings_are_read(tmp_path):
    stamp = json.dumps(year_file_stamp()).encode()
    record = json.dumps({LEGACY: LIVE}).encode()
    path = _write_year_file(
        tmp_path / "year.h5", stamp=("bytes", stamp), record=("bytes", record)
    )

    assert year_file_stamp_problem(path) is None
    assert read_year_file_stamp(path) == year_file_stamp()
    assert read_renames_record(path) == {LEGACY: LIVE}


def test_raising_the_format_revision_makes_older_files_out_of_date(
    tmp_path, monkeypatch
):
    older = _write_year_file(tmp_path / "older.h5", stamp=year_file_stamp(), record={})
    monkeypatch.setattr(legacy_inputs, "YEAR_FILE_STAMP_REVISION", 7)
    newer = _write_year_file(tmp_path / "newer.h5", stamp=year_file_stamp(), record={})

    assert year_file_stamp()["revision"] == 7
    assert year_file_stamp_problem(newer) is None
    assert year_file_stamp_problem(older) == (
        "it was cut with year-file format revision 1, and this version of "
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
        (
            ("text", DEEP_JSON),
            {},
            "its stamp of the register of renamed inputs it was cut under is malformed",
        ),
        (
            year_file_stamp(),
            ("text", DEEP_JSON),
            "its record of the renamed stored inputs mapped when it was cut is "
            "malformed",
        ),
        (
            {"revision": 2},
            ("text", DEEP_JSON),
            "it was cut with year-file format revision 2, and this version of "
            "policyengine.py reads only revision 1",
        ),
    ],
)
def test_json_nested_too_deeply_is_out_of_date_not_an_error(
    tmp_path, stamp, record, reason
):
    path = _write_year_file(tmp_path / "year.h5", stamp=stamp, record=record)

    assert year_file_stamp_problem(path) == reason
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
    path = _write_year_file(tmp_path / "year.h5", stamp=year_file_stamp(), record={})
    loads = json.loads

    def deep(text, *args, **kwargs):
        with h5py.File(path, "r") as file:
            if text == file[name].asstr()[()]:
                raise RecursionError("maximum recursion depth exceeded")
        return loads(text, *args, **kwargs)

    monkeypatch.setattr(legacy_inputs.json, "loads", deep)

    assert year_file_stamp_problem(path) == (
        "its stamp of the register of renamed inputs it was cut under is malformed"
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

    assert year_file_stamp_problem(path).startswith(
        "it has no record of the renamed stored inputs mapped when it was cut"
    )
    assert read_year_file_stamp(path) is None
    assert read_renames_record(path) is None


@pytest.mark.parametrize("record", [{}, {LEGACY: LIVE}])
def test_a_file_stamped_with_this_releases_register_is_current(tmp_path, record):
    path = _write_year_file(
        tmp_path / "year.h5", stamp=year_file_stamp(), record=record
    )

    assert year_file_stamp_problem(path) is None


# --- Named renames ------------------------------------------------------


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
            problem = year_file_stamp_problem(path)

    if stamped == register:
        assert problem is None
        return
    missing = {k: v for k, v in register.items() if stamped.get(k) != v}
    unknown = {k: v for k, v in stamped.items() if register.get(k) != v}
    for legacy, live in missing.items():
        assert f"{legacy} -> {live}" in problem.split("; ")[0]
    for legacy, live in unknown.items():
        assert f"{legacy} -> {live}" in problem.split("; ")[-1]
    assert ("cut before these renames were registered" in problem) == bool(missing)
    assert ("does not register" in problem) == bool(unknown)
    for legacy, live in register.items() & stamped.items():
        assert f"{legacy} -> {live}" not in problem


def test_a_future_register_entry_makes_a_stamped_file_out_of_date(
    tmp_path, monkeypatch
):
    path = _write_year_file(tmp_path / "year.h5", stamp=year_file_stamp(), record={})
    monkeypatch.setattr(
        legacy_inputs,
        "LEGACY_INPUT_RENAMES",
        {**LEGACY_INPUT_RENAMES, "old_input": "new_input"},
    )

    assert year_file_stamp_problem(path) == (
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
        tmp_path / "year.h5", stamp=year_file_stamp(), record={LEGACY: LIVE}
    )
    monkeypatch.setattr(legacy_inputs, "LEGACY_INPUT_RENAMES", register)

    # The record of a file cut under the old register lies within that
    # register, so the register is what makes it out of date.
    assert year_file_stamp_problem(path) == reason


# --- No partial file is current -----------------------------------------


@functools.cache
def _current_year_file_bytes() -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        path = _write_year_file(
            Path(directory) / "year.h5", stamp=year_file_stamp(), record={}
        )
        assert year_file_stamp_problem(path) is None
        return path.read_bytes()


@settings(max_examples=100, deadline=None)
@given(data=st.data())
def test_a_truncated_year_file_is_never_current(data):
    content = _current_year_file_bytes()
    length = data.draw(st.integers(0, len(content) - 1))
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "year.h5"
        path.write_bytes(content[:length])

        assert year_file_stamp_problem(path) is not None


def test_a_file_that_is_not_hdf5_is_out_of_date(tmp_path):
    path = tmp_path / "year.h5"
    path.write_text("not an H5 file")

    assert year_file_stamp_problem(path) == (
        "it cannot be read as an HDF5 file (it may be half-written or corrupt)"
    )


def test_saving_a_year_file_again_drops_its_stamp(tmp_path):
    path = _write_year_file(tmp_path / "year.h5", stamp=year_file_stamp(), record={})

    dataset = PolicyEngineUSDataset(
        name="year-file", description="reload", filepath=str(path), year=2024
    )
    dataset.save()

    # ``save()`` rewrites the tables and the record it loaded, but not the
    # stamp, which only ``create_datasets`` writes.
    assert read_renames_record(path) == {}
    assert read_year_file_stamp(path) is None
    assert year_file_stamp_problem(path).startswith("it has no stamp")


def test_a_save_that_stops_part_way_leaves_no_stamp(tmp_path, monkeypatch):
    path = _write_year_file(tmp_path / "year.h5", stamp=year_file_stamp(), record={})
    put = pd.HDFStore.put

    def put_until_family(self, key, value, *args, **kwargs):
        if key == "family":
            raise RuntimeError("stopped part-way")
        return put(self, key, value, *args, **kwargs)

    monkeypatch.setattr(pd.HDFStore, "put", put_until_family)
    with pytest.raises(RuntimeError, match="stopped part-way"):
        _year_dataset(path).save()

    assert read_year_file_stamp(path) is None
    assert year_file_stamp_problem(path) is not None


# --- Errors unrelated to the file's contents ----------------------------


def _unreadable_by_permission(path) -> Path:
    path = _write_year_file(path, stamp=year_file_stamp(), record={})
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
            year_file_stamp_problem(path)
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
    path = _write_year_file(tmp_path / "year.h5", stamp=year_file_stamp(), record={})

    def locked(*args, **kwargs):
        raise BlockingIOError(35, "Unable to lock file")

    monkeypatch.setattr(h5py, "File", locked)
    with pytest.raises(BlockingIOError):
        year_file_stamp_problem(path)


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
    path = _write_year_file(tmp_path / "year.h5", stamp=year_file_stamp(), record={})

    def fail(self, *args, **kwargs):
        raise error

    monkeypatch.setattr(h5py.Dataset, "asstr", fail)
    with pytest.raises(type(error)):
        year_file_stamp_problem(path)


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
    "current": (dict(stamp=year_file_stamp(), record={}), True),
    "current, mapped": (
        dict(stamp=year_file_stamp(), record=dict(LEGACY_INPUT_RENAMES)),
        True,
    ),
    "6.1.1 and earlier": (dict(), False),
    "record only": (dict(record={}), False),
    "missing entry": (dict(stamp=_stamp({}), record={}), False),
    "extra entry": (
        dict(stamp=_stamp({**LEGACY_INPUT_RENAMES, "old": "new"}), record={}),
        False,
    ),
    "retargeted": (dict(stamp=_stamp({LEGACY: "elsewhere"}), record={}), False),
    "older revision": (dict(stamp=_stamp(LEGACY_INPUT_RENAMES, 0), record={}), False),
    "newer revision": (dict(stamp={"revision": 2}, record={}), False),
    "malformed stamp": (dict(stamp=("text", "not json"), record={}), False),
    "no record": (dict(stamp=year_file_stamp()), False),
    "record outside": (dict(stamp=year_file_stamp(), record={"x": "y"}), False),
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


def _create_current_files(
    datasets,
    years,
    data_folder,
    allow_unmanaged=False,
    allow_unsupported_years=False,
):
    """Stand in for ``create_datasets``: write current year files."""
    for year in years:
        _write_year_file(
            Path(data_folder) / f"{STEM}_year_{year}.h5",
            stamp=year_file_stamp(),
            record={},
        )
    return {"created": True}


@settings(max_examples=60, deadline=None)
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
            and (problem := year_file_stamp_problem(path)) is not None
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


@pytest.mark.parametrize(
    "states", [["current", "current, mapped"], ["current", "record only"]]
)
def test_ensure_decides_from_the_stamps_alone(tmp_path, states):
    """Deciding never opens a year file's tables or the source dataset."""
    data_folder = tmp_path / "data"
    years = [2024, 2025]
    for year, state in zip(years, states):
        _make_state(data_folder / f"{STEM}_year_{year}.h5", state)
    load, create = MagicMock(return_value="loaded"), MagicMock(return_value="created")

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

    with (
        patch.object(h5py, "File", StampAndRecordOnly),
        patch.object(pd, "HDFStore", RefusedStore),
        # ``pd.read_hdf`` looks HDFStore up in its own module, and PyTables
        # opens files without h5py.
        patch("pandas.io.pytables.HDFStore", RefusedStore),
        patch("tables.open_file", refuse),
        patch.object(us_datasets, "materialize_dataset", refuse),
        patch.object(us_datasets, "load_datasets", load),
        patch.object(us_datasets, "create_datasets", create),
    ):
        result = ensure_datasets(
            datasets=[SOURCE], years=years, data_folder=str(data_folder)
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
