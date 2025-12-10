from pathlib import Path

import pandas as pd
from microdf import MicroDataFrame
from pydantic import ConfigDict

from policyengine.core import Dataset, YearData


class UKYearData(YearData):
    """Entity-level data for a single year."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    person: MicroDataFrame
    benunit: MicroDataFrame
    household: MicroDataFrame

    @property
    def entity_data(self) -> dict[str, MicroDataFrame]:
        """Return a dictionary of entity names to their data."""
        return {
            "person": self.person,
            "benunit": self.benunit,
            "household": self.household,
        }


class PolicyEngineUKDataset(Dataset):
    """UK dataset with multi-year entity-level data."""

    data: UKYearData | None = None

    def model_post_init(self, __context):
        """Called after Pydantic initialization."""
        # Make sure we are synchronised between in-memory and storage, at least on initialisation
        if self.data is not None:
            self.save()
        elif self.filepath and not self.data:
            self.load()

    def save(self) -> None:
        """Save dataset to HDF5 file.

        Converts object columns to categorical dtype to avoid slow pickle serialization.
        """
        filepath = Path(self.filepath)
        if not filepath.parent.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)

        # Convert DataFrames and optimize object columns to categorical
        person_df = pd.DataFrame(self.data.person)
        benunit_df = pd.DataFrame(self.data.benunit)
        household_df = pd.DataFrame(self.data.household)

        # Convert object columns to categorical to avoid pickle serialization
        for col in person_df.columns:
            if person_df[col].dtype == "object":
                person_df[col] = person_df[col].astype("category")

        for col in benunit_df.columns:
            if benunit_df[col].dtype == "object":
                benunit_df[col] = benunit_df[col].astype("category")

        for col in household_df.columns:
            if household_df[col].dtype == "object":
                household_df[col] = household_df[col].astype("category")

        with pd.HDFStore(filepath, mode="w") as store:
            # Use format='table' to support categorical dtypes
            store.put("person", person_df, format="table")
            store.put("benunit", benunit_df, format="table")
            store.put("household", household_df, format="table")

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
    data_folder: str = "./data",
) -> dict[str, PolicyEngineUKDataset]:
    result = {}
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
                how="left",
            )
            person_df = person_df.rename(
                columns={"household_weight": "person_weight"}
            )
            person_df = person_df.drop(columns=["household_id"])

            # Get household_id for each benunit from person table
            benunit_household_map = person_df[
                ["person_benunit_id", "person_household_id"]
            ].drop_duplicates()
            benunit_df = benunit_df.merge(
                benunit_household_map,
                left_on="benunit_id",
                right_on="person_benunit_id",
                how="left",
            )
            benunit_df = benunit_df.merge(
                household_df[["household_id", "household_weight"]],
                left_on="person_household_id",
                right_on="household_id",
                how="left",
            )
            benunit_df = benunit_df.rename(
                columns={"household_weight": "benunit_weight"}
            )
            benunit_df = benunit_df.drop(
                columns=[
                    "person_benunit_id",
                    "person_household_id",
                    "household_id",
                ],
                errors="ignore",
            )

            uk_dataset = PolicyEngineUKDataset(
                id=f"{Path(dataset).stem}_year_{year}",
                name=f"{Path(dataset).stem}-year-{year}",
                description=f"UK Dataset for year {year} based on {Path(dataset).stem}",
                filepath=f"{data_folder}/{Path(dataset).stem}_year_{year}.h5",
                year=int(year),
                data=UKYearData(
                    person=MicroDataFrame(person_df, weights="person_weight"),
                    benunit=MicroDataFrame(
                        benunit_df, weights="benunit_weight"
                    ),
                    household=MicroDataFrame(
                        household_df, weights="household_weight"
                    ),
                ),
            )
            uk_dataset.save()

            dataset_key = f"{Path(dataset).stem}_{year}"
            result[dataset_key] = uk_dataset

    return result


def load_datasets(
    datasets: list[str] = [
        "hf://policyengine/policyengine-uk-data/frs_2023_24.h5",
        "hf://policyengine/policyengine-uk-data/enhanced_frs_2023_24.h5",
    ],
    years: list[int] = [2026, 2027, 2028, 2029, 2030],
    data_folder: str = "./data",
) -> dict[str, PolicyEngineUKDataset]:
    result = {}
    for dataset in datasets:
        for year in years:
            filepath = f"{data_folder}/{Path(dataset).stem}_year_{year}.h5"
            uk_dataset = PolicyEngineUKDataset(
                name=f"{Path(dataset).stem}-year-{year}",
                description=f"UK Dataset for year {year} based on {Path(dataset).stem}",
                filepath=filepath,
                year=int(year),
            )
            uk_dataset.load()

            dataset_key = f"{Path(dataset).stem}_{year}"
            result[dataset_key] = uk_dataset

    return result


def ensure_datasets(
    datasets: list[str] = [
        "hf://policyengine/policyengine-uk-data/frs_2023_24.h5",
        "hf://policyengine/policyengine-uk-data/enhanced_frs_2023_24.h5",
    ],
    years: list[int] = [2026, 2027, 2028, 2029, 2030],
    data_folder: str = "./data",
) -> dict[str, PolicyEngineUKDataset]:
    """Ensure datasets exist, loading if available or creating if not.

    Args:
        datasets: List of HuggingFace dataset paths
        years: List of years to load/create data for
        data_folder: Directory containing or to save the dataset files

    Returns:
        Dictionary mapping dataset keys to PolicyEngineUKDataset objects
    """
    # Check if all dataset files exist
    all_exist = True
    for dataset in datasets:
        for year in years:
            filepath = Path(
                f"{data_folder}/{Path(dataset).stem}_year_{year}.h5"
            )
            if not filepath.exists():
                all_exist = False
                break
        if not all_exist:
            break

    if all_exist:
        return load_datasets(
            datasets=datasets, years=years, data_folder=data_folder
        )
    else:
        return create_datasets(
            datasets=datasets, years=years, data_folder=data_folder
        )
