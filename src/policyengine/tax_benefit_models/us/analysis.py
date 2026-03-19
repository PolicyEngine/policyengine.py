"""General utility functions for US policy reform analysis."""

import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from microdf import MicroDataFrame
from pydantic import BaseModel, Field

from policyengine.core import Simulation
from policyengine.core.policy import Policy
from policyengine.outputs.analysis_strategy import (
    InequalityResult,
    PovertyResult,
    ProgramDefinition,
)
from policyengine.outputs.economic_impact import (
    economic_impact_analysis as _shared_economic_impact_analysis,
)
from policyengine.outputs.inequality import calculate_us_inequality
from policyengine.outputs.policy_reform_analysis import PolicyReformAnalysis
from policyengine.outputs.poverty import (
    calculate_us_poverty_by_age,
    calculate_us_poverty_by_gender,
    calculate_us_poverty_by_race,
    calculate_us_poverty_rates,
)

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


# ---------------------------------------------------------------------------
# US analysis strategy
# ---------------------------------------------------------------------------


class USAnalysisStrategy:
    """Country-specific strategy for US economic impact analysis."""

    @property
    def income_variable(self) -> str:
        return "household_net_income"

    @property
    def budget_variable_names(self) -> list[str]:
        return [
            "household_tax",
            "household_benefits",
            "household_net_income",
            "household_state_income_tax",
        ]

    @property
    def programs(self) -> dict[str, ProgramDefinition]:
        return {
            "income_tax": ProgramDefinition(entity="tax_unit", is_tax=True),
            "employee_payroll_tax": ProgramDefinition(entity="person", is_tax=True),
            "snap": ProgramDefinition(entity="spm_unit", is_tax=False),
            "tanf": ProgramDefinition(entity="spm_unit", is_tax=False),
            "ssi": ProgramDefinition(entity="spm_unit", is_tax=False),
            "social_security": ProgramDefinition(entity="person", is_tax=False),
        }

    def compute_poverty(
        self,
        baseline: Simulation,
        reform: Simulation,
    ) -> PovertyResult:
        return PovertyResult(
            baseline_poverty=calculate_us_poverty_rates(baseline),
            reform_poverty=calculate_us_poverty_rates(reform),
            baseline_poverty_by_age=calculate_us_poverty_by_age(baseline),
            reform_poverty_by_age=calculate_us_poverty_by_age(reform),
            baseline_poverty_by_gender=calculate_us_poverty_by_gender(baseline),
            reform_poverty_by_gender=calculate_us_poverty_by_gender(reform),
            baseline_poverty_by_race=calculate_us_poverty_by_race(baseline),
            reform_poverty_by_race=calculate_us_poverty_by_race(reform),
        )

    def compute_inequality(
        self,
        baseline: Simulation,
        reform: Simulation,
    ) -> InequalityResult:
        return InequalityResult(
            baseline_inequality=calculate_us_inequality(baseline),
            reform_inequality=calculate_us_inequality(reform),
        )


US_STRATEGY = USAnalysisStrategy()


def economic_impact_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> PolicyReformAnalysis:
    """Perform comprehensive economic impact analysis of a US policy reform."""
    return _shared_economic_impact_analysis(
        baseline_simulation,
        reform_simulation,
        US_STRATEGY,
    )
