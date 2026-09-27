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
#: ``ensure_datasets`` regenerates it. A new register entry would need those
#: checks to tell files written before it apart as well.
RENAMES_H5_DATASET = "policyengine_legacy_input_renames"

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


def read_renames_record(path: str | Path) -> dict[str, str] | None:
    """Return the renames record stored in an H5 file, or ``None``.

    ``None`` means the file stores no record (see :data:`RENAMES_H5_DATASET`)
    or is not an H5 file.
    """
    import h5py

    try:
        with h5py.File(path, "r") as file:
            if RENAMES_H5_DATASET not in file:
                return None
            raw = file[RENAMES_H5_DATASET].asstr()[()]
    except OSError:
        return None
    return dict(json.loads(raw))


def write_renames_record(path: str | Path, record: Mapping[str, str]) -> None:
    """Store a renames record in an H5 file, replacing any it has."""
    import h5py

    with h5py.File(path, "a") as file:
        if RENAMES_H5_DATASET in file:
            del file[RENAMES_H5_DATASET]
        # UTF-8 JSON in a dataset, as for the SPM receipt of a saved output.
        file.create_dataset(
            RENAMES_H5_DATASET,
            data=json.dumps(dict(record), sort_keys=True),
            dtype=h5py.string_dtype("utf-8"),
        )


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
    boolean. Otherwise this raises ``ValueError`` rather than set misaligned
    or invented values.

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
            values = _live_values(table[legacy], variable, context)
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


def _live_values(stored: pd.Series, variable: Any, context: str) -> np.ndarray:
    if stored.isna().any():
        raise ValueError(f"{context}: the stored column has missing values.")
    if variable.value_type is not bool:
        return np.asarray(stored.to_numpy())
    if pd.api.types.is_bool_dtype(stored.dtype):
        return np.asarray(stored.to_numpy(dtype=bool))
    if pd.api.types.is_numeric_dtype(stored.dtype) and stored.isin((0, 1)).all():
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
