"""Region scoping strategies for geographic simulations.

Provides three concrete strategies for scoping datasets to sub-national regions:

1. RowFilterStrategy: Filters dataset rows where a household variable matches
   a specific value (e.g., US states by 'state_fips', US congressional districts
   by 'congressional_district_geoid').

2. WeightReplacementStrategy: Legacy strategy that replaces household weights from
   a pre-computed weight matrix resolved locally or from GCS.

3. RegionGroupStrategy: Scopes to the union of several RowFilterStrategy regions
   (e.g. multiple whole states) so one simulation covers the whole group. Used to
   segment a national run into parallel region-group runs.
"""

import logging
from abc import abstractmethod
from typing import Annotated, Literal, Optional, Union

import numpy as np
import pandas as pd
from microdf import MicroDataFrame
from pydantic import BaseModel, Discriminator, Field

from policyengine.utils.entity_utils import (
    filter_dataset_by_household_ids,
    filter_dataset_by_household_variable,
    matching_household_ids,
)

logger = logging.getLogger(__name__)


class RegionScopingStrategy(BaseModel):
    """Base class for region scoping strategies.

    Subclasses implement apply() to scope a dataset's entity data
    to a specific sub-national region.
    """

    strategy_type: str

    @abstractmethod
    def apply(
        self,
        entity_data: dict[str, MicroDataFrame],
        group_entities: list[str],
        year: int,
    ) -> dict[str, MicroDataFrame]:
        """Apply the scoping strategy to entity data.

        Args:
            entity_data: Dict mapping entity names to their MicroDataFrames.
            group_entities: List of group entity names for this country.
            year: The simulation year (used for time-indexed weight matrices).

        Returns:
            A dict mapping entity names to scoped MicroDataFrames.
        """

    @property
    def cache_key(self) -> str:
        """Return a string key for deterministic simulation ID hashing."""
        return f"{self.strategy_type}:{self.model_dump_json()}"


class RowFilterStrategy(RegionScopingStrategy):
    """Scoping strategy that filters dataset rows by a household variable.

    Used for regions where we want to keep only households matching a
    specific variable value (e.g., US states or congressional districts).
    """

    strategy_type: Literal["row_filter"] = "row_filter"
    variable_name: str
    variable_value: Union[str, int, float]
    additional_filters: dict[str, Union[str, int, float]] = Field(default_factory=dict)

    def apply(
        self,
        entity_data: dict[str, MicroDataFrame],
        group_entities: list[str],
        year: int,
    ) -> dict[str, MicroDataFrame]:
        return filter_dataset_by_household_variable(
            entity_data=entity_data,
            group_entities=group_entities,
            variable_name=self.variable_name,
            variable_value=self.variable_value,
            additional_filters=self.additional_filters,
        )

    @property
    def cache_key(self) -> str:
        filters = [
            (self.variable_name, self.variable_value),
            *self.additional_filters.items(),
        ]
        filter_key = ",".join(f"{name}={value}" for name, value in sorted(filters))
        return f"row_filter:{filter_key}"


