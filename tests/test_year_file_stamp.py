"""Property tests for the year-file stamp code the countries share.

``policyengine.provenance.year_file_stamp`` holds what the US and UK
year-file checks have in common. ``test_us_year_file_stamp.py`` and
``test_uk_year_file_stamp.py`` test each country's check through it; these
tests state the shared pieces' own invariants:

- **Reasons are exact.** ``source_and_package_differences`` gives no clause
  exactly when the sources and package maps are equal, one clause when the
  sources differ, and one per package that differs or only one side records.
- **Versions come from metadata.** ``installed_package_versions`` reads each
  named distribution's version, ``None`` when it is not installed, and
  imports nothing.
- **Stems never collide silently.** ``year_file_sources`` refuses two
  requests that would share year files exactly when their stems agree and
  their sources differ, naming the country.
- **Publishing is whole.** A year file written beside its path and published
  replaces the file at the path in one step, with its stamp.
"""

from __future__ import annotations

import builtins
from importlib import metadata as importlib_metadata
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from policyengine.provenance.year_file_stamp import (
    installed_package_versions,
    is_version_map,
    publish_year_file,
    read_stored_json,
    source_and_package_differences,
    temporary_year_file,
    write_json_dataset,
    year_file_sources,
)

SOURCES = st.one_of(
    st.builds(
        lambda uri: {"uri": uri}, st.sampled_from(["hf://o/r/a.h5", "hf://o/r/b.h5"])
    ),
    st.builds(
        lambda sha256: {"uri": "hf://o/r/a.h5@v", "sha256": sha256},
        st.sampled_from(["a" * 64, "b" * 64]),
    ),
    st.builds(
        lambda size: {"path": "/data/a.h5", "size": size, "mtime_ns": 0},
        st.sampled_from([1, 2]),
    ),
)
PACKAGE_MAPS = st.dictionaries(
    st.sampled_from(["policyengine-core", "policyengine-uk", "policyengine-us"]),
    st.one_of(st.none(), st.sampled_from(["1.0", "1.1"])),
    max_size=3,
)


@settings(max_examples=300, deadline=None)
@given(
    source=SOURCES,
    stamped_source=SOURCES,
    packages=PACKAGE_MAPS,
    stamped_packages=PACKAGE_MAPS,
)
def test_differences_are_named_exactly(
    source, stamped_source, packages, stamped_packages
):
    clauses = source_and_package_differences(
        {"source": stamped_source, "packages": stamped_packages},
        {"source": source, "packages": packages},
    )

    differing = {
        name
        for name in stamped_packages.keys() | packages.keys()
        if stamped_packages.get(name, ...) != packages.get(name, ...)
    }
    assert (clauses == []) == (stamped_source == source and not differing)
    assert len(clauses) == (stamped_source != source) + len(differing)
    assert all(clause.startswith("it ") for clause in clauses)
    package_clauses = clauses[1:] if stamped_source != source else clauses
    for name, clause in zip(sorted(differing), package_clauses):
        assert name in clause


def test_installed_package_versions_reads_metadata_without_importing():
    real_import = builtins.__import__

    def refuse_policyengine(name, *args, **kwargs):
        if name.startswith("policyengine_"):
            raise AssertionError(f"imported {name}")
        return real_import(name, *args, **kwargs)

    with patch.object(builtins, "__import__", refuse_policyengine):
        versions = installed_package_versions(
            ["pytest", "policyengine-core", "not-a-distribution-policyengine-test"]
        )

    assert versions == {
        "pytest": importlib_metadata.version("pytest"),
        "policyengine-core": importlib_metadata.version("policyengine-core"),
        "not-a-distribution-policyengine-test": None,
    }
    assert is_version_map(versions)


@pytest.mark.parametrize(
    "value, expected",
    [
        ({}, True),
        ({"a": "1", "b": None}, True),
        ({"a": 1}, False),
        ({1: "1"}, False),
        ([["a", "1"]], False),
        (None, False),
    ],
)
def test_a_version_map_maps_names_to_versions_or_none(value, expected):
    assert is_version_map(value) is expected


