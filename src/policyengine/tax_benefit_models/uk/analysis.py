"""General utility functions for UK policy reform analysis."""

import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from microdf import MicroDataFrame
from pydantic import BaseModel, Field, create_model

from policyengine.core import Simulation
from policyengine.core.policy import Policy
from policyengine.outputs.budget_summary import compute_budget_summary
from policyengine.outputs.country_config import UK_CONFIG
from policyengine.outputs.decile_impact import compute_decile_impacts
from policyengine.outputs.inequality import calculate_uk_inequality
from policyengine.outputs.intra_decile_impact import compute_intra_decile_impacts
from policyengine.outputs.policy_reform_analysis import PolicyReformAnalysis
from policyengine.outputs.poverty import calculate_uk_poverty_rates
from policyengine.outputs.program_statistics import compute_program_statistics

from .datasets import PolicyEngineUKDataset, UKYearData
from .model import uk_latest


def _create_entity_output_model(entity: str, variables: list[str]) -> type[BaseModel]:
    """Create a dynamic Pydantic model for entity output variables."""
    fields = {var: (float, ...) for var in variables}
    return create_model(f"{entity.title()}Output", **fields)


# Create output models dynamically from uk_latest.entity_variables
PersonOutput = _create_entity_output_model(
    "person", uk_latest.entity_variables["person"]
)
BenunitOutput = _create_entity_output_model(
    "benunit", uk_latest.entity_variables["benunit"]
)
HouseholdEntityOutput = _create_entity_output_model(
    "household", uk_latest.entity_variables["household"]
)


class UKHouseholdOutput(BaseModel):
    """Output from a UK household calculation with all entity data."""

    person: list[dict[str, Any]]
    benunit: list[dict[str, Any]]
    household: dict[str, Any]


class UKHouseholdInput(BaseModel):
    """Input for a UK household calculation."""

    people: list[dict[str, Any]]
    benunit: dict[str, Any] = Field(default_factory=dict)
    household: dict[str, Any] = Field(default_factory=dict)
    year: int = 2026


def calculate_household_impact(
    household_input: UKHouseholdInput,
    policy: Policy | None = None,
) -> UKHouseholdOutput:
    """Calculate tax and benefit impacts for a single UK household."""
    n_people = len(household_input.people)

    # Build person data with defaults
    person_data = {
        "person_id": list(range(n_people)),
        "person_benunit_id": [0] * n_people,
        "person_household_id": [0] * n_people,
        "person_weight": [1.0] * n_people,
    }
    # Add user-provided person fields
    for i, person in enumerate(household_input.people):
        for key, value in person.items():
            if key not in person_data:
                person_data[key] = [0.0] * n_people  # Default to 0 for numeric fields
            person_data[key][i] = value

    # Build benunit data with defaults
    benunit_data = {
        "benunit_id": [0],
        "benunit_weight": [1.0],
    }
    for key, value in household_input.benunit.items():
        benunit_data[key] = [value]

    # Build household data with defaults (required for uprating)
    household_data = {
        "household_id": [0],
        "household_weight": [1.0],
        "region": ["LONDON"],
        "tenure_type": ["RENT_PRIVATELY"],
        "council_tax": [0.0],
        "rent": [0.0],
    }
    for key, value in household_input.household.items():
        household_data[key] = [value]

    # Create MicroDataFrames
    person_df = MicroDataFrame(pd.DataFrame(person_data), weights="person_weight")
    benunit_df = MicroDataFrame(pd.DataFrame(benunit_data), weights="benunit_weight")
    household_df = MicroDataFrame(
        pd.DataFrame(household_data), weights="household_weight"
    )

    # Create temporary dataset
    tmpdir = tempfile.mkdtemp()
    filepath = str(Path(tmpdir) / "household_impact.h5")

    dataset = PolicyEngineUKDataset(
        name="Household impact calculation",
        description="Single household for impact calculation",
        filepath=filepath,
        year=household_input.year,
        data=UKYearData(
            person=person_df,
            benunit=benunit_df,
            household=household_df,
        ),
    )

    # Run simulation
    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=uk_latest,
        policy=policy,
    )
    simulation.run()

    # Extract all output variables defined in entity_variables
    output_data = simulation.output_dataset.data

    def safe_convert(value):
        """Convert value to float if numeric, otherwise return as string."""
        try:
            return float(value)
        except (ValueError, TypeError):
            return str(value)

    person_outputs = []
    for i in range(n_people):
        person_dict = {}
        for var in uk_latest.entity_variables["person"]:
            person_dict[var] = safe_convert(output_data.person[var].iloc[i])
        person_outputs.append(person_dict)

    benunit_outputs = []
    for i in range(len(output_data.benunit)):
        benunit_dict = {}
        for var in uk_latest.entity_variables["benunit"]:
            benunit_dict[var] = safe_convert(output_data.benunit[var].iloc[i])
        benunit_outputs.append(benunit_dict)

    household_dict = {}
    for var in uk_latest.entity_variables["household"]:
        household_dict[var] = safe_convert(output_data.household[var].iloc[0])

    return UKHouseholdOutput(
        person=person_outputs,
        benunit=benunit_outputs,
        household=household_dict,
    )


