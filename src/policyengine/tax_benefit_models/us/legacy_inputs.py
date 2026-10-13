"""Map stored US inputs that policyengine-us has since renamed.

A country engine sets a stored column as an input only when it defines a
variable of that name, and skips every other column. When policyengine-us
renames an input variable, datasets written before the rename still store the
old name, so the engine skips the stored values and the live input falls back
to its default.

:data:`LEGACY_INPUT_RENAMES` registers each such rename, and
:func:`apply_legacy_input_renames` sets the live input from the stored legacy
column. A rename applies only when all of these hold:

- the loaded engine does not define the legacy name (an engine that does reads
  the stored column itself);
- the loaded engine defines the live name;
- the stored data carries the legacy column but not the live one (data that
  already stores the live name loads it natively).

So the mapping retires itself once the data is re-cut under the live name, or
if the engine defines the legacy name again.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Iterable, Iterator, Mapping
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from policyengine.provenance.dataset_materialization import (
    describe_dataset_source_identity,
    is_dataset_source_identity,
)

#: Stored input columns that policyengine-us has since renamed, mapped to the
#: live input that replaced each one.
#:
#: ``would_claim_wic``: policyengine-us 2.2.1 defines no ``would_claim_wic``.
#: Its WIC take-up input is ``takes_up_wic_if_eligible`` (Person, MONTH,
#: ``default_value = True``), and ``wic`` is ``defined_for`` it. The certified
#: US default ``populace-us-2024-spm-20260915`` stores the take-up draw as
#: ``would_claim_wic`` only, so without this mapping every WIC-eligible person
#: takes WIC up (PolicyEngine/microcosm#1026).
#:
#: Each ``create_datasets`` year file is stamped with this register (see
#: :data:`YEAR_FILE_STAMP_H5_DATASET`), so any change to it (an entry added,
#: removed or pointed at another live input) makes every year file stale, and
#: ``ensure_datasets`` cuts them all again. An entry that no longer applies
#: turns itself off, so leave it in place rather than remove it.
LEGACY_INPUT_RENAMES: dict[str, str] = {
    "would_claim_wic": "takes_up_wic_if_eligible",
}

#: Key under which a run records the renames it applied, ``{legacy: live}``:
#: in a dataset's ``metadata`` (a ``create_datasets`` year file or a run's
#: output), ``Simulation.release_bundle``, a managed Microsimulation's
#: ``policyengine_bundle`` and a run record's results.
#:
#: ``{}`` means no stored column was mapped. It does not show that the data
#: carried a take-up draw at all: data that stores neither name runs with
#: the live input's default.
RENAMES_RECORD_KEY = "legacy_input_renames"

#: H5 dataset holding that record, as UTF-8 JSON, in a US file written by
#: ``PolicyEngineUSDataset.save()`` (a saved output or a ``create_datasets``
#: year file). Files written before this mapping existed have none, so its
#: absence marks them as calculated or cut without it: ``Simulation.load()``
#: refuses such an output, ``load_datasets`` refuses such a year file and
#: ``ensure_datasets`` regenerates it.
#:
#: The record shows that a file was written with the mapping, not under which
#: register. Year files also carry :data:`YEAR_FILE_STAMP_H5_DATASET`, which
#: ties them to the register they were cut under. Saved outputs carry only
#: this record, so an output saved before a register entry was added is still
#: reused.
RENAMES_H5_DATASET = "policyengine_legacy_input_renames"

#: H5 dataset stamping a ``create_datasets`` year file, as UTF-8 JSON (see
#: :func:`year_file_stamp`)::
#:
#:     {"packages": {"policyengine-core": str, "policyengine-us": str},
#:      "register": {legacy: live, ...},
#:      "revision": int,
#:      "source": {...}}
#:
#: It holds the versions of the packages that calculated the file's values,
#: the whole register the file was cut under, its year-file format revision
#: and the identity of the dataset it was cut from. ``create_datasets`` writes
#: it after the tables and the renames record, so a year file whose write
#: stopped part-way has none. ``ensure_datasets`` cuts a year file again, and
#: ``load_datasets`` refuses it, unless its stamp equals the one a file cut
#: now from the requested dataset would carry (see
#: :func:`year_file_stamp_problem`). ``PolicyEngineUSDataset.save()`` neither
#: writes nor keeps it, so saving a year file again drops the stamp.
YEAR_FILE_STAMP_H5_DATASET = "policyengine_year_file_stamp"

#: Format revision of ``create_datasets`` year files, stored in their stamp.
#: Raise it when the stamp changes shape, or when a change to year-file
#: extraction means that files cut before it must be cut again, for a reason
#: the rest of the stamp does not capture (for example, policyengine.py 6.1.1
#: and earlier exported only the engine's input variables, so a stored column
#: the engine had renamed was dropped).
#:
#: Removing the temporary ACS WIC assumption (:func:`_temporary_acs_wic_values`)
#: is such a change: year files cut while it applies store assumed claiming
#: as ``takes_up_wic_if_eligible`` for ACS people with no stored decision.
#: Re-pinning ``populace_us_2024_acs_local`` to its replacement changes its
#: source identity, so year files cut from the bundle's old pin are cut again
#: without a new revision. Year files cut from the old dataset requested by
#: its explicit URI are reused unless the revision is raised.
#:
#: Revision 2 added the source dataset's identity and the package versions,
#: so year files stamped with revision 1, which record neither, are cut again
#: once.
YEAR_FILE_STAMP_REVISION = 2

#: Distributions whose installed versions a year file's stamp records.
#: ``create_datasets`` stores each input as policyengine-us calculates it for
#: the year, and policyengine-core uprates an input from its stored year by a
#: policyengine-us parameter, so either can change a year file's values.
YEAR_FILE_PACKAGES = ("policyengine-core", "policyengine-us")

#: ``{year: {entity key: stored table}}``, one table per entity per dataset
#: year, in the dataset's own row order.
StoredTables = Mapping[int, Mapping[str, pd.DataFrame]]


def pending_legacy_input_renames(variables: Any) -> dict[str, str]:
    """Return the register entries an engine needs mapped.

    An entry is pending when the engine's ``variables`` define the live name
    and not the legacy name. Anything other than a variable mapping yields
    nothing.
    """
    if not isinstance(variables, Mapping):
        return {}
    return {
        legacy: live
        for legacy, live in LEGACY_INPUT_RENAMES.items()
        if legacy not in variables and live in variables
    }


#: What :func:`_read_json_dataset` returns for a node a file does not have, and
#: for one that is not a scalar dataset holding UTF-8 JSON.
_ABSENT = object()
_UNREADABLE = object()


def read_renames_record(path: str | Path) -> dict[str, str] | None:
    """Return the renames record stored in an H5 file, or ``None``.

    ``None`` means the file stores no record (see :data:`RENAMES_H5_DATASET`),
    stores one that is not a JSON object of strings, or is not an H5 file.
    """
    import h5py

    try:
        with h5py.File(path, "r") as file:
            record = _read_json_dataset(file, RENAMES_H5_DATASET)
    except OSError:
        return None
    return dict(record) if _is_str_map(record) else None


def write_renames_record(path: str | Path, record: Mapping[str, str]) -> None:
    """Store a renames record in an H5 file, replacing any it has."""
    _write_json_dataset(path, RENAMES_H5_DATASET, dict(record))


def installed_package_versions() -> dict[str, str | None]:
    """Return the installed version of each of :data:`YEAR_FILE_PACKAGES`.

    ``None`` stands for a package that is not installed. The versions come
    from the installed distributions' metadata, so no package is imported.
    """
    versions: dict[str, str | None] = {}
    for name in YEAR_FILE_PACKAGES:
        try:
            versions[name] = importlib_metadata.version(name)
        except importlib_metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def year_file_stamp(
    source: Mapping[str, Any],
    packages: Mapping[str, str | None] | None = None,
) -> dict[str, Any]:
    """Return the stamp for a year file cut now from ``source``.

    ``source`` is the source dataset's identity (see
    ``policyengine.provenance.dataset_materialization.dataset_source_identity``).
    ``packages`` defaults to :func:`installed_package_versions`.

    The stamp holds the whole register, not only the entries an engine needs
    mapped, so checking a stamp never imports policyengine-us. The register
    and the package versions are read when this is called.
    """
    if packages is None:
        packages = installed_package_versions()
    return {
        "packages": dict(sorted(packages.items())),
        "register": dict(sorted(LEGACY_INPUT_RENAMES.items())),
        "revision": YEAR_FILE_STAMP_REVISION,
        "source": dict(source),
    }


def read_year_file_stamp(path: str | Path) -> Any | None:
    """Return the JSON value of a year file's stamp, well formed or not.

    ``None`` means the file stores no readable stamp (see
    :data:`YEAR_FILE_STAMP_H5_DATASET`) or is not an H5 file.
    """
    import h5py

    try:
        with h5py.File(path, "r") as file:
            stamp = _read_json_dataset(file, YEAR_FILE_STAMP_H5_DATASET)
    except OSError:
        return None
    return None if stamp is _ABSENT or stamp is _UNREADABLE else stamp


def write_year_file_stamp(path: str | Path, stamp: Mapping[str, Any]) -> None:
    """Stamp a year file (see :func:`year_file_stamp`), replacing any stamp."""
    _write_json_dataset(path, YEAR_FILE_STAMP_H5_DATASET, dict(stamp))


def year_file_stamp_problem(
    path: str | Path,
    source: Mapping[str, Any],
    packages: Mapping[str, str | None] | None = None,
) -> str | None:
    """Return why a ``create_datasets`` year file is out of date, or ``None``.

    ``source`` is the identity of the dataset the year file is requested for
    (see ``policyengine.provenance.dataset_materialization
    .requested_dataset_source_identity``), and ``packages`` defaults to
    :func:`installed_package_versions`. A year file is current only when both
    of these hold:

    - its stamp equals ``year_file_stamp(source, packages)``: the same format
      revision, register, source identity and package versions;
    - it stores the renames record, listing only renames in that register.

    The register must match exactly. A file cut under a register that lacks
    an entry may have lost that entry's input, as year files that
    policyengine.py 6.1.1 and earlier cut from the certified default lost the
    WIC take-up draw. A file cut under an entry this release does not
    register, or registers with another live input, may store a live name
    this release's engine does not define, and a run skips any column the
    engine does not define.

    The source must match exactly too: a file cut from another revision or
    file of a dataset that keeps its logical name (and so the year file's
    name) holds the other data. So must the package versions, which
    calculated every value in the file.

    Only the stamp and the record are read, never the tables or the source
    dataset. A file that cannot be read as HDF5 is out of date. An error that
    says nothing about the file's contents (no permission, a directory, a file
    another process has locked) is raised instead, since the file could not
    be written again either.

    Returns:
        ``None`` for a current year file; otherwise a clause, starting "it"
        or "its", that says why the file is out of date. It names the renames
        the file may have lost, the source it was cut from and the source
        requested, and the package versions it was cut with and those
        installed, wherever they differ.
    """
    import h5py

    current = year_file_stamp(source, packages)
    register = current["register"]
    try:
        with h5py.File(path, "r") as file:
            stamp = _read_json_dataset(file, YEAR_FILE_STAMP_H5_DATASET)
            record = _read_json_dataset(file, RENAMES_H5_DATASET)
    except (PermissionError, IsADirectoryError, BlockingIOError):
        raise
    except OSError:
        return "it cannot be read as an HDF5 file (it may be half-written or corrupt)"

    # The revision comes first: a later revision may shape its stamp and
    # record differently.
    revision = stamp.get("revision") if isinstance(stamp, dict) else None
    if type(revision) is int and revision != YEAR_FILE_STAMP_REVISION:
        return (
            f"it was cut with year-file format revision {revision}, and this "
            f"version of policyengine.py reads only revision "
            f"{YEAR_FILE_STAMP_REVISION}"
        )
    if stamp is _ABSENT:
        if record is _ABSENT:
            return (
                "it has no record of the renamed stored inputs mapped when it "
                "was cut, so it was cut by an older policyengine.py or not "
                "written completely"
                + (
                    f", and may have lost any of: {_describe(register)}"
                    if register
                    else ""
                )
            )
        return "it has no stamp of the register of renamed inputs it was cut under" + (
            f", so it may have lost any of: {_describe(register)}" if register else ""
        )
    # ``type(...) is int`` rather than ``isinstance``: JSON ``true`` loads as
    # ``True``, which equals 1.
    if not (
        isinstance(stamp, dict)
        and set(stamp) == {"packages", "register", "revision", "source"}
        and type(revision) is int
        and _is_str_map(stamp["register"])
        and _is_version_map(stamp["packages"])
        and is_dataset_source_identity(stamp["source"])
    ):
        return "its stamp of what it was cut from and under is malformed"
    if record is _ABSENT:
        return "it has no record of the renamed stored inputs mapped when it was cut"
    if not _is_str_map(record):
        return (
            "its record of the renamed stored inputs mapped when it was cut is "
            "malformed"
        )
    stamped = stamp["register"]
    outside = dict(record.items() - stamped.items())
    if outside:
        return (
            "its record lists renames outside the register it was stamped "
            f"with: {_describe(outside)}"
        )
    if stamp == current:
        return None
    missing = {
        legacy: live for legacy, live in register.items() if stamped.get(legacy) != live
    }
    unknown = {
        legacy: live for legacy, live in stamped.items() if register.get(legacy) != live
    }
    reasons = []
    if missing:
        reasons.append(
            "it was cut before these renames were registered, so it may have "
            f"lost them: {_describe(missing)}"
        )
    if unknown:
        reasons.append(
            "it was cut under renames this version of policyengine.py does not "
            f"register: {_describe(unknown)}"
        )
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
    return "; ".join(reasons)


def _read_json_dataset(file: Any, name: str) -> Any:
    """Return the JSON value stored in an open H5 file's ``name`` dataset."""
    import h5py

    try:
        node = file.get(name)
        if node is None:
            return _ABSENT
        if not isinstance(node, h5py.Dataset) or node.shape != ():
            return _UNREADABLE
        # A numeric dataset raises TypeError; bytes that are not UTF-8, or
        # not JSON, raise ValueError; JSON nested too deeply raises
        # RecursionError.
        return json.loads(node.asstr()[()])
    except (PermissionError, IsADirectoryError, BlockingIOError):
        raise
    except (KeyError, OSError, RecursionError, TypeError, ValueError):
        return _UNREADABLE


