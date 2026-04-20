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

from .datasets import PolicyEngineUKDataset, UKYearData

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation

UK_GROUP_ENTITIES = ["benunit", "household"]


class PolicyEngineUK(TaxBenefitModel):
    id: str = "policyengine-uk"
    description: str = "The UK's open-source dynamic tax and benefit microsimulation model maintained by PolicyEngine."


uk_model = PolicyEngineUK()


class PolicyEngineUKLatest(MicrosimulationModelVersion):
    country_code = "uk"
    package_name = "policyengine-uk"
    group_entities = UK_GROUP_ENTITIES

    model: TaxBenefitModel = uk_model
    version: str = None
    created_at: datetime.datetime = None

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
            "is_male",
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
            "pension_credit",
            "income_support",
            "working_tax_credit",
            "child_tax_credit",
        ],
        "household": [
            # IDs and weights
            "household_id",
            "household_weight",
            "household_count_people",
            # Income measures
            "household_net_income",
            "household_income_decile",
            "household_wealth_decile",
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

    # --- Hooks -----------------------------------------------------------
    @classmethod
    def _get_runtime_data_build_metadata(cls) -> dict[str, Optional[str]]:
        try:
            from policyengine_uk.build_metadata import get_data_build_metadata
        except ModuleNotFoundError as exc:
            if exc.name != "policyengine_uk.build_metadata":
                raise
            return {}
        return get_data_build_metadata() or {}

    def _load_system(self):
        from policyengine_uk.system import system

        return system

    def _load_region_registry(self):
        from policyengine.countries.uk.regions import uk_region_registry

        return uk_region_registry

    @property
    def _dataset_class(self):
        return PolicyEngineUKDataset

    # --- run -------------------------------------------------------------
    def run(self, simulation: "Simulation") -> "Simulation":
        from policyengine_uk import Microsimulation
        from policyengine_uk.data import UKSingleYearDataset

        from policyengine.utils.parametric_reforms import (
            simulation_modifier_from_parameter_values,
        )

        assert isinstance(simulation.dataset, PolicyEngineUKDataset)

        dataset = simulation.dataset
        dataset.load()

        # Apply regional scoping if specified
        if simulation.scoping_strategy:
            scoped_data = simulation.scoping_strategy.apply(
                entity_data=dataset.data.entity_data,
                group_entities=UK_GROUP_ENTITIES,
                year=dataset.year,
            )
            dataset = PolicyEngineUKDataset(
                id=dataset.id + "_scoped",
                name=dataset.name,
                description=dataset.description,
                filepath=dataset.filepath,
                year=dataset.year,
                is_output_dataset=dataset.is_output_dataset,
                data=UKYearData(
                    person=scoped_data["person"],
                    benunit=scoped_data["benunit"],
                    household=scoped_data["household"],
                ),
            )

        input_data = UKSingleYearDataset(
            person=dataset.data.person,
            benunit=dataset.data.benunit,
            household=dataset.data.household,
            fiscal_year=dataset.year,
        )
        microsim = Microsimulation(dataset=input_data)

        if simulation.policy and simulation.policy.simulation_modifier is not None:
            simulation.policy.simulation_modifier(microsim)
        elif simulation.policy:
            modifier = simulation_modifier_from_parameter_values(
                simulation.policy.parameter_values
            )
            modifier(microsim)

        if simulation.dynamic and simulation.dynamic.simulation_modifier is not None:
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

        # ``resolve_entity_variables`` merges the bundled defaults
        # with caller-supplied ``simulation.extra_variables``; unknown
        # entity keys or variable names raise with close-match hints.
        for entity, variables in self.resolve_entity_variables(simulation).items():
            for var in variables:
                data[entity][var] = microsim.calculate(
                    var, period=simulation.dataset.year, map_to=entity
                ).values

        data["person"] = MicroDataFrame(data["person"], weights="person_weight")
        data["benunit"] = MicroDataFrame(data["benunit"], weights="benunit_weight")
        data["household"] = MicroDataFrame(
            data["household"], weights="household_weight"
        )

        simulation.output_dataset = PolicyEngineUKDataset(
            id=simulation.id,
            name=dataset.name,
            description=dataset.description,
            filepath=str(
                Path(simulation.dataset.filepath).parent / (simulation.id + ".h5")
            ),
            year=simulation.dataset.year,
            is_output_dataset=True,
            data=UKYearData(
                person=data["person"],
                benunit=data["benunit"],
                household=data["household"],
            ),
        )


def _managed_release_bundle(
    dataset_uri: str,
    dataset_source: Optional[str] = None,
) -> dict[str, Optional[str]]:
    bundle = dict(uk_latest.release_bundle)
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

    from policyengine_uk import Microsimulation

    if "dataset" in kwargs:
        raise ValueError(
            "Pass `dataset=` directly to managed_microsimulation, not through "
            "**kwargs, so policyengine.py can enforce the release bundle."
        )

    dataset_uri = resolve_managed_dataset_reference(
        "uk",
        dataset,
        allow_unmanaged=allow_unmanaged,
    )
    dataset_source = resolve_local_managed_dataset_source(
        "uk",
        dataset_uri,
        allow_local_mirror=not (
            allow_unmanaged and dataset is not None and "://" in dataset
        ),
    )
    runtime_dataset = dataset_source
    if isinstance(dataset_source, str) and "hf://" not in dataset_source:
        from policyengine_uk.data.dataset_schema import (
            UKMultiYearDataset,
            UKSingleYearDataset,
        )

        if UKMultiYearDataset.validate_file_path(dataset_source, False):
            runtime_dataset = UKMultiYearDataset(dataset_source)
        elif UKSingleYearDataset.validate_file_path(dataset_source, False):
            runtime_dataset = UKSingleYearDataset(dataset_source)
    microsim = Microsimulation(dataset=runtime_dataset, **kwargs)
    microsim.policyengine_bundle = _managed_release_bundle(
        dataset_uri,
        dataset_source,
    )
    return microsim


uk_latest = PolicyEngineUKLatest()
