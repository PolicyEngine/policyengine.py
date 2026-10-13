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

import copy
import inspect
import json
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

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
#: Each ``create_datasets`` year file and each saved output is stamped with
#: this register (see :data:`YEAR_FILE_STAMP_H5_DATASET` and
#: :data:`OUTPUT_STAMP_H5_DATASET`), so any change to it (an entry added,
#: removed or pointed at another live input) makes every year file and every
#: saved output stale: ``ensure_datasets`` cuts the year files again, and
#: ``Simulation.ensure()`` calculates the outputs again. An entry that no
#: longer applies turns itself off, so leave it in place rather than remove it.
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
#: register. Year files also carry :data:`YEAR_FILE_STAMP_H5_DATASET`, and
#: saved outputs :data:`OUTPUT_STAMP_H5_DATASET`, which tie each to the
#: register it was cut or calculated under.
RENAMES_H5_DATASET = "policyengine_legacy_input_renames"

#: H5 dataset stamping a ``create_datasets`` year file, as UTF-8 JSON
#: ``{"register": {legacy: live, ...}, "revision": int}``: the whole register
#: the file was cut under and its year-file format revision (see
#: :func:`year_file_stamp`). ``create_datasets`` writes it after the tables and
#: the renames record, so a year file whose write stopped part-way has none.
#: ``ensure_datasets`` cuts a year file again, and ``load_datasets`` refuses
#: it, unless its stamp equals this release's (see
#: :func:`year_file_stamp_problem`). ``PolicyEngineUSDataset.save()`` neither
#: writes nor keeps it, so saving a year file again drops the stamp.
YEAR_FILE_STAMP_H5_DATASET = "policyengine_year_file_stamp"

#: Format revision of ``create_datasets`` year files, stored in their stamp.
#: Raise it when a change to year-file extraction means that files cut before
#: it must be cut again, for a reason the register does not capture (for
#: example, policyengine.py 6.1.1 and earlier exported only the engine's input
#: variables, so a stored column the engine had renamed was dropped).
#:
#: Removing the temporary ACS WIC assumption (:func:`_temporary_acs_wic_values`)
#: is such a change: year files cut while it applies store assumed claiming
#: as ``takes_up_wic_if_eligible`` for ACS people with no stored decision.
#:
#: A saved output records the stamp of the year file it was calculated from,
#: so raising this makes those outputs out of date too.
YEAR_FILE_STAMP_REVISION = 1

#: Key under which a dataset read from, or cut into, a year file keeps that
#: file's stamp in its ``metadata``, as the JSON value stored (see
#: :func:`read_year_file_stamp`). A run records it in its output's stamp.
YEAR_FILE_STAMP_KEY = "year_file_stamp"

#: H5 dataset stamping a saved US simulation output, as UTF-8 JSON
#: ``{"register": {legacy: live, ...}, "revision": int, "year_file": ...}``:
#: the whole register the output was calculated under, its output format
#: revision, and the stamp of the year file it was calculated from (``null``
#: when the input dataset carried none). See :func:`output_stamp`.
#:
#: A US run records the stamp in its output's ``metadata`` (under
#: :data:`OUTPUT_STAMP_KEY`) when it is calculated, before applying the
#: mapping. ``MicrosimulationModelVersion.save()`` writes it after the tables,
#: the renames record and the SPM receipt, so an output whose save stopped
#: part-way has none. ``Simulation.load()`` refuses an output whose stamp does
#: not match this release's (see :func:`output_stamp_problem`), and
#: ``Simulation.ensure()`` then calculates it again.
#:
#: Its name and its keys differ from :data:`YEAR_FILE_STAMP_H5_DATASET`'s, so
#: an output never passes as a year file, nor a year file as an output.
OUTPUT_STAMP_H5_DATASET = "policyengine_output_stamp"

#: Format revision of saved outputs, stored in their stamp. Raise it when a
#: change to the mapping, or to how a run uses it, means that outputs
#: calculated before it must be calculated again, for a reason neither the
#: register nor the year-file stamp captures.
#:
#: Removing the temporary ACS WIC assumption (:func:`_temporary_acs_wic_values`)
#: is such a change: a run over a source that stores ``would_claim_wic``
#: assumes claiming for ACS people with no stored decision while it applies.
#: Raise :data:`YEAR_FILE_STAMP_REVISION` with it.
OUTPUT_STAMP_REVISION = 1

#: Key under which a US run's output keeps its stamp in ``metadata``.
OUTPUT_STAMP_KEY = "output_stamp"

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