def _write_json_dataset(path: str | Path, name: str, value: Any) -> None:
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


def _is_str_map(value: Any) -> bool:
    return isinstance(value, dict) and all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    )


def _is_version_map(value: Any) -> bool:
    """Whether ``value`` maps package names to versions, ``None`` for absent."""
    return isinstance(value, dict) and all(
        isinstance(key, str) and (item is None or isinstance(item, str))
        for key, item in value.items()
    )


def _describe(renames: Mapping[str, str]) -> str:
    return ", ".join(f"{legacy} -> {live}" for legacy, live in sorted(renames.items()))


def check_yearly_periods(column: str, periods: Iterable[Any], source: Any) -> None:
    """Refuse a legacy column stored for any period that is not a year.

    A value stored for part of a year (or for ``ETERNITY``) cannot stand for
    every month of a year, so it is not mapped rather than spread over them.
    """
    for period in periods:
        if not str(period).isdigit():
            raise ValueError(
                f"Cannot map stored {column!r} from {source}: it is stored "
                f"for period {str(period)!r}, and only yearly periods are "
                "supported."
            )


def apply_legacy_input_renames(
    simulation, stored_tables: StoredTables
) -> dict[str, str]:
    """Set each pending live input from its stored legacy column.

    For each pending rename (see :func:`pending_legacy_input_renames`), every
    year whose stored table for the live input's entity carries the legacy
    column but not the live one is mapped: the live input is set to the stored
    values for each month of that year (or for the year, if the live input is
    yearly).

    Every mapped table is checked before anything is set. Its ``{entity}_id``
    column must list the simulation's entity IDs in the simulation's order,
    and its stored values must be complete and, for a boolean live input,
    boolean. A temporary WIC-only exception assumes claiming for missing
    decisions on explicitly identified ACS people. Missing donor decisions
    and malformed stored values still raise ``ValueError``.

    Applying the mapping again sets the same values, so it is idempotent.

    Returns:
        The renames applied, ``{legacy: live}``.
    """
    variables = simulation.tax_benefit_system.variables
    planned: list[tuple[str, str, list[str], np.ndarray]] = []
    for legacy, live in pending_legacy_input_renames(variables).items():
        variable = variables[live]
        entity = variable.entity.key
        for year, tables in sorted(stored_tables.items()):
            table = tables.get(entity)
            if table is None or legacy not in table.columns or live in table.columns:
                continue
            context = f"Cannot map stored {legacy!r} onto {live!r} for {year}"
            _check_order(simulation, table, entity, context)
            stored = table[legacy]
            if (
                legacy == "would_claim_wic"
                and live == "takes_up_wic_if_eligible"
                and entity == "person"
                and variable.value_type is bool
            ):
                stored = _temporary_acs_wic_values(table, context)
            values = _live_values(stored, variable, context)
            periods = _periods_of_year(int(year), variable.definition_period, context)
            planned.append((legacy, live, periods, values))

    applied: dict[str, str] = {}
    for legacy, live, periods, values in planned:
        for period in periods:
            simulation.set_input(live, period, values)
        applied[legacy] = live
    _record_input_variables(simulation, applied.values())
    return applied


