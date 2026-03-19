"""General utility functions for UK policy reform analysis."""

import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from microdf import MicroDataFrame
from pydantic import BaseModel, Field, create_model

from policyengine.core import Simulation
from policyengine.core.policy import Policy
from policyengine.outputs.analysis_strategy import InequalityResult, PovertyResult
from policyengine.outputs.economic_impact import (
    economic_impact_analysis as _shared_economic_impact_analysis,
)
from policyengine.outputs.inequality import calculate_uk_inequality
from policyengine.outputs.policy_reform_analysis import PolicyReformAnalysis
from policyengine.outputs.poverty import (
    calculate_uk_poverty_by_age,
    calculate_uk_poverty_by_gender,
    calculate_uk_poverty_rates,
)

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


# ---------------------------------------------------------------------------
# UK analysis strategy
# ---------------------------------------------------------------------------


class UKAnalysisStrategy:
    """Country-specific strategy for UK economic impact analysis."""

    @property
    def income_variable(self) -> str:
        return "equiv_hbai_household_net_income"

    @property
    def budget_variable_names(self) -> list[str]:
        return [
            "household_tax",
            "household_benefits",
            "household_net_income",
        ]

    @property
    def programs(self) -> dict[str, dict]:
        return {
            "income_tax": {"entity": "person", "is_tax": True},
            "national_insurance": {"entity": "person", "is_tax": True},
            "vat": {"entity": "household", "is_tax": True},
            "council_tax": {"entity": "household", "is_tax": True},
            "universal_credit": {"entity": "person", "is_tax": False},
            "child_benefit": {"entity": "person", "is_tax": False},
            "pension_credit": {"entity": "person", "is_tax": False},
            "income_support": {"entity": "person", "is_tax": False},
            "working_tax_credit": {"entity": "person", "is_tax": False},
            "child_tax_credit": {"entity": "person", "is_tax": False},
        }

    def compute_poverty(
        self,
        baseline: Simulation,
        reform: Simulation,
    ) -> PovertyResult:
        return PovertyResult(
            baseline_poverty=calculate_uk_poverty_rates(baseline),
            reform_poverty=calculate_uk_poverty_rates(reform),
            baseline_poverty_by_age=calculate_uk_poverty_by_age(baseline),
            reform_poverty_by_age=calculate_uk_poverty_by_age(reform),
            baseline_poverty_by_gender=calculate_uk_poverty_by_gender(baseline),
            reform_poverty_by_gender=calculate_uk_poverty_by_gender(reform),
        )

    def compute_inequality(
        self,
        baseline: Simulation,
        reform: Simulation,
    ) -> InequalityResult:
        return InequalityResult(
            baseline_inequality=calculate_uk_inequality(baseline),
            reform_inequality=calculate_uk_inequality(reform),
        )


def economic_impact_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> PolicyReformAnalysis:
    """Perform comprehensive economic impact analysis of a UK policy reform."""
    return _shared_economic_impact_analysis(
        baseline_simulation,
        reform_simulation,
        UKAnalysisStrategy(),
    )
