import datetime
from typing import TYPE_CHECKING, Optional

import numpy as np
import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import TaxBenefitModel
from policyengine.provenance.dataset_materialization import (
    materialize_dataset,
)
from policyengine.tax_benefit_models.common import MicrosimulationModelVersion
from policyengine.tax_benefit_models.common.model_version import (
    build_runtime_dataset_provenance,
)
from policyengine.tax_benefit_models.common.model_version import (
    output_dataset_filepath as _output_dataset_filepath,
)

from .datasets import PolicyEngineUKDataset, UKYearData

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation

UK_GROUP_ENTITIES = ["benunit", "household"]
UK_ENTITY_ID_COLUMNS = {
    "person": "person_id",
    "benunit": "benunit_id",
    "household": "household_id",
}
UK_HOUSEHOLD_PASSTHROUGH_COLUMNS = [
    "oa_code",
    "lsoa_code",
    "msoa_code",
    "constituency_code_oa",
    "la_code_oa",
    "region_code_oa",
]


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
            "state_pension",
            # Tax
            "income_tax",
            "national_insurance",
            "ni_employer",
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
            "tax_credits",
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
            "fuel_duty",
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

        from policyengine.utils.parametric_reforms import (
            simulation_modifier_from_parameter_values,
        )

        assert isinstance(simulation.dataset, PolicyEngineUKDataset)

        dataset = simulation.dataset
        # Load from disk only when the caller did not already supply data.
        # An unconditional reload discards caller-provided in-memory data
        # and forced construction to persist datasets to disk (see the
        # autosave removal in datasets.py).
        if dataset.data is None:
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
                # Derived in-memory copy: no filepath, so it can never be
                # persisted back over the shared source file it was filtered
                # from.
                filepath=None,
                year=dataset.year,
                is_output_dataset=dataset.is_output_dataset,
                data=UKYearData(
                    person=scoped_data["person"],
                    benunit=scoped_data["benunit"],
                    household=scoped_data["household"],
                ),
                # The data year's tables stay whole; they are matched to the
                # scoped records by ID when the input is built.
                data_year=dataset.data_year,
                data_year_data=dataset.data_year_data,
            )

        microsim = Microsimulation(dataset=_policyengine_uk_input(dataset))

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

        household_input_df = pd.DataFrame(dataset.data.household)
        for column in UK_HOUSEHOLD_PASSTHROUGH_COLUMNS:
            if column in household_input_df.columns and column not in data["household"]:
                data["household"][column] = household_input_df[column].values

        data["person"] = MicroDataFrame(data["person"], weights="person_weight")
        data["benunit"] = MicroDataFrame(data["benunit"], weights="benunit_weight")
        data["household"] = MicroDataFrame(
            data["household"], weights="household_weight"
        )

        simulation.output_dataset = PolicyEngineUKDataset(
            id=simulation.id,
            name=dataset.name,
            description=dataset.description,
            filepath=str(_output_dataset_filepath(simulation)),
            year=simulation.dataset.year,
            is_output_dataset=True,
            data=UKYearData(
                person=data["person"],
                benunit=data["benunit"],
                household=data["household"],
            ),
        )


