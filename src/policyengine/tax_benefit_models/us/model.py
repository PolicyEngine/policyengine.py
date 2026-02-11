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

from .datasets import PolicyEngineUSDataset, USYearData

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation


class PolicyEngineUS(TaxBenefitModel):
    id: str = "policyengine-us"
    description: str = "The US's open-source dynamic tax and benefit microsimulation model maintained by PolicyEngine."


us_model = PolicyEngineUS()


def _get_us_package_metadata():
    """Get PolicyEngine US package version and upload time (lazy-loaded)."""
    pkg_version = version("policyengine-us")
    # Get published time from PyPI
    response = requests.get("https://pypi.org/pypi/policyengine-us/json")
    data = response.json()
    upload_time = data["releases"][pkg_version][0]["upload_time_iso_8601"]
    return pkg_version, upload_time


class PolicyEngineUSLatest(TaxBenefitModelVersion):
    model: TaxBenefitModel = us_model
    version: str = None
    created_at: datetime.datetime = None

    entity_variables: dict[str, list[str]] = {
        "person": [
            # IDs and weights
            "person_id",
            "marital_unit_id",
            "family_id",
            "spm_unit_id",
            "tax_unit_id",
            "household_id",
            "person_weight",
            # Demographics
            "age",
            "is_child",
            "is_adult",
            # Income
            "employment_income",
            # Benefits
            "ssi",
            "social_security",
            "medicaid",
            "unemployment_compensation",
        ],
        "marital_unit": [
            "marital_unit_id",
            "marital_unit_weight",
        ],
        "family": [
            "family_id",
            "family_weight",
        ],
        "spm_unit": [
            "spm_unit_id",
            "spm_unit_weight",
            "snap",
            "tanf",
            "spm_unit_net_income",
            # Poverty measures
            "spm_unit_is_in_spm_poverty",
            "spm_unit_is_in_deep_spm_poverty",
        ],
        "tax_unit": [
            "tax_unit_id",
            "tax_unit_weight",
            "income_tax",
            "employee_payroll_tax",
            "eitc",
            "ctc",
        ],
        "household": [
            "household_id",
            "household_weight",
            "household_net_income",
            "household_benefits",
            "household_tax",
            "household_market_income",
        ],
    }

    def __init__(self, **kwargs: dict):
        # Lazy-load package metadata if not provided
        if "version" not in kwargs or kwargs.get("version") is None:
            pkg_version, upload_time = _get_us_package_metadata()
            kwargs["version"] = pkg_version
            kwargs["created_at"] = datetime.datetime.fromisoformat(upload_time)

        super().__init__(**kwargs)
        from policyengine_core.enums import Enum
        from policyengine_us.system import system

        # Attach region registry
        from policyengine.countries.us.regions import us_region_registry

        self.region_registry = us_region_registry

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
        self, dataset: PolicyEngineUSDataset
    ) -> pd.DataFrame:
        """Build a DataFrame mapping each person to their containing entities.

        Creates an explicit relationship map between persons and all entity
        types (household, tax_unit, spm_unit, family, marital_unit). This
        enables filtering at any entity level while preserving the integrity
        of all related entities.

        Args:
            dataset: The dataset to extract relationships from.

        Returns:
            A DataFrame indexed by person with columns for each entity ID.
        """
        person_data = pd.DataFrame(dataset.data.person)

        # Determine column naming convention
        household_id_col = (
            "person_household_id"
            if "person_household_id" in person_data.columns
            else "household_id"
        )
        tax_unit_id_col = (
            "person_tax_unit_id"
            if "person_tax_unit_id" in person_data.columns
            else "tax_unit_id"
        )
        spm_unit_id_col = (
            "person_spm_unit_id"
            if "person_spm_unit_id" in person_data.columns
            else "spm_unit_id"
        )
        family_id_col = (
            "person_family_id"
            if "person_family_id" in person_data.columns
            else "family_id"
        )
        marital_unit_id_col = (
            "person_marital_unit_id"
            if "person_marital_unit_id" in person_data.columns
            else "marital_unit_id"
        )

        entity_rel = pd.DataFrame(
            {
                "person_id": person_data["person_id"].values,
                "household_id": person_data[household_id_col].values,
                "tax_unit_id": person_data[tax_unit_id_col].values,
                "spm_unit_id": person_data[spm_unit_id_col].values,
                "family_id": person_data[family_id_col].values,
                "marital_unit_id": person_data[marital_unit_id_col].values,
            }
        )

        return entity_rel

    def _filter_dataset_by_household_variable(
        self,
        dataset: PolicyEngineUSDataset,
        variable_name: str,
        variable_value: str,
    ) -> PolicyEngineUSDataset:
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
        filtered_tax_unit_ids = set(filtered_entity_rel["tax_unit_id"])
        filtered_spm_unit_ids = set(filtered_entity_rel["spm_unit_id"])
        filtered_family_ids = set(filtered_entity_rel["family_id"])
        filtered_marital_unit_ids = set(filtered_entity_rel["marital_unit_id"])

        # Filter each entity DataFrame
        person_df = pd.DataFrame(dataset.data.person)
        household_df = pd.DataFrame(dataset.data.household)
        tax_unit_df = pd.DataFrame(dataset.data.tax_unit)
        spm_unit_df = pd.DataFrame(dataset.data.spm_unit)
        family_df = pd.DataFrame(dataset.data.family)
        marital_unit_df = pd.DataFrame(dataset.data.marital_unit)

        filtered_person = person_df[
            person_df["person_id"].isin(filtered_person_ids)
        ]
        filtered_household = household_df[
            household_df["household_id"].isin(filtered_household_ids)
        ]
        filtered_tax_unit = tax_unit_df[
            tax_unit_df["tax_unit_id"].isin(filtered_tax_unit_ids)
        ]
        filtered_spm_unit = spm_unit_df[
            spm_unit_df["spm_unit_id"].isin(filtered_spm_unit_ids)
        ]
        filtered_family = family_df[
            family_df["family_id"].isin(filtered_family_ids)
        ]
        filtered_marital_unit = marital_unit_df[
            marital_unit_df["marital_unit_id"].isin(filtered_marital_unit_ids)
        ]

        # Create filtered dataset
        return PolicyEngineUSDataset(
            id=dataset.id + f"_filtered_{variable_name}_{variable_value}",
            name=dataset.name,
            description=f"{dataset.description} (filtered: {variable_name}={variable_value})",
            filepath=dataset.filepath,
            year=dataset.year,
            is_output_dataset=dataset.is_output_dataset,
            data=USYearData(
                person=MicroDataFrame(
                    filtered_person.reset_index(drop=True),
                    weights="person_weight",
                ),
                household=MicroDataFrame(
                    filtered_household.reset_index(drop=True),
                    weights="household_weight",
                ),
                tax_unit=MicroDataFrame(
                    filtered_tax_unit.reset_index(drop=True),
                    weights="tax_unit_weight",
                ),
                spm_unit=MicroDataFrame(
                    filtered_spm_unit.reset_index(drop=True),
                    weights="spm_unit_weight",
                ),
                family=MicroDataFrame(
                    filtered_family.reset_index(drop=True),
                    weights="family_weight",
                ),
                marital_unit=MicroDataFrame(
                    filtered_marital_unit.reset_index(drop=True),
                    weights="marital_unit_weight",
                ),
            ),
        )

    def run(self, simulation: "Simulation") -> "Simulation":
        from policyengine_us import Microsimulation
        from policyengine_us.system import system

        from policyengine.utils.parametric_reforms import (
            reform_dict_from_parameter_values,
        )

        assert isinstance(simulation.dataset, PolicyEngineUSDataset)

        dataset = simulation.dataset
        dataset.load()

        # Apply regional filtering if specified
        if simulation.filter_field and simulation.filter_value:
            dataset = self._filter_dataset_by_household_variable(
                dataset, simulation.filter_field, simulation.filter_value
            )

        # Build reform dict from policy and dynamic parameter values
        # US requires reforms to be passed at Microsimulation construction time
        # (unlike UK which supports p.update() after construction)
        reform_dict = None

        # Collect policy reforms
        if simulation.policy:
            if simulation.policy.simulation_modifier is not None:
                # Custom simulation modifier - extract parameter values if available
                # Fall back to parameter_values if no custom modifier logic needed
                if simulation.policy.parameter_values:
                    reform_dict = reform_dict_from_parameter_values(
                        simulation.policy.parameter_values
                    )
            elif simulation.policy.parameter_values:
                reform_dict = reform_dict_from_parameter_values(
                    simulation.policy.parameter_values
                )

        # Merge dynamic reforms into reform_dict
        if simulation.dynamic:
            dynamic_reform = None
            if simulation.dynamic.simulation_modifier is not None:
                if simulation.dynamic.parameter_values:
                    dynamic_reform = reform_dict_from_parameter_values(
                        simulation.dynamic.parameter_values
                    )
            elif simulation.dynamic.parameter_values:
                dynamic_reform = reform_dict_from_parameter_values(
                    simulation.dynamic.parameter_values
                )

            if dynamic_reform:
                if reform_dict is None:
                    reform_dict = dynamic_reform
                else:
                    # Merge dynamic reforms into policy reforms
                    for param_name, period_values in dynamic_reform.items():
                        if param_name not in reform_dict:
                            reform_dict[param_name] = {}
                        reform_dict[param_name].update(period_values)

        # Create Microsimulation with reform at construction time
        microsim = Microsimulation(reform=reform_dict)
        self._build_simulation_from_dataset(microsim, dataset, system)

        data = {
            "person": pd.DataFrame(),
            "marital_unit": pd.DataFrame(),
            "family": pd.DataFrame(),
            "spm_unit": pd.DataFrame(),
            "tax_unit": pd.DataFrame(),
            "household": pd.DataFrame(),
        }

        # ID columns should be preserved from input dataset, not calculated
        id_columns = {
            "person_id",
            "household_id",
            "marital_unit_id",
            "family_id",
            "spm_unit_id",
            "tax_unit_id",
        }
        weight_columns = {
            "person_weight",
            "household_weight",
            "marital_unit_weight",
            "family_weight",
            "spm_unit_weight",
            "tax_unit_weight",
        }

        # First, copy ID and weight columns from input dataset
        for entity in data.keys():
            input_df = pd.DataFrame(getattr(dataset.data, entity))
            entity_id_col = f"{entity}_id"
            entity_weight_col = f"{entity}_weight"

            if entity_id_col in input_df.columns:
                data[entity][entity_id_col] = input_df[entity_id_col].values
            if entity_weight_col in input_df.columns:
                data[entity][entity_weight_col] = input_df[
                    entity_weight_col
                ].values

        # For person entity, also copy person-level group ID columns
        person_input_df = pd.DataFrame(dataset.data.person)
        for col in person_input_df.columns:
            if col.startswith("person_") and col.endswith("_id"):
                # Map person_household_id -> household_id, etc.
                target_col = col.replace("person_", "")
                if target_col in id_columns:
                    data["person"][target_col] = person_input_df[col].values

        # Then calculate non-ID, non-weight variables from simulation
        for entity, variables in self.entity_variables.items():
            for var in variables:
                if var not in id_columns and var not in weight_columns:
                    data[entity][var] = microsim.calculate(
                        var, period=simulation.dataset.year, map_to=entity
                    ).values

        data["person"] = MicroDataFrame(
            data["person"], weights="person_weight"
        )
        data["marital_unit"] = MicroDataFrame(
            data["marital_unit"], weights="marital_unit_weight"
        )
        data["family"] = MicroDataFrame(
            data["family"], weights="family_weight"
        )
        data["spm_unit"] = MicroDataFrame(
            data["spm_unit"], weights="spm_unit_weight"
        )
        data["tax_unit"] = MicroDataFrame(
            data["tax_unit"], weights="tax_unit_weight"
        )
        data["household"] = MicroDataFrame(
            data["household"], weights="household_weight"
        )

        simulation.output_dataset = PolicyEngineUSDataset(
            id=simulation.id,
            name=dataset.name,
            description=dataset.description,
            filepath=str(
                Path(simulation.dataset.filepath).parent
                / (simulation.id + ".h5")
            ),
            year=simulation.dataset.year,
            is_output_dataset=True,
            data=USYearData(
                person=data["person"],
                marital_unit=data["marital_unit"],
                family=data["family"],
                spm_unit=data["spm_unit"],
                tax_unit=data["tax_unit"],
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

        simulation.output_dataset = PolicyEngineUSDataset(
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

    def _build_simulation_from_dataset(self, microsim, dataset, system):
        """Build a PolicyEngine Core simulation from dataset entity IDs.

        This follows the same pattern as policyengine-uk, initializing
        entities from IDs first, then using set_input() for variables.

        Args:
            microsim: The Microsimulation object to populate
            dataset: The dataset containing entity data
            system: The tax-benefit system
        """
        import numpy as np
        from policyengine_core.simulations.simulation_builder import (
            SimulationBuilder,
        )

        # Create builder and instantiate entities
        builder = SimulationBuilder()
        builder.populations = system.instantiate_entities()

        # Extract entity IDs from dataset
        person_data = pd.DataFrame(dataset.data.person)

        # Determine column naming convention
        # Support both person_X_id (from create_datasets) and X_id (from custom datasets)
        household_id_col = (
            "person_household_id"
            if "person_household_id" in person_data.columns
            else "household_id"
        )
        marital_unit_id_col = (
            "person_marital_unit_id"
            if "person_marital_unit_id" in person_data.columns
            else "marital_unit_id"
        )
        family_id_col = (
            "person_family_id"
            if "person_family_id" in person_data.columns
            else "family_id"
        )
        spm_unit_id_col = (
            "person_spm_unit_id"
            if "person_spm_unit_id" in person_data.columns
            else "spm_unit_id"
        )
        tax_unit_id_col = (
            "person_tax_unit_id"
            if "person_tax_unit_id" in person_data.columns
            else "tax_unit_id"
        )

        # Declare entities
        builder.declare_person_entity(
            "person", person_data["person_id"].values
        )
        builder.declare_entity(
            "household", np.unique(person_data[household_id_col].values)
        )
        builder.declare_entity(
            "spm_unit", np.unique(person_data[spm_unit_id_col].values)
        )
        builder.declare_entity(
            "family", np.unique(person_data[family_id_col].values)
        )
        builder.declare_entity(
            "tax_unit", np.unique(person_data[tax_unit_id_col].values)
        )
        builder.declare_entity(
            "marital_unit", np.unique(person_data[marital_unit_id_col].values)
        )

        # Join persons to group entities
        builder.join_with_persons(
            builder.populations["household"],
            person_data[household_id_col].values,
            np.array(["member"] * len(person_data)),
        )
        builder.join_with_persons(
            builder.populations["spm_unit"],
            person_data[spm_unit_id_col].values,
            np.array(["member"] * len(person_data)),
        )
        builder.join_with_persons(
            builder.populations["family"],
            person_data[family_id_col].values,
            np.array(["member"] * len(person_data)),
        )
        builder.join_with_persons(
            builder.populations["tax_unit"],
            person_data[tax_unit_id_col].values,
            np.array(["member"] * len(person_data)),
        )
        builder.join_with_persons(
            builder.populations["marital_unit"],
            person_data[marital_unit_id_col].values,
            np.array(["member"] * len(person_data)),
        )

        # Build simulation from populations
        microsim.build_from_populations(builder.populations)

        # Set input variables for each entity
        # Skip ID columns as they're structural and already used in entity building
        # Support both naming conventions
        id_columns = {
            "person_id",
            "household_id",
            "person_household_id",
            "spm_unit_id",
            "person_spm_unit_id",
            "family_id",
            "person_family_id",
            "tax_unit_id",
            "person_tax_unit_id",
            "marital_unit_id",
            "person_marital_unit_id",
        }

        for entity_name, entity_df in [
            ("person", dataset.data.person),
            ("household", dataset.data.household),
            ("spm_unit", dataset.data.spm_unit),
            ("family", dataset.data.family),
            ("tax_unit", dataset.data.tax_unit),
            ("marital_unit", dataset.data.marital_unit),
        ]:
            df = pd.DataFrame(entity_df)
            for column in df.columns:
                # Skip ID columns and check if variable exists in system
                if column not in id_columns and column in system.variables:
                    microsim.set_input(column, dataset.year, df[column].values)


us_latest = PolicyEngineUSLatest()
