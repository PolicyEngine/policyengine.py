from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict
import pandas as pd
from microdf import MicroDataFrame

from .tax_benefit_model import TaxBenefitModel
from .dataset_version import DatasetVersion


class Dataset(BaseModel):
    """Base class for datasets.

    The data field contains entity-level data as a BaseModel with DataFrame fields.

    Example:
        class YearData(BaseModel):
            model_config = ConfigDict(arbitrary_types_allowed=True)
            person: pd.DataFrame
            household: pd.DataFrame

        class MyDataset(Dataset):
            data: YearData | None = None
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    dataset_version: DatasetVersion | None = None
    filepath: str
    is_output_dataset: bool = False
    tax_benefit_model: TaxBenefitModel | None = None
    year: int

    data: BaseModel | None = None


def map_to_entity(
    entity_data: dict[str, MicroDataFrame],
    source_entity: str,
    target_entity: str,
    person_entity: str = "person",
    columns: list[str] | None = None,
) -> MicroDataFrame:
    """Map data from source entity to target entity using join keys.

    This is a generic entity mapping utility that handles:
    - Same entity mapping (returns as is)
    - Person to group entity mapping (aggregates values)
    - Group to person entity mapping (expands values)
    - Group to group entity mapping (aggregates through person entity)

    Args:
        entity_data: Dictionary mapping entity names to their MicroDataFrame data
        source_entity: The source entity name
        target_entity: The target entity name
        person_entity: The name of the person entity (default "person")
        columns: List of column names to map. If None, maps all columns

    Returns:
        MicroDataFrame: The mapped data at the target entity level

    Raises:
        ValueError: If source or target entity is invalid
    """
    valid_entities = set(entity_data.keys())

    if source_entity not in valid_entities:
        raise ValueError(
            f"Invalid source entity '{source_entity}'. Must be one of {valid_entities}"
        )
    if target_entity not in valid_entities:
        raise ValueError(
            f"Invalid target entity '{target_entity}'. Must be one of {valid_entities}"
        )

    # Get source data (convert to plain DataFrame to avoid weighted operations during mapping)
    source_df = pd.DataFrame(entity_data[source_entity])

    if columns:
        # Select only requested columns (keep all ID columns for joins)
        id_cols = {col for col in source_df.columns if col.endswith("_id")}
        cols_to_keep = list(set(columns) | id_cols)
        source_df = source_df[cols_to_keep]

    # Determine weight column for target entity
    target_weight = f"{target_entity}_weight"

    # Same entity - return as is
    if source_entity == target_entity:
        return MicroDataFrame(source_df, weights=target_weight)

    # Get target data and key
    target_df = entity_data[target_entity]
    target_key = f"{target_entity}_id"

    # Person to group entity: aggregate person-level data to group level
    if source_entity == person_entity and target_entity != person_entity:
        # Check for both naming patterns: "entity_id" and "person_entity_id"
        person_target_key = f"{person_entity}_{target_entity}_id"
        join_key = (
            person_target_key
            if person_target_key in source_df.columns
            else target_key
        )

        if join_key in source_df.columns:
            # Get columns to aggregate (exclude ID and weight columns)
            id_cols = {col for col in source_df.columns if col.endswith("_id")}
            weight_cols = {
                col for col in source_df.columns if col.endswith("_weight")
            }
            agg_cols = [
                c
                for c in source_df.columns
                if c not in id_cols and c not in weight_cols
            ]

            # Group by join key and sum
            aggregated = source_df.groupby(join_key, as_index=False)[
                agg_cols
            ].sum()

            # Rename join key to target key if needed
            if join_key != target_key:
                aggregated = aggregated.rename(columns={join_key: target_key})

            # Merge with target, preserving original order
            target_pd = pd.DataFrame(target_df)[[target_key, target_weight]]
            target_pd = target_pd.reset_index(drop=False)
            result = target_pd.merge(aggregated, on=target_key, how="left")

            # Sort back to original order
            result = (
                result.sort_values("index")
                .drop("index", axis=1)
                .reset_index(drop=True)
            )

            # Fill NaN with 0 for groups with no members in source entity
            result[agg_cols] = result[agg_cols].fillna(0)

            return MicroDataFrame(result, weights=target_weight)

    # Group entity to person: expand group-level data to person level
    if source_entity != person_entity and target_entity == person_entity:
        source_key = f"{source_entity}_id"
        # Check for both naming patterns
        person_source_key = f"{person_entity}_{source_entity}_id"

        target_pd = pd.DataFrame(target_df)
        join_key = (
            person_source_key
            if person_source_key in target_pd.columns
            else source_key
        )

        if join_key in target_pd.columns:
            # Rename source key to match join key if needed
            if join_key != source_key and source_key in source_df.columns:
                source_df = source_df.rename(columns={source_key: join_key})

            result = target_pd.merge(source_df, on=join_key, how="left")
            return MicroDataFrame(result, weights=target_weight)

    # Group to group: go through person table
    if source_entity != person_entity and target_entity != person_entity:
        # Get person link table with both entity IDs
        person_df = pd.DataFrame(entity_data[person_entity])
        source_key = f"{source_entity}_id"

        # Check for both naming patterns for person-level links
        person_source_key = f"{person_entity}_{source_entity}_id"
        person_target_key = f"{person_entity}_{target_entity}_id"

        # Determine which keys exist in person table
        source_link_key = (
            person_source_key
            if person_source_key in person_df.columns
            else source_key
        )
        target_link_key = (
            person_target_key
            if person_target_key in person_df.columns
            else target_key
        )

        # Link source -> person -> target
        if (
            source_link_key in person_df.columns
            and target_link_key in person_df.columns
        ):
            person_link = person_df[
                [source_link_key, target_link_key]
            ].drop_duplicates()

            # Rename source key to match link key if needed
            source_df_copy = source_df.copy()
            if (
                source_link_key != source_key
                and source_key in source_df_copy.columns
            ):
                source_df_copy = source_df_copy.rename(
                    columns={source_key: source_link_key}
                )

            # Join source data with target key
            source_with_target = source_df_copy.merge(
                person_link, on=source_link_key, how="left"
            )

            # Aggregate to target level
            id_cols = {
                col
                for col in source_with_target.columns
                if col.endswith("_id")
            }
            weight_cols = {
                col
                for col in source_with_target.columns
                if col.endswith("_weight")
            }
            agg_cols = [
                c
                for c in source_with_target.columns
                if c not in id_cols and c not in weight_cols
            ]

            aggregated = source_with_target.groupby(
                target_link_key, as_index=False
            )[agg_cols].sum()

            # Rename target link key to target key if needed
            if target_link_key != target_key:
                aggregated = aggregated.rename(
                    columns={target_link_key: target_key}
                )

            # Merge with target, preserving original order
            target_pd = pd.DataFrame(target_df)[[target_key, target_weight]]
            target_pd = target_pd.reset_index(drop=False)
            result = target_pd.merge(aggregated, on=target_key, how="left")

            # Sort back to original order
            result = (
                result.sort_values("index")
                .drop("index", axis=1)
                .reset_index(drop=True)
            )

            # Fill NaN with 0
            result[agg_cols] = result[agg_cols].fillna(0)

            return MicroDataFrame(result, weights=target_weight)

    raise ValueError(
        f"Unsupported mapping from {source_entity} to {target_entity}"
    )
