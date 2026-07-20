"""Shared utilities for entity relationship building and dataset filtering."""

import logging
from typing import Iterable, Optional, Union

import pandas as pd
from microdf import MicroDataFrame

logger = logging.getLogger(__name__)


def _resolve_id_column(person_data: pd.DataFrame, entity_name: str) -> str:
    """Resolve the ID column name for a group entity in person data.

    Tries `person_{entity}_id` first (standard convention), falls back
    to `{entity}_id` (custom datasets).
    """
    prefixed = f"person_{entity_name}_id"
    bare = f"{entity_name}_id"
    if prefixed in person_data.columns:
        return prefixed
    if bare in person_data.columns:
        return bare
    raise ValueError(
        f"No ID column found for entity '{entity_name}'. "
        f"Tried '{prefixed}' and '{bare}'. "
        f"Available columns: {list(person_data.columns)}"
    )


def build_entity_relationships(
    person_data: pd.DataFrame,
    group_entities: list[str],
) -> pd.DataFrame:
    """Build a DataFrame mapping each person to their containing entities.

    Creates an explicit relationship map between persons and all specified
    group entity types. This enables filtering at any entity level while
    preserving the integrity of all related entities.

    Args:
        person_data: DataFrame of person-level data with ID columns.
        group_entities: List of group entity names (e.g., ["household", "tax_unit"]).

    Returns:
        A DataFrame with person_id and one {entity}_id column per group entity.
    """
    columns = {"person_id": person_data["person_id"].values}
    for entity in group_entities:
        id_col = _resolve_id_column(person_data, entity)
        columns[f"{entity}_id"] = person_data[id_col].values
    return pd.DataFrame(columns)


def _household_mask(
    household_data: pd.DataFrame,
    variable_name: str,
    variable_value: Union[str, int, float],
    additional_filters: Optional[dict[str, Union[str, int, float]]] = None,
):
    """Boolean mask over the household table for a single-value filter.

    Local intermediate only — never crosses a function boundary — so no
    positional-alignment invariant leaks out (callers key on household_id).
    """
    if variable_name not in household_data.columns:
        raise ValueError(
            f"Variable '{variable_name}' not found in household data. "
            f"Available columns: {list(household_data.columns)}"
        )
    additional_filters = additional_filters or {}
    for extra_variable in additional_filters:
        if extra_variable not in household_data.columns:
            raise ValueError(
                f"Variable '{extra_variable}' not found in household data. "
                f"Available columns: {list(household_data.columns)}"
            )

    mask = _values_match(household_data[variable_name].values, variable_value)
    for extra_variable, extra_value in additional_filters.items():
        mask &= _values_match(household_data[extra_variable].values, extra_value)
    return mask


def matching_household_ids(
    entity_data: dict[str, MicroDataFrame],
    variable_name: str,
    variable_value: Union[str, int, float],
    additional_filters: Optional[dict[str, Union[str, int, float]]] = None,
) -> set:
    """Return the set of ``household_id`` values matching a household filter.

    This is the stable, order-proof boundary between "which households" and the
    entity cascade: the household selection is expressed as a set of household
    IDs, never a positional mask.
    """
    household_data = pd.DataFrame(entity_data["household"])
    mask = _household_mask(
        household_data, variable_name, variable_value, additional_filters
    )
    return set(household_data["household_id"].values[mask])


def filter_dataset_by_household_ids(
    entity_data: dict[str, MicroDataFrame],
    group_entities: list[str],
    keep_household_ids: Iterable,
) -> dict[str, MicroDataFrame]:
    """Filter every entity to the given households, cascading to persons and
    all group entities.

    The selection is keyed on the stable ``household_id`` value (a household
    table primary key), so it is independent of row order. Both the single-value
    filter and the multi-region (union) group strategy funnel through here, so
    the cascade lives in exactly one place.
    """
    keep_household_ids = set(keep_household_ids)
    if len(keep_household_ids) == 0:
        raise ValueError("No households match the requested household id set.")

    person_data = pd.DataFrame(entity_data["person"])
    entity_rel = build_entity_relationships(person_data, group_entities)

    # Keep persons whose household is selected, then collect the entity IDs
    # those persons carry (household included, since it is a group entity).
    person_mask = entity_rel["household_id"].isin(keep_household_ids)
    filtered_rel = entity_rel[person_mask]

    filtered_ids = {"person": set(filtered_rel["person_id"])}
    for entity in group_entities:
        filtered_ids[entity] = set(filtered_rel[f"{entity}_id"])

    result = {}
    for entity_name, mdf in entity_data.items():
        df = pd.DataFrame(mdf)
        id_col = f"{entity_name}_id"
        if entity_name in filtered_ids and id_col in df.columns:
            filtered_df = df[df[id_col].isin(filtered_ids[entity_name])]
        else:
            if entity_name != "person":
                logger.warning(
                    "Entity '%s' not in filtered_ids or missing '%s' column; "
                    "passing through unfiltered.",
                    entity_name,
                    id_col,
                )
            filtered_df = df

        weight_col = f"{entity_name}_weight"
        weights = weight_col if weight_col in filtered_df.columns else None
        result[entity_name] = MicroDataFrame(
            filtered_df.reset_index(drop=True),
            weights=weights,
        )

    return result


def filter_dataset_by_household_variable(
    entity_data: dict[str, MicroDataFrame],
    group_entities: list[str],
    variable_name: str,
    variable_value: Union[str, int, float],
    additional_filters: Optional[dict[str, Union[str, int, float]]] = None,
) -> dict[str, MicroDataFrame]:
    """Filter dataset entities to only include households matching variables.

    Thin wrapper composing :func:`matching_household_ids` (which households) with
    :func:`filter_dataset_by_household_ids` (the entity cascade). Public behavior
    is unchanged.

    Args:
        entity_data: Dict mapping entity names to their MicroDataFrames
                     (from YearData.entity_data).
        group_entities: List of group entity names for this country.
        variable_name: The household-level variable to filter on.
        variable_value: The value to match. Handles both str and bytes encoding.
        additional_filters: Optional household-level filters that must also
                            match, keyed by variable name.

    Returns:
        A dict mapping entity names to filtered MicroDataFrames.

    Raises:
        ValueError: If variable_name is not found or no households match.
    """
    keep_household_ids = matching_household_ids(
        entity_data, variable_name, variable_value, additional_filters
    )
    if len(keep_household_ids) == 0:
        raise ValueError(
            f"No households found matching {variable_name}={variable_value}"
        )
    return filter_dataset_by_household_ids(
        entity_data, group_entities, keep_household_ids
    )


def _values_match(values, expected: Union[str, int, float]):
    if isinstance(expected, str):
        return (values == expected) | (values == expected.encode())
    return values == expected