def apply_legacy_input_renames_to_microsimulation(microsimulation) -> dict[str, str]:
    """Apply the register to a country Microsimulation built from a file.

    The stored tables come from the dataset the Microsimulation loaded (see
    :func:`stored_entity_tables`). The Microsimulation and every branch it
    already has (a reform's ``baseline`` is branched off during construction,
    before this runs) are each mapped.

    Returns:
        The renames applied, ``{legacy: live}``.
    """
    variables = microsimulation.tax_benefit_system.variables
    pending = pending_legacy_input_renames(variables)
    if not pending:
        return {}
    renames_by_entity: dict[str, dict[str, str]] = {}
    for legacy, live in pending.items():
        renames_by_entity.setdefault(variables[live].entity.key, {})[legacy] = live
    stored_tables = stored_entity_tables(
        getattr(microsimulation, "dataset", None), renames_by_entity
    )
    applied: dict[str, str] = {}
    for simulation in _simulation_and_branches(microsimulation):
        applied.update(apply_legacy_input_renames(simulation, stored_tables))
    return applied


def stored_entity_tables(
    dataset: Any, renames_by_entity: Mapping[str, Mapping[str, str]]
) -> dict[int, dict[str, pd.DataFrame]]:
    """Return the per-year stored tables a country Microsimulation loaded.

    ``renames_by_entity`` maps each entity key to the ``{legacy: live}``
    renames whose live input belongs to it.

    policyengine-us loads an entity-table H5 (the layout of the certified
    Populace default) into a multi-year dataset whose ``datasets`` map each
    year to that year's entity DataFrames. Those keep every stored column, including the
    ones the engine skipped, so they are returned as they are.

    A policyengine-core ``variable/period`` H5 is read again from
    ``dataset.file_path``, but only each entity's ID column and the legacy
    columns that need mapping (see :func:`_variable_centric_tables`).

    Any other dataset yields no tables.
    """
    datasets = _static_attribute(dataset, "datasets")
    if isinstance(datasets, Mapping):
        tables: dict[int, dict[str, pd.DataFrame]] = {}
        for year, single_year in datasets.items():
            tables[int(year)] = {
                entity: table
                for entity in renames_by_entity
                if isinstance(
                    table := _static_attribute(single_year, entity), pd.DataFrame
                )
            }
        return tables
    if _static_attribute(dataset, "data_format") in ("arrays", "time_period_arrays"):
        file_path = _static_attribute(dataset, "file_path")
        if file_path is not None and Path(file_path).suffix == ".h5":
            if Path(file_path).is_file():
                return _variable_centric_tables(
                    Path(file_path),
                    _static_attribute(dataset, "time_period"),
                    renames_by_entity,
                )
    return {}


