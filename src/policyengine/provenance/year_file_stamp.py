"""Stamp year files with what they were cut from and under.

A country's ``create_datasets`` cuts one file per requested year from a
source dataset and names it ``{data_folder}/{stem}_year_{year}.h5``, after
the source's logical name. The name drops any revision, so files cut from
every release of a dataset share names. Each year file is therefore stamped
(:data:`YEAR_FILE_STAMP_H5_DATASET`) with the identity of the source it was
cut from and the versions of the packages that calculated it, and the
country's ``ensure_datasets`` and ``load_datasets`` compare that stamp with
the one a file cut now would carry.

This module holds what the countries share:

- reading and writing a JSON value in an H5 dataset
  (:func:`read_json_dataset`, :func:`write_json_dataset`), and the stamp
  itself (:func:`read_year_file_stamp`, :func:`write_year_file_stamp`);
- the installed versions of the packages a stamp records
  (:func:`installed_package_versions`);
- the clauses naming how a stamp's source and package versions differ from
  the current ones (:func:`source_and_package_differences`);
- each requested dataset's year-file stem and source identity, refusing two
  sources that would share year files (:func:`year_file_sources`).

The US stamp (``tax_benefit_models.us.legacy_inputs``) also records the
register of renamed stored inputs; the UK stamp
(``tax_benefit_models.uk.datasets``) records the source, the packages and its
format revision.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Optional

from .dataset_materialization import (
    describe_dataset_source_identity,
    requested_dataset_source_identity,
)
from .manifest import dataset_logical_name, resolve_dataset_reference

#: H5 dataset stamping a ``create_datasets`` year file, as UTF-8 JSON. Each
#: country gives its own shape (see the module docstring); every shape has a
#: ``"revision"``, the country's year-file format revision, a ``"source"``,
#: the identity of the dataset the file was cut from (see
#: ``dataset_materialization.dataset_source_identity``), and a
#: ``"packages"``, the installed versions of the packages that calculated it.
YEAR_FILE_STAMP_H5_DATASET = "policyengine_year_file_stamp"

#: What :func:`read_json_dataset` returns for a node a file does not have, and
#: for one that is not a scalar dataset holding UTF-8 JSON.
ABSENT = object()
UNREADABLE = object()

#: Errors opening or reading a year file that say nothing about its
#: contents: no permission, a directory at its path, or a lock another
#: process holds. A year-file check raises them rather than reporting the
#: file out of date, since the file could not be written again either.
UNRELATED_TO_CONTENTS = (PermissionError, IsADirectoryError, BlockingIOError)

#: The clause a year-file check gives for a file h5py cannot open.
NOT_HDF5 = "it cannot be read as an HDF5 file (it may be half-written or corrupt)"


def installed_package_versions(names: Iterable[str]) -> dict[str, Optional[str]]:
    """Return the installed version of each named distribution.

    ``None`` stands for a distribution that is not installed. The versions
    come from the installed distributions' metadata, so no package is
    imported.
    """
    versions: dict[str, Optional[str]] = {}
    for name in names:
        try:
            versions[name] = importlib_metadata.version(name)
        except importlib_metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def read_json_dataset(file: Any, name: str) -> Any:
    """Return the JSON value stored in an open H5 file's ``name`` dataset.

    Returns :data:`ABSENT` when the file has no such node, and
    :data:`UNREADABLE` when the node is not a scalar dataset holding UTF-8
    JSON, or cannot be followed. Errors in :data:`UNRELATED_TO_CONTENTS` are
    raised.
    """
    import h5py

    try:
        # A cycle of soft links, or a chain too long to follow, raises
        # RuntimeError here.
        node = file.get(name)
        if node is None:
            return ABSENT
        if not isinstance(node, h5py.Dataset) or node.shape != ():
            return UNREADABLE
        # A numeric dataset raises TypeError; bytes that are not UTF-8, or
        # not JSON, raise ValueError; JSON nested too deeply raises
        # RecursionError, a RuntimeError.
        return json.loads(node.asstr()[()])
    except UNRELATED_TO_CONTENTS:
        raise
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        return UNREADABLE


def write_json_dataset(path: str | Path, name: str, value: Any) -> None:
    """Store ``value`` as UTF-8 JSON in an H5 file's ``name`` dataset."""
    import h5py

    with h5py.File(path, "a") as file:
        if name in file:
            del file[name]
        # UTF-8 JSON in a dataset, as for the SPM receipt of a saved output.
        file.create_dataset(
            name,
            data=json.dumps(value, sort_keys=True),
            dtype=h5py.string_dtype("utf-8"),
        )


