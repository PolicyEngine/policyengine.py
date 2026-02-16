"""Shared utilities for entity relationship building and dataset filtering."""

import pandas as pd
from microdf import MicroDataFrame


def _resolve_id_column(
    person_data: pd.DataFrame, entity_name: str
) -> str:
    """Resolve the ID column name for a group entity in person data.

    Tries `person_{entity}_id` first (standard convention), falls back
    to `{entity}_id` (custom datasets).
    """
    prefixed = f"person_{entity_name}_id"
    bare = f"{entity_name}_id"
    if prefixed in person_data.columns:
        return prefixed
    return bare


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


def filter_dataset_by_household_variable(
    entity_data: dict[str, MicroDataFrame],
    group_entities: list[str],
    variable_name: str,
    variable_value: str,
) -> dict[str, MicroDataFrame]:
    """Filter dataset entities to only include households where a variable matches.

    Uses an entity relationship approach: builds an explicit map of all
    entity relationships, filters at the household level, and keeps all
    persons in matching households to preserve entity integrity.

    Args:
        entity_data: Dict mapping entity names to their MicroDataFrames
                     (from YearData.entity_data).
        group_entities: List of group entity names for this country.
        variable_name: The household-level variable to filter on.
        variable_value: The value to match. Handles both str and bytes encoding.

    Returns:
        A dict mapping entity names to filtered MicroDataFrames.

    Raises:
        ValueError: If variable_name is not found or no households match.
    """
    person_data = pd.DataFrame(entity_data["person"])
    household_data = pd.DataFrame(entity_data["household"])

    if variable_name not in household_data.columns:
        raise ValueError(
            f"Variable '{variable_name}' not found in household data. "
            f"Available columns: {list(household_data.columns)}"
        )

    # Build entity relationships
    entity_rel = build_entity_relationships(person_data, group_entities)

    # Find matching household IDs
    hh_values = household_data[variable_name].values
    hh_ids = household_data["household_id"].values

    if isinstance(variable_value, str):
        hh_mask = (hh_values == variable_value) | (
            hh_values == variable_value.encode()
        )
    else:
        hh_mask = hh_values == variable_value

    matching_hh_ids = set(hh_ids[hh_mask])

    if len(matching_hh_ids) == 0:
        raise ValueError(
            f"No households found matching {variable_name}={variable_value}"
        )

    # Filter persons to those in matching households
    person_mask = entity_rel["household_id"].isin(matching_hh_ids)
    filtered_rel = entity_rel[person_mask]

    # Collect filtered IDs for each entity
    filtered_ids = {"person": set(filtered_rel["person_id"])}
    for entity in group_entities:
        filtered_ids[entity] = set(filtered_rel[f"{entity}_id"])

    # Filter each entity DataFrame
    result = {}
    for entity_name, mdf in entity_data.items():
        df = pd.DataFrame(mdf)
        id_col = f"{entity_name}_id"
        if entity_name in filtered_ids and id_col in df.columns:
            filtered_df = df[df[id_col].isin(filtered_ids[entity_name])]
        else:
            filtered_df = df

        weight_col = f"{entity_name}_weight"
        weights = weight_col if weight_col in filtered_df.columns else None
        result[entity_name] = MicroDataFrame(
            filtered_df.reset_index(drop=True),
            weights=weights,
        )

    return result