def _variable_centric_tables(
    path: Path,
    default_period: Any,
    renames_by_entity: Mapping[str, Mapping[str, str]],
) -> dict[int, dict[str, pd.DataFrame]]:
    """Read legacy columns from a ``variable/period`` H5 into yearly tables.

    A file that stores a live name under any period loads it natively, so the
    legacy column it replaces is not read at all. A legacy column is read only
    for yearly periods; one stored for a part of a year is refused, since it
    cannot stand for the whole year.

    policyengine-core builds each population from the ID array stored under
    the first period key, so a year that stores no IDs of its own is checked
    against those.
    """
    import h5py

    tables: dict[int, dict[str, pd.DataFrame]] = {}
    with h5py.File(path, "r") as file:
        for entity, renames in renames_by_entity.items():
            id_column = f"{entity}_id"
            legacy_columns = sorted(
                legacy
                for legacy, live in renames.items()
                if legacy in file and live not in file
            )
            if not legacy_columns or id_column not in file:
                continue
            ids_by_period = _stored_periods(file[id_column], default_period)
            first_ids = next(iter(ids_by_period.values()), None)
            columns_by_year: dict[int, dict[str, np.ndarray]] = {}
            for column in legacy_columns:
                stored_by_period = _stored_periods(file[column], default_period)
                check_yearly_periods(column, stored_by_period, path)
                for period, stored in stored_by_period.items():
                    columns_by_year.setdefault(int(period), {})[column] = stored
            for year, columns in sorted(columns_by_year.items()):
                ids = ids_by_period.get(str(year), first_ids)
                if ids is None or any(
                    len(array) != len(ids) for array in columns.values()
                ):
                    raise ValueError(
                        f"Cannot map stored columns from {path} for {year}: "
                        f"their length differs from the stored {id_column}."
                    )
                tables.setdefault(year, {})[entity] = pd.DataFrame(
                    {id_column: ids, **columns}
                )
    return tables


