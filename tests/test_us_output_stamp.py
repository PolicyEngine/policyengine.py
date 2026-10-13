"""Unit and property tests for the stamp on saved US simulation outputs.

A US run records a stamp in its output (``legacy_inputs.OUTPUT_STAMP_H5_DATASET``
once saved): the register of renamed stored inputs it was calculated under, an
output format revision, and the stamp of the year file its input data was cut
into, or ``null``. ``Simulation.load()`` refuses an output, and
``Simulation.ensure()`` calculates it again, unless the stamp matches this
release's. These tests state the check's invariants over generated stamps,
records and registers, without a country engine:

- **Exactness.** An output is current exactly when its stamp has this
  release's output format revision and register, its year-file stamp is
  ``null`` or this release's year-file stamp, and its renames record lists
  only renames in its stamped register.
- **Totality.** Whatever the stamp and record hold, the check returns a
  reason or ``None``, and raises only for errors unrelated to the file's
  contents (a missing file, no permission, a directory, a lock).
- **Round trip.** A stamp reads back as written, and writing again replaces it.
- **Named renames.** The reason names every rename the output's registers
  (its own and its year file's) and this release's disagree on.
- **No partial output is current.** Every truncation of a current output is
  out of date.
- **Distinct stamps.** An output never passes as a year file, nor a year file
  as an output.

``test_us_legacy_inputs_integration.py`` saves, loads and ensures outputs over
a real policyengine-us engine.
"""

from __future__ import annotations

import functools
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import h5py
import numpy as np
import pandas as pd
import pytest
from hypothesis import event, given, settings
from hypothesis import strategies as st
from microdf import MicroDataFrame

from policyengine.tax_benefit_models.us import legacy_inputs
from policyengine.tax_benefit_models.us.datasets import (
    PolicyEngineUSDataset,
    USYearData,
)
from policyengine.tax_benefit_models.us.legacy_inputs import (
    LEGACY_INPUT_RENAMES,
    OUTPUT_STAMP_H5_DATASET,
    OUTPUT_STAMP_REVISION,
    RENAMES_H5_DATASET,
    YEAR_FILE_STAMP_H5_DATASET,
    YEAR_FILE_STAMP_KEY,
    YEAR_FILE_STAMP_REVISION,
    output_stamp,
    output_stamp_problem,
    read_output_stamp,
    read_renames_record,
    read_year_file_stamp,
    write_output_stamp,
    year_file_stamp,
    year_file_stamp_metadata,
    year_file_stamp_problem,
)

LEGACY = "would_claim_wic"
LIVE = "takes_up_wic_if_eligible"
REVISION = OUTPUT_STAMP_REVISION
YEAR_FILE_REVISION = YEAR_FILE_STAMP_REVISION
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
#: Text stored as it is, not as JSON. HDF5 variable-length strings cannot
#: hold a NUL character, and a lone surrogate cannot be encoded as UTF-8.
RAW_TEXT = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    max_size=12,
)


def _frames() -> dict[str, pd.DataFrame]:
    person = pd.DataFrame(
        {
            "person_id": [1, 2],
            **{f"{group}_id": [1, 1] for group in GROUPS},
            "person_weight": [1.0, 1.0],
            "wic": [0.0, 50.0],
        }
    )
    frames = {"person": person}
    for group in GROUPS:
        frames[group] = pd.DataFrame({f"{group}_id": [1], f"{group}_weight": [1.0]})
    return frames


