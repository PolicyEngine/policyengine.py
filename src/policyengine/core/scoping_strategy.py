"""Region scoping strategies for geographic simulations.

Provides two concrete strategies for scoping datasets to sub-national regions:

1. RowFilterStrategy: Filters dataset rows where a household variable matches
   a specific value (e.g., UK countries by 'country' field, US places by 'place_fips').

2. WeightReplacementStrategy: Replaces household weights from a pre-computed weight
   matrix stored in GCS (e.g., UK constituencies and local authorities).
"""

import logging
from abc import abstractmethod
from pathlib import Path
from typing import Annotated, Literal, Optional, Union

import numpy as np
import pandas as pd
from microdf import MicroDataFrame
from pydantic import BaseModel, Discriminator

from policyengine.utils.entity_utils import (
    filter_dataset_by_household_variable,
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
    specific variable value (e.g., UK countries, US places/cities).
    """

    strategy_type: Literal["row_filter"] = "row_filter"
    variable_name: str
    variable_value: Union[str, int, float]

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
        )

    @property
    def cache_key(self) -> str:
        return f"row_filter:{self.variable_name}={self.variable_value}"


class WeightReplacementStrategy(RegionScopingStrategy):
    """Scoping strategy that replaces household weights from a pre-computed matrix.

    Used for UK constituencies and local authorities. Instead of removing
    households, this strategy keeps all households but replaces their weights
    with region-specific values from a weight matrix stored in GCS.

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

    def apply(
        self,
        entity_data: dict[str, MicroDataFrame],
        group_entities: list[str],
        year: int,
    ) -> dict[str, MicroDataFrame]:
        from policyengine_core.tools.google_cloud import download_gcs_file

        # Download lookup CSV and find region index
        lookup_path = Path(
            download_gcs_file(
                bucket=self.lookup_csv_bucket,
                file_path=self.lookup_csv_key,
            )
        )
        lookup_df = pd.read_csv(lookup_path)

        region_id = self._find_region_index(lookup_df, self.region_code)

        # Download weight matrix and extract weights for this region.
        # h5py is only needed here, so import lazily to keep
        # `from policyengine.core import ...` light.
        import h5py

        weights_path = download_gcs_file(
            bucket=self.weight_matrix_bucket,
            file_path=self.weight_matrix_key,
        )
        with h5py.File(weights_path, "r") as f:
            weights = f[str(year)][...]

        region_weights = weights[region_id]

        # Validate weight row length matches household count
        household_df = pd.DataFrame(entity_data["household"])
        if len(region_weights) != len(household_df):
            raise ValueError(
                f"Weight matrix row length ({len(region_weights)}) does not match "
                f"household count ({len(household_df)}) for region '{self.region_code}'. "
                f"The weight matrix may be out of date."
            )

        # Replace household weights
        result = {}
        for entity_name, mdf in entity_data.items():
            df = pd.DataFrame(mdf)
            if entity_name == "household":
                df["household_weight"] = region_weights
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
                        df[weight_col] = new_weights

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


ScopingStrategy = Annotated[
    Union[RowFilterStrategy, WeightReplacementStrategy],
    Discriminator("strategy_type"),
]
