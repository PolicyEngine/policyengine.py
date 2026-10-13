"""Stamp year files with what they were cut from and under.

A country's ``create_datasets`` cuts one file per requested year from a
source dataset and names it ``{data_folder}/{stem}_year_{year}.h5``, after
the source's logical name. The name drops any revision, so files cut from
every release of a dataset share names. Each year file is therefore stamped
with the identity of the source it was cut from and the versions of the
packages that calculated it, and the country's ``ensure_datasets`` and
``load_datasets`` compare that stamp with the one a file cut now would carry.

Each country stores its stamp, as UTF-8 JSON, in an H5 dataset of its own
name, so a year file of one country never passes as one of another:
``tax_benefit_models.us.legacy_inputs.YEAR_FILE_STAMP_H5_DATASET`` (which
also records the register of renamed stored inputs) and
``tax_benefit_models.uk.datasets.YEAR_FILE_STAMP_H5_DATASET`` (which also
records the year the file was cut for).

This module holds what the countries share:

- reading and writing a JSON value in an H5 dataset
  (:func:`read_json_dataset`, :func:`read_stored_json`,
  :func:`write_json_dataset`);
- the installed versions of the packages a stamp records
  (:func:`installed_package_versions`);
- the clauses naming how a stamp's source and package versions differ from
  the current ones (:func:`source_and_package_differences`);
- each requested dataset's year-file stem and source identity, refusing two
  sources that would share year files (:func:`year_file_sources`);
- writing a year file beside its path and moving it into place only once it
  is stamped (:func:`temporary_year_file`, :func:`publish_year_file`);
- reading a file's stamp and its tables from one file, though each is read
  through its own open of the path (:func:`read_one_file`).

A saved UK simulation output is written, stamped and read the same way (see
``tax_benefit_models.uk.datasets.OUTPUT_STAMP_H5_DATASET``).
"""

from __future__ import annotations

import json
import os
import secrets
from collections.abc import Callable, Iterable, Mapping
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Optional, TypeVar

from .dataset_materialization import (
    describe_dataset_source_identity,
    requested_dataset_source_identity,
)
from .manifest import dataset_logical_name, resolve_dataset_reference

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


def read_stored_json(path: str | Path, name: str) -> Any | None:
    """Return the JSON value of an H5 file's ``name`` dataset, well formed or
    not.

    ``None`` means the file stores no readable JSON there (see
    :func:`read_json_dataset`) or is not an H5 file.
    """
    import h5py

    try:
        with h5py.File(path, "r") as file:
            value = read_json_dataset(file, name)
    except OSError:
        return None
    return None if value is ABSENT or value is UNREADABLE else value


def temporary_year_file(path: str | Path) -> Path:
    """Create an empty file beside ``path`` to write a year file to.

    ``create_datasets`` writes a year file's tables there, stamps it once the
    source has been checked again, and only then moves it onto ``path`` (see
    :func:`publish_year_file`). The tables and the stamp at ``path`` then
    always come from one cut, even when two processes cut the same year files
    at once, and a cut that stops part-way leaves ``path`` as it was. The
    file's name starts with ``.{stem}.`` and ends with ``.partial``; the
    caller removes it if the cut fails.

    The file is created with the mode a new file gets (``0o666`` less the
    umask), as pandas would create the year file itself, so a year file moved
    into place is as readable by others as one written at its path. (A file
    from ``tempfile.mkstemp`` would be readable by its owner alone.)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    for _ in range(100):
        temporary = path.parent / f".{path.stem}.{secrets.token_hex(8)}.partial"
        try:
            descriptor = os.open(temporary, flags, 0o666)
        except FileExistsError:
            continue
        os.close(descriptor)
        return temporary
    raise FileExistsError(f"Could not create a temporary file beside {path}")


def publish_year_file(
    temporary: str | Path, path: str | Path, name: str, stamp: Mapping[str, Any]
) -> None:
    """Stamp a year file written to ``temporary``, then move it onto ``path``.

    ``name`` is the country's stamp dataset. The move replaces any file at
    ``path`` in one step (``os.replace`` within one folder), so a reader sees
    either the old file or the new one, each with its own stamp.
    """
    write_json_dataset(temporary, name, dict(stamp))
    os.replace(temporary, path)


_Read = TypeVar("_Read")


def read_one_file(
    path: str | Path, read: Callable[[str], _Read], attempts: int = 3
) -> _Read:
    """Return ``read(path)``, having checked that it read one unchanged file.

    ``read`` may open ``path`` several times, for example once for a stamp
    and once for the tables. Another process can move another file onto the
    path in between (:func:`publish_year_file` does), so what one open reads
    need not belong with what the next reads.

    The file at ``path`` is therefore held open while ``read`` runs. After it
    returns, ``path`` must still name that file (the same device and inode,
    which the file system does not give to another file while this one is
    held open), and the file must have the size and modification time it had
    before. If not, ``read`` runs again, up to ``attempts`` times in all, and
    then ``RuntimeError`` is raised. A file moved onto the path is another
    file, even when its contents are those of an earlier one.

    Two changes are not noticed: a file rewritten in place to the same size
    within one tick of the file system's modification time, and a file
    replaced and then put back by moving another hard link to it onto the
    path. Neither ``create_datasets`` nor ``save_output`` writes that way:
    each moves a newly written file onto the path.

    Whatever ``read`` raises is raised, as is whatever opening ``path``
    raises (``FileNotFoundError`` for a missing file).
    """
    path = str(path)
    for _ in range(attempts):
        with open(path, "rb") as held:
            before = os.fstat(held.fileno())
            result = read(path)
            after = os.fstat(held.fileno())
            try:
                named = os.stat(path)
            except FileNotFoundError:
                continue
        if os.path.samestat(named, before) and (
            after.st_size,
            after.st_mtime_ns,
        ) == (before.st_size, before.st_mtime_ns):
            return result
    raise RuntimeError(
        f"{path} was replaced or modified while it was read, {attempts} times; "
        "read it again once it is no longer being written"
    )


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
    reasons.extend(package_differences(stamp["packages"], current["packages"]))
    return reasons


def package_differences(
    stamped: Mapping[str, Optional[str]],
    packages: Mapping[str, Optional[str]],
    done: str = "cut",
) -> list[str]:
    """Return the clauses naming the package versions a stamp differs in.

    ``stamped`` is the version map a stamp records and ``packages`` the one a
    stamp made now would (each as :func:`is_version_map` accepts). ``done``
    says what the stamped file had done to it with those versions: a year
    file was "cut" with them, an output "calculated". One clause, starting
    "it", names each package whose version differs, in name order. A package
    ``stamped`` records that ``packages`` does not is named too, and a
    package recorded in both with one version is not.

    Returns no clause exactly when the two maps are equal.
    """
    reasons = []
    for name in sorted(stamped.keys() | packages.keys()):
        if name not in packages:
            reasons.append(
                f"it records the {name} version it was {done} with, which this "
                "version of policyengine.py does not check"
            )
            continue
        if name in stamped and stamped[name] == packages[name]:
            continue
        done_with = (
            f"{name} {stamped[name]}"
            if stamped.get(name) is not None
            else f"no recorded {name} version"
        )
        installed = (
            f"{name} {packages[name]} is installed"
            if packages[name] is not None
            else f"{name} is not installed"
        )
        reasons.append(f"it was {done} with {done_with}, and {installed}")
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
