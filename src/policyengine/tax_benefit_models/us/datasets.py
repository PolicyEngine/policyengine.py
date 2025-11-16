from policyengine.core import Dataset
from pydantic import BaseModel, ConfigDict
import pandas as pd
from microdf import MicroDataFrame
from pathlib import Path


class USYearData(BaseModel):
    """Entity-level data for a single year."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    person: MicroDataFrame
    marital_unit: MicroDataFrame
    family: MicroDataFrame
    spm_unit: MicroDataFrame
    tax_unit: MicroDataFrame
    household: MicroDataFrame

    def map_to_entity(
        self, source_entity: str, target_entity: str, columns: list[str] = None
    ) -> MicroDataFrame:
        """Map data from source entity to target entity using join keys.

        Args:
            source_entity (str): The source entity name.
            target_entity (str): The target entity name.
            columns (list[str], optional): List of column names to map. If None, maps all columns.

        Returns:
            MicroDataFrame: The mapped data at the target entity level.

        Raises:
            ValueError: If source or target entity is invalid.
        """
        valid_entities = {
            "person",
            "marital_unit",
            "family",
            "spm_unit",
            "tax_unit",
            "household",
        }
        if source_entity not in valid_entities:
            raise ValueError(
                f"Invalid source entity '{source_entity}'. Must be one of {valid_entities}"
            )
        if target_entity not in valid_entities:
            raise ValueError(
                f"Invalid target entity '{target_entity}'. Must be one of {valid_entities}"
            )

        # Get source data
        source_df = getattr(self, source_entity)
        if columns:
            # Select only requested columns (keep join keys)
            join_keys = {
                "person_id",
                "marital_unit_id",
                "family_id",
                "spm_unit_id",
                "tax_unit_id",
                "household_id",
            }
            cols_to_keep = list(
                set(columns) | (join_keys & set(source_df.columns))
            )
            source_df = source_df[cols_to_keep]

        # Determine weight column for target entity
        weight_col_map = {
            "person": "person_weight",
            "marital_unit": "marital_unit_weight",
            "family": "family_weight",
            "spm_unit": "spm_unit_weight",
            "tax_unit": "tax_unit_weight",
            "household": "household_weight",
        }
        target_weight = weight_col_map[target_entity]

        # Same entity - return as is
        if source_entity == target_entity:
            return MicroDataFrame(
                pd.DataFrame(source_df), weights=target_weight
            )

        # Map to different entity
        target_df = getattr(self, target_entity)
        target_key = f"{target_entity}_id"

        # Person to group entity: aggregate person-level data to group level
        if source_entity == "person" and target_entity != "person":
            if target_key in pd.DataFrame(source_df).columns:
                # Merge source (person) with target (group) on target_key
                result = pd.DataFrame(target_df).merge(
                    pd.DataFrame(source_df), on=target_key, how="left"
                )
                return MicroDataFrame(result, weights=target_weight)

        # Group entity to person: expand group-level data to person level
        if source_entity != "person" and target_entity == "person":
            source_key = f"{source_entity}_id"
            if source_key in pd.DataFrame(target_df).columns:
                result = pd.DataFrame(target_df).merge(
                    pd.DataFrame(source_df), on=source_key, how="left"
                )
                return MicroDataFrame(result, weights=target_weight)

        # Group to group: go through person table
        if source_entity != "person" and target_entity != "person":
            # Get person link table with both entity IDs
            person_df = pd.DataFrame(self.person)
            source_key = f"{source_entity}_id"

            # Link source -> person -> target
            if (
                source_key in person_df.columns
                and target_key in person_df.columns
            ):
                person_link = person_df[
                    [source_key, target_key]
                ].drop_duplicates()
                source_with_target = pd.DataFrame(source_df).merge(
                    person_link, on=source_key, how="left"
                )
                result = pd.DataFrame(target_df).merge(
                    source_with_target, on=target_key, how="left"
                )
                return MicroDataFrame(result, weights=target_weight)

        raise ValueError(
            f"Unsupported mapping from {source_entity} to {target_entity}"
        )


class PolicyEngineUSDataset(Dataset):
    """US dataset with multi-year entity-level data."""

    data: USYearData | None = None

    def model_post_init(self, __context):
        """Called after Pydantic initialization."""
        # Make sure we are synchronised between in-memory and storage, at least on initialisation
        if self.data is not None:
            self.save()
        elif self.filepath and not self.data:
            try:
                self.load()
            except FileNotFoundError:
                # File doesn't exist yet, that's OK
                pass

    def save(self) -> None:
        """Save dataset to HDF5 file."""
        filepath = Path(self.filepath)
        if not filepath.parent.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)
        with pd.HDFStore(filepath, mode="w") as store:
            store["person"] = pd.DataFrame(self.data.person)
            store["marital_unit"] = pd.DataFrame(self.data.marital_unit)
            store["family"] = pd.DataFrame(self.data.family)
            store["spm_unit"] = pd.DataFrame(self.data.spm_unit)
            store["tax_unit"] = pd.DataFrame(self.data.tax_unit)
            store["household"] = pd.DataFrame(self.data.household)

    def load(self) -> None:
        """Load dataset from HDF5 file into this instance."""
        filepath = self.filepath
        with pd.HDFStore(filepath, mode="r") as store:
            self.data = USYearData(
                person=MicroDataFrame(
                    store["person"], weights="person_weight"
                ),
                marital_unit=MicroDataFrame(
                    store["marital_unit"], weights="marital_unit_weight"
                ),
                family=MicroDataFrame(
                    store["family"], weights="family_weight"
                ),
                spm_unit=MicroDataFrame(
                    store["spm_unit"], weights="spm_unit_weight"
                ),
                tax_unit=MicroDataFrame(
                    store["tax_unit"], weights="tax_unit_weight"
                ),
                household=MicroDataFrame(
                    store["household"], weights="household_weight"
                ),
            )

    def __repr__(self) -> str:
        if self.data is None:
            return f"<PolicyEngineUSDataset id={self.id} year={self.year} filepath={self.filepath} (not loaded)>"
        else:
            n_people = len(self.data.person)
            n_marital_units = len(self.data.marital_unit)
            n_families = len(self.data.family)
            n_spm_units = len(self.data.spm_unit)
            n_tax_units = len(self.data.tax_unit)
            n_households = len(self.data.household)
            return f"<PolicyEngineUSDataset id={self.id} year={self.year} filepath={self.filepath} people={n_people} marital_units={n_marital_units} families={n_families} spm_units={n_spm_units} tax_units={n_tax_units} households={n_households}>"