def year_file_stamp() -> dict[str, Any]:
    """Return the stamp for a year file cut now.

    It holds the whole register, not only the entries an engine needs mapped,
    so checking a stamp never imports policyengine-us. The register is read
    when this is called.
    """
    return {
        "register": dict(sorted(LEGACY_INPUT_RENAMES.items())),
        "revision": YEAR_FILE_STAMP_REVISION,
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


def year_file_stamp_problem(path: str | Path) -> str | None:
    """Return why a ``create_datasets`` year file is out of date, or ``None``.

    A year file is current only when both of these hold:

    - its stamp equals :func:`year_file_stamp`: the same format revision and
      the same register;
    - it stores the renames record, listing only renames in that register.

    The register must match exactly. A file cut under a register that lacks
    an entry may have lost that entry's input, as year files that
    policyengine.py 6.1.1 and earlier cut from the certified default lost the
    WIC take-up draw. A file cut under an entry this release does not
    register, or registers with another live input, may store a live name
    this release's engine does not define, and a run skips any column the
    engine does not define.

    Only the stamp and the record are read, never the tables or the source
    dataset. A file that cannot be read as HDF5 is out of date. An error that
    says nothing about the file's contents (no permission, a directory, a file
    another process has locked) is raised instead, since the file could not
    be written again either.

    Returns:
        ``None`` for a current year file; otherwise a clause, starting "it"
        or "its", that says why the file is out of date and names the
        renames it may have lost.
    """
    import h5py

    current = year_file_stamp()
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
        and set(stamp) == {"register", "revision"}
        and type(revision) is int
        and _is_str_map(stamp["register"])
    ):
        return (
            "its stamp of the register of renamed inputs it was cut under is malformed"
        )
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
    missing, unknown = _register_differences(stamped, register)
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
    return "; ".join(reasons)


def year_file_stamp_metadata(path: str | Path) -> Any | None:
    """Return the year-file stamp a dataset read from ``path`` keeps.

    A dataset keeps it in ``metadata`` under :data:`YEAR_FILE_STAMP_KEY`, and
    a run records it in its output's stamp (see :func:`output_stamp`).

    An error that says nothing about the file's contents (a missing file, no
    permission, a directory, a lock) is raised, as by
    :func:`year_file_stamp_problem`.

    Returns:
        ``None`` when the file stores no stamp or is not an H5 file; the
        stored JSON value when it is readable and not ``null``; otherwise
        ``"unreadable"``. No release stamps a year file with a string, so an
        output calculated from a file whose stamp is unreadable is never
        current.
    """
    import h5py

    try:
        with h5py.File(path, "r") as file:
            stamp = _read_json_dataset(file, YEAR_FILE_STAMP_H5_DATASET)
    except (FileNotFoundError, PermissionError, IsADirectoryError, BlockingIOError):
        raise
    except OSError:
        return None
    if stamp is _ABSENT:
        return None
    return "unreadable" if stamp is _UNREADABLE or stamp is None else stamp


def output_stamp(year_file: Any = None) -> dict[str, Any]:
    """Return the stamp for an output calculated now.

    ``year_file`` is the stamp the input dataset keeps under
    :data:`YEAR_FILE_STAMP_KEY` (see :func:`year_file_stamp_metadata`), or
    ``None`` when it keeps none. Like :func:`year_file_stamp`, the stamp holds
    the whole register, read when this is called.
    """
    return {
        "register": dict(sorted(LEGACY_INPUT_RENAMES.items())),
        "revision": OUTPUT_STAMP_REVISION,
        "year_file": copy.deepcopy(year_file),
    }


def read_output_stamp(path: str | Path) -> Any | None:
    """Return the JSON value of a saved output's stamp, well formed or not.

    ``None`` means the file stores no readable stamp (see
    :data:`OUTPUT_STAMP_H5_DATASET`) or is not an H5 file.
    """
    import h5py

    try:
        with h5py.File(path, "r") as file:
            stamp = _read_json_dataset(file, OUTPUT_STAMP_H5_DATASET)
    except OSError:
        return None
    return None if stamp is _ABSENT or stamp is _UNREADABLE else stamp


def write_output_stamp(path: str | Path, stamp: Mapping[str, Any]) -> None:
    """Stamp a saved output (see :func:`output_stamp`), replacing any stamp."""
    _write_json_dataset(path, OUTPUT_STAMP_H5_DATASET, dict(stamp))