def _policyengine_uk_input(dataset: PolicyEngineUKDataset):
    """Build the policyengine-uk dataset a run of ``dataset`` simulates.

    policyengine-uk takes the first year of its dataset as observed data:
    the State Pension formulas split each person's reported State Pension
    against that year's legislated rates and scale the share to the
    simulated year's rates. A dataset projected from an earlier observed
    year (``data_year`` before ``year``) therefore gets the input a direct
    policyengine-uk run on its source builds: the data year's tables
    projected forward by policyengine-uk, with ``dataset.data`` as the
    simulated year. Passing ``dataset.data`` alone would make the simulated
    year the observed year, and the State Pension would follow the CPI
    uprating of its reported amount instead of the triple lock
    (PolicyEngine/policyengine.py#556).

    Any other dataset is passed as observed data for its year, as
    policyengine-uk treats a single-year dataset.
    """
    from policyengine_uk.data import UKMultiYearDataset, UKSingleYearDataset

    year = int(dataset.year)
    # Copies: policyengine-uk encodes enum columns in place on the tables it
    # is given, which would change the caller's dataset.
    simulated = UKSingleYearDataset(
        person=pd.DataFrame(dataset.data.person).copy(),
        benunit=pd.DataFrame(dataset.data.benunit).copy(),
        household=pd.DataFrame(dataset.data.household).copy(),
        fiscal_year=year,
    )
    if dataset.data_year is None or int(dataset.data_year) >= year:
        return simulated

    from policyengine_uk.data.economic_assumptions import (
        extend_single_year_dataset,
    )
    from policyengine_uk.system import system

    data_year = int(dataset.data_year)
    observed_tables = _match_records(
        dataset.data_year_data.entity_data,
        dataset.data.entity_data,
        data_year=data_year,
        year=year,
    )
    observed = UKSingleYearDataset(**observed_tables, fiscal_year=data_year)
    projected = extend_single_year_dataset(observed, system.parameters)
    if year not in projected.years:
        projected = extend_single_year_dataset(
            observed, system.parameters, end_year=year
        )
    return UKMultiYearDataset(
        datasets=[projected[y] for y in projected.years if y != year] + [simulated]
    )


def _match_records(
    observed: dict[str, pd.DataFrame],
    simulated: dict[str, pd.DataFrame],
    *,
    data_year: int,
    year: int,
) -> dict[str, pd.DataFrame]:
    """Return the observed tables for the simulated records, in their order.

    policyengine-uk builds its entities from the first year of a dataset and
    sets each year's inputs by position, so the observed year must hold the
    same records in the same order as the simulated year. Records are
    matched by ID, which carries region scoping (a subset of households)
    over to the observed year.
    """
    matched = {}
    for entity, id_column in UK_ENTITY_ID_COLUMNS.items():
        table = pd.DataFrame(observed[entity])
        ids = pd.Index(table[id_column].to_numpy())
        if not ids.is_unique:
            raise ValueError(
                f"The {data_year} {entity} table repeats {id_column} values, "
                "so its records cannot be matched to the simulated year."
            )
        positions = ids.get_indexer(pd.DataFrame(simulated[entity])[id_column])
        missing = int((positions < 0).sum())
        if missing:
            raise ValueError(
                f"{missing} {entity} record(s) of the {year} tables are not in "
                f"the {data_year} tables they were projected from, so "
                "policyengine-uk has no observed data for them. Keep the data "
                "year's tables in step with `data`, or set data_year=None to "
                f"treat `data` as observed data for {year}."
            )
        matched[entity] = table.iloc[positions].reset_index(drop=True).copy()
    simulated_person = pd.DataFrame(simulated["person"])
    for link in ("person_benunit_id", "person_household_id"):
        if not np.array_equal(
            matched["person"][link].to_numpy(), simulated_person[link].to_numpy()
        ):
            raise ValueError(
                f"People belong to different units ({link}) in the {data_year} "
                f"and {year} tables, so the {year} tables were not projected "
                f"from the {data_year} ones."
            )
    return matched


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

    source = materialize_dataset(
        "uk",
        dataset,
        allow_unmanaged=allow_unmanaged,
    )
    runtime_dataset = source.path
    if "://" not in source.path:
        from policyengine_uk.data.dataset_schema import (
            UKMultiYearDataset,
            UKSingleYearDataset,
        )

        if UKMultiYearDataset.validate_file_path(source.path, False):
            runtime_dataset = UKMultiYearDataset(source.path)
        elif UKSingleYearDataset.validate_file_path(source.path, False):
            runtime_dataset = UKSingleYearDataset(source.path)
    microsim = Microsimulation(dataset=runtime_dataset, **kwargs)
    microsim.policyengine_bundle = dict(uk_latest.release_bundle)
    microsim.policyengine_bundle.update(
        build_runtime_dataset_provenance(
            source.source_uri,
            source.path,
            source.bundle_dataset,
        )
    )
    return microsim


uk_latest = PolicyEngineUKLatest()
