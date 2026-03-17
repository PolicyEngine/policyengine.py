"""General utility functions for US policy reform analysis."""

import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from microdf import MicroDataFrame
from pydantic import BaseModel, Field

from policyengine.core import Simulation
from policyengine.core.policy import Policy
from policyengine.outputs.budget_summary import compute_budget_summary
from policyengine.outputs.country_config import US_CONFIG
from policyengine.outputs.decile_impact import compute_decile_impacts
from policyengine.outputs.inequality import calculate_us_inequality
from policyengine.outputs.intra_decile_impact import compute_intra_decile_impacts
from policyengine.outputs.policy_reform_analysis import PolicyReformAnalysis
from policyengine.outputs.poverty import calculate_us_poverty_rates
from policyengine.outputs.program_statistics import compute_program_statistics

from .datasets import PolicyEngineUSDataset, USYearData
from .model import us_latest


class USHouseholdOutput(BaseModel):
    """Output from a US household calculation with all entity data."""

    person: list[dict[str, Any]]
    marital_unit: list[dict[str, Any]]
    family: list[dict[str, Any]]
    spm_unit: list[dict[str, Any]]
    tax_unit: list[dict[str, Any]]
    household: dict[str, Any]


class USHouseholdInput(BaseModel):
    """Input for a US household calculation."""

    people: list[dict[str, Any]]
    marital_unit: dict[str, Any] = Field(default_factory=dict)
    family: dict[str, Any] = Field(default_factory=dict)
    spm_unit: dict[str, Any] = Field(default_factory=dict)
    tax_unit: dict[str, Any] = Field(default_factory=dict)
    household: dict[str, Any] = Field(default_factory=dict)
    year: int = 2024


def calculate_household_impact(
    household_input: USHouseholdInput,
    policy: Policy | None = None,
) -> USHouseholdOutput:
    """Calculate tax and benefit impacts for a single US household."""
    n_people = len(household_input.people)

    # Build person data with defaults
    person_data = {
        "person_id": list(range(n_people)),
        "person_household_id": [0] * n_people,
        "person_marital_unit_id": [0] * n_people,
        "person_family_id": [0] * n_people,
        "person_spm_unit_id": [0] * n_people,
        "person_tax_unit_id": [0] * n_people,
        "person_weight": [1.0] * n_people,
    }
    # Add user-provided person fields
    for i, person in enumerate(household_input.people):
        for key, value in person.items():
            if key not in person_data:
                person_data[key] = [0.0] * n_people  # Default to 0 for numeric fields
            person_data[key][i] = value

    # Build entity data with defaults
    household_data = {
        "household_id": [0],
        "household_weight": [1.0],
    }
    for key, value in household_input.household.items():
        household_data[key] = [value]

    marital_unit_data = {
        "marital_unit_id": [0],
        "marital_unit_weight": [1.0],
    }
    for key, value in household_input.marital_unit.items():
        marital_unit_data[key] = [value]

    family_data = {
        "family_id": [0],
        "family_weight": [1.0],
    }
    for key, value in household_input.family.items():
        family_data[key] = [value]

    spm_unit_data = {
        "spm_unit_id": [0],
        "spm_unit_weight": [1.0],
    }
    for key, value in household_input.spm_unit.items():
        spm_unit_data[key] = [value]

    tax_unit_data = {
        "tax_unit_id": [0],
        "tax_unit_weight": [1.0],
    }
    for key, value in household_input.tax_unit.items():
        tax_unit_data[key] = [value]

    # Create MicroDataFrames
    person_df = MicroDataFrame(pd.DataFrame(person_data), weights="person_weight")
    household_df = MicroDataFrame(
        pd.DataFrame(household_data), weights="household_weight"
    )
    marital_unit_df = MicroDataFrame(
        pd.DataFrame(marital_unit_data), weights="marital_unit_weight"
    )
    family_df = MicroDataFrame(pd.DataFrame(family_data), weights="family_weight")
    spm_unit_df = MicroDataFrame(pd.DataFrame(spm_unit_data), weights="spm_unit_weight")
    tax_unit_df = MicroDataFrame(pd.DataFrame(tax_unit_data), weights="tax_unit_weight")

    # Create temporary dataset
    tmpdir = tempfile.mkdtemp()
    filepath = str(Path(tmpdir) / "household_impact.h5")

    dataset = PolicyEngineUSDataset(
        name="Household impact calculation",
        description="Single household for impact calculation",
        filepath=filepath,
        year=household_input.year,
        data=USYearData(
            person=person_df,
            household=household_df,
            marital_unit=marital_unit_df,
            family=family_df,
            spm_unit=spm_unit_df,
            tax_unit=tax_unit_df,
        ),
    )

    # Run simulation
    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=us_latest,
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

    def extract_entity_outputs(
        entity_name: str, entity_data, n_rows: int
    ) -> list[dict[str, Any]]:
        outputs = []
        for i in range(n_rows):
            row_dict = {}
            for var in us_latest.entity_variables[entity_name]:
                row_dict[var] = safe_convert(entity_data[var].iloc[i])
            outputs.append(row_dict)
        return outputs

    return USHouseholdOutput(
        person=extract_entity_outputs("person", output_data.person, n_people),
        marital_unit=extract_entity_outputs(
            "marital_unit", output_data.marital_unit, 1
        ),
        family=extract_entity_outputs("family", output_data.family, 1),
        spm_unit=extract_entity_outputs("spm_unit", output_data.spm_unit, 1),
        tax_unit=extract_entity_outputs("tax_unit", output_data.tax_unit, 1),
        household={
            var: safe_convert(output_data.household[var].iloc[0])
            for var in us_latest.entity_variables["household"]
        },
    )