def output_stamp_problem(path: str | Path) -> str | None:
    """Return why a saved US simulation output is out of date, or ``None``.

    A saved output is current only when both of these hold:

    - its stamp equals :func:`output_stamp` for an input that kept no
      year-file stamp, or for one cut into a year file under this release's
      :func:`year_file_stamp`. That is, it has the same output format
      revision and the same register, and the stamp of the year file it was
      calculated from is ``null`` or this release's;
    - it stores the renames record, listing only renames in its stamped
      register.

    The registers must match exactly, for the reasons
    :func:`year_file_stamp_problem` gives. An output calculated before an
    entry was registered may lack that entry's input, as outputs calculated
    before the WIC entry gave every WIC-eligible person WIC. A run over a year
    file maps only what the file still stores under a legacy name, so an
    output calculated from a year file that is out of date under this release
    is out of date too.

    Only the stamp and the record are read, never the tables. A file that
    cannot be read as HDF5 is out of date. A missing file raises
    ``FileNotFoundError``, so ``Simulation.ensure()`` calculates the output
    without reporting an unexpected error. An error that says nothing about
    the file's contents (no permission, a directory, a file another process
    has locked) is raised too, since the output could not be saved again
    either.

    Returns:
        ``None`` for a current output; otherwise a clause, starting "it" or
        "its", that says why the output is out of date and names the renames
        it may lack.
    """
    import h5py

    register = dict(sorted(LEGACY_INPUT_RENAMES.items()))
    current_year_file = year_file_stamp()
    try:
        with h5py.File(path, "r") as file:
            stamp = _read_json_dataset(file, OUTPUT_STAMP_H5_DATASET)
            record = _read_json_dataset(file, RENAMES_H5_DATASET)
    except (FileNotFoundError, PermissionError, IsADirectoryError, BlockingIOError):
        raise
    except OSError:
        return "it cannot be read as an HDF5 file (it may be half-written or corrupt)"

    # The revision comes first: a later revision may shape its stamp and
    # record differently.
    revision = stamp.get("revision") if isinstance(stamp, dict) else None
    if type(revision) is int and revision != OUTPUT_STAMP_REVISION:
        return (
            f"it was saved with output format revision {revision}, and this "
            f"version of policyengine.py reads only revision "
            f"{OUTPUT_STAMP_REVISION}"
        )
    if stamp is _ABSENT:
        if record is _ABSENT:
            return (
                "it has no record of the renamed stored inputs mapped when it "
                "was calculated, so it was saved by an older policyengine.py "
                "or not saved completely"
                + (
                    f", and may have been calculated without any of: "
                    f"{_describe(register)}"
                    if register
                    else ""
                )
            )
        return (
            "it has no stamp of the register of renamed inputs it was "
            "calculated under"
            + (
                f", so it may have been calculated without any of: "
                f"{_describe(register)}"
                if register
                else ""
            )
        )
    # ``type(...) is int`` rather than ``isinstance``: JSON ``true`` loads as
    # ``True``, which equals 1.
    if not (
        isinstance(stamp, dict)
        and set(stamp) == {"register", "revision", "year_file"}
        and type(revision) is int
        and _is_str_map(stamp["register"])
    ):
        return (
            "its stamp of the register of renamed inputs it was calculated "
            "under is malformed"
        )
    if record is _ABSENT:
        return (
            "it has no record of the renamed stored inputs mapped when it was "
            "calculated"
        )
    if not _is_str_map(record):
        return (
            "its record of the renamed stored inputs mapped when it was "
            "calculated is malformed"
        )
    stamped = stamp["register"]
    outside = dict(record.items() - stamped.items())
    if outside:
        return (
            "its record lists renames outside the register it was stamped "
            f"with: {_describe(outside)}"
        )
    missing, unknown = _register_differences(stamped, register)
    reasons = []
    if missing:
        reasons.append(
            "it was calculated before these renames were registered, so it "
            f"may have been calculated without them: {_describe(missing)}"
        )
    if unknown:
        reasons.append(
            "it was calculated under renames this version of policyengine.py "
            f"does not register: {_describe(unknown)}"
        )
    if stamp["year_file"] is not None:
        reasons.extend(_year_file_reasons(stamp["year_file"], current_year_file))
    return "; ".join(reasons) or None


def _year_file_reasons(stamp: Any, current: Mapping[str, Any]) -> list[str]:
    """Say why the stamp of an output's year file is not ``current``.

    Returns no reason exactly when ``stamp`` equals ``current``.
    """
    revision = stamp.get("revision") if isinstance(stamp, dict) else None
    if type(revision) is int and revision != current["revision"]:
        return [
            "it was calculated from a year file cut with year-file format "
            f"revision {revision}, and this version of policyengine.py reads "
            f"only revision {current['revision']}"
        ]
    if not (
        isinstance(stamp, dict)
        and set(stamp) == {"register", "revision"}
        and type(revision) is int
        and _is_str_map(stamp["register"])
    ):
        return [
            "its record of the stamp of the year file it was calculated from "
            "is malformed"
        ]
    missing, unknown = _register_differences(stamp["register"], current["register"])
    reasons = []
    if missing:
        reasons.append(
            "it was calculated from a year file cut before these renames were "
            f"registered, which may have lost them: {_describe(missing)}"
        )
    if unknown:
        reasons.append(
            "it was calculated from a year file cut under renames this version "
            f"of policyengine.py does not register: {_describe(unknown)}"
        )
    return reasons


def _register_differences(
    stamped: Mapping[str, str], register: Mapping[str, str]
) -> tuple[dict[str, str], dict[str, str]]:
    """Return the entries each register has that the other lacks or retargets.

    The first holds ``register``'s entries that ``stamped`` lacks or maps to
    another live input; the second, ``stamped``'s that ``register`` does.
    """
    missing = {
        legacy: live for legacy, live in register.items() if stamped.get(legacy) != live
    }
    unknown = {
        legacy: live for legacy, live in stamped.items() if register.get(legacy) != live
    }
    return missing, unknown


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
        # RecursionError, a RuntimeError, as does h5py following a soft link
        # at ``name`` that leads back to itself. Any RuntimeError counts as
        # unreadable content: the errors that say nothing about the content
        # are OSErrors, re-raised first.
        return json.loads(node.asstr()[()])
    except (PermissionError, IsADirectoryError, BlockingIOError):
        raise
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
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
