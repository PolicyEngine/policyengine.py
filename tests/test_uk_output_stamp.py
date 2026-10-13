"""Unit and property tests for the stamp on saved UK simulation outputs.

A UK run records a stamp in its output (``uk.datasets.OUTPUT_STAMP_H5_DATASET``
once saved): the installed versions of the packages that calculated it, an
output format revision, and the stamp of the year file its input data was cut
into, or ``null``. ``Simulation.load()`` refuses an output, and
``Simulation.ensure()`` calculates it again, unless the stamp is the one a run
of the simulation's dataset would record now. These tests state the check's
invariants over generated stamps, data-year nodes, package versions and input
year-file stamps, without a country engine:

- **Exactness.** An output is current exactly when it records its data year,
  its stamp has this release's output format revision and the installed
  package versions, its year-file stamp equals the simulation's dataset's,
  and that is ``null`` or a well-formed year-file stamp.
- **Totality.** Whatever the stamp, the data year and the dataset's stamp
  hold, the check returns a reason or ``None``, and raises only for errors
  unrelated to the file's contents (a missing file, no permission, a
  directory, a lock).
- **Round trip.** A stamp reads back as written, and writing again replaces it.
- **Named differences.** The reason names every year, format revision,
  source and package version that differs between the year file the output
  was calculated from and the simulation's dataset, and every package
  version the output was calculated with that is not the one installed, and
  nothing that agrees.
- **No partial output is current.** Every truncation of a current output is
  out of date.
- **Distinct stamps.** An output never passes as a year file, nor a year file
  as an output, nor a US output as a UK one.
- **One save per output.** The tables and the stamp at an output's path come
  from one save: a save that fails leaves the output already there whole,
  and two saves to one path never leave one's tables under the other's
  stamp.
- **One file per load.** A dataset loaded from a year file keeps the stamp of
  the cut its tables came from, even when the file is replaced, replaced and
  put back, or modified while it is read.

``test_uk_output_stamp_integration.py`` runs, saves, loads and ensures outputs
over a real policyengine-uk engine, on a tiny dataset.
"""

from __future__ import annotations

import copy
import functools
import json
import os
import shutil
import tempfile
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest
from hypothesis import event, given, settings
from hypothesis import strategies as st
from microdf import MicroDataFrame

from policyengine.provenance import year_file_stamp as shared_stamp
from policyengine.provenance.dataset_materialization import (
    describe_dataset_source_identity,
)
from policyengine.provenance.year_file_stamp import (
    NOT_HDF5,
    package_differences,
    read_one_file,
)
from policyengine.tax_benefit_models.uk import datasets as uk_datasets
from policyengine.tax_benefit_models.uk.datasets import (
    DATA_YEAR_KEY,
    MALFORMED_OUTPUT_STAMP,
    MALFORMED_OUTPUT_YEAR_FILE,
    OUTPUT_PACKAGES,
    OUTPUT_STAMP_H5_DATASET,
    OUTPUT_STAMP_KEY,
    OUTPUT_STAMP_REVISION,
    OUTPUT_WITHOUT_DATA_YEAR,
    STAMPED_OUTPUT_WITHOUT_DATA_YEAR,
    UNREADABLE_YEAR_FILE_STAMP,
    UNSTAMPED_OUTPUT,
    YEAR_FILE_STAMP_H5_DATASET,
    YEAR_FILE_STAMP_KEY,
    YEAR_FILE_STAMP_REVISION,
    PolicyEngineUKDataset,
    UKYearData,
    input_year_file_stamp,
    output_stamp,
    output_stamp_problem,
    read_output_stamp,
    read_year_file_stamp,
    save_output,
    write_output_stamp,
    year_file_stamp,
    year_file_stamp_metadata,
    year_file_stamp_problem,
)

REVISION = OUTPUT_STAMP_REVISION
YEAR_FILE_REVISION = YEAR_FILE_STAMP_REVISION
DATA_YEAR = 2024
YEAR = 2026
SOURCE = "hf://fixture/repo/tiny.h5"
IDENTITY = {"uri": SOURCE}
#: The installed versions every test in this module sees (see
#: ``_installed_packages``), so no expectation depends on the environment.
PACKAGES = {"policyengine-core": "3.33.0", "policyengine-uk": "2.126.12"}
#: The real reader, kept before ``_installed_packages`` replaces it.
REAL_INSTALLED_OUTPUT_PACKAGES = uk_datasets.installed_output_packages
#: The US output stamp's H5 dataset (``us.legacy_inputs.OUTPUT_STAMP_H5_DATASET``,
#: PolicyEngine/policyengine.py#594), named here so this module does not
#: depend on that change.
US_OUTPUT_STAMP_H5_DATASET = "policyengine_output_stamp"

#: Small alphabets of source identities in each of their three shapes (see
#: ``dataset_source_identity``), so generated stamps often agree.
URIS = st.sampled_from([SOURCE, f"{SOURCE}@r1", f"{SOURCE}@r2"])
SOURCES = st.one_of(
    st.builds(lambda uri: {"uri": uri}, URIS),
    st.builds(
        lambda uri, sha256: {"uri": uri, "sha256": sha256},
        URIS,
        st.sampled_from(["a" * 64, "b" * 64]),
    ),
    st.builds(
        lambda path, size, mtime_ns: {"path": path, "size": size, "mtime_ns": mtime_ns},
        st.sampled_from(["/data/tiny.h5", "/elsewhere/tiny.h5"]),
        st.sampled_from([10, 11]),
        st.sampled_from([0, 1_760_000_000_123_456_789]),
    ),
)
PACKAGE_NAMES = st.sampled_from([*OUTPUT_PACKAGES, "policyengine-us", "extra"])
VERSIONS = st.one_of(st.none(), st.sampled_from(["1.0", "1.1"]))
PACKAGE_MAPS = st.one_of(
    st.just(PACKAGES), st.dictionaries(PACKAGE_NAMES, VERSIONS, max_size=3)
)
YEARS = st.sampled_from([YEAR, YEAR + 1])
YEAR_FILE_REVISIONS = st.sampled_from([YEAR_FILE_REVISION, YEAR_FILE_REVISION + 1])
#: Well-formed year-file stamps, often this release's.
YEAR_FILE_STAMPS = st.builds(
    lambda revision, source, packages, year: {
        "packages": dict(packages),
        "revision": revision,
        "source": dict(source),
        "year": year,
    },
    YEAR_FILE_REVISIONS,
    SOURCES,
    PACKAGE_MAPS,
    YEARS,
)
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
#: Year-file stamps a dataset may keep: none, well formed, unreadable, or any
#: JSON value, including well-formed keys holding values of the wrong type.
DATASET_STAMPS = st.one_of(
    st.none(),
    YEAR_FILE_STAMPS,
    st.just(UNREADABLE_YEAR_FILE_STAMP),
    JSON_VALUES,
    st.builds(
        lambda stamp, key, value: {**stamp, key: value},
        YEAR_FILE_STAMPS,
        st.sampled_from(["packages", "revision", "source", "year", "extra"]),
        st.one_of(st.booleans(), st.floats(), JSON_VALUES),
    ),
)
#: Text stored as it is, not as JSON. HDF5 variable-length strings cannot
#: hold a NUL character, and a lone surrogate cannot be encoded as UTF-8.
RAW_TEXT = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    max_size=12,
)
#: How an output's data year can be stored: ``True`` as ``save()`` writes it
#: (a group), ``False`` for none, or a node that is not a data year.
DATA_YEAR_NODES = ("dataset", "dangling link", "link cycle")


@pytest.fixture(autouse=True, scope="module")
def _installed_packages():
    """Pin the installed package versions a stamp records to ``PACKAGES``.

    Module-scoped, so Hypothesis tests can run under it.
    """
    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(
            uk_datasets, "installed_package_versions", lambda: dict(PACKAGES)
        )
        patcher.setattr(
            uk_datasets, "installed_output_packages", lambda: dict(PACKAGES)
        )
        yield


def _frames(age=70) -> dict[str, pd.DataFrame]:
    return {
        "person": pd.DataFrame(
            {
                "person_id": [1, 2],
                "person_benunit_id": [1, 1],
                "person_household_id": [1, 1],
                "person_weight": [1.0, 1.0],
                "age": [age, 68],
            }
        ),
        "benunit": pd.DataFrame({"benunit_id": [1], "benunit_weight": [1.0]}),
        "household": pd.DataFrame(
            {"household_id": [1], "household_weight": [1.0], "region": ["LONDON"]}
        ),
    }