def _stored_periods(node: Any, default_period: Any) -> dict[str, np.ndarray]:
    """Map each stored period of an H5 node to its values, in file order.

    A flat ``arrays`` file stores one array per variable, which
    policyengine-core sets for the dataset's own period.
    """
    import h5py

    if isinstance(node, h5py.Dataset):
        if default_period is None:
            return {}
        return {str(default_period): node[()]}
    return {str(key): node[key][()] for key in node.keys()}


def _static_attribute(obj: Any, name: str) -> Any:
    """Return ``obj.<name>``, or ``None`` when ``obj`` has no such attribute.

    Only attributes found without a dynamic ``__getattr__`` count.
    policyengine-core's ``Dataset.__getattr__`` loads any other name as an H5
    key and raises ``KeyError`` when the file has none, so probing a dataset
    with ``getattr(dataset, name, None)`` is not safe.
    """
    try:
        inspect.getattr_static(obj, name)
    except AttributeError:
        return None
    return getattr(obj, name)


def _check_order(simulation, table: pd.DataFrame, entity: str, context: str) -> None:
    id_column = f"{entity}_id"
    if id_column not in table.columns:
        raise ValueError(
            f"{context}: the stored {entity} table has no {id_column} column, "
            "so its row order cannot be checked against the simulation."
        )
    stored_ids = table[id_column].to_numpy()
    simulated_ids = np.asarray(simulation.populations[entity].ids)
    if not np.array_equal(stored_ids, simulated_ids):
        raise ValueError(
            f"{context}: the stored {entity} table is not in the simulation's "
            f"{entity} order ({id_column} differs), so its values would attach "
            "to the wrong rows."
        )


