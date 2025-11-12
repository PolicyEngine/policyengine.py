from policyengine.core import *
from pydantic import BaseModel, Field, ConfigDict
import pandas as pd
from typing import Dict
import datetime
import requests
from policyengine.utils import parse_safe_date
from pathlib import Path
from importlib.metadata import version
from microdf import MicroDataFrame


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

        # Make sure we are synchronised between in-memory and storage, at least on initialisation.
        if "data" in kwargs:
            self.save()
        elif "filepath" in kwargs:
            self.load()

    def save(self) -> None:
        """Save dataset to HDF5 file."""
        filepath = self.filepath
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


class PolicyEngineUK(TaxBenefitModel):
    id: str = "policyengine-uk"
    description: str = "The UK's open-source dynamic tax and benefit microsimulation model maintained by PolicyEngine."


uk_model = PolicyEngineUK()

pkg_version = version("policyengine-uk")

# Get published time from PyPI
response = requests.get("https://pypi.org/pypi/policyengine-uk/json")
data = response.json()
upload_time = data["releases"][pkg_version][0]["upload_time_iso_8601"]


class PolicyEngineUKLatest(TaxBenefitModelVersion):
    model: TaxBenefitModel = uk_model
    version: str = pkg_version
    created_at: datetime.datetime = datetime.datetime.fromisoformat(
        upload_time
    )

    def __init__(self, **kwargs: dict):
        super().__init__(**kwargs)
        from policyengine_uk.system import system
        from policyengine_core.enums import Enum

        self.id = f"{self.model.id}@{self.version}"

        self.variables = []
        for var_obj in system.variables.values():
            variable = Variable(
                id=self.id + "-" + var_obj.name,
                name=var_obj.name,
                tax_benefit_model_version=self,
                entity=var_obj.entity.key,
                description=var_obj.documentation,
                data_type=var_obj.value_type
                if var_obj.value_type is not Enum
                else str,
            )
            if (
                hasattr(var_obj, "possible_values")
                and var_obj.possible_values is not None
            ):
                variable.possible_values = list(
                    map(
                        lambda x: x.name,
                        var_obj.possible_values._value2member_map_.values(),
                    )
                )
            self.variables.append(variable)

        self.parameters = []
        from policyengine_core.parameters import Parameter as CoreParameter

        for param_node in system.parameters.get_descendants():
            if isinstance(param_node, CoreParameter):
                parameter = Parameter(
                    id=self.id + "-" + param_node.name,
                    name=param_node.name,
                    tax_benefit_model_version=self,
                    description=param_node.description,
                    data_type=type(
                        param_node(2025)
                    ),  # Example year to infer type
                    unit=param_node.metadata.get("unit"),
                )
                self.parameters.append(parameter)

                for i in range(len(param_node.values_list)):
                    param_at_instant = param_node.values_list[i]
                    if i + 1 < len(param_node.values_list):
                        next_instant = param_node.values_list[i + 1]
                    else:
                        next_instant = None
                    parameter_value = ParameterValue(
                        parameter=parameter,
                        start_date=parse_safe_date(
                            param_at_instant.instant_str
                        ),
                        end_date=parse_safe_date(next_instant.instant_str)
                        if next_instant
                        else None,
                        value=param_at_instant.value,
                    )
                    self.parameter_values.append(parameter_value)

    def run(self, simulation: "Simulation") -> "Simulation":
        from policyengine_uk import Microsimulation
        from policyengine_uk.data import UKSingleYearDataset

        assert isinstance(simulation.dataset, PolicyEngineUKDataset)

        dataset = simulation.dataset
        dataset.load()
        input_data = UKSingleYearDataset(
            person=dataset.data.person,
            benunit=dataset.data.benunit,
            household=dataset.data.household,
            fiscal_year=dataset.year,
        )
        microsim = Microsimulation(dataset=input_data)

        if (
            simulation.policy
            and simulation.policy.simulation_modifier is not None
        ):
            simulation.policy.simulation_modifier(microsim)

        if (
            simulation.dynamic
            and simulation.dynamic.simulation_modifier is not None
        ):
            simulation.dynamic.simulation_modifier(microsim)

        # Allow custom variable selection, or use defaults
        if simulation.variables is not None:
            entity_variables = simulation.variables
        else:
            # Default comprehensive variable set
            entity_variables = {
                "person": [
                    # IDs and weights
                    "person_id",
                    "benunit_id",
                    "household_id",
                    "person_weight",
                    # Demographics
                    "age",
                    "gender",
                    "is_adult",
                    "is_child",
                    # Income
                    "employment_income",
                    "self_employment_income",
                    "pension_income",
                    "private_pension_income",
                    "savings_interest_income",
                    "dividend_income",
                    "property_income",
                    "total_income",
                    "earned_income",
                    # Benefits
                    "universal_credit",
                    "child_benefit",
                    "pension_credit",
                    "income_support",
                    "working_tax_credit",
                    "child_tax_credit",
                    # Tax
                    "income_tax",
                    "national_insurance",
                    "net_income",
                ],
                "benunit": [
                    # IDs and weights
                    "benunit_id",
                    "benunit_weight",
                    # Structure
                    "family_type",
                    "num_adults",
                    "num_children",
                    # Income and benefits
                    "benunit_total_income",
                    "benunit_net_income",
                    "universal_credit",
                    "child_benefit",
                    "working_tax_credit",
                    "child_tax_credit",
                ],
                "household": [
                    # IDs and weights
                    "household_id",
                    "household_weight",
                    # Income measures
                    "household_net_income",
                    "hbai_household_net_income",
                    "equiv_hbai_household_net_income",
                    "household_market_income",
                    "household_gross_income",
                    # Benefits and tax
                    "household_benefits",
                    "household_tax",
                    # Housing
                    "rent",
                    "council_tax",
                    "housing_benefit",
                ],
            }

        data = {
            "person": pd.DataFrame(),
            "benunit": pd.DataFrame(),
            "household": pd.DataFrame(),
        }

        for entity, variables in entity_variables.items():
            for var in variables:
                data[entity][var] = microsim.calculate(
                    var, period=simulation.dataset.year, map_to=entity
                ).values

        data["person"] = MicroDataFrame(
            data["person"], weights="person_weight"
        )
        data["benunit"] = MicroDataFrame(
            data["benunit"], weights="benunit_weight"
        )
        data["household"] = MicroDataFrame(
            data["household"], weights="household_weight"
        )

        simulation.output_dataset = PolicyEngineUKDataset(
            name=dataset.name,
            description=dataset.description,
            filepath=str(
                Path(simulation.dataset.filepath).parent
                / (simulation.id + ".h5")
            ),
            year=simulation.dataset.year,
            is_output_dataset=True,
            data=UKYearData(
                person=data["person"],
                benunit=data["benunit"],
                household=data["household"],
            ),
        )

        simulation.output_dataset.save()


# Rebuild models to resolve forward references
PolicyEngineUKDataset.model_rebuild()
PolicyEngineUKLatest.model_rebuild()

uk_latest = PolicyEngineUKLatest()
