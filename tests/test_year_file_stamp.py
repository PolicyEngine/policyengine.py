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
"""

from __future__ import annotations

import builtins
from importlib import metadata as importlib_metadata
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from policyengine.provenance.year_file_stamp import (
    installed_package_versions,
    is_version_map,
    source_and_package_differences,
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