def economic_impact_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> PolicyReformAnalysis:
    """Perform comprehensive economic impact analysis of a US policy reform.

    Calls individual compute functions and assembles the results into
    a single ``PolicyReformAnalysis`` object.

    Both simulations must already be run (i.e. ``ensure()`` called).
    """
    baseline_simulation.ensure()
    reform_simulation.ensure()

    config = US_CONFIG

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

    # Program statistics
    programs = compute_program_statistics(
        baseline_simulation,
        reform_simulation,
        config.programs,
    )

    # Poverty — overall
    baseline_poverty = calculate_us_poverty_rates(baseline_simulation)
    reform_poverty = calculate_us_poverty_rates(reform_simulation)

    # Poverty by demographics
    from policyengine.outputs.poverty import (
        calculate_us_poverty_by_age,
        calculate_us_poverty_by_gender,
        calculate_us_poverty_by_race,
    )

    baseline_poverty_by_age = calculate_us_poverty_by_age(baseline_simulation)
    reform_poverty_by_age = calculate_us_poverty_by_age(reform_simulation)
    baseline_poverty_by_gender = calculate_us_poverty_by_gender(baseline_simulation)
    reform_poverty_by_gender = calculate_us_poverty_by_gender(reform_simulation)
    baseline_poverty_by_race = calculate_us_poverty_by_race(baseline_simulation)
    reform_poverty_by_race = calculate_us_poverty_by_race(reform_simulation)

    # Inequality
    baseline_inequality = calculate_us_inequality(baseline_simulation)
    reform_inequality = calculate_us_inequality(reform_simulation)

    return PolicyReformAnalysis(
        decile_impacts=decile_impacts,
        intra_decile_impacts=intra_decile_impacts,
        budget_summary=budget,
        household_count_baseline=household_count_baseline,
        household_count_reform=household_count_reform,
        program_statistics=programs,
        baseline_poverty=baseline_poverty,
        reform_poverty=reform_poverty,
        baseline_poverty_by_age=baseline_poverty_by_age,
        reform_poverty_by_age=reform_poverty_by_age,
        baseline_poverty_by_gender=baseline_poverty_by_gender,
        reform_poverty_by_gender=reform_poverty_by_gender,
        baseline_poverty_by_race=baseline_poverty_by_race,
        reform_poverty_by_race=reform_poverty_by_race,
        baseline_inequality=baseline_inequality,
        reform_inequality=reform_inequality,
    )