#: Requests by stem: ``pop`` from two revisions and two repositories, and one
#: ``other``.
REQUESTS = [
    "hf://fixture/repo/pop.h5@r1",
    "hf://fixture/repo/pop.h5@r2",
    "hf://elsewhere/repo/pop.h5@r1",
    "hf://fixture/repo/other.h5@r1",
]


@settings(max_examples=100, deadline=None)
@given(
    country=st.sampled_from(["us", "uk"]),
    requests=st.lists(st.sampled_from(REQUESTS), min_size=1, max_size=4),
)
def test_year_file_sources_refuse_exactly_the_requests_that_collide(country, requests):
    by_stem = {}
    for request in requests:
        by_stem.setdefault(request.rsplit("/", 1)[-1].split(".")[0], set()).add(request)
    collide = any(len(sources) > 1 for sources in by_stem.values())

    if collide:
        with pytest.raises(
            ValueError, match=f"would share the {country.upper()} year files"
        ):
            year_file_sources(country, requests)
        return
    sources = year_file_sources(country, requests)
    assert sources == [
        (request.rsplit("/", 1)[-1].split(".")[0], {"uri": request})
        for request in requests
    ]


def test_a_temporary_year_file_is_hidden_beside_its_path(tmp_path):
    path = tmp_path / "data" / "pop_year_2026.h5"

    temporary = temporary_year_file(path)

    assert temporary.parent == path.parent
    assert temporary.name.startswith(".pop_year_2026.")
    assert temporary.name.endswith(".partial")
    assert temporary.exists() and temporary.stat().st_size == 0
    assert temporary != temporary_year_file(path)


def test_publishing_moves_a_stamped_file_onto_its_path_in_one_step(tmp_path):
    """The file at the path is replaced whole: its old contents and stamp go
    together, and the new contents arrive with their stamp."""
    import h5py

    path = tmp_path / "pop_year_2026.h5"
    with h5py.File(path, "w") as file:
        file["tables"] = [1]
    write_json_dataset(path, "stamp", {"cut": "old"})
    temporary = temporary_year_file(path)
    with h5py.File(temporary, "w") as file:
        file["tables"] = [2]

    publish_year_file(temporary, path, "stamp", {"cut": "new"})

    assert not temporary.exists()
    assert read_stored_json(path, "stamp") == {"cut": "new"}
    with h5py.File(path, "r") as file:
        assert list(file["tables"][()]) == [2]


def test_stored_json_reads_none_for_absent_or_foreign_files(tmp_path):
    assert read_stored_json(tmp_path / "missing.h5", "stamp") is None
    (tmp_path / "text.h5").write_text("not an H5 file")
    assert read_stored_json(tmp_path / "text.h5", "stamp") is None
    write_json_dataset(tmp_path / "file.h5", "other", {"a": 1})
    assert read_stored_json(tmp_path / "file.h5", "stamp") is None
    assert read_stored_json(tmp_path / "file.h5", "other") == {"a": 1}


def test_publishing_stamps_the_file_before_moving_it(tmp_path, monkeypatch):
    """Stamped first, so a process that moves its own file onto the path in
    between can never leave one cut's tables under another cut's stamp."""
    import os

    path = tmp_path / "pop_year_2026.h5"
    temporary = temporary_year_file(path)
    write_json_dataset(temporary, "tables", [1])
    replace = os.replace
    moved = []

    def replace_after_checking_the_stamp(source, destination):
        assert read_stored_json(source, "stamp") == {"cut": "this"}
        moved.append((Path(source), Path(destination)))
        replace(source, destination)

    monkeypatch.setattr(os, "replace", replace_after_checking_the_stamp)
    publish_year_file(temporary, path, "stamp", {"cut": "this"})

    assert moved == [(temporary, path)]