def _temporary_acs_wic_values(table: pd.DataFrame, context: str) -> pd.Series:
    """Preserve stored decisions; assume claiming only for missing ACS cells."""
    stored = table["would_claim_wic"]
    missing = stored.isna()
    if not missing.any():
        return stored
    channel = "person_support_channel"
    if channel not in table or not (
        table.loc[missing, channel].eq("acs_2024_1yr").fillna(False).all()
    ):
        raise ValueError(
            f"{context}: the stored column has missing values outside "
            "explicitly identified ACS people."
        )
    # TEMPORARY ACS WIC COMPATIBILITY — REMOVE AS SOON AS POSSIBLE.
    # Replacement dataset: https://github.com/PolicyEngine/microcosm/issues/1154
    # Prepared removal: https://github.com/PolicyEngine/policyengine.py/pull/563
    # The currently certified ACS-local dataset did not generate WIC
    # participation decisions for ACS people. For missing ACS decisions only,
    # assume that every eligible person claims WIC.
    # This is an explicit modelling assumption, not observed participation.
    # Replace the dataset with a corrected Microcosm release and DELETE
    # this exception immediately after that replacement is certified.
    # Nullable numeric columns reject boolean replacement values. Preserve the
    # original decisions as objects; _live_values still validates before casting.
    return stored.astype(object).mask(missing, True)