class WeightReplacementStrategy(RegionScopingStrategy):
    """Scoping strategy that replaces household weights from a pre-computed matrix.

    Instead of removing households, this strategy keeps all households but
    replaces their weights with region-specific values from a locally cached
    or downloaded weight matrix.

    The weight matrix is an HDF5 file with shape (N_regions x N_households),
    where each row contains household weights for a specific region.
    A companion CSV maps region codes/names to row indices.
    """

    strategy_type: Literal["weight_replacement"] = "weight_replacement"
    weight_matrix_bucket: str
    weight_matrix_key: str
    lookup_csv_bucket: str
    lookup_csv_key: str
    region_code: str
    download_missing_assets: bool = True

    def apply(
        self,
        entity_data: dict[str, MicroDataFrame],
        group_entities: list[str],
        year: int,
    ) -> dict[str, MicroDataFrame]:
        from policyengine.data.uk_geography_assets import (
            UKGeographyAssetSpec,
            resolve_uk_geography_asset_paths,
        )

        paths = resolve_uk_geography_asset_paths(
            UKGeographyAssetSpec(
                geography_type="weight replacement",
                weight_matrix_filename=self.weight_matrix_key,
                lookup_csv_filename=self.lookup_csv_key,
                bucket=self.weight_matrix_bucket,
                weight_matrix_bucket=self.weight_matrix_bucket,
                lookup_csv_bucket=self.lookup_csv_bucket,
            ),
            download_missing_assets=self.download_missing_assets,
        )

        lookup_df = pd.read_csv(paths.lookup_csv_path)

        region_id = self._find_region_index(lookup_df, self.region_code)

        # Load weight matrix and extract weights for this region.
        # h5py is only needed here, so import lazily to keep
        # `from policyengine.core import ...` light.
        import h5py

        with h5py.File(paths.weight_matrix_path, "r") as f:
            weights = f[str(year)][...]

        region_weights = weights[region_id]

        # Validate weight row length matches household count
        household_df = pd.DataFrame(entity_data["household"]).copy()
        if len(region_weights) != len(household_df):
            raise ValueError(
                f"Weight matrix row length ({len(region_weights)}) does not match "
                f"household count ({len(household_df)}) for region '{self.region_code}'. "
                f"The weight matrix may be out of date."
            )

        # Replace household weights
        result = {}
        for entity_name, mdf in entity_data.items():
            df = pd.DataFrame(mdf).copy()
            if entity_name == "household":
                df.loc[:, "household_weight"] = region_weights
                result[entity_name] = MicroDataFrame(df, weights="household_weight")
            else:
                weight_col = f"{entity_name}_weight"
                if weight_col in df.columns:
                    # Map new household weights to sub-entities via their
                    # household membership. Build a mapping from household_id
                    # to new weight.
                    hh_ids = household_df["household_id"].values
                    weight_map = dict(zip(hh_ids, region_weights))

                    # Find the entity's household ID column
                    person_hh_col = self._find_household_id_column(df, entity_name)
                    if person_hh_col:
                        new_weights = np.array(
                            [
                                weight_map.get(hh_id, 0.0)
                                for hh_id in df[person_hh_col].values
                            ]
                        )
                        df.loc[:, weight_col] = new_weights

                result[entity_name] = MicroDataFrame(
                    df,
                    weights=(
                        f"{entity_name}_weight"
                        if f"{entity_name}_weight" in df.columns
                        else None
                    ),
                )

        return result

    @staticmethod
    def _find_region_index(lookup_df: pd.DataFrame, region_code: str) -> int:
        """Find the row index for a region in the lookup CSV.

        Searches by 'code' column first, then 'name' column.
        """
        if "code" in lookup_df.columns and region_code in lookup_df["code"].values:
            return lookup_df[lookup_df["code"] == region_code].index[0]
        if "name" in lookup_df.columns and region_code in lookup_df["name"].values:
            return lookup_df[lookup_df["name"] == region_code].index[0]
        raise ValueError(
            f"Region '{region_code}' not found in lookup CSV. "
            f"Available columns: {list(lookup_df.columns)}. "
            f"Searched 'code' and 'name' columns."
        )

    @staticmethod
    def _find_household_id_column(df: pd.DataFrame, entity_name: str) -> Optional[str]:
        """Find the column linking an entity to its household."""
        candidates = [
            "person_household_id",
            f"{entity_name}_household_id",
            "household_id",
        ]
        for col in candidates:
            if col in df.columns:
                return col
        return None

    @property
    def cache_key(self) -> str:
        return f"weight_replacement:{self.weight_matrix_key}:{self.region_code}"


class RegionGroupStrategy(RegionScopingStrategy):
    """Scope to the UNION of several row-filter regions in one simulation.

    Members are ordinary ``RowFilterStrategy`` regions (e.g. several whole
    states); their households are unioned at the household level and the sim
    runs once over that union. Because member regions never share households,
    the union is a disjoint concatenation — no household is counted twice.
    """

    strategy_type: Literal["region_group"] = "region_group"
    members: list[RowFilterStrategy] = Field(min_length=1)

    def apply(
        self,
        entity_data: dict[str, MicroDataFrame],
        group_entities: list[str],
        year: int,
    ) -> dict[str, MicroDataFrame]:
        keep_household_ids: set = set()
        for member in self.members:
            keep_household_ids |= matching_household_ids(
                entity_data,
                member.variable_name,
                member.variable_value,
                member.additional_filters,
            )
        return filter_dataset_by_household_ids(
            entity_data, group_entities, keep_household_ids
        )

    @property
    def cache_key(self) -> str:
        # Sorted so the key is independent of member order (deterministic
        # simulation-ID hashing).
        member_keys = sorted(member.cache_key for member in self.members)
        return "region_group:" + "|".join(member_keys)


ScopingStrategy = Annotated[
    Union[RowFilterStrategy, WeightReplacementStrategy, RegionGroupStrategy],
    Discriminator("strategy_type"),
]