def read_year_file_stamp(path: str | Path) -> Any | None:
    """Return the JSON value of a year file's stamp, well formed or not.

    ``None`` means the file stores no readable stamp (see
    :data:`YEAR_FILE_STAMP_H5_DATASET`) or is not an H5 file.
    """
    import h5py

    try:
        with h5py.File(path, "r") as file:
            stamp = read_json_dataset(file, YEAR_FILE_STAMP_H5_DATASET)
    except OSError:
        return None
    return None if stamp is ABSENT or stamp is UNREADABLE else stamp


def write_year_file_stamp(path: str | Path, stamp: Mapping[str, Any]) -> None:
    """Stamp a year file, replacing any stamp it has."""
    write_json_dataset(path, YEAR_FILE_STAMP_H5_DATASET, dict(stamp))


def is_version_map(value: Any) -> bool:
    """Whether ``value`` maps package names to versions, ``None`` for absent."""
    return isinstance(value, dict) and all(
        isinstance(key, str) and (item is None or isinstance(item, str))
        for key, item in value.items()
    )


def source_and_package_differences(
    stamp: Mapping[str, Any], current: Mapping[str, Any]
) -> list[str]:
    """Return the clauses naming how a stamp's source and packages differ.

    ``stamp`` is a year file's well-formed stamp and ``current`` the stamp a
    file cut now would carry: each has a ``"source"`` that
    ``dataset_materialization.is_dataset_source_identity`` accepts and
    ``"packages"`` that :func:`is_version_map` accepts. One clause, starting
    "it", names both sources when they differ, and one more names each
    package whose version differs, in name order. A package the stamp
    records that ``current`` does not is named too, and a package recorded
    in both with one version is not.

    Returns no clause exactly when the sources and the package maps are
    equal.
    """
    reasons = []
    if stamp["source"] != current["source"]:
        reasons.append(
            "it was cut from "
            f"{describe_dataset_source_identity(stamp['source'])}, and the "
            "requested source is "
            f"{describe_dataset_source_identity(current['source'])}"
        )
    stamped_packages, packages = stamp["packages"], current["packages"]
    for name in sorted(stamped_packages.keys() | packages.keys()):
        if name not in packages:
            reasons.append(
                f"it records the {name} version it was cut with, which this "
                "version of policyengine.py does not check"
            )
            continue
        if name in stamped_packages and stamped_packages[name] == packages[name]:
            continue
        cut_with = (
            f"{name} {stamped_packages[name]}"
            if stamped_packages.get(name) is not None
            else f"no recorded {name} version"
        )
        installed = (
            f"{name} {packages[name]} is installed"
            if packages[name] is not None
            else f"{name} is not installed"
        )
        reasons.append(f"it was cut with {cut_with}, and {installed}")
    return reasons


def year_file_sources(
    country_id: str, datasets: list[str], allow_unmanaged: bool = True
) -> list[tuple[str, dict[str, Any]]]:
    """Return each requested dataset's year-file stem and source identity.

    The stem names the year files (``{stem}_year_{year}.h5``) and drops any
    revision, so files cut from every release of a logical dataset share
    names; the identity tells them apart. Neither downloads nor reads the
    source (see ``dataset_materialization.requested_dataset_source_identity``).
    A request ``materialize_dataset`` would refuse with the same
    ``allow_unmanaged`` raises the same error, before its stem is resolved.

    Raises ``ValueError`` when two of them are different sources with one
    stem. They would write the same year files, each cut overwriting the
    other's, so a request of both would cut them all again every time.
    """
    sources = []
    for dataset in datasets:
        identity = requested_dataset_source_identity(
            country_id, dataset, allow_unmanaged=allow_unmanaged
        )
        stem = dataset_logical_name(resolve_dataset_reference(country_id, dataset))
        sources.append((stem, identity))
    first_by_stem: dict[str, tuple[str, dict[str, Any]]] = {}
    for dataset, (stem, identity) in zip(datasets, sources):
        first, first_identity = first_by_stem.setdefault(stem, (dataset, identity))
        if first_identity != identity:
            raise ValueError(
                f"Datasets {first!r} and {dataset!r} would share the "
                f"{country_id.upper()} year files {stem}_year_{{year}}.h5, but "
                "are different sources: "
                f"{describe_dataset_source_identity(first_identity)} and "
                f"{describe_dataset_source_identity(identity)}. Request them "
                "in separate calls with separate data folders."
            )
    return sources
