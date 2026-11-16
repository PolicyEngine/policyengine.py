"""Scope a native projected US dataset without dropping supplied years."""

from __future__ import annotations

import hashlib

import pandas as pd

from policyengine.core.scoping_strategy import RowFilterStrategy
from policyengine.utils.entity_utils import _resolve_id_column

GROUPS = ("household", "tax_unit", "spm_unit", "family", "marital_unit")
ENTITIES = ("person", *GROUPS)


def _digest(values: pd.Series) -> str:
    """Hash native values, dtype and order without exposing household IDs."""
    digest = hashlib.sha256(str(values.dtype).encode())
    digest.update(pd.util.hash_pandas_object(values, index=False).values.tobytes())
    return digest.hexdigest()


def scope_native_history(dataset, strategy: RowFilterStrategy, variables=None):
    """Return an official native dataset for one fixed, closed cohort.

    The caller obtains ``dataset`` from the ordinary native constructor, so
    the country package owns projection and its parameter/reform timing.
    This function only filters the stored tables. It never calculates a
    variable, derives a weight or writes an input file.
    """
    from policyengine_us.data import USMultiYearDataset, USSingleYearDataset

    if type(strategy) is not RowFilterStrategy:
        raise ValueError("Managed scoping supports only RowFilterStrategy.")
    if not isinstance(dataset, USMultiYearDataset) or not dataset.datasets:
        raise ValueError("Managed scoping requires a native USMultiYearDataset.")

    scoped_years = []
    reference_ids = None
    reference_memberships = None
    eternity_inputs = {}
    receipt_years = {}
    for year, single in sorted(dataset.datasets.items()):
        tables = {entity: getattr(single, entity) for entity in ENTITIES}
        for entity, table in tables.items():
            id_column = f"{entity}_id"
            if (
                not isinstance(table, pd.DataFrame)
                or not table.columns.is_unique
                or id_column not in table
                or table[id_column].isna().any()
                or not table[id_column].is_unique
            ):
                raise ValueError(f"Invalid native {entity} IDs or columns for {year}.")

        person = tables["person"]
        household_column = _resolve_id_column(person, "household")
        for group in GROUPS:
            column = _resolve_id_column(person, group)
            if not person[column].isin(tables[group][f"{group}_id"]).all():
                raise ValueError(f"Dangling {group} membership for {year}.")
            if set(person[column]) != set(tables[group][f"{group}_id"]):
                raise ValueError(f"Managed scoping requires members in every {group}.")
            # A group spanning selected and unselected households cannot be
            # calculated on either subset without changing its population.
            membership = pd.DataFrame(
                {"group": person[column], "household": person[household_column]}
            )
            if (
                membership.groupby("group", dropna=False)
                .household.nunique()
                .gt(1)
                .any()
            ):
                raise ValueError(f"Managed scoping requires household-closed {group}s.")

        scoped = strategy.apply(tables, list(GROUPS), int(year))
        # RowFilterStrategy's temporary MicroDataFrame metadata never supplies
        # statistical weights here. Keep only the original table columns.
        scoped = {entity: pd.DataFrame(scoped[entity]).copy() for entity in ENTITIES}
        for table in scoped.values():
            for name in table:
                variable = (variables or {}).get(name)
                if (
                    variable is not None
                    and str(variable.definition_period) == "eternity"
                ):
                    values = table[name].reset_index(drop=True)
                    if name in eternity_inputs and not values.equals(
                        eternity_inputs[name]
                    ):
                        raise ValueError(
                            f"Conflicting ETERNITY input {name} across years."
                        )
                    eternity_inputs[name] = values
        ids = {
            entity: table[f"{entity}_id"].reset_index(drop=True)
            for entity, table in scoped.items()
        }
        scoped_memberships = {
            group: scoped["person"][
                _resolve_id_column(scoped["person"], group)
            ].reset_index(drop=True)
            for group in GROUPS
        }
        if reference_ids is not None and (
            any(not ids[entity].equals(reference_ids[entity]) for entity in ENTITIES)
            or any(
                not scoped_memberships[group].equals(reference_memberships[group])
                for group in GROUPS
            )
        ):
            raise ValueError(
                "Managed scoping requires the same ordered cohort every year."
            )
        reference_ids = ids
        reference_memberships = scoped_memberships
        scoped_years.append(USSingleYearDataset(**scoped, time_period=int(year)))
        receipt_years[str(year)] = {
            "source_rows": {entity: len(table) for entity, table in tables.items()},
            "scoped_rows": {entity: len(table) for entity, table in scoped.items()},
            "id_sha256": {entity: _digest(values) for entity, values in ids.items()},
            "household_weight_sha256": (
                _digest(scoped["household"]["household_weight"])
                if "household_weight" in scoped["household"]
                else None
            ),
        }
    return USMultiYearDataset(datasets=scoped_years), {
        "strategy": strategy.model_dump(mode="json"),
        "cache_key": strategy.cache_key,
        "years": receipt_years,
        "method": "native_projected_history_row_filter",
    }
