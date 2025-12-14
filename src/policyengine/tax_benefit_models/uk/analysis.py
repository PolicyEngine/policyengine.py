"""General utility functions for UK policy reform analysis."""

import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from microdf import MicroDataFrame
from pydantic import BaseModel, Field, create_model

from policyengine.core import OutputCollection, Simulation
from policyengine.core.policy import Policy
from policyengine.outputs.decile_impact import (
    DecileImpact,
    calculate_decile_impacts,
)

from .datasets import PolicyEngineUKDataset, UKYearData
from .model import uk_latest
from .outputs import ProgrammeStatistics


def _create_entity_output_model(
    entity: str, variables: list[str]
) -> type[BaseModel]:
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
                person_data[key] = [
                    0.0
                ] * n_people  # Default to 0 for numeric fields
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
    person_df = MicroDataFrame(
        pd.DataFrame(person_data), weights="person_weight"
    )
    benunit_df = MicroDataFrame(
        pd.DataFrame(benunit_data), weights="benunit_weight"
    )
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


class PolicyReformAnalysis(BaseModel):
    """Complete policy reform analysis result."""

    decile_impacts: OutputCollection[DecileImpact]
    programme_statistics: OutputCollection[ProgrammeStatistics]


def economic_impact_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> PolicyReformAnalysis:
    """Perform comprehensive analysis of a policy reform.

    Returns:
        PolicyReformAnalysis containing decile impacts and programme statistics
    """
    baseline_simulation.ensure()
    reform_simulation.ensure()

    assert len(baseline_simulation.dataset.data.household) > 100, (
        "Baseline simulation must have more than 100 households"
    )
    assert len(reform_simulation.dataset.data.household) > 100, (
        "Reform simulation must have more than 100 households"
    )

    # Decile impact
    decile_impacts = calculate_decile_impacts(
        dataset=baseline_simulation.dataset,
        tax_benefit_model_version=baseline_simulation.tax_benefit_model_version,
        baseline_policy=baseline_simulation.policy,
        reform_policy=reform_simulation.policy,
        dynamic=baseline_simulation.dynamic,
    )

    # Major programmes to analyse
    programmes = {
        # Tax
        "income_tax": {"entity": "person", "is_tax": True},
        "national_insurance": {"entity": "person", "is_tax": True},
        "vat": {"entity": "household", "is_tax": True},
        "council_tax": {"entity": "household", "is_tax": True},
        # Benefits
        "universal_credit": {"entity": "person", "is_tax": False},
        "child_benefit": {"entity": "person", "is_tax": False},
        "pension_credit": {"entity": "person", "is_tax": False},
        "income_support": {"entity": "person", "is_tax": False},
        "working_tax_credit": {"entity": "person", "is_tax": False},
        "child_tax_credit": {"entity": "person", "is_tax": False},
    }

    programme_statistics = []

    for programme_name, programme_info in programmes.items():
        entity = programme_info["entity"]
        is_tax = programme_info["is_tax"]

        stats = ProgrammeStatistics(
            baseline_simulation=baseline_simulation,
            reform_simulation=reform_simulation,
            programme_name=programme_name,
            entity=entity,
            is_tax=is_tax,
        )
        stats.run()
        programme_statistics.append(stats)

    # Create DataFrame
    programme_df = pd.DataFrame(
        [
            {
                "baseline_simulation_id": p.baseline_simulation.id,
                "reform_simulation_id": p.reform_simulation.id,
                "programme_name": p.programme_name,
                "entity": p.entity,
                "is_tax": p.is_tax,
                "baseline_total": p.baseline_total,
                "reform_total": p.reform_total,
                "change": p.change,
                "baseline_count": p.baseline_count,
                "reform_count": p.reform_count,
                "winners": p.winners,
                "losers": p.losers,
            }
            for p in programme_statistics
        ]
    )

    programme_collection = OutputCollection(
        outputs=programme_statistics, dataframe=programme_df
    )

    return PolicyReformAnalysis(
        decile_impacts=decile_impacts,
        programme_statistics=programme_collection,
    )