def _live_values(stored: pd.Series, variable: Any, context: str) -> np.ndarray:
    if stored.isna().any():
        raise ValueError(f"{context}: the stored column has missing values.")
    if variable.value_type is not bool:
        return np.asarray(stored.to_numpy())
    if pd.api.types.is_bool_dtype(stored.dtype):
        return np.asarray(stored.to_numpy(dtype=bool))
    if pd.api.types.is_numeric_dtype(stored.dtype) and stored.isin((0, 1)).all():
        return np.asarray(stored.to_numpy(), dtype=bool)
    # Nullable legacy H5 columns may contain genuine booleans and numeric 0/1
    # as objects. Validate each value before casting: bool("False") is True.
    if stored.map(
        lambda value: (
            isinstance(value, bool | np.bool_ | int | np.integer | float | np.floating)
            and value in (0, 1)
        )
    ).all():
        return np.asarray(stored.to_numpy(), dtype=bool)
    raise ValueError(f"{context}: the stored values are not boolean.")


def _periods_of_year(year: int, definition_period: Any, context: str) -> list[str]:
    unit = str(definition_period)
    if unit == "month":
        return [f"{year}-{month:02d}" for month in range(1, 13)]
    if unit == "year":
        return [str(year)]
    raise ValueError(f"{context}: definition period {unit!r} is not supported.")


def _record_input_variables(simulation, live_names: Iterable[str]) -> None:
    """List mapped inputs as inputs, as if the dataset had stored them.

    A country Microsimulation lists ``input_variables`` once, at construction.
    Dataset extraction (``create_datasets``) exports that list, and
    policyengine-core's ``derivative`` keeps only those inputs in its clone, so
    a mapped input must join it.
    """
    input_variables = getattr(simulation, "input_variables", None)
    if not isinstance(input_variables, list):
        return
    missing = [name for name in live_names if name not in input_variables]
    if missing:
        simulation.input_variables = [*input_variables, *missing]


def _simulation_and_branches(simulation) -> Iterator[Any]:
    seen: set[int] = set()
    stack = [simulation]
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        branches = getattr(current, "branches", None)
        if isinstance(branches, Mapping):
            stack.extend(branches.values())