def economic_impact_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> PolicyReformAnalysis:
    """Perform comprehensive economic impact analysis of a UK policy reform.

    Calls individual compute functions and assembles the results into
    a single ``PolicyReformAnalysis`` object.

    Both simulations must already be run (i.e. ``ensure()`` called).
    """
    baseline_simulation.ensure()
    reform_simulation.ensure()

    config = UK_CONFIG

    # Decile impacts
    decile_impacts = compute_decile_impacts(
        baseline_simulation,
        reform_simulation,
        income_variable=config.income_variable,
    )

    # Intra-decile impacts
    intra_decile_impacts = compute_intra_decile_impacts(
        baseline_simulation,
        reform_simulation,
        income_variable=config.income_variable,
    )

    # Budget summary
    budget = compute_budget_summary(
        baseline_simulation,
        reform_simulation,
        config.budget_variables,
    )

    # Household counts — raw weight sums to avoid MicroSeries double-weighting
    import numpy as np

    hh_weight_baseline = baseline_simulation.output_dataset.data.household[
        "household_weight"
    ]
    hh_weight_reform = reform_simulation.output_dataset.data.household[
        "household_weight"
    ]
    household_count_baseline = float(np.array(hh_weight_baseline).sum())
    household_count_reform = float(np.array(hh_weight_reform).sum())

    # Programme statistics
    programmes = compute_program_statistics(
        baseline_simulation,
        reform_simulation,
        config.programs,
    )

    # Poverty — overall
    baseline_poverty = calculate_uk_poverty_rates(baseline_simulation)
    reform_poverty = calculate_uk_poverty_rates(reform_simulation)

    # Poverty by demographics
    from policyengine.outputs.poverty import (
        calculate_uk_poverty_by_age,
        calculate_uk_poverty_by_gender,
    )

    baseline_poverty_by_age = calculate_uk_poverty_by_age(baseline_simulation)
    reform_poverty_by_age = calculate_uk_poverty_by_age(reform_simulation)
    baseline_poverty_by_gender = calculate_uk_poverty_by_gender(baseline_simulation)
    reform_poverty_by_gender = calculate_uk_poverty_by_gender(reform_simulation)

    # Inequality
    baseline_inequality = calculate_uk_inequality(baseline_simulation)
    reform_inequality = calculate_uk_inequality(reform_simulation)

    return PolicyReformAnalysis(
        decile_impacts=decile_impacts,
        intra_decile_impacts=intra_decile_impacts,
        budget_summary=budget,
        household_count_baseline=household_count_baseline,
        household_count_reform=household_count_reform,
        program_statistics=programmes,
        baseline_poverty=baseline_poverty,
        reform_poverty=reform_poverty,
        baseline_poverty_by_age=baseline_poverty_by_age,
        reform_poverty_by_age=reform_poverty_by_age,
        baseline_poverty_by_gender=baseline_poverty_by_gender,
        reform_poverty_by_gender=reform_poverty_by_gender,
        baseline_inequality=baseline_inequality,
        reform_inequality=reform_inequality,
    )
