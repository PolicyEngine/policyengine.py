from policyengine.core import Dataset
from pydantic import BaseModel, ConfigDict
import pandas as pd
from microdf import MicroDataFrame
from pathlib import Path


class UKYearData(BaseModel):
    """Entity-level data for a single year."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    person: MicroDataFrame
    benunit: MicroDataFrame
    household: MicroDataFrame

    def map_to_entity(
        self, source_entity: str, target_entity: str, columns: list[str] = None
    ) -> MicroDataFrame:
        """Map data from source entity to target entity using join keys.

        Args:
            source_entity (str): The source entity name ('person', 'benunit', 'household').
            target_entity (str): The target entity name ('person', 'benunit', 'household').
            columns (list[str], optional): List of column names to map. If None, maps all columns.

        Returns:
            MicroDataFrame: The mapped data at the target entity level.

        Raises:
            ValueError: If source or target entity is invalid.
        """
        valid_entities = {"person", "benunit", "household"}
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
            join_keys = {"person_id", "benunit_id", "household_id"}
            cols_to_keep = list(
                set(columns) | (join_keys & set(source_df.columns))
            )
            source_df = source_df[cols_to_keep]

        # Determine weight column for target entity
        weight_col_map = {
            "person": "person_weight",
            "benunit": "benunit_weight",
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

        # Person -> Benunit
        if source_entity == "person" and target_entity == "benunit":
            result = pd.DataFrame(target_df).merge(
                pd.DataFrame(source_df), on="benunit_id", how="left"
            )
            return MicroDataFrame(result, weights=target_weight)

        # Person -> Household
        elif source_entity == "person" and target_entity == "household":
            result = pd.DataFrame(target_df).merge(
                pd.DataFrame(source_df), on="household_id", how="left"
            )
            return MicroDataFrame(result, weights=target_weight)

        # Benunit -> Person
        elif source_entity == "benunit" and target_entity == "person":
            result = pd.DataFrame(target_df).merge(
                pd.DataFrame(source_df), on="benunit_id", how="left"
            )
            return MicroDataFrame(result, weights=target_weight)

        # Benunit -> Household
        elif source_entity == "benunit" and target_entity == "household":
            # Need to go through person to link benunit and household
            person_link = pd.DataFrame(self.person)[
                ["benunit_id", "household_id"]
            ].drop_duplicates()
            source_with_hh = pd.DataFrame(source_df).merge(
                person_link, on="benunit_id", how="left"
            )
            result = pd.DataFrame(target_df).merge(
                source_with_hh, on="household_id", how="left"
            )
            return MicroDataFrame(result, weights=target_weight)

        # Household -> Person
        elif source_entity == "household" and target_entity == "person":
            result = pd.DataFrame(target_df).merge(
                pd.DataFrame(source_df), on="household_id", how="left"
            )
            return MicroDataFrame(result, weights=target_weight)

        # Household -> Benunit
        elif source_entity == "household" and target_entity == "benunit":
            # Need to go through person to link household and benunit
            person_link = pd.DataFrame(self.person)[
                ["benunit_id", "household_id"]
            ].drop_duplicates()
            source_with_bu = pd.DataFrame(source_df).merge(
                person_link, on="household_id", how="left"
            )
            result = pd.DataFrame(target_df).merge(
                source_with_bu, on="benunit_id", how="left"
            )
            return MicroDataFrame(result, weights=target_weight)

        else:
            raise ValueError(
                f"Unsupported mapping from {source_entity} to {target_entity}"
            )


class PolicyEngineUKDataset(Dataset):
    """UK dataset with multi-year entity-level data."""

    data: UKYearData | None = None

    def __init__(self, **kwargs: dict):
        super().__init__(**kwargs)

        # Make sure we are synchronised between in-memory and storage, at least on initialisation
        if "data" in kwargs:
            self.save()
        elif "filepath" in kwargs:
            self.load()

    def save(self) -> None:
        """Save dataset to HDF5 file."""
        filepath = Path(self.filepath)
        if not filepath.parent.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)
        with pd.HDFStore(filepath, mode="w") as store:
            store["person"] = pd.DataFrame(self.data.person)
            store["benunit"] = pd.DataFrame(self.data.benunit)
            store["household"] = pd.DataFrame(self.data.household)

    def load(self) -> None:
        """Load dataset from HDF5 file into this instance."""
        filepath = self.filepath
        with pd.HDFStore(filepath, mode="r") as store:
            self.data = UKYearData(
                person=MicroDataFrame(
                    store["person"], weights="person_weight"
                ),
                benunit=MicroDataFrame(
                    store["benunit"], weights="benunit_weight"
                ),
                household=MicroDataFrame(
                    store["household"], weights="household_weight"
                ),
            )

    def __repr__(self) -> str:
        if self.data is None:
            return f"<PolicyEngineUKDataset id={self.id} year={self.year} filepath={self.filepath} (not loaded)>"
        else:
            n_people = len(self.data.person)
            n_benunits = len(self.data.benunit)
            n_households = len(self.data.household)
            return f"<PolicyEngineUKDataset id={self.id} year={self.year} filepath={self.filepath} people={n_people} benunits={n_benunits} households={n_households}>"


def create_datasets(
    datasets: list[str] = [
        "hf://policyengine/policyengine-uk-data/frs_2023_24.h5",
        "hf://policyengine/policyengine-uk-data/enhanced_frs_2023_24.h5",
    ],
    years: list[int] = [2026, 2027, 2028, 2029, 2030],
) -> None:
    for dataset in datasets:
        from policyengine_uk import Microsimulation
        sim = Microsimulation(dataset=dataset)
        for year in years:
            year_dataset = sim.dataset[year]

            # Convert to pandas DataFrames and add weight columns
            person_df = pd.DataFrame(year_dataset.person)
            benunit_df = pd.DataFrame(year_dataset.benunit)
            household_df = pd.DataFrame(year_dataset.household)

            # Map household weights to person and benunit levels
            person_df = person_df.merge(
                household_df[["household_id", "household_weight"]],
                left_on="person_household_id",
                right_on="household_id",
                how="left"
            )
            person_df = person_df.rename(columns={"household_weight": "person_weight"})
            person_df = person_df.drop(columns=["household_id"])

            # Get household_id for each benunit from person table
            benunit_household_map = person_df[["person_benunit_id", "person_household_id"]].drop_duplicates()
            benunit_df = benunit_df.merge(
                benunit_household_map,
                left_on="benunit_id",
                right_on="person_benunit_id",
                how="left"
            )
            benunit_df = benunit_df.merge(
                household_df[["household_id", "household_weight"]],
                left_on="person_household_id",
                right_on="household_id",
                how="left"
            )
            benunit_df = benunit_df.rename(columns={"household_weight": "benunit_weight"})
            benunit_df = benunit_df.drop(columns=["person_benunit_id", "person_household_id", "household_id"], errors="ignore")

            uk_dataset = PolicyEngineUKDataset(
                name=f"{dataset}-year-{year}",
                description=f"UK Dataset for year {year} based on {dataset}",
                filepath=f"./data/{Path(dataset).stem}_year_{year}.h5",
                year=year,
                data=UKYearData(
                    person=MicroDataFrame(person_df, weights="person_weight"),
                    benunit=MicroDataFrame(benunit_df, weights="benunit_weight"),
                    household=MicroDataFrame(household_df, weights="household_weight"),
                ),
            )
            uk_dataset.save()
