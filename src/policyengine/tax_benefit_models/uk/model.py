import datetime
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import requests
from microdf import MicroDataFrame

from policyengine.core import (
    Parameter,
    TaxBenefitModel,
    TaxBenefitModelVersion,
    Variable,
)
from policyengine.utils.parameter_labels import (
    build_scale_lookup,
    generate_label_for_parameter,
)

from .datasets import PolicyEngineUKDataset, UKYearData

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation


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

    entity_variables: dict[str, list[str]] = {
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
            "is_SP_age",
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
        ],
        "benunit": [
            # IDs and weights
            "benunit_id",
            "benunit_weight",
            # Structure
            "family_type",
            # Income and benefits
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
            "vat",
            # Housing
            "rent",
            "council_tax",
            "tenure_type",
            # Poverty measures
            "in_poverty_bhc",
            "in_poverty_ahc",
            "in_relative_poverty_bhc",
            "in_relative_poverty_ahc",
        ],
    }

    def __init__(self, **kwargs: dict):
        super().__init__(**kwargs)
        from policyengine_core.enums import Enum
        from policyengine_uk.system import system

        # Attach region registry
        from policyengine.countries.uk.regions import uk_region_registry

        self.region_registry = uk_region_registry

        self.id = f"{self.model.id}@{self.version}"

        for var_obj in system.variables.values():
            # Serialize default_value for JSON compatibility
            default_val = var_obj.default_value
            if var_obj.value_type is Enum:
                default_val = default_val.name
            elif var_obj.value_type is datetime.date:
                default_val = default_val.isoformat()

            variable = Variable(
                id=self.id + "-" + var_obj.name,
                name=var_obj.name,
                tax_benefit_model_version=self,
                entity=var_obj.entity.key,
                description=var_obj.documentation,
                data_type=var_obj.value_type
                if var_obj.value_type is not Enum
                else str,
                default_value=default_val,
                value_type=var_obj.value_type,
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
            self.add_variable(variable)

        from policyengine_core.parameters import Parameter as CoreParameter

        scale_lookup = build_scale_lookup(system)

        for param_node in system.parameters.get_descendants():
            if isinstance(param_node, CoreParameter):
                parameter = Parameter(
                    id=self.id + "-" + param_node.name,
                    name=param_node.name,
                    label=generate_label_for_parameter(
                        param_node, system, scale_lookup
                    ),
                    tax_benefit_model_version=self,
                    description=param_node.description,
                    data_type=type(param_node(2025)),
                    unit=param_node.metadata.get("unit"),
                    _core_param=param_node,
                )
                self.add_parameter(parameter)

    def _build_entity_relationships(
        self, dataset: PolicyEngineUKDataset
    ) -> pd.DataFrame:
        """Build a DataFrame mapping each person to their containing entities.

        Creates an explicit relationship map between persons and all entity
        types (benunit, household). This enables filtering at any entity
        level while preserving the integrity of all related entities.

        Args:
            dataset: The dataset to extract relationships from.

        Returns:
            A DataFrame indexed by person with columns for each entity ID.
        """
        person_data = pd.DataFrame(dataset.data.person)

        # Determine column naming convention
        benunit_id_col = (
            "person_benunit_id"
            if "person_benunit_id" in person_data.columns
            else "benunit_id"
        )
        household_id_col = (
            "person_household_id"
            if "person_household_id" in person_data.columns
            else "household_id"
        )

        entity_rel = pd.DataFrame(
            {
                "person_id": person_data["person_id"].values,
                "benunit_id": person_data[benunit_id_col].values,
                "household_id": person_data[household_id_col].values,
            }
        )

        return entity_rel

    def _filter_dataset_by_household_variable(
        self,
        dataset: PolicyEngineUKDataset,
        variable_name: str,
        variable_value: str,
    ) -> PolicyEngineUKDataset:
        """Filter a dataset to only include households where a variable matches.

        Uses the entity relationship approach: builds an explicit map of all
        entity relationships, filters at the household level, and keeps all
        persons in matching households to preserve entity integrity.

        Args:
            dataset: The dataset to filter.
            variable_name: The name of the household-level variable to filter on.
            variable_value: The value to match. Handles both str and bytes encoding.

        Returns:
            A new filtered dataset containing only matching households.
        """
        # Build entity relationships
        entity_rel = self._build_entity_relationships(dataset)

        # Get household-level variable values
        household_data = pd.DataFrame(dataset.data.household)

        if variable_name not in household_data.columns:
            raise ValueError(
                f"Variable '{variable_name}' not found in household data. "
                f"Available columns: {list(household_data.columns)}"
            )

        hh_values = household_data[variable_name].values
        hh_ids = household_data["household_id"].values

        # Create mask for matching households, handling bytes encoding
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

        # Filter entity_rel to persons in matching households
        person_mask = entity_rel["household_id"].isin(matching_hh_ids)
        filtered_entity_rel = entity_rel[person_mask]

        # Get the filtered entity IDs
        filtered_person_ids = set(filtered_entity_rel["person_id"])
        filtered_household_ids = matching_hh_ids
        filtered_benunit_ids = set(filtered_entity_rel["benunit_id"])

        # Filter each entity DataFrame
        person_df = pd.DataFrame(dataset.data.person)
        household_df = pd.DataFrame(dataset.data.household)
        benunit_df = pd.DataFrame(dataset.data.benunit)

        filtered_person = person_df[
            person_df["person_id"].isin(filtered_person_ids)
        ]
        filtered_household = household_df[
            household_df["household_id"].isin(filtered_household_ids)
        ]
        filtered_benunit = benunit_df[
            benunit_df["benunit_id"].isin(filtered_benunit_ids)
        ]

        # Create filtered dataset
        return PolicyEngineUKDataset(
            id=dataset.id + f"_filtered_{variable_name}_{variable_value}",
            name=dataset.name,
            description=f"{dataset.description} (filtered: {variable_name}={variable_value})",
            filepath=dataset.filepath,
            year=dataset.year,
            is_output_dataset=dataset.is_output_dataset,
            data=UKYearData(
                person=MicroDataFrame(
                    filtered_person.reset_index(drop=True),
                    weights="person_weight",
                ),
                benunit=MicroDataFrame(
                    filtered_benunit.reset_index(drop=True),
                    weights="benunit_weight",
                ),
                household=MicroDataFrame(
                    filtered_household.reset_index(drop=True),
                    weights="household_weight",
                ),
            ),
        )

    def run(self, simulation: "Simulation") -> "Simulation":
        from policyengine_uk import Microsimulation
        from policyengine_uk.data import UKSingleYearDataset

        from policyengine.utils.parametric_reforms import (
            simulation_modifier_from_parameter_values,
        )

        assert isinstance(simulation.dataset, PolicyEngineUKDataset)

        dataset = simulation.dataset
        dataset.load()

        # Apply regional filtering if specified
        if simulation.filter_field and simulation.filter_value:
            dataset = self._filter_dataset_by_household_variable(
                dataset, simulation.filter_field, simulation.filter_value
            )

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
        elif simulation.policy:
            modifier = simulation_modifier_from_parameter_values(
                simulation.policy.parameter_values
            )
            modifier(microsim)

        if (
            simulation.dynamic
            and simulation.dynamic.simulation_modifier is not None
        ):
            simulation.dynamic.simulation_modifier(microsim)
        elif simulation.dynamic:
            modifier = simulation_modifier_from_parameter_values(
                simulation.dynamic.parameter_values
            )
            modifier(microsim)

        data = {
            "person": pd.DataFrame(),
            "benunit": pd.DataFrame(),
            "household": pd.DataFrame(),
        }

        for entity, variables in self.entity_variables.items():
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
            id=simulation.id,
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

    def save(self, simulation: "Simulation"):
        """Save the simulation's output dataset."""
        simulation.output_dataset.save()

    def load(self, simulation: "Simulation"):
        """Load the simulation's output dataset."""
        import os

        filepath = str(
            Path(simulation.dataset.filepath).parent / (simulation.id + ".h5")
        )

        simulation.output_dataset = PolicyEngineUKDataset(
            id=simulation.id,
            name=simulation.dataset.name,
            description=simulation.dataset.description,
            filepath=filepath,
            year=simulation.dataset.year,
            is_output_dataset=True,
        )

        # Load timestamps from file system metadata
        if os.path.exists(filepath):
            simulation.created_at = datetime.datetime.fromtimestamp(
                os.path.getctime(filepath)
            )
            simulation.updated_at = datetime.datetime.fromtimestamp(
                os.path.getmtime(filepath)
            )


uk_latest = PolicyEngineUKLatest()
