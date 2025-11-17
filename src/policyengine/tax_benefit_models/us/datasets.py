import warnings
from pathlib import Path

import pandas as pd
from microdf import MicroDataFrame
from pydantic import ConfigDict

from policyengine.core import Dataset, YearData


class USYearData(YearData):
    """Entity-level data for a single year."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    person: MicroDataFrame
    marital_unit: MicroDataFrame
    family: MicroDataFrame
    spm_unit: MicroDataFrame
    tax_unit: MicroDataFrame
    household: MicroDataFrame

    @property
    def entity_data(self) -> dict[str, MicroDataFrame]:
        """Return a dictionary of entity names to their data."""
        return {
            "person": self.person,
            "marital_unit": self.marital_unit,
            "family": self.family,
            "spm_unit": self.spm_unit,
            "tax_unit": self.tax_unit,
            "household": self.household,
        }


class PolicyEngineUSDataset(Dataset):
    """US dataset with multi-year entity-level data."""

    data: USYearData | None = None

    def model_post_init(self, __context) -> None:
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
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                category=pd.errors.PerformanceWarning,
                message=".*PyTables will pickle object types.*",
            )
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


def create_datasets(
    datasets: list[str] = [
        "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5",
    ],
    years: list[int] = [2024, 2025, 2026, 2027, 2028],
) -> None:
    """Create PolicyEngineUSDataset instances from HuggingFace dataset paths.

    Args:
        datasets: List of HuggingFace dataset paths (e.g., "hf://policyengine/policyengine-us-data/cps_2024.h5")
        years: List of years to extract data for
    """
    from policyengine_us import Microsimulation

    for dataset in datasets:
        sim = Microsimulation(dataset=dataset)

        for year in years:
            # Get all input variables from the simulation
            # We'll calculate each input variable for the specified year
            entity_data = {
                "person": {},
                "household": {},
                "marital_unit": {},
                "family": {},
                "spm_unit": {},
                "tax_unit": {},
            }

            # First, get ID columns which are structural (not input variables)
            # These define entity membership and relationships
            # For person-level links to group entities, use person_X_id naming
            id_variables = {
                "person": [
                    "person_id",
                    "person_household_id",
                    "person_marital_unit_id",
                    "person_family_id",
                    "person_spm_unit_id",
                    "person_tax_unit_id",
                ],
                "household": ["household_id"],
                "marital_unit": ["marital_unit_id"],
                "family": ["family_id"],
                "spm_unit": ["spm_unit_id"],
                "tax_unit": ["tax_unit_id"],
            }

            for entity_key, var_names in id_variables.items():
                for id_var in var_names:
                    if id_var in sim.tax_benefit_system.variables:
                        values = sim.calculate(id_var, period=year).values
                        entity_data[entity_key][id_var] = values

            # Get input variables and calculate them for this year
            for variable_name in sim.input_variables:
                variable = sim.tax_benefit_system.variables[variable_name]
                entity_key = variable.entity.key

                # Calculate the variable for the given year
                values = sim.calculate(variable_name, period=year).values

                # Store in the appropriate entity dictionary
                entity_data[entity_key][variable_name] = values

            # Build entity DataFrames
            person_df = pd.DataFrame(entity_data["person"])
            household_df = pd.DataFrame(entity_data["household"])
            marital_unit_df = pd.DataFrame(entity_data["marital_unit"])
            family_df = pd.DataFrame(entity_data["family"])
            spm_unit_df = pd.DataFrame(entity_data["spm_unit"])
            tax_unit_df = pd.DataFrame(entity_data["tax_unit"])

            # Add weight columns - household weights are primary, map to all entities
            # Person weights = household weights (mapped via person_household_id)
            if "household_weight" in household_df.columns:
                # Only add person_weight if it doesn't already exist
                if "person_weight" not in person_df.columns:
                    person_df = person_df.merge(
                        household_df[["household_id", "household_weight"]],
                        left_on="person_household_id",
                        right_on="household_id",
                        how="left",
                    )
                    person_df = person_df.rename(
                        columns={"household_weight": "person_weight"}
                    )
                    person_df = person_df.drop(
                        columns=["household_id"], errors="ignore"
                    )

                # Map household weights to other group entities via person table
                for entity_name, entity_df, person_id_col, entity_id_col in [
                    (
                        "marital_unit",
                        marital_unit_df,
                        "person_marital_unit_id",
                        "marital_unit_id",
                    ),
                    ("family", family_df, "person_family_id", "family_id"),
                    (
                        "spm_unit",
                        spm_unit_df,
                        "person_spm_unit_id",
                        "spm_unit_id",
                    ),
                    (
                        "tax_unit",
                        tax_unit_df,
                        "person_tax_unit_id",
                        "tax_unit_id",
                    ),
                ]:
                    # Only add entity weight if it doesn't already exist
                    if f"{entity_name}_weight" not in entity_df.columns:
                        # Get household_id for each entity from person table
                        entity_household_map = person_df[
                            [person_id_col, "person_household_id"]
                        ].drop_duplicates()
                        entity_df = entity_df.merge(
                            entity_household_map,
                            left_on=entity_id_col,
                            right_on=person_id_col,
                            how="left",
                        )
                        entity_df = entity_df.merge(
                            household_df[["household_id", "household_weight"]],
                            left_on="person_household_id",
                            right_on="household_id",
                            how="left",
                        )
                        entity_df = entity_df.rename(
                            columns={
                                "household_weight": f"{entity_name}_weight"
                            }
                        )
                        entity_df = entity_df.drop(
                            columns=[
                                "household_id",
                                "person_household_id",
                                person_id_col,
                            ],
                            errors="ignore",
                        )

                    # Update the entity_data
                    if entity_name == "marital_unit":
                        marital_unit_df = entity_df
                    elif entity_name == "family":
                        family_df = entity_df
                    elif entity_name == "spm_unit":
                        spm_unit_df = entity_df
                    elif entity_name == "tax_unit":
                        tax_unit_df = entity_df

            us_dataset = PolicyEngineUSDataset(
                name=f"{dataset}-year-{year}",
                description=f"US Dataset for year {year} based on {dataset}",
                filepath=f"./data/{Path(dataset).stem}_year_{year}.h5",
                year=year,
                data=USYearData(
                    person=MicroDataFrame(person_df, weights="person_weight"),
                    household=MicroDataFrame(
                        household_df, weights="household_weight"
                    ),
                    marital_unit=MicroDataFrame(
                        marital_unit_df, weights="marital_unit_weight"
                    ),
                    family=MicroDataFrame(family_df, weights="family_weight"),
                    spm_unit=MicroDataFrame(
                        spm_unit_df, weights="spm_unit_weight"
                    ),
                    tax_unit=MicroDataFrame(
                        tax_unit_df, weights="tax_unit_weight"
                    ),
                ),
            )
            us_dataset.save()
