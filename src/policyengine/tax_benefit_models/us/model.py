import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import TaxBenefitModel
from policyengine.provenance.manifest import (
    dataset_logical_name,
    resolve_local_managed_dataset_source,
    resolve_managed_dataset_reference,
)
from policyengine.tax_benefit_models.common import MicrosimulationModelVersion

from .datasets import PolicyEngineUSDataset, USYearData

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation

US_GROUP_ENTITIES = [
    "household",
    "tax_unit",
    "spm_unit",
    "family",
    "marital_unit",
]


class PolicyEngineUS(TaxBenefitModel):
    id: str = "policyengine-us"
    description: str = "The US's open-source dynamic tax and benefit microsimulation model maintained by PolicyEngine."


us_model = PolicyEngineUS()


class PolicyEngineUSLatest(MicrosimulationModelVersion):
    country_code = "us"
    package_name = "policyengine-us"
    group_entities = US_GROUP_ENTITIES

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
            "is_male",
            "race",
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
            "household_state_income_tax",
            "eitc",
            "ctc",
        ],
        "household": [
            "household_id",
            "household_weight",
            "household_count_people",
            "household_net_income",
            "household_income_decile",
            "household_benefits",
            "household_tax",
            "household_market_income",
            "congressional_district_geoid",
        ],
    }

    # --- Hooks -----------------------------------------------------------
    @classmethod
    def _get_runtime_data_build_metadata(cls) -> dict[str, Optional[str]]:
        try:
            from policyengine_us.build_metadata import get_data_build_metadata
        except ModuleNotFoundError as exc:
            if exc.name != "policyengine_us.build_metadata":
                raise
            return {}
        return get_data_build_metadata() or {}

    def _load_system(self):
        from policyengine_us.system import system

        return system

    def _load_region_registry(self):
        from policyengine.countries.us.regions import us_region_registry

        return us_region_registry

    @property
    def _dataset_class(self):
        return PolicyEngineUSDataset

    # --- run -------------------------------------------------------------
    def run(self, simulation: "Simulation") -> "Simulation":
        from policyengine_us import Microsimulation

        from policyengine.utils.parametric_reforms import (
            build_reform_dict,
            merge_reform_dicts,
        )

        assert isinstance(simulation.dataset, PolicyEngineUSDataset)

        dataset = simulation.dataset
        dataset.load()

        # Apply regional scoping if specified
        if simulation.scoping_strategy:
            scoped_data = simulation.scoping_strategy.apply(
                entity_data=dataset.data.entity_data,
                group_entities=US_GROUP_ENTITIES,
                year=dataset.year,
            )
            dataset = PolicyEngineUSDataset(
                id=dataset.id + "_scoped",
                name=dataset.name,
                description=dataset.description,
                filepath=dataset.filepath,
                year=dataset.year,
                is_output_dataset=dataset.is_output_dataset,
                data=USYearData(
                    person=scoped_data["person"],
                    marital_unit=scoped_data["marital_unit"],
                    family=scoped_data["family"],
                    spm_unit=scoped_data["spm_unit"],
                    tax_unit=scoped_data["tax_unit"],
                    household=scoped_data["household"],
                ),
            )

        # US requires reforms at Microsimulation construction time
        # (unlike UK which supports p.update() after construction).
        policy_reform = build_reform_dict(simulation.policy)
        dynamic_reform = build_reform_dict(simulation.dynamic)
        reform_dict = merge_reform_dicts(policy_reform, dynamic_reform)

        microsim = Microsimulation(reform=reform_dict)
        # Use ``microsim.tax_benefit_system``, not the module-level
        # ``system``: ``Microsimulation.__init__`` applies structural
        # reforms (e.g. ``gov.contrib.ctc.*``) to its per-sim system but
        # leaves the module-level one untouched. Building populations
        # against the module-level system would hide reform-registered
        # variables like ``ctc_minimum_refundable_amount`` at calc time.
        self._build_simulation_from_dataset(
            microsim, dataset, microsim.tax_benefit_system
        )

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

        # Copy ID and weight columns from input dataset.
        for entity in data.keys():
            input_df = pd.DataFrame(getattr(dataset.data, entity))
            entity_id_col = f"{entity}_id"
            entity_weight_col = f"{entity}_weight"

            if entity_id_col in input_df.columns:
                data[entity][entity_id_col] = input_df[entity_id_col].values
            if entity_weight_col in input_df.columns:
                data[entity][entity_weight_col] = input_df[entity_weight_col].values

        # Person entity also needs person-level group ID columns so that
        # downstream joins (e.g. person->tax_unit) work.
        person_input_df = pd.DataFrame(dataset.data.person)
        for col in person_input_df.columns:
            if col.startswith("person_") and col.endswith("_id"):
                target_col = col.replace("person_", "")
                if target_col in id_columns:
                    data["person"][target_col] = person_input_df[col].values

        # Calculate non-ID, non-weight variables from simulation
        for entity, variables in self.entity_variables.items():
            for var in variables:
                if var not in id_columns and var not in weight_columns:
                    data[entity][var] = microsim.calculate(
                        var, period=simulation.dataset.year, map_to=entity
                    ).values

        data["person"] = MicroDataFrame(data["person"], weights="person_weight")
        data["marital_unit"] = MicroDataFrame(
            data["marital_unit"], weights="marital_unit_weight"
        )
        data["family"] = MicroDataFrame(data["family"], weights="family_weight")
        data["spm_unit"] = MicroDataFrame(data["spm_unit"], weights="spm_unit_weight")
        data["tax_unit"] = MicroDataFrame(data["tax_unit"], weights="tax_unit_weight")
        data["household"] = MicroDataFrame(
            data["household"], weights="household_weight"
        )

        simulation.output_dataset = PolicyEngineUSDataset(
            id=simulation.id,
            name=dataset.name,
            description=dataset.description,
            filepath=str(
                Path(simulation.dataset.filepath).parent / (simulation.id + ".h5")
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

    def _build_simulation_from_dataset(self, microsim, dataset, system):
        """Build a PolicyEngine Core simulation from dataset entity IDs.

        Mirrors the policyengine-uk pattern of instantiating entities from
        IDs first and then setting variable inputs. Handles both the legacy
        ``person_X_id`` and the ``X_id`` column-naming conventions.
        """
        import numpy as np
        from policyengine_core.simulations.simulation_builder import (
            SimulationBuilder,
        )

        builder = SimulationBuilder()
        builder.populations = system.instantiate_entities()

        person_data = pd.DataFrame(dataset.data.person)

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

        builder.declare_person_entity("person", person_data["person_id"].values)
        builder.declare_entity(
            "household", np.unique(person_data[household_id_col].values)
        )
        builder.declare_entity(
            "spm_unit", np.unique(person_data[spm_unit_id_col].values)
        )
        builder.declare_entity("family", np.unique(person_data[family_id_col].values))
        builder.declare_entity(
            "tax_unit", np.unique(person_data[tax_unit_id_col].values)
        )
        builder.declare_entity(
            "marital_unit", np.unique(person_data[marital_unit_id_col].values)
        )

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

        microsim.build_from_populations(builder.populations)

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
                if column not in id_columns and column in system.variables:
                    microsim.set_input(column, dataset.year, df[column].values)


def _managed_release_bundle(
    dataset_uri: str,
    dataset_source: Optional[str] = None,
) -> dict[str, Optional[str]]:
    bundle = dict(us_latest.release_bundle)
    bundle["runtime_dataset"] = dataset_logical_name(dataset_uri)
    bundle["runtime_dataset_uri"] = dataset_uri
    if dataset_source:
        bundle["runtime_dataset_source"] = dataset_source
    bundle["managed_by"] = "policyengine.py"
    return bundle


def managed_microsimulation(
    *,
    dataset: Optional[str] = None,
    allow_unmanaged: bool = False,
    **kwargs,
):
    """Construct a country-package Microsimulation pinned to this bundle.

    By default this enforces the dataset selection from the bundled
    ``policyengine.py`` release manifest. Arbitrary dataset URIs require
    ``allow_unmanaged=True``.
    """

    from policyengine_us import Microsimulation

    if "dataset" in kwargs:
        raise ValueError(
            "Pass `dataset=` directly to managed_microsimulation, not through "
            "**kwargs, so policyengine.py can enforce the release bundle."
        )

    dataset_uri = resolve_managed_dataset_reference(
        "us",
        dataset,
        allow_unmanaged=allow_unmanaged,
    )
    dataset_source = resolve_local_managed_dataset_source(
        "us",
        dataset_uri,
        allow_local_mirror=not (
            allow_unmanaged and dataset is not None and "://" in dataset
        ),
    )
    microsim = Microsimulation(dataset=dataset_source, **kwargs)
    microsim.policyengine_bundle = _managed_release_bundle(
        dataset_uri,
        dataset_source,
    )
    return microsim


us_latest = PolicyEngineUSLatest()