def _tables(age=70) -> UKYearData:
    return UKYearData(
        **{
            entity: MicroDataFrame(frame, weights=f"{entity}_weight")
            for entity, frame in _frames(age).items()
        }
    )


def _output_dataset(path, data_year=DATA_YEAR, age=70) -> PolicyEngineUKDataset:
    """A two-person UK output for ``YEAR``, as a run makes one."""
    return PolicyEngineUKDataset(
        name="output",
        description="Uncertified two-person UK output fixture",
        filepath=str(path),
        year=YEAR,
        is_output_dataset=True,
        data=_tables(age),
        data_year=data_year,
    )


def _year_dataset(path, age=70) -> PolicyEngineUKDataset:
    """A two-person UK year file for ``YEAR`` projected from ``DATA_YEAR``."""
    return PolicyEngineUKDataset(
        name="year-file",
        description="Uncertified two-person UK year-file fixture",
        filepath=str(path),
        year=YEAR,
        data=_tables(age),
        data_year=DATA_YEAR,
        data_year_data=_tables(age),
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


def _link_cycle(file, name) -> None:
    """Point ``name`` into a cycle of soft links."""
    file[name] = h5py.SoftLink(f"/{name}_loop")
    file[f"{name}_loop"] = h5py.SoftLink(f"/{name}")


def _write_data_year_node(file, kind) -> None:
    if kind == "dataset":
        file.create_dataset(DATA_YEAR_KEY, data=DATA_YEAR)
    elif kind == "dangling link":
        file[DATA_YEAR_KEY] = h5py.SoftLink("/nowhere")
    elif kind == "link cycle":
        _link_cycle(file, DATA_YEAR_KEY)
    else:
        raise AssertionError(kind)


def _write_output(
    path, *, stamp=_ABSENT, data_year=True, year_file_stamp=_ABSENT, age=70
):
    """Write an output's tables and data year, then its stamps, as given.

    ``stamp`` (the output stamp) and ``year_file_stamp`` are JSON values,
    ``_ABSENT``, or a raw node (see :func:`_write_node`). ``data_year`` is
    ``True`` for the data year as ``save()`` writes it, ``False`` for none,
    or one of :data:`DATA_YEAR_NODES`.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    _output_dataset(path, DATA_YEAR if data_year is True else None, age).save()
    with h5py.File(path, "a") as file:
        if data_year not in (True, False):
            _write_data_year_node(file, data_year)
        _write_node(file, YEAR_FILE_STAMP_H5_DATASET, year_file_stamp)
        _write_node(file, OUTPUT_STAMP_H5_DATASET, stamp)
    return Path(path)


def _write_year_file(path, stamp, age=70) -> Path:
    """Write a year file's tables and data year, then its stamp."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    _year_dataset(path, age).save()
    with h5py.File(path, "a") as file:
        _write_node(file, YEAR_FILE_STAMP_H5_DATASET, stamp)
    return Path(path)


def _write_stamps(path, *, stamp=_ABSENT, data_year=True, year_file_stamp=_ABSENT):
    """Write what the checks read of an output or a year file, and no tables.

    The checks read the stamps and whether there is a data year, never the
    tables (``test_the_decision_reads_only_the_stamp_and_the_data_year``), and
    decide alike with and without them
    (``test_a_file_without_tables_is_checked_as_one_with_them``). The property
    tests write one file per example, so they write these, a fortieth of the
    size of :func:`_write_output`'s. Arguments are as for that function.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as file:
        if data_year is True:
            # As pandas stores the data year: a group.
            file.create_group(DATA_YEAR_KEY)
        elif data_year is not False:
            _write_data_year_node(file, data_year)
        _write_node(file, YEAR_FILE_STAMP_H5_DATASET, year_file_stamp)
        _write_node(file, OUTPUT_STAMP_H5_DATASET, stamp)
    return Path(path)


def _age(path) -> int:
    """The first person's age in the tables stored at ``path``."""
    with pd.HDFStore(path, mode="r") as store:
        return int(store["person"]["age"].iloc[0])


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


def _well_formed_year_file_stamp(value) -> bool:
    """The year-file stamp's shape, stated directly (see ``year_file_stamp``)."""
    if not (
        isinstance(value, dict)
        and set(value) == {"packages", "revision", "source", "year"}
        and type(value["revision"]) is int
        and type(value["year"]) is int
        and isinstance(value["packages"], dict)
        and all(
            isinstance(name, str) and (version is None or isinstance(version, str))
            for name, version in value["packages"].items()
        )
        and isinstance(value["source"], dict)
    ):
        return False
    source = value["source"]
    shapes = {
        frozenset({"uri"}): {"uri": str},
        frozenset({"uri", "sha256"}): {"uri": str, "sha256": str},
        frozenset({"path", "size", "mtime_ns"}): {
            "path": str,
            "size": int,
            "mtime_ns": int,
        },
    }
    types = shapes.get(frozenset(source))
    return types is not None and all(
        type(source[key]) is kind for key, kind in types.items()
    )


def _is_current(stamp, data_year, dataset_stamp, packages=PACKAGES) -> bool:
    """The exactness invariant, stated directly on the stored values.

    Only a data year written as ``save()`` writes it (a group) counts.
    """
    if dataset_stamp is not None and not _well_formed_year_file_stamp(dataset_stamp):
        return False
    return (
        data_year is True
        and isinstance(stamp, dict)
        and set(stamp) == {"packages", "revision", "year_file"}
        and type(stamp["revision"]) is int
        and stamp["revision"] == REVISION
        and _same_json(stamp["packages"], dict(packages))
        and _same_json(stamp["year_file"], dataset_stamp)
    )


def _year_stamp(
    revision=YEAR_FILE_REVISION, source=IDENTITY, packages=PACKAGES, year=YEAR
):
    return {
        "packages": dict(packages),
        "revision": revision,
        "source": dict(source),
        "year": year,
    }


def _current_year_stamp(year=YEAR):
    return year_file_stamp(IDENTITY, year)


def _stamp(year_file=None, packages=PACKAGES, revision=REVISION):
    """An output stamp, stated directly rather than through ``output_stamp``."""
    return {
        "packages": dict(packages),
        "revision": revision,
        "year_file": copy.deepcopy(year_file),
    }


# --- The stamp ----------------------------------------------------------


def test_the_stamp_holds_the_packages_the_revision_and_the_year_file():
    assert output_stamp() == {
        "packages": PACKAGES,
        "revision": REVISION,
        "year_file": None,
    }
    assert output_stamp(_current_year_stamp()) == {
        "packages": PACKAGES,
        "revision": REVISION,
        "year_file": _current_year_stamp(),
    }
    assert OUTPUT_STAMP_REVISION == 1
    assert list(output_stamp()["packages"]) == sorted(PACKAGES)


def test_the_stamp_reads_the_packages_and_revision_when_called(monkeypatch):
    monkeypatch.setattr(
        uk_datasets,
        "installed_output_packages",
        lambda: {"policyengine-uk": "9.0.0", "policyengine-core": None},
    )
    monkeypatch.setattr(uk_datasets, "OUTPUT_STAMP_REVISION", 7)

    assert output_stamp() == {
        "packages": {"policyengine-core": None, "policyengine-uk": "9.0.0"},
        "revision": 7,
        "year_file": None,
    }


def test_explicit_packages_override_the_installed_ones():
    assert output_stamp(None, {"policyengine-uk": "1.0"})["packages"] == {
        "policyengine-uk": "1.0"
    }


def test_the_stamp_records_the_packages_that_calculate_a_run():
    assert OUTPUT_PACKAGES == ("policyengine-core", "policyengine-uk")


def test_installed_output_packages_reads_the_distributions(monkeypatch):
    """The real reader asks for the output's packages, importing none."""
    seen = []

    def recording(names):
        seen.append(tuple(names))
        return {name: "1.0" for name in names}

    monkeypatch.setattr(shared_stamp, "installed_package_versions", recording)

    assert REAL_INSTALLED_OUTPUT_PACKAGES() == {
        "policyengine-core": "1.0",
        "policyengine-uk": "1.0",
    }
    assert seen == [OUTPUT_PACKAGES]


def test_the_stamp_copies_the_year_file_stamp():
    year_file = _current_year_stamp()
    stamp = output_stamp(year_file)
    year_file["source"]["uri"] = "changed"
    year_file["packages"]["policyengine-uk"] = "changed"

    assert stamp["year_file"] == _current_year_stamp()


def test_the_stamp_is_stored_as_utf8_json(tmp_path):
    path = _write_output(tmp_path / "output.h5")
    write_output_stamp(path, output_stamp(_current_year_stamp()))

    with h5py.File(path, "r") as file:
        node = file[OUTPUT_STAMP_H5_DATASET]
        assert node.shape == ()
        assert h5py.check_string_dtype(node.dtype).encoding == "utf-8"
        assert json.loads(node.asstr()[()]) == output_stamp(_current_year_stamp())


STAMPS = st.fixed_dictionaries(
    {
        "packages": PACKAGE_MAPS,
        "revision": st.integers(),
        "year_file": st.one_of(st.none(), YEAR_FILE_STAMPS),
    }
)


@settings(max_examples=50, deadline=None)
@given(first=STAMPS, second=STAMPS)
def test_an_output_stamp_reads_back_as_written(first, second):
    with tempfile.TemporaryDirectory() as directory:
        path = _write_stamps(Path(directory) / "output.h5")
        write_output_stamp(path, first)
        assert read_output_stamp(path) == first
        write_output_stamp(path, second)
        assert read_output_stamp(path) == second


def test_a_missing_or_foreign_file_has_no_output_stamp(tmp_path):
    assert read_output_stamp(tmp_path / "missing.h5") is None
    foreign = tmp_path / "foreign.h5"
    foreign.write_text("not an H5 file")
    assert read_output_stamp(foreign) is None
    assert read_output_stamp(_write_output(tmp_path / "unstamped.h5")) is None


def test_the_stamp_does_not_disturb_pandas_or_loading(tmp_path):
    path = _write_output(tmp_path / "output.h5", stamp=output_stamp())

    with pd.HDFStore(path, mode="r") as store:
        assert {"/person", "/benunit", "/household", f"/{DATA_YEAR_KEY}"} <= set(
            store.keys()
        )
    loaded = PolicyEngineUKDataset(
        name="output",
        description="reload",
        filepath=str(path),
        year=YEAR,
        is_output_dataset=True,
    )
    assert loaded.data_year == DATA_YEAR
    assert len(loaded.data.person) == 2


# --- Exactness ----------------------------------------------------------


def _weighted(draw, *choices):
    """Draw one of ``choices``, each a ``(weight, strategy)`` pair."""
    total = sum(weight for weight, _ in choices)
    pick = draw(st.integers(0, total - 1))
    for weight, strategy in choices:
        if pick < weight:
            return draw(strategy)
        pick -= weight
    raise AssertionError


@st.composite
def stamped_outputs(draw):
    """An output stamped as a run would, near the simulation's dataset.

    Most draws stamp the output from the dataset's own stamp, or one a single
    field away, with the installed packages, so current outputs and near
    misses are both common.
    """
    dataset_stamp = draw(DATASET_STAMPS)
    near = st.one_of(YEAR_FILE_STAMPS, DATASET_STAMPS)
    if _well_formed_year_file_stamp(dataset_stamp):
        near = st.one_of(
            near,
            st.builds(
                lambda key, value: {**dataset_stamp, key: value},
                st.sampled_from(["packages", "revision", "source", "year"]),
                st.one_of(PACKAGE_MAPS, YEAR_FILE_REVISIONS, SOURCES, YEARS),
            ),
        )
    year_file = _weighted(
        draw,
        (5, st.just(copy.deepcopy(dataset_stamp))),
        (3, near),
        (1, st.none()),
    )
    packages = _weighted(
        draw,
        (6, st.just(dict(PACKAGES))),
        (2, PACKAGE_MAPS),
        (1, st.one_of(st.booleans(), JSON_VALUES)),
    )
    stamp = _weighted(
        draw,
        (
            7,
            st.just(
                {"packages": packages, "revision": REVISION, "year_file": year_file}
            ),
        ),
        (
            1,
            st.fixed_dictionaries(
                {
                    "packages": st.just(packages),
                    "revision": st.one_of(
                        st.sampled_from([REVISION + 1, 0]), st.booleans(), st.floats()
                    ),
                    "year_file": st.just(year_file),
                }
            ),
        ),
        (1, st.just(_ABSENT)),
        (1, JSON_VALUES),
    )
    data_year = draw(st.sampled_from([True, True, True, True, False, *DATA_YEAR_NODES]))
    return stamp, data_year, dataset_stamp


@settings(max_examples=400, deadline=None)
@given(case=stamped_outputs())
def test_an_output_is_current_only_under_the_exact_stamp_its_run_would_record(case):
    stamp, data_year, dataset_stamp = case
    with tempfile.TemporaryDirectory() as directory:
        path = _write_stamps(
            Path(directory) / "output.h5", stamp=stamp, data_year=data_year
        )
        problem = output_stamp_problem(path, dataset_stamp)

    expected = _is_current(_stored(stamp), data_year, dataset_stamp)
    event(f"current: {expected}")
    assert (problem is None) == expected, problem
    if problem is not None:
        assert problem.startswith(("it ", "its ")), problem


NODES = st.one_of(
    st.just(_ABSENT),
    JSON_VALUES,
    st.fixed_dictionaries(
        {
            "packages": st.one_of(PACKAGE_MAPS, JSON_VALUES),
            "revision": st.one_of(st.just(REVISION), st.booleans(), JSON_VALUES),
            "year_file": DATASET_STAMPS,
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
    dataset_stamp=DATASET_STAMPS,
    packages=PACKAGE_MAPS,
)
def test_the_output_problem_is_total_and_exact_for_any_content(
    stamp, data_year, dataset_stamp, packages
):
    with tempfile.TemporaryDirectory() as directory:
        path = _write_stamps(
            Path(directory) / "output.h5", stamp=stamp, data_year=data_year
        )
        problem = output_stamp_problem(path, dataset_stamp, packages)

    assert problem is None or isinstance(problem, str)
    expected = _is_current(_stored(stamp), data_year, dataset_stamp, packages)
    assert (problem is None) == expected, problem
    if problem is not None:
        assert problem.startswith(("it ", "its ")), problem


def test_an_output_stamped_with_what_its_run_would_record_is_current(tmp_path):
    for dataset_stamp in (None, _current_year_stamp()):
        path = _write_output(
            tmp_path / f"{dataset_stamp is None}.h5",
            stamp=_stamp(dataset_stamp),
        )
        assert output_stamp_problem(path, dataset_stamp) is None


@pytest.mark.parametrize("data_year", [True, False, *DATA_YEAR_NODES])
@pytest.mark.parametrize(
    "stamp",
    [
        _ABSENT,
        None,
        {"revision": REVISION + 1},
        {"packages": PACKAGES, "revision": REVISION, "year_file": None},
        {
            "packages": {"policyengine-uk": "1.0"},
            "revision": REVISION,
            "year_file": None,
        },
        {
            "packages": PACKAGES,
            "revision": REVISION,
            "year_file": {
                "packages": {},
                "revision": 1,
                "source": {"uri": "u"},
                "year": 1,
            },
        },
        ("text", "not json"),
        ("group", None),
    ],
)
def test_a_file_without_tables_is_checked_as_one_with_them(tmp_path, stamp, data_year):
    """The property tests' files hold no tables (see ``_write_stamps``)."""
    full = _write_output(tmp_path / "full.h5", stamp=stamp, data_year=data_year)
    light = _write_stamps(tmp_path / "light.h5", stamp=stamp, data_year=data_year)

    for dataset_stamp in (None, _current_year_stamp()):
        assert output_stamp_problem(light, dataset_stamp) == output_stamp_problem(
            full, dataset_stamp
        )
    assert light.stat().st_size < full.stat().st_size / 10
    year_file = _write_year_file(tmp_path / "year.h5", stamp)
    light_year_file = _write_stamps(tmp_path / "light_year.h5", year_file_stamp=stamp)
    assert year_file_stamp_metadata(light_year_file) == year_file_stamp_metadata(
        year_file
    )
    assert year_file_stamp_problem(
        light_year_file, IDENTITY, YEAR
    ) == year_file_stamp_problem(year_file, IDENTITY, YEAR)


def test_outputs_without_a_stamp_or_data_year_are_out_of_date_with_distinct_reasons(
    tmp_path,
):
    no_data_year = _write_output(tmp_path / "a.h5", data_year=False)
    stamped = _write_output(tmp_path / "b.h5", stamp=_stamp(), data_year=False)
    unstamped = _write_output(tmp_path / "c.h5")

    assert output_stamp_problem(no_data_year, None) == OUTPUT_WITHOUT_DATA_YEAR
    assert output_stamp_problem(stamped, None) == STAMPED_OUTPUT_WITHOUT_DATA_YEAR
    assert output_stamp_problem(unstamped, None) == UNSTAMPED_OUTPUT
    reasons = {
        OUTPUT_WITHOUT_DATA_YEAR,
        STAMPED_OUTPUT_WITHOUT_DATA_YEAR,
        UNSTAMPED_OUTPUT,
        MALFORMED_OUTPUT_STAMP,
        MALFORMED_OUTPUT_YEAR_FILE,
    }
    assert len(reasons) == 5
    # The wording the data-year refusal has always matched.
    assert "records none" in OUTPUT_WITHOUT_DATA_YEAR


@pytest.mark.parametrize(
    "stamp",
    [
        None,
        [],
        "stamp",
        {},
        {"revision": REVISION},
        {"revision": REVISION, "year_file": None},
        {"packages": PACKAGES, "revision": REVISION},
        {"packages": PACKAGES, "year_file": None},
        {"packages": PACKAGES, "revision": REVISION, "year_file": None, "extra": 1},
        {"packages": PACKAGES, "revision": True, "year_file": None},
        {"packages": PACKAGES, "revision": 1.0, "year_file": None},
        {"packages": PACKAGES, "revision": "1", "year_file": None},
        {"packages": None, "revision": REVISION, "year_file": None},
        {"packages": [], "revision": REVISION, "year_file": None},
        {"packages": {"policyengine-uk": 2}, "revision": REVISION, "year_file": None},
        ("text", "not json"),
        ("number", 3),
        ("group", None),
    ],
)
def test_a_malformed_stamp_is_out_of_date(tmp_path, stamp):
    path = _write_output(tmp_path / "output.h5", stamp=stamp)

    assert output_stamp_problem(path, None) == MALFORMED_OUTPUT_STAMP


@pytest.mark.parametrize("revision", [0, 2, -1])
def test_an_output_from_another_format_revision_is_out_of_date(tmp_path, revision):
    # Even without a data year: a later revision may record it differently.
    path = _write_output(
        tmp_path / "output.h5",
        stamp={"revision": revision, "shape": "of another revision"},
        data_year=False,
    )

    assert output_stamp_problem(path, None) == (
        f"it was saved with output format revision {revision}, and this version "
        f"of policyengine.py reads only revision {REVISION}"
    )


def test_raising_the_output_revision_makes_older_outputs_out_of_date(
    tmp_path, monkeypatch
):
    path = _write_output(tmp_path / "output.h5", stamp=_stamp())
    assert output_stamp_problem(path, None) is None

    monkeypatch.setattr(uk_datasets, "OUTPUT_STAMP_REVISION", REVISION + 1)

    assert output_stamp_problem(path, None) == (
        f"it was saved with output format revision {REVISION}, and this version "
        f"of policyengine.py reads only revision {REVISION + 1}"
    )


def test_an_outputs_year_file_need_not_be_this_releases(tmp_path, monkeypatch):
    """Whether a year file is current is ``load_datasets``' check: an output
    calculated from a year file cut with other versions, or another year-file
    format revision, is what a run of that year file would save now."""
    old = _year_stamp(
        revision=YEAR_FILE_REVISION + 1,
        packages={**PACKAGES, "policyengine-uk": "2.126.11"},
    )
    path = _write_output(tmp_path / "output.h5", stamp=_stamp(old))

    assert year_file_stamp(IDENTITY, YEAR) != old
    assert output_stamp_problem(path, old) is None
    monkeypatch.setattr(uk_datasets, "YEAR_FILE_STAMP_REVISION", YEAR_FILE_REVISION + 5)
    assert output_stamp_problem(path, old) is None


# --- Named differences --------------------------------------------------


def _cut_with(packages, name):
    if name not in packages:
        return f"without a recorded {name} version"
    if packages[name] is None:
        return f"without {name} installed"
    return f"with {name} {packages[name]}"


def _year_file_clauses(recorded, current) -> list[str]:
    """Each difference between two well-formed year-file stamps, in order."""
    expected = []
    if recorded["year"] != current["year"]:
        expected.append(
            f"it was calculated from the year file for {recorded['year']}, and "
            f"the simulation's dataset is the one for {current['year']}"
        )
    if recorded["revision"] != current["revision"]:
        expected.append(
            "it was calculated from a year file of year-file format revision "
            f"{recorded['revision']}, and the simulation's dataset is of "
            f"revision {current['revision']}"
        )
    if recorded["source"] != current["source"]:
        expected.append(
            "it was calculated from a year file cut from "
            f"{describe_dataset_source_identity(recorded['source'])}, and the "
            "simulation's dataset was cut from "
            f"{describe_dataset_source_identity(current['source'])}"
        )
    for name in sorted(recorded["packages"].keys() | current["packages"].keys()):
        if _cut_with(recorded["packages"], name) != _cut_with(
            current["packages"], name
        ):
            expected.append(
                f"it was calculated from a year file cut "
                f"{_cut_with(recorded['packages'], name)}, and the simulation's "
                f"dataset was cut {_cut_with(current['packages'], name)}"
            )
    return expected


def _package_clauses(calculated_with, installed) -> list[str]:
    """Each package version an output was calculated with that is not the one
    installed, in name order."""
    expected = []
    for name in sorted(calculated_with.keys() | installed.keys()):
        if name not in installed:
            expected.append(
                f"it records the {name} version it was calculated with, which "
                "this version of policyengine.py does not check"
            )
        elif calculated_with.get(name, _ABSENT) != installed[name]:
            with_version = (
                f"{name} {calculated_with[name]}"
                if calculated_with.get(name) is not None
                else f"no recorded {name} version"
            )
            now = (
                f"{name} {installed[name]} is installed"
                if installed[name] is not None
                else f"{name} is not installed"
            )
            expected.append(f"it was calculated with {with_version}, and {now}")
    return expected


@settings(max_examples=300, deadline=None)
@given(
    recorded=YEAR_FILE_STAMPS,
    current=YEAR_FILE_STAMPS,
    calculated_with=PACKAGE_MAPS,
    installed=PACKAGE_MAPS,
)
def test_a_stale_output_names_each_difference(
    recorded, current, calculated_with, installed
):
    with tempfile.TemporaryDirectory() as directory:
        path = _write_stamps(
            Path(directory) / "output.h5", stamp=_stamp(recorded, calculated_with)
        )
        problem = output_stamp_problem(path, current, installed)

    expected = _year_file_clauses(recorded, current) + _package_clauses(
        calculated_with, installed
    )
    assert (problem.split("; ") if problem else []) == expected
    assert (problem is None) == (recorded == current and calculated_with == installed)


@settings(max_examples=200, deadline=None)
@given(stamped=PACKAGE_MAPS, packages=PACKAGE_MAPS)
def test_package_differences_name_what_was_done_with_them(stamped, packages):
    """The shared clauses, for a year file ("cut") and an output
    ("calculated"), differ only in that word."""
    calculated = package_differences(stamped, packages, "calculated")

    assert calculated == _package_clauses(stamped, packages)
    assert package_differences(stamped, packages) == [
        clause.replace("calculated with", "cut with") for clause in calculated
    ]
    assert (calculated == []) == (dict(stamped) == dict(packages))


@pytest.mark.parametrize(
    "recorded, current, reason",
    [
        (
            None,
            _year_stamp(),
            "it was calculated from data that kept no year-file stamp, and the "
            "simulation's dataset keeps one",
        ),
        (
            _year_stamp(),
            None,
            "it was calculated from a year file, and the simulation's dataset "
            "keeps no year-file stamp",
        ),
        (
            _year_stamp(),
            UNREADABLE_YEAR_FILE_STAMP,
            "it was calculated from another year file, or another cut of it, "
            "than the simulation's dataset was read from",
        ),
        (
            {**_year_stamp(), "year": True},
            _year_stamp(),
            "it was calculated from another year file, or another cut of it, "
            "than the simulation's dataset was read from",
        ),
        (
            UNREADABLE_YEAR_FILE_STAMP,
            UNREADABLE_YEAR_FILE_STAMP,
            MALFORMED_OUTPUT_YEAR_FILE,
        ),
        (
            {**_year_stamp(), "year": 2026.0},
            {**_year_stamp(), "year": 2026.0},
            MALFORMED_OUTPUT_YEAR_FILE,
        ),
    ],
)
def test_outputs_from_other_or_unreadable_year_files_are_out_of_date(
    tmp_path, recorded, current, reason
):
    path = _write_output(tmp_path / "output.h5", stamp=_stamp(recorded))

    assert output_stamp_problem(path, current) == reason
    assert MALFORMED_OUTPUT_YEAR_FILE == (
        "it was calculated from a year file whose stamp is unreadable or malformed"
    )


def test_a_stamp_equal_in_python_but_not_in_json_is_not_current(tmp_path):
    # JSON ``true`` loads as ``True``, which equals 1: neither stamp may pass
    # for the other.
    stamp = _current_year_stamp()
    tampered = {**stamp, "revision": True}
    assert tampered == stamp

    for recorded, current in ((stamp, tampered), (tampered, stamp)):
        path = _write_output(tmp_path / "output.h5", stamp=_stamp(recorded))
        assert output_stamp_problem(path, current) == MALFORMED_OUTPUT_YEAR_FILE


def test_an_output_from_another_source_names_both(tmp_path):
    old = _year_stamp(source={"uri": f"{SOURCE}@1.57.0", "sha256": "a" * 64})
    new = _year_stamp(source={"uri": f"{SOURCE}@1.58.0", "sha256": "b" * 64})
    path = _write_output(tmp_path / "output.h5", stamp=_stamp(old))

    assert output_stamp_problem(path, new) == (
        f"it was calculated from a year file cut from {SOURCE}@1.57.0 (sha256 "
        f"{'a' * 64}), and the simulation's dataset was cut from "
        f"{SOURCE}@1.58.0 (sha256 {'b' * 64})"
    )


def test_an_output_calculated_with_another_policyengine_uk_names_both(tmp_path):
    """After an upgrade, before and after the year file is cut again."""
    before = {**PACKAGES, "policyengine-uk": "2.126.11"}
    old = _year_stamp(packages=before)
    path = _write_output(tmp_path / "output.h5", stamp=_stamp(old, before))

    # Before the year file is cut again: the versions that calculated the
    # output are not the ones installed.
    assert output_stamp_problem(path, old) == (
        "it was calculated with policyengine-uk 2.126.11, and policyengine-uk "
        "2.126.12 is installed"
    )
    # After: the simulation's dataset is the new cut, too.
    assert output_stamp_problem(path, _current_year_stamp()) == (
        "it was calculated from a year file cut with policyengine-uk 2.126.11, "
        "and the simulation's dataset was cut with policyengine-uk 2.126.12; it "
        "was calculated with policyengine-uk 2.126.11, and policyengine-uk "
        "2.126.12 is installed"
    )


def test_an_output_records_the_versions_that_calculated_it_not_its_year_files(
    tmp_path,
):
    """A year file cut with one policyengine-uk and run with another: the
    output is that other version's, whatever the year file's stamp says."""
    cut_with = {**PACKAGES, "policyengine-uk": "2.126.11"}
    year_file = _year_stamp(packages=cut_with)
    # Calculated under the installed versions, from the old cut.
    path = _write_output(tmp_path / "output.h5", stamp=_stamp(year_file, PACKAGES))

    assert output_stamp_problem(path, year_file) is None
    # With the year file's versions installed again, it is not their output.
    assert output_stamp_problem(path, year_file, cut_with) == (
        "it was calculated with policyengine-uk 2.126.12, and policyengine-uk "
        "2.126.11 is installed"
    )


def test_an_output_from_data_built_in_memory_is_out_of_date_after_an_upgrade(
    tmp_path,
):
    path = _write_output(tmp_path / "output.h5", stamp=_stamp(None))

    assert output_stamp_problem(path, None) is None
    assert output_stamp_problem(
        path, None, {**PACKAGES, "policyengine-core": "3.34.0"}
    ) == (
        "it was calculated with policyengine-core 3.33.0, and policyengine-core "
        "3.34.0 is installed"
    )


def test_explicit_packages_override_the_installed_ones_in_the_check(tmp_path):
    other = {"policyengine-core": "9.0.0", "policyengine-uk": "9.0.0"}
    path = _write_output(tmp_path / "output.h5", stamp=_stamp(None, other))

    assert output_stamp_problem(path, None, other) is None
    assert output_stamp_problem(path, None) is not None
    assert output_stamp_problem(path, None, PACKAGES) == output_stamp_problem(
        path, None
    )


@pytest.mark.parametrize(
    "recorded, current, cut, dataset_cut",
    [
        (
            {"policyengine-uk": "1.0"},
            {"policyengine-uk": "1.1"},
            "with policyengine-uk 1.0",
            "with policyengine-uk 1.1",
        ),
        (
            {"policyengine-uk": None},
            {"policyengine-uk": "1.1"},
            "without policyengine-uk installed",
            "with policyengine-uk 1.1",
        ),
        (
            {},
            {"policyengine-uk": None},
            "without a recorded policyengine-uk version",
            "without policyengine-uk installed",
        ),
        (
            {"policyengine-uk": "1.0"},
            {},
            "with policyengine-uk 1.0",
            "without a recorded policyengine-uk version",
        ),
    ],
)
def test_a_version_the_year_file_lacked_or_did_not_record_is_named(
    tmp_path, recorded, current, cut, dataset_cut
):
    path = _write_output(
        tmp_path / "output.h5", stamp=_stamp(_year_stamp(packages=recorded))
    )

    assert output_stamp_problem(path, _year_stamp(packages=current)) == (
        f"it was calculated from a year file cut {cut}, and the simulation's "
        f"dataset was cut {dataset_cut}"
    )


@pytest.mark.parametrize(
    "calculated_with, installed, reason",
    [
        (
            {"policyengine-uk": "1.0"},
            {"policyengine-uk": "1.1"},
            "it was calculated with policyengine-uk 1.0, and policyengine-uk 1.1 "
            "is installed",
        ),
        (
            {"policyengine-uk": None},
            {"policyengine-uk": "1.1"},
            "it was calculated with no recorded policyengine-uk version, and "
            "policyengine-uk 1.1 is installed",
        ),
        (
            {"policyengine-uk": "1.0"},
            {"policyengine-uk": None},
            "it was calculated with policyengine-uk 1.0, and policyengine-uk is "
            "not installed",
        ),
        (
            {"policyengine-uk": "1.0", "extra": "2"},
            {"policyengine-uk": "1.0"},
            "it records the extra version it was calculated with, which this "
            "version of policyengine.py does not check",
        ),
        (
            {},
            {"policyengine-uk": "1.1"},
            "it was calculated with no recorded policyengine-uk version, and "
            "policyengine-uk 1.1 is installed",
        ),
    ],
)
def test_a_version_the_output_was_calculated_with_is_named(
    tmp_path, calculated_with, installed, reason
):
    path = _write_output(tmp_path / "output.h5", stamp=_stamp(None, calculated_with))

    assert output_stamp_problem(path, None, installed) == reason


def test_an_output_of_another_year_names_both(tmp_path):
    path = _write_output(
        tmp_path / "output.h5", stamp=_stamp(_current_year_stamp(YEAR))
    )

    assert output_stamp_problem(path, _current_year_stamp(YEAR + 1)) == (
        f"it was calculated from the year file for {YEAR}, and the simulation's "
        f"dataset is the one for {YEAR + 1}"
    )


# --- Partial and foreign files -------------------------------------------


@functools.cache
def _current_output_bytes() -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        path = _write_stamps(
            Path(directory) / "output.h5", stamp=_stamp(_current_year_stamp())
        )
        assert output_stamp_problem(path, _current_year_stamp()) is None
        return path.read_bytes()


@settings(max_examples=100, deadline=None)
@given(data=st.data())
def test_a_truncated_output_is_never_current(data):
    content = _current_output_bytes()
    length = data.draw(st.integers(0, len(content) - 1))
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "output.h5"
        path.write_bytes(content[:length])

        assert output_stamp_problem(path, _current_year_stamp()) is not None


def test_a_file_that_is_not_hdf5_is_out_of_date(tmp_path):
    path = tmp_path / "output.h5"
    path.write_text("not an H5 file")

    assert output_stamp_problem(path, None) == NOT_HDF5


def test_saving_the_tables_again_drops_the_stamp(tmp_path):
    path = _write_output(tmp_path / "output.h5", stamp=_stamp())

    PolicyEngineUKDataset(
        name="output",
        description="reload",
        filepath=str(path),
        year=YEAR,
        is_output_dataset=True,
    ).save()

    assert read_output_stamp(path) is None
    assert output_stamp_problem(path, None) == UNSTAMPED_OUTPUT


def test_a_dangling_link_in_place_of_the_stamp_reads_as_absent(tmp_path):
    path = _write_output(tmp_path / "output.h5")
    with h5py.File(path, "a") as file:
        file[OUTPUT_STAMP_H5_DATASET] = h5py.SoftLink("/nowhere")

    assert output_stamp_problem(path, None) == UNSTAMPED_OUTPUT


def test_a_stamp_link_that_leads_back_to_itself_is_unreadable(tmp_path):
    path = _write_output(tmp_path / "output.h5")
    with h5py.File(path, "a") as file:
        _link_cycle(file, OUTPUT_STAMP_H5_DATASET)

    assert output_stamp_problem(path, None) == MALFORMED_OUTPUT_STAMP


def test_json_nested_too_deeply_is_out_of_date_not_an_error(tmp_path):
    path = _write_output(
        tmp_path / "output.h5", stamp=("text", "[" * 100_000 + "0" + "]" * 100_000)
    )

    assert output_stamp_problem(path, None) == MALFORMED_OUTPUT_STAMP


# --- Distinct stamps ----------------------------------------------------


def test_the_stamps_have_distinct_names_and_keys():
    names = {
        OUTPUT_STAMP_H5_DATASET,
        YEAR_FILE_STAMP_H5_DATASET,
        US_OUTPUT_STAMP_H5_DATASET,
    }
    assert len(names) == 3
    assert set(output_stamp()) != set(_current_year_stamp())
    # The US output stamp records a register of renamed inputs.
    assert set(output_stamp()) != {"register", "revision", "year_file"}


@settings(max_examples=100, deadline=None)
@given(year_file=st.one_of(st.none(), YEAR_FILE_STAMPS))
def test_an_output_never_passes_as_a_year_file_nor_the_reverse(year_file):
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        # An output stamped as current carries no year-file stamp.
        output = _write_stamps(directory / "output.h5", stamp=_stamp(year_file))
        assert output_stamp_problem(output, year_file) is None
        assert read_year_file_stamp(output) is None
        assert year_file_stamp_metadata(output) is None
        assert year_file_stamp_problem(output, IDENTITY, YEAR) is not None

        # A current year file carries no output stamp.
        year = _write_stamps(
            directory / "year.h5", year_file_stamp=_current_year_stamp()
        )
        assert year_file_stamp_problem(year, IDENTITY, YEAR) is None
        assert read_output_stamp(year) is None
        assert output_stamp_problem(year, _current_year_stamp()) == UNSTAMPED_OUTPUT

        # Nor does a US output stamp pass as a UK one.
        us_output = _write_stamps(directory / "us.h5")
        with h5py.File(us_output, "a") as file:
            _write_node(file, US_OUTPUT_STAMP_H5_DATASET, _stamp(year_file))
        assert output_stamp_problem(us_output, year_file) == UNSTAMPED_OUTPUT


# --- Errors unrelated to the file's contents ----------------------------


def test_a_missing_output_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        output_stamp_problem(tmp_path / "missing.h5", None)
    with pytest.raises(FileNotFoundError):
        year_file_stamp_metadata(tmp_path / "missing.h5")


def _unreadable_by_permission(path) -> Path:
    path = _write_output(path, stamp=_stamp())
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
@pytest.mark.parametrize(
    "check",
    [lambda path: output_stamp_problem(path, None), year_file_stamp_metadata],
)
def test_errors_unrelated_to_the_contents_are_raised(tmp_path, make, error, check):
    if error is PermissionError and hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root can read a file without permission bits")
    path = make(tmp_path / "output.h5")
    try:
        with pytest.raises(error):
            check(path)
    finally:
        if path.is_file():
            os.chmod(path, 0o644)


ERRORS = [
    PermissionError(13, "Permission denied"),
    IsADirectoryError(21, "Is a directory"),
    BlockingIOError(35, "Unable to lock file"),
]


@pytest.mark.parametrize("error", ERRORS)
@pytest.mark.parametrize(
    "check",
    [lambda path: output_stamp_problem(path, None), year_file_stamp_metadata],
)
def test_errors_unrelated_to_the_contents_are_raised_on_opening(
    tmp_path, monkeypatch, error, check
):
    path = _write_output(tmp_path / "output.h5", stamp=_stamp())

    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(h5py, "File", fail)
    with pytest.raises(type(error)):
        check(path)


@pytest.mark.parametrize("error", ERRORS)
def test_errors_unrelated_to_the_contents_are_raised_while_reading(
    tmp_path, monkeypatch, error
):
    path = _write_output(
        tmp_path / "output.h5",
        stamp=_stamp(),
        year_file_stamp=_current_year_stamp(),
    )

    def fail(self, *args, **kwargs):
        raise error

    monkeypatch.setattr(h5py.Dataset, "asstr", fail)
    with pytest.raises(type(error)):
        output_stamp_problem(path, None)
    with pytest.raises(type(error)):
        year_file_stamp_metadata(path)


@pytest.mark.parametrize("error", ERRORS)
def test_errors_unrelated_to_the_contents_are_raised_while_finding_the_data_year(
    tmp_path, monkeypatch, error
):
    path = _write_output(tmp_path / "output.h5", stamp=_stamp())
    get = h5py.Group.get

    def fail_for_the_data_year(self, name, *args, **kwargs):
        if name == DATA_YEAR_KEY:
            raise error
        return get(self, name, *args, **kwargs)

    monkeypatch.setattr(h5py.Group, "get", fail_for_the_data_year)
    with pytest.raises(type(error)):
        output_stamp_problem(path, None)


def test_the_decision_reads_only_the_stamp_and_the_data_year(tmp_path, monkeypatch):
    path = _write_output(tmp_path / "output.h5", stamp=_stamp(_current_year_stamp()))
    read = []
    get = h5py.Group.get

    def recording_get(self, name, *args, **kwargs):
        read.append(name)
        return get(self, name, *args, **kwargs)

    def no_tables(*args, **kwargs):
        raise AssertionError("the tables were opened")

    monkeypatch.setattr(h5py.Group, "get", recording_get)
    monkeypatch.setattr(pd, "HDFStore", no_tables)
    monkeypatch.setattr(pd, "read_hdf", no_tables)

    assert output_stamp_problem(path, _current_year_stamp()) is None
    assert set(read) == {OUTPUT_STAMP_H5_DATASET, DATA_YEAR_KEY}


# --- The year-file stamp a dataset keeps --------------------------------


def _load(path) -> PolicyEngineUKDataset:
    return PolicyEngineUKDataset(
        name="year-file", description="load", filepath=str(path), year=YEAR
    )


@pytest.mark.parametrize(
    "stored, kept",
    [
        (_ABSENT, None),
        (_year_stamp(), _year_stamp()),
        ({"any": "json"}, {"any": "json"}),
        (None, UNREADABLE_YEAR_FILE_STAMP),
        (("text", "not json"), UNREADABLE_YEAR_FILE_STAMP),
        (("number", 3), UNREADABLE_YEAR_FILE_STAMP),
        (("group", None), UNREADABLE_YEAR_FILE_STAMP),
    ],
)
def test_a_dataset_keeps_its_year_files_stamp(tmp_path, stored, kept):
    path = _write_year_file(tmp_path / "year.h5", stored)

    assert year_file_stamp_metadata(path) == kept
    dataset = _load(path)
    assert dataset.metadata.get(YEAR_FILE_STAMP_KEY) == kept
    assert (YEAR_FILE_STAMP_KEY in dataset.metadata) == (kept is not None)
    assert input_year_file_stamp(dataset) == kept


def test_a_file_that_is_not_hdf5_keeps_no_year_file_stamp(tmp_path):
    path = tmp_path / "year.h5"
    path.write_text("not an H5 file")

    assert year_file_stamp_metadata(path) is None


def test_reloading_a_resaved_year_file_drops_the_stamp_it_kept(tmp_path):
    path = _write_year_file(tmp_path / "year.h5", _current_year_stamp())
    dataset = _load(path)
    assert dataset.metadata[YEAR_FILE_STAMP_KEY] == _current_year_stamp()

    dataset.save()
    # Saving writes no stamp, so the file no longer holds the cut it named.
    dataset.load()

    assert YEAR_FILE_STAMP_KEY not in dataset.metadata
    assert input_year_file_stamp(dataset) is None


def test_a_dataset_built_in_memory_keeps_no_year_file_stamp():
    dataset = PolicyEngineUKDataset(
        name="memory", description="memory", year=YEAR, data=_tables()
    )

    assert dataset.metadata == {}
    assert input_year_file_stamp(dataset) is None


def test_loading_a_dataset_with_no_filepath_is_refused():
    dataset = PolicyEngineUKDataset(
        name="memory", description="memory", year=YEAR, data=_tables()
    )

    with pytest.raises(ValueError, match="no filepath"):
        dataset.load()


def test_a_dataset_whose_tables_are_not_loaded_gives_its_files_stamp(tmp_path):
    path = _write_year_file(tmp_path / "year.h5", _current_year_stamp())
    dataset = _load(path)
    # A run loads a dataset whose tables are not loaded, so the stamp it
    # records is the one the file holds, not one kept from before.
    dataset.data = None
    dataset.metadata[YEAR_FILE_STAMP_KEY] = "kept from before"

    assert input_year_file_stamp(dataset) == _current_year_stamp()


def test_a_loaded_dataset_keeps_the_stamp_of_the_tables_it_holds(tmp_path):
    """A year file cut again after it was loaded: the dataset still holds the
    old cut's tables, so a run of it records the old cut's stamp."""
    path, replacement, old, new = _two_cuts(tmp_path)
    dataset = _load(path)

    os.replace(replacement, path)

    assert year_file_stamp_metadata(path) == new
    assert pd.DataFrame(dataset.data.person)["age"].iloc[0] == 70
    assert input_year_file_stamp(dataset) == old
    dataset.load()
    assert pd.DataFrame(dataset.data.person)["age"].iloc[0] == 99
    assert input_year_file_stamp(dataset) == new


def test_the_stamp_a_run_records_is_a_copy(tmp_path):
    path = _write_year_file(tmp_path / "year.h5", _current_year_stamp())
    dataset = _load(path)

    stamp = input_year_file_stamp(dataset)
    stamp["year"] = 0
    stamp["source"]["uri"] = "changed"
    stamp["packages"]["policyengine-uk"] = "changed"

    assert dataset.metadata[YEAR_FILE_STAMP_KEY] == _current_year_stamp()


def test_the_metadata_a_dataset_keeps_survives_a_json_round_trip():
    dataset = PolicyEngineUKDataset(
        name="memory",
        description="memory",
        year=YEAR,
        metadata={
            YEAR_FILE_STAMP_KEY: _current_year_stamp(),
            OUTPUT_STAMP_KEY: _stamp(_current_year_stamp()),
        },
    )

    restored = PolicyEngineUKDataset.model_validate_json(dataset.model_dump_json())

    assert restored.metadata == dataset.metadata
    assert dataset.model_dump(mode="json")["metadata"] == dataset.metadata


def test_the_metadata_keys_are_the_documented_ones():
    assert OUTPUT_STAMP_KEY == "output_stamp"
    assert YEAR_FILE_STAMP_KEY == "year_file_stamp"
    assert OUTPUT_STAMP_H5_DATASET == "policyengine_uk_output_stamp"


# --- One save per output ------------------------------------------------


def _partial_files(folder: Path) -> list[Path]:
    """Temporary files left in a folder."""
    return sorted(folder.glob(".*.partial"))


def test_saving_an_output_writes_its_tables_and_stamp(tmp_path):
    path = tmp_path / "data" / "output.h5"
    stamp = _stamp(_current_year_stamp())

    save_output(_output_dataset(path, age=41), stamp)

    assert output_stamp_problem(path, _current_year_stamp()) is None
    assert read_output_stamp(path) == stamp
    assert _age(path) == 41
    assert _partial_files(path.parent) == []


def test_saving_an_output_with_no_filepath_is_refused():
    dataset = PolicyEngineUKDataset(
        name="memory",
        description="memory",
        year=YEAR,
        is_output_dataset=True,
        data=_tables(),
        data_year=DATA_YEAR,
    )

    with pytest.raises(ValueError, match="no filepath"):
        save_output(dataset, _stamp())


@pytest.mark.parametrize("stop", ["in the tables", "at the stamp", "at the move"])
def test_a_save_that_fails_leaves_the_output_already_there_whole(tmp_path, stop):
    path = tmp_path / "output.h5"
    save_output(_output_dataset(path, age=41), _stamp(_current_year_stamp()))
    before = path.read_bytes()

    def stopped(*args, **kwargs):
        raise RuntimeError("stopped part-way")

    with pytest.MonkeyPatch.context() as patcher:
        if stop == "in the tables":
            put = pd.HDFStore.put

            def put_until_household(self, key, value, *args, **kwargs):
                if key == "household":
                    raise RuntimeError("stopped part-way")
                return put(self, key, value, *args, **kwargs)

            patcher.setattr(pd.HDFStore, "put", put_until_household)
        elif stop == "at the stamp":
            patcher.setattr(shared_stamp, "write_json_dataset", stopped)
        else:
            patcher.setattr(shared_stamp.os, "replace", stopped)
        with pytest.raises(RuntimeError, match="stopped part-way"):
            save_output(_output_dataset(path, age=99), _stamp(None))

    assert path.read_bytes() == before
    assert output_stamp_problem(path, _current_year_stamp()) is None
    assert _age(path) == 41
    assert _partial_files(tmp_path) == []


def test_a_first_save_that_fails_leaves_no_output(tmp_path, monkeypatch):
    path = tmp_path / "output.h5"

    def stopped(*args, **kwargs):
        raise RuntimeError("stopped part-way")

    monkeypatch.setattr(shared_stamp, "write_json_dataset", stopped)
    with pytest.raises(RuntimeError, match="stopped part-way"):
        save_output(_output_dataset(path), _stamp())

    assert not path.exists()
    assert _partial_files(tmp_path) == []


def test_two_saves_to_one_path_never_mix_ones_tables_with_the_others_stamp(
    tmp_path, monkeypatch
):
    """Another process saves a whole output to the path between this save's
    tables and its stamp. Whichever save's file is at the path, its tables
    and its stamp are that save's."""
    path = tmp_path / "output.h5"
    one = _stamp(_year_stamp(source={"uri": f"{SOURCE}@1"}))
    other = _stamp(_year_stamp(source={"uri": f"{SOURCE}@2"}))
    publish = uk_datasets.publish_year_file
    seen = []

    def publish_after_the_other_save(temporary, target, name, stamp):
        if not seen:
            seen.append("other")
            # The other save runs to completion before this one stamps.
            save_output(_output_dataset(path, age=99), other)
            assert (read_output_stamp(path), _age(path)) == (other, 99)
        return publish(temporary, target, name, stamp)

    monkeypatch.setattr(uk_datasets, "publish_year_file", publish_after_the_other_save)
    save_output(_output_dataset(path, age=41), one)

    assert seen == ["other"]
    assert (read_output_stamp(path), _age(path)) == (one, 41)
    assert _partial_files(tmp_path) == []


def test_an_output_is_saved_where_its_filepath_says(tmp_path):
    dataset = _output_dataset(tmp_path / "first.h5")
    dataset.filepath = str(tmp_path / "moved" / "second.h5")

    save_output(dataset, _stamp())

    assert not (tmp_path / "first.h5").exists()
    assert output_stamp_problem(tmp_path / "moved" / "second.h5", None) is None


# --- One file per load --------------------------------------------------


def _two_cuts(directory: Path):
    """A year file at ``directory/year.h5`` and another cut of it beside it,
    with other tables (the first person's age) and another stamp."""
    old = _year_stamp(source={"uri": f"{SOURCE}@1", "sha256": "a" * 64})
    new = _year_stamp(source={"uri": f"{SOURCE}@2", "sha256": "b" * 64})
    path = _write_year_file(directory / "year.h5", old, age=70)
    replacement = _write_year_file(directory / "next.h5", new, age=99)
    return path, replacement, old, new


class _DuringTheRead:
    """Stand in for ``pd.HDFStore``, calling ``before`` as the tables are
    opened and ``after`` as they are closed, as another process acting at
    those moments would: on the first open only, or on every open."""

    def __init__(self, before=None, after=None, every_time=False):
        self.before, self.after, self.every_time = before, after, every_time
        self.store = pd.HDFStore
        self.opened = 0

    def __call__(self, *args, **kwargs):
        acting = self.opened == 0 or self.every_time
        self.opened += 1
        outer = self

        class Store:
            def __init__(self):
                if outer.before and acting:
                    outer.before()
                self.store = outer.store(*args, **kwargs)

            def __enter__(self):
                return self.store.__enter__()

            def __exit__(self, *exc):
                result = self.store.__exit__(*exc)
                if outer.after and acting:
                    outer.after()
                return result

        return Store()


@pytest.mark.parametrize("when", ["before", "after"])
def test_a_year_file_replaced_while_it_is_read_is_read_again(
    tmp_path, monkeypatch, when
):
    """The dataset keeps the stamp of the cut its tables came from."""
    path, replacement, _, new = _two_cuts(tmp_path)
    stores = _DuringTheRead(**{when: lambda: os.replace(replacement, path)})

    monkeypatch.setattr(pd, "HDFStore", stores)
    dataset = _load(path)

    assert stores.opened == 2
    assert dataset.metadata[YEAR_FILE_STAMP_KEY] == new
    assert pd.DataFrame(dataset.data.person)["age"].iloc[0] == 99
    assert pd.DataFrame(dataset.data_year_data.person)["age"].iloc[0] == 99


def test_a_year_file_replaced_and_put_back_while_it_is_read_is_read_again(
    tmp_path, monkeypatch
):
    """Another cut is moved onto the path after the stamp is read, its tables
    are read, and a copy of the first cut is moved back before the read ends.
    The stamp at the path is the same before and after, yet the tables read
    are the other cut's: the file put back is another file, so the read is
    done again."""
    path, replacement, old, _ = _two_cuts(tmp_path)
    put_back = tmp_path / "back.h5"
    shutil.copy(path, put_back)
    stores = _DuringTheRead(
        before=lambda: os.replace(replacement, path),
        after=lambda: os.replace(put_back, path),
    )

    monkeypatch.setattr(pd, "HDFStore", stores)
    dataset = _load(path)

    assert stores.opened == 2
    assert dataset.metadata[YEAR_FILE_STAMP_KEY] == old
    assert pd.DataFrame(dataset.data.person)["age"].iloc[0] == 70


def test_a_year_file_modified_while_it_is_read_is_read_again(tmp_path, monkeypatch):
    """A writer that rewrites the file in place, as ``save()`` does."""
    path = _write_year_file(tmp_path / "year.h5", _current_year_stamp(), age=70)
    write = PolicyEngineUKDataset._write
    store = pd.HDFStore

    def rewrite():
        # With the real store, so this writer's open is not counted.
        with pytest.MonkeyPatch.context() as patcher:
            patcher.setattr(pd, "HDFStore", store)
            write(_year_dataset(path, age=99), path)
        status = os.stat(path)
        os.utime(path, ns=(status.st_atime_ns, status.st_mtime_ns + 10**9))

    stores = _DuringTheRead(after=rewrite)
    monkeypatch.setattr(pd, "HDFStore", stores)
    dataset = _load(path)

    assert stores.opened == 2
    assert pd.DataFrame(dataset.data.person)["age"].iloc[0] == 99
    # Rewriting the tables wrote no stamp.
    assert YEAR_FILE_STAMP_KEY not in dataset.metadata


def test_a_year_file_replaced_on_every_read_is_refused(tmp_path, monkeypatch):
    path = _write_year_file(tmp_path / "year.h5", _current_year_stamp())
    spare = tmp_path / "spare.h5"

    def replace():
        shutil.copy(path, spare)
        os.replace(spare, path)

    stores = _DuringTheRead(after=replace, every_time=True)
    monkeypatch.setattr(pd, "HDFStore", stores)
    with pytest.raises(
        RuntimeError, match="was replaced or modified while it was read, 3 times"
    ):
        _load(path)
    assert stores.opened == 3


def test_an_unchanged_year_file_is_read_once(tmp_path, monkeypatch):
    path = _write_year_file(tmp_path / "year.h5", _current_year_stamp())
    stores = _DuringTheRead()

    monkeypatch.setattr(pd, "HDFStore", stores)
    dataset = _load(path)

    assert stores.opened == 1
    assert dataset.metadata[YEAR_FILE_STAMP_KEY] == _current_year_stamp()


def test_read_one_file_returns_what_was_read_of_one_unchanged_file(tmp_path):
    path = tmp_path / "file"
    path.write_text("first")
    reads = []

    def read(name):
        reads.append(name)
        return Path(name).read_text()

    assert read_one_file(path, read) == "first"
    assert reads == [str(path)]


def test_read_one_file_reads_again_after_a_replacement_and_gives_up(tmp_path):
    path = tmp_path / "file"
    path.write_text("first")
    reads = []

    def replacing(until):
        def read(name):
            reads.append(Path(name).read_text())
            if len(reads) <= until:
                spare = tmp_path / "spare"
                spare.write_text(f"replacement {len(reads)}")
                os.replace(spare, name)
            return reads[-1]

        return read

    assert read_one_file(path, replacing(1)) == "replacement 1"
    assert reads == ["first", "replacement 1"]

    reads.clear()
    with pytest.raises(RuntimeError, match="2 times"):
        read_one_file(path, replacing(5), attempts=2)
    assert len(reads) == 2


def test_read_one_file_reads_again_after_the_file_is_modified_in_place(tmp_path):
    path = tmp_path / "file"
    path.write_text("first")
    reads = []

    def appending(name):
        reads.append(Path(name).read_text())
        if len(reads) == 1:
            with open(name, "a") as file:
                file.write(" and more")
        return reads[-1]

    assert read_one_file(path, appending) == "first and more"
    assert reads == ["first", "first and more"]

    # Another size, at the same time.
    reads.clear()

    def appending_unseen(name):
        reads.append(Path(name).read_text())
        if len(reads) == 1:
            status = os.stat(name)
            with open(name, "a") as file:
                file.write("!")
            os.utime(name, ns=(status.st_atime_ns, status.st_mtime_ns))
        return reads[-1]

    assert read_one_file(path, appending_unseen) == "first and more!"
    assert len(reads) == 2
    path.write_text("first and more")

    # The same size, at another time.
    reads.clear()

    def touching(name):
        reads.append(Path(name).read_text())
        if len(reads) == 1:
            status = os.stat(name)
            os.utime(name, ns=(status.st_atime_ns, status.st_mtime_ns + 10**9))
        return reads[-1]

    assert read_one_file(path, touching) == "first and more"
    assert len(reads) == 2


def test_read_one_file_finds_no_file_once_it_is_removed_meanwhile(tmp_path):
    path = tmp_path / "file"
    path.write_text("first")

    def removing(name):
        os.unlink(name)
        return "read"

    # The read is not trusted; the second attempt finds no file to read.
    with pytest.raises(FileNotFoundError):
        read_one_file(path, removing)


def test_read_one_file_raises_what_the_read_raises_and_what_opening_does(tmp_path):
    path = tmp_path / "file"
    path.write_text("first")

    def failing(name):
        raise ValueError("refused")

    with pytest.raises(ValueError, match="refused"):
        read_one_file(path, failing)
    with pytest.raises(FileNotFoundError):
        read_one_file(tmp_path / "missing", failing)
    with pytest.raises(IsADirectoryError):
        read_one_file(tmp_path, failing)