def _dataset(path) -> PolicyEngineUSDataset:
    return PolicyEngineUSDataset(
        name="output",
        description="Uncertified two-person output fixture",
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


def _write_output(path, *, stamp=_ABSENT, record=_ABSENT, year_file_stamp=_ABSENT):
    """Write an output's tables, then its record and stamps as given.

    ``stamp`` (the output stamp), ``record`` and ``year_file_stamp`` are JSON
    values, ``_ABSENT``, or a raw node (see :func:`_write_node`).
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    _dataset(path).save()
    with h5py.File(path, "a") as file:
        _write_node(file, RENAMES_H5_DATASET, record)
        _write_node(file, YEAR_FILE_STAMP_H5_DATASET, year_file_stamp)
        _write_node(file, OUTPUT_STAMP_H5_DATASET, stamp)
    return Path(path)


_UNREADABLE = object()


def _stored(content):
    """The JSON value a stored node holds, decoded as HDF5 stores it.

    ``_ABSENT`` for no node, ``_UNREADABLE`` for a node that does not hold a
    UTF-8 JSON scalar, and the value otherwise. This decodes the raw node
    kinds of :func:`_write_node` directly, not through the reader under test.
    """
    if content is _ABSENT or not isinstance(content, tuple):
        return content
    kind, value = content
    try:
        if kind == "text":
            return json.loads(value)
        if kind == "bytes":
            # A fixed-length string reads back without its trailing NUL bytes.
            return json.loads(value.rstrip(b"\x00").decode("utf-8"))
    except (RecursionError, ValueError):
        pass
    return _UNREADABLE


def _same_json(left, right) -> bool:
    """Equal as JSON text, so ``true`` is not ``1`` and ``1.0`` is not ``1``."""
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def _str_map(value) -> bool:
    return isinstance(value, dict) and all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    )


def _is_current(stamp, record, register) -> bool:
    """The exactness invariant, stated directly on the stored JSON values."""
    year_file = {"register": dict(register), "revision": YEAR_FILE_REVISION}
    return (
        isinstance(stamp, dict)
        and set(stamp) == {"register", "revision", "year_file"}
        and type(stamp["revision"]) is int
        and stamp["revision"] == REVISION
        and _str_map(stamp["register"])
        and stamp["register"] == register
        and (stamp["year_file"] is None or _same_json(stamp["year_file"], year_file))
        and _str_map(record)
        and record.items() <= stamp["register"].items()
    )


def _stamp(register, revision=REVISION, year_file=None):
    return {"register": dict(register), "revision": revision, "year_file": year_file}


def _year_stamp(register, revision=YEAR_FILE_REVISION):
    return {"register": dict(register), "revision": revision}


# --- The stamp ----------------------------------------------------------


def test_the_stamp_holds_the_register_the_revision_and_the_year_file():
    assert output_stamp() == {
        "register": {LEGACY: LIVE},
        "revision": 1,
        "year_file": None,
    }
    assert output_stamp()["register"] == LEGACY_INPUT_RENAMES
    assert output_stamp(year_file_stamp()) == {
        "register": {LEGACY: LIVE},
        "revision": 1,
        "year_file": {"register": {LEGACY: LIVE}, "revision": 1},
    }


def test_the_stamp_reads_the_register_and_revision_when_called(monkeypatch):
    """model.py must not freeze the register at import."""
    monkeypatch.setattr(legacy_inputs, "LEGACY_INPUT_RENAMES", {"b": "c", "a": "d"})
    monkeypatch.setattr(legacy_inputs, "OUTPUT_STAMP_REVISION", 4)

    assert output_stamp() == {
        "register": {"a": "d", "b": "c"},
        "revision": 4,
        "year_file": None,
    }


def test_the_stamp_copies_the_year_file_stamp():
    """A later change to the input's metadata does not change the stamp."""
    year_file = year_file_stamp()
    stamp = output_stamp(year_file)
    year_file["register"]["x"] = "y"
    year_file["revision"] = 9

    assert stamp["year_file"] == {"register": {LEGACY: LIVE}, "revision": 1}


def test_the_stamp_is_stored_as_utf8_json(tmp_path):
    path = _write_output(tmp_path / "output.h5")

    write_output_stamp(path, output_stamp())

    with h5py.File(path, "r") as file:
        assert file[OUTPUT_STAMP_H5_DATASET].asstr()[()] == (
            f'{{"register": {{"{LEGACY}": "{LIVE}"}}, "revision": 1, '
            '"year_file": null}'
        )


@settings(max_examples=50, deadline=None)
@given(
    first=st.fixed_dictionaries(
        {"register": REGISTERS, "revision": st.integers(), "year_file": JSON_VALUES}
    ),
    second=st.fixed_dictionaries(
        {"register": REGISTERS, "revision": st.integers(), "year_file": JSON_VALUES}
    ),
)
def test_an_output_stamp_reads_back_as_written(first, second):
    """Round trip: a stamp reads back exactly, a new one replaces it, and
    the tables, the record and any year-file stamp are left alone."""
    with tempfile.TemporaryDirectory() as directory:
        path = _write_output(
            Path(directory) / "output.h5", record={}, year_file_stamp=[1]
        )
        assert read_output_stamp(path) is None

        write_output_stamp(path, first)
        assert _same_json(read_output_stamp(path), first)

        write_output_stamp(path, second)
        assert _same_json(read_output_stamp(path), second)
        assert read_renames_record(path) == {}
        assert read_year_file_stamp(path) == [1]
        with pd.HDFStore(path, mode="r") as store:
            assert store["person"]["wic"].tolist() == [0.0, 50.0]


def test_a_missing_or_foreign_file_has_no_output_stamp(tmp_path):
    assert read_output_stamp(tmp_path / "missing.h5") is None
    text = tmp_path / "notes.txt"
    text.write_text("not an H5 file")
    assert read_output_stamp(text) is None


# --- Exactness ----------------------------------------------------------


def _weighted(draw, *choices):
    """Draw from one of ``(weight, strategy)`` pairs, in proportion to weight.

    ``st.one_of`` drops a repeated branch, so repeating one does not weight it.
    """
    indices = [
        index for index, (weight, _) in enumerate(choices) for _ in range(weight)
    ]
    return draw(choices[draw(st.sampled_from(indices))][1])


@st.composite
def near(draw, register):
    """``register`` itself (most often), one entry away from it, or any."""
    return _weighted(
        draw,
        (6, st.just(dict(register))),
        (1, REGISTERS),
        (
            1,
            st.builds(
                lambda name: {k: v for k, v in register.items() if k != name},
                NAMES,
            ),
        ),
        (1, st.builds(lambda k, v: {**register, k: v}, NAMES, NAMES)),
    )


@st.composite
def stamped_outputs(draw):
    """A current register, and an output's stamp and record near it.

    Each part is usually right, so current outputs and outputs wrong in a
    single part are both common.
    """
    register = draw(REGISTERS)
    stamped = draw(near(register))
    revision = draw(st.sampled_from([REVISION] * 12 + [0, 2, -1, True, 1.0]))
    year_file = _weighted(
        draw,
        (5, st.none()),
        (
            4,
            st.builds(
                _year_stamp,
                near(register),
                st.sampled_from([YEAR_FILE_REVISION] * 12 + [0, 2, True, 1.0, "1"]),
            ),
        ),
        (1, st.just("unreadable")),
        (1, JSON_VALUES),
    )
    record = _weighted(
        draw,
        # A subset of the stamped register, as a run records, most often.
        (
            6,
            st.builds(
                lambda keep: {k: v for k, v in stamped.items() if k in keep},
                st.sets(NAMES),
            ),
        ),
        (1, st.just(_ABSENT)),
        (1, REGISTERS),
        (1, JSON_VALUES),
    )
    return register, _stamp(stamped, revision, year_file), record


@settings(max_examples=300, deadline=None)
@given(case=stamped_outputs())
def test_an_output_is_current_only_under_this_releases_exact_stamp(case):
    """Exactness, and refinement of the record check outputs had before.

    Equivalently: the stamp is what this release would write for a run over
    a dataset with no year-file stamp, or over a current year file.
    """
    register, stamp, record = case
    with tempfile.TemporaryDirectory() as directory:
        path = _write_output(Path(directory) / "output.h5", stamp=stamp, record=record)
        with patch.object(legacy_inputs, "LEGACY_INPUT_RENAMES", register):
            problem = output_stamp_problem(path)
            expected = (
                any(
                    _same_json(stamp, output_stamp(year_file))
                    for year_file in (None, year_file_stamp())
                )
                and _str_map(record)
                and record.items() <= stamp["register"].items()
            )

        assert (problem is None) == _is_current(stamp, record, register) == expected
        assert problem is None or (isinstance(problem, str) and problem)
        event(
            "current"
            if problem is None
            else "out of date: " + ("year file" if "year file" in problem else "other")
        )
        if problem is None:
            # Every output the stamp accepts, the record check accepted too.
            assert read_renames_record(path) == record
            assert _same_json(read_output_stamp(path), stamp)


NODES = st.one_of(
    st.just(_ABSENT),
    JSON_VALUES,
    st.fixed_dictionaries(
        {
            "register": st.one_of(REGISTERS, JSON_VALUES),
            "revision": st.one_of(
                st.just(REVISION), st.booleans(), st.floats(), JSON_VALUES
            ),
            "year_file": st.one_of(
                st.none(),
                st.fixed_dictionaries(
                    {
                        "register": st.one_of(REGISTERS, JSON_VALUES),
                        "revision": st.one_of(
                            st.just(YEAR_FILE_REVISION), st.booleans(), JSON_VALUES
                        ),
                    }
                ),
                JSON_VALUES,
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
def test_the_output_problem_is_total_and_exact_for_any_content(stamp, record, register):
    """Totality: any stamp and record give a reason or ``None``, never an
    error, and ``None`` only for this release's exact stamp."""
    with tempfile.TemporaryDirectory() as directory:
        path = _write_output(Path(directory) / "output.h5", stamp=stamp, record=record)
        with patch.object(legacy_inputs, "LEGACY_INPUT_RENAMES", register):
            problem = output_stamp_problem(path)

    assert problem is None or (isinstance(problem, str) and problem)
    assert (problem is None) == _is_current(_stored(stamp), _stored(record), register)


@pytest.mark.parametrize(
    "stamp",
    [
        {"register": {LEGACY: LIVE}, "revision": True, "year_file": None},
        {"register": {LEGACY: LIVE}, "revision": 1.0, "year_file": None},
        {"register": {LEGACY: LIVE}, "revision": "1", "year_file": None},
        {"register": {LEGACY: LIVE}, "revision": 1},
        {"register": {LEGACY: LIVE}, "year_file": None},
        {"register": {LEGACY: LIVE}, "revision": 1, "year_file": None, "x": None},
        {"register": {LEGACY: 5}, "revision": 1, "year_file": None},
        {"register": [[LEGACY, LIVE]], "revision": 1, "year_file": None},
        [{"register": {LEGACY: LIVE}, "revision": 1, "year_file": None}],
        None,
        ("text", "not json"),
        ("text", ""),
        ("bytes", b"\xff\xfe"),
        ("number", 1),
        ("array", ["{}"]),
        ("group", None),
    ],
)
def test_a_malformed_stamp_is_out_of_date(tmp_path, stamp):
    path = _write_output(tmp_path / "output.h5", stamp=stamp, record={})

    assert output_stamp_problem(path) == (
        "its stamp of the register of renamed inputs it was calculated under is "
        "malformed"
    )


@pytest.mark.parametrize("revision", [0, 2, -1])
def test_an_output_from_another_format_revision_is_out_of_date(tmp_path, revision):
    # A later revision may shape the rest of its stamp and record differently,
    # and is still reported by revision rather than as malformed.
    stamp = {"revision": revision, "registers": [[LEGACY, LIVE]]}
    path = _write_output(tmp_path / "output.h5", stamp=stamp)

    assert output_stamp_problem(path) == (
        f"it was saved with output format revision {revision}, and this "
        "version of policyengine.py reads only revision 1"
    )


def test_outputs_without_a_stamp_are_out_of_date_with_distinct_reasons(tmp_path):
    """Outputs saved before the mapping wrote neither; #531 wrote the record."""
    oldest = _write_output(tmp_path / "oldest.h5")
    record_only = _write_output(tmp_path / "record_only.h5", record={LEGACY: LIVE})

    assert output_stamp_problem(oldest) == (
        "it has no record of the renamed stored inputs mapped when it was "
        "calculated, so it was saved by an older policyengine.py or not saved "
        f"completely, and may have been calculated without any of: {LEGACY} -> "
        f"{LIVE}"
    )
    assert output_stamp_problem(record_only) == (
        "it has no stamp of the register of renamed inputs it was calculated "
        f"under, so it may have been calculated without any of: {LEGACY} -> {LIVE}"
    )


def test_an_unstamped_output_is_out_of_date_even_with_an_empty_register(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(legacy_inputs, "LEGACY_INPUT_RENAMES", {})
    oldest = _write_output(tmp_path / "oldest.h5")
    record_only = _write_output(tmp_path / "record_only.h5", record={})

    assert output_stamp_problem(oldest) == (
        "it has no record of the renamed stored inputs mapped when it was "
        "calculated, so it was saved by an older policyengine.py or not saved "
        "completely"
    )
    assert output_stamp_problem(record_only) == (
        "it has no stamp of the register of renamed inputs it was calculated under"
    )


MALFORMED_RECORD = (
    "its record of the renamed stored inputs mapped when it was calculated is malformed"
)


@pytest.mark.parametrize(
    "record, reason",
    [
        (
            _ABSENT,
            "it has no record of the renamed stored inputs mapped when it was "
            "calculated",
        ),
        ([], MALFORMED_RECORD),
        ([[LEGACY, LIVE]], MALFORMED_RECORD),
        (5, MALFORMED_RECORD),
        (None, MALFORMED_RECORD),
        ({LEGACY: 1}, MALFORMED_RECORD),
        (("text", "{"), MALFORMED_RECORD),
        (("group", None), MALFORMED_RECORD),
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
def test_a_stamped_output_needs_a_record_within_its_register(tmp_path, record, reason):
    path = _write_output(tmp_path / "output.h5", stamp=output_stamp(), record=record)

    assert output_stamp_problem(path) == reason


@pytest.mark.parametrize("record", [{}, {LEGACY: LIVE}])
@pytest.mark.parametrize("year_file", [None, year_file_stamp()])
def test_an_output_stamped_with_this_releases_stamp_is_current(
    tmp_path, record, year_file
):
    path = _write_output(
        tmp_path / "output.h5", stamp=output_stamp(year_file), record=record
    )

    assert output_stamp_problem(path) is None


def test_a_stamp_and_record_stored_as_fixed_length_strings_are_read(tmp_path):
    stamp = json.dumps(output_stamp(year_file_stamp())).encode()
    record = json.dumps({LEGACY: LIVE}).encode()
    path = _write_output(
        tmp_path / "output.h5", stamp=("bytes", stamp), record=("bytes", record)
    )

    assert output_stamp_problem(path) is None
    assert read_output_stamp(path) == output_stamp(year_file_stamp())


@pytest.mark.parametrize(
    "record",
    [
        ("text", "{}"),
        ("bytes", b"{}"),
        ("bytes", b"{}\x00"),
        ("text", json.dumps({LEGACY: LIVE})),
        ("bytes", json.dumps({LEGACY: LIVE}).encode()),
    ],
)
def test_a_record_stored_as_raw_text_or_bytes_is_read(tmp_path, record):
    path = _write_output(tmp_path / "output.h5", stamp=output_stamp(), record=record)

    assert output_stamp_problem(path) is None
    assert read_renames_record(path) == _stored(record)


@pytest.mark.parametrize(
    "name", [OUTPUT_STAMP_H5_DATASET, RENAMES_H5_DATASET, YEAR_FILE_STAMP_H5_DATASET]
)
def test_a_soft_link_that_leads_back_to_itself_is_unreadable(tmp_path, name):
    """h5py raises ``RuntimeError`` following such a link."""
    path = _write_output(
        tmp_path / "output.h5",
        stamp=output_stamp(),
        record={},
        year_file_stamp=year_file_stamp(),
    )
    with h5py.File(path, "a") as file:
        del file[name]
        file[name] = h5py.SoftLink(f"/{name}")

    if name == OUTPUT_STAMP_H5_DATASET:
        assert output_stamp_problem(path) == (
            "its stamp of the register of renamed inputs it was calculated under "
            "is malformed"
        )
        assert read_output_stamp(path) is None
    elif name == RENAMES_H5_DATASET:
        assert output_stamp_problem(path) == MALFORMED_RECORD
        assert read_renames_record(path) is None
    else:
        assert year_file_stamp_metadata(path) == "unreadable"
        assert read_year_file_stamp(path) is None
        assert year_file_stamp_problem(path) is not None


# --- The year file an output was calculated from ------------------------


MALFORMED_YEAR_FILE = (
    "its record of the stamp of the year file it was calculated from is malformed"
)


@pytest.mark.parametrize(
    "year_file, reason",
    [
        (
            _year_stamp({}),
            "it was calculated from a year file cut before these renames were "
            f"registered, which may have lost them: {LEGACY} -> {LIVE}",
        ),
        (
            _year_stamp({**LEGACY_INPUT_RENAMES, "old": "new"}),
            "it was calculated from a year file cut under renames this version of "
            "policyengine.py does not register: old -> new",
        ),
        (
            _year_stamp({LEGACY: "elsewhere"}),
            "it was calculated from a year file cut before these renames were "
            f"registered, which may have lost them: {LEGACY} -> {LIVE}; it was "
            "calculated from a year file cut under renames this version of "
            f"policyengine.py does not register: {LEGACY} -> elsewhere",
        ),
        (
            _year_stamp(LEGACY_INPUT_RENAMES, 0),
            "it was calculated from a year file cut with year-file format "
            "revision 0, and this version of policyengine.py reads only revision 1",
        ),
        (
            {"revision": 2, "registers": []},
            "it was calculated from a year file cut with year-file format "
            "revision 2, and this version of policyengine.py reads only revision 1",
        ),
        (_year_stamp(LEGACY_INPUT_RENAMES, True), MALFORMED_YEAR_FILE),
        (_year_stamp(LEGACY_INPUT_RENAMES, 1.0), MALFORMED_YEAR_FILE),
        ({**year_file_stamp(), "extra": None}, MALFORMED_YEAR_FILE),
        ({"register": {LEGACY: LIVE}}, MALFORMED_YEAR_FILE),
        ({"register": {LEGACY: 1}, "revision": 1}, MALFORMED_YEAR_FILE),
        ("unreadable", MALFORMED_YEAR_FILE),
        (False, MALFORMED_YEAR_FILE),
        (0, MALFORMED_YEAR_FILE),
        ([], MALFORMED_YEAR_FILE),
        ({}, MALFORMED_YEAR_FILE),
    ],
)
def test_an_output_from_an_out_of_date_year_file_is_out_of_date(
    tmp_path, year_file, reason
):
    """A run over a year file maps only what the file still stores under a
    legacy name, so the output inherits whatever the file lost."""
    path = _write_output(
        tmp_path / "output.h5",
        stamp=_stamp(LEGACY_INPUT_RENAMES, 1, year_file),
        record={},
    )

    assert output_stamp_problem(path) == reason


def test_raising_the_year_file_revision_makes_outputs_from_year_files_out_of_date(
    tmp_path, monkeypatch
):
    from_year_file = _write_output(
        tmp_path / "from_year_file.h5", stamp=output_stamp(year_file_stamp()), record={}
    )
    from_source = _write_output(
        tmp_path / "from_source.h5", stamp=output_stamp(), record={}
    )
    monkeypatch.setattr(legacy_inputs, "YEAR_FILE_STAMP_REVISION", 2)

    assert output_stamp_problem(from_year_file) == (
        "it was calculated from a year file cut with year-file format revision 1, "
        "and this version of policyengine.py reads only revision 2"
    )
    assert output_stamp_problem(from_source) is None


def test_raising_the_output_revision_makes_older_outputs_out_of_date(
    tmp_path, monkeypatch
):
    older = _write_output(tmp_path / "older.h5", stamp=output_stamp(), record={})
    monkeypatch.setattr(legacy_inputs, "OUTPUT_STAMP_REVISION", 7)
    newer = _write_output(tmp_path / "newer.h5", stamp=output_stamp(), record={})

    assert output_stamp()["revision"] == 7
    assert output_stamp_problem(newer) is None
    assert output_stamp_problem(older) == (
        "it was saved with output format revision 1, and this version of "
        "policyengine.py reads only revision 7"
    )


# --- Named renames ------------------------------------------------------


def _expected_differences(stamped, register):
    missing = {k: v for k, v in register.items() if stamped.get(k) != v}
    unknown = {k: v for k, v in stamped.items() if register.get(k) != v}
    return missing, unknown


@settings(max_examples=200, deadline=None)
@given(register=REGISTERS, stamped=REGISTERS, year_file=REGISTERS)
def test_a_stale_output_names_each_rename_it_may_lack(register, stamped, year_file):
    """The reason names every entry its registers and this release's disagree
    on, as ``old -> new`` from the register that has it, and no other."""
    with tempfile.TemporaryDirectory() as directory:
        path = _write_output(
            Path(directory) / "output.h5",
            stamp=_stamp(stamped, year_file=_year_stamp(year_file)),
            record={},
        )
        with patch.object(legacy_inputs, "LEGACY_INPUT_RENAMES", register):
            problem = output_stamp_problem(path)

    if stamped == register and year_file == register:
        assert problem is None
        return
    reasons = problem.split("; ")
    own = [r for r in reasons if "from a year file" not in r]
    cut = [r for r in reasons if "from a year file" in r]
    for registered, clauses in ((stamped, own), (year_file, cut)):
        missing, unknown = _expected_differences(registered, register)
        assert len(clauses) == bool(missing) + bool(unknown)
        if missing:
            assert "before these renames were registered" in clauses[0]
            for legacy, live in missing.items():
                assert f"{legacy} -> {live}" in clauses[0]
        if unknown:
            assert "does not register" in clauses[-1]
            for legacy, live in unknown.items():
                assert f"{legacy} -> {live}" in clauses[-1]
        for legacy, live in register.items() & registered.items():
            assert all(f"{legacy} -> {live}" not in clause for clause in clauses)


def test_a_future_register_entry_makes_a_stamped_output_out_of_date(
    tmp_path, monkeypatch
):
    path = _write_output(tmp_path / "output.h5", stamp=output_stamp(), record={})
    monkeypatch.setattr(
        legacy_inputs,
        "LEGACY_INPUT_RENAMES",
        {**LEGACY_INPUT_RENAMES, "old_input": "new_input"},
    )

    assert output_stamp_problem(path) == (
        "it was calculated before these renames were registered, so it may have "
        "been calculated without them: old_input -> new_input"
    )


@pytest.mark.parametrize(
    "register, reason",
    [
        (
            {},
            "it was calculated under renames this version of policyengine.py does "
            f"not register: {LEGACY} -> {LIVE}",
        ),
        (
            {LEGACY: "elsewhere"},
            "it was calculated before these renames were registered, so it may "
            f"have been calculated without them: {LEGACY} -> elsewhere; it was "
            "calculated under renames this version of policyengine.py does not "
            f"register: {LEGACY} -> {LIVE}",
        ),
    ],
)
def test_retiring_or_retargeting_an_entry_makes_a_stamped_output_out_of_date(
    tmp_path, monkeypatch, register, reason
):
    path = _write_output(
        tmp_path / "output.h5", stamp=output_stamp(), record={LEGACY: LIVE}
    )
    monkeypatch.setattr(legacy_inputs, "LEGACY_INPUT_RENAMES", register)

    assert output_stamp_problem(path) == reason


# --- No partial output is current ---------------------------------------


@functools.cache
def _current_output_bytes() -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        path = _write_output(
            Path(directory) / "output.h5",
            stamp=output_stamp(year_file_stamp()),
            record={LEGACY: LIVE},
        )
        assert output_stamp_problem(path) is None
        return path.read_bytes()


@settings(max_examples=100, deadline=None)
@given(data=st.data())
def test_a_truncated_output_is_never_current(data):
    content = _current_output_bytes()
    length = data.draw(st.integers(0, len(content) - 1))
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "output.h5"
        path.write_bytes(content[:length])

        assert output_stamp_problem(path) is not None


def test_a_file_that_is_not_hdf5_is_out_of_date(tmp_path):
    path = tmp_path / "output.h5"
    path.write_text("not an H5 file")

    assert output_stamp_problem(path) == (
        "it cannot be read as an HDF5 file (it may be half-written or corrupt)"
    )


def test_saving_the_tables_again_drops_the_stamp(tmp_path):
    """``PolicyEngineUSDataset.save()`` truncates; only the model version's
    ``save()`` stamps an output."""
    path = _write_output(tmp_path / "output.h5", stamp=output_stamp(), record={})

    _dataset(path).save()

    assert read_output_stamp(path) is None
    assert output_stamp_problem(path) is not None


#: JSON nested very deeply. Whether the parser reaches its limit depends on
#: the interpreter and the platform (see ``test_us_year_file_stamp.py``).
DEEP_JSON = "[" * 100_000 + "0" + "]" * 100_000


@pytest.mark.parametrize(
    "stamp, record, reason",
    [
        (
            ("text", DEEP_JSON),
            {},
            "its stamp of the register of renamed inputs it was calculated under "
            "is malformed",
        ),
        (output_stamp(), ("text", DEEP_JSON), MALFORMED_RECORD),
    ],
)
def test_json_nested_too_deeply_is_out_of_date_not_an_error(
    tmp_path, stamp, record, reason
):
    path = _write_output(tmp_path / "output.h5", stamp=stamp, record=record)

    assert output_stamp_problem(path) == reason


@pytest.mark.parametrize("name", [OUTPUT_STAMP_H5_DATASET, RENAMES_H5_DATASET])
def test_a_recursion_error_while_parsing_is_unreadable_content(
    tmp_path, monkeypatch, name
):
    """The RecursionError path, on every platform."""
    path = _write_output(tmp_path / "output.h5", stamp=output_stamp(), record={})
    loads = json.loads

    def deep(text, *args, **kwargs):
        with h5py.File(path, "r") as file:
            if text == file[name].asstr()[()]:
                raise RecursionError("maximum recursion depth exceeded")
        return loads(text, *args, **kwargs)

    monkeypatch.setattr(legacy_inputs.json, "loads", deep)

    assert output_stamp_problem(path) == (
        "its stamp of the register of renamed inputs it was calculated under is "
        "malformed"
        if name == OUTPUT_STAMP_H5_DATASET
        else MALFORMED_RECORD
    )


def test_dangling_links_in_place_of_the_stamp_and_record_read_as_absent(tmp_path):
    path = _write_output(tmp_path / "output.h5")
    with h5py.File(path, "a") as file:
        file[OUTPUT_STAMP_H5_DATASET] = h5py.SoftLink("/nowhere")
        file[RENAMES_H5_DATASET] = h5py.ExternalLink(
            str(tmp_path / "missing.h5"), "/record"
        )

    assert output_stamp_problem(path).startswith(
        "it has no record of the renamed stored inputs mapped when it was calculated"
    )
    assert read_output_stamp(path) is None


# --- Errors unrelated to the file's contents ----------------------------


def test_a_missing_output_raises_file_not_found(tmp_path):
    """``Simulation.ensure()`` treats it as a plain miss."""
    with pytest.raises(FileNotFoundError):
        output_stamp_problem(tmp_path / "missing.h5")


def _unreadable_by_permission(path) -> Path:
    path = _write_output(path, stamp=output_stamp(), record={})
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
    path = make(tmp_path / "output.h5")
    try:
        with pytest.raises(error):
            output_stamp_problem(path)
        with pytest.raises(error):
            year_file_stamp_metadata(path)
    finally:
        if path.is_file():
            os.chmod(path, 0o644)


@pytest.mark.parametrize("check", [output_stamp_problem, year_file_stamp_metadata])
def test_a_locked_file_is_raised(tmp_path, monkeypatch, check):
    path = _write_output(tmp_path / "output.h5", stamp=output_stamp(), record={})

    def locked(*args, **kwargs):
        raise BlockingIOError(35, "Unable to lock file")

    monkeypatch.setattr(h5py, "File", locked)
    with pytest.raises(BlockingIOError):
        check(path)


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
    path = _write_output(
        tmp_path / "output.h5",
        stamp=output_stamp(),
        record={},
        year_file_stamp=year_file_stamp(),
    )

    def fail(self, *args, **kwargs):
        raise error

    monkeypatch.setattr(h5py.Dataset, "asstr", fail)
    with pytest.raises(type(error)):
        output_stamp_problem(path)
    with pytest.raises(type(error)):
        year_file_stamp_metadata(path)


def test_the_decision_reads_only_the_stamp_and_the_record(tmp_path, monkeypatch):
    path = _write_output(
        tmp_path / "output.h5", stamp=output_stamp(year_file_stamp()), record={}
    )
    real_file = h5py.File

    class StampAndRecordOnly:
        def __init__(self, path, mode="r", **kwargs):
            assert mode == "r"
            self._file = real_file(path, mode, **kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self._file.close()

        def get(self, name, default=None):
            assert name in (OUTPUT_STAMP_H5_DATASET, RENAMES_H5_DATASET), name
            return self._file.get(name, default)

    monkeypatch.setattr(h5py, "File", StampAndRecordOnly)

    assert output_stamp_problem(path) is None


# --- Distinct stamps: an output never passes as a year file -------------


@settings(max_examples=100, deadline=None)
@given(
    register=REGISTERS,
    keep=st.sets(NAMES),
    from_year_file=st.booleans(),
)
def test_an_output_never_passes_as_a_year_file_nor_the_reverse(
    register, keep, from_year_file
):
    """Current files of each kind, under any register, are out of date as the
    other kind, and so is either stamp stored under the other's name."""
    record = {k: v for k, v in register.items() if k in keep}
    with (
        tempfile.TemporaryDirectory() as directory,
        patch.object(legacy_inputs, "LEGACY_INPUT_RENAMES", register),
    ):
        stamp = output_stamp(year_file_stamp() if from_year_file else None)
        output = _write_output(
            Path(directory) / "output.h5", stamp=stamp, record=record
        )
        year_file = _write_output(
            Path(directory) / "year.h5",
            year_file_stamp=year_file_stamp(),
            record=record,
        )
        assert output_stamp_problem(output) is None
        assert year_file_stamp_problem(year_file) is None

        assert year_file_stamp_problem(output) is not None
        assert output_stamp_problem(year_file) is not None

        # Each stamp stored under the other's name.
        swapped_output = _write_output(
            Path(directory) / "swapped_output.h5",
            year_file_stamp=stamp,
            record=record,
        )
        swapped_year_file = _write_output(
            Path(directory) / "swapped_year.h5",
            stamp=year_file_stamp(),
            record=record,
        )
        assert year_file_stamp_problem(swapped_output) is not None
        assert output_stamp_problem(swapped_year_file) is not None


def test_the_two_stamps_have_different_keys():
    assert set(output_stamp()) == {"register", "revision", "year_file"}
    assert set(year_file_stamp()) == {"register", "revision"}
    assert OUTPUT_STAMP_H5_DATASET != YEAR_FILE_STAMP_H5_DATASET


# --- The year-file stamp a dataset keeps --------------------------------


@pytest.mark.parametrize(
    "stored, kept",
    [
        (_ABSENT, None),
        ({"register": {LEGACY: LIVE}, "revision": 1}, year_file_stamp()),
        ([1, 2], [1, 2]),
        (False, False),
        (0, 0),
        ("text", "text"),
        (None, "unreadable"),
        (("text", "not json"), "unreadable"),
        (("bytes", b"\xff"), "unreadable"),
        (("number", 3), "unreadable"),
        (("group", None), "unreadable"),
    ],
)
def test_a_dataset_keeps_its_year_files_stamp(tmp_path, stored, kept):
    path = _write_output(tmp_path / "year.h5", year_file_stamp=stored, record={})

    assert year_file_stamp_metadata(path) == kept
    dataset = PolicyEngineUSDataset(
        name="year-file", description="reload", filepath=str(path), year=2024
    )
    if kept is None:
        assert YEAR_FILE_STAMP_KEY not in dataset.metadata
    else:
        assert dataset.metadata[YEAR_FILE_STAMP_KEY] == kept


def test_a_file_that_is_not_hdf5_keeps_no_year_file_stamp(tmp_path):
    path = tmp_path / "notes.h5"
    path.write_text("not an H5 file")

    assert year_file_stamp_metadata(path) is None


def test_reloading_a_resaved_year_file_drops_the_stamp_it_kept(tmp_path):
    path = _write_output(
        tmp_path / "year.h5", year_file_stamp=year_file_stamp(), record={}
    )
    dataset = PolicyEngineUSDataset(
        name="year-file", description="reload", filepath=str(path), year=2024
    )
    assert dataset.metadata[YEAR_FILE_STAMP_KEY] == year_file_stamp()

    # Saving drops the file's stamp, so the data reloaded from it is no
    # longer a stamped year file's.
    dataset.save()
    dataset.load()

    assert read_year_file_stamp(path) is None
    assert YEAR_FILE_STAMP_KEY not in dataset.metadata
    assert dataset.metadata["legacy_input_renames"] == {}
