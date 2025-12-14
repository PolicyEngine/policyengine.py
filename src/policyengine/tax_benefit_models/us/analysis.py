"""General utility functions for US policy reform analysis."""

import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from microdf import MicroDataFrame
from pydantic import BaseModel, Field

from policyengine.core import OutputCollection, Simulation
from policyengine.core.policy import Policy
from policyengine.outputs.decile_impact import (
    DecileImpact,
    calculate_decile_impacts,
)

from .datasets import PolicyEngineUSDataset, USYearData
from .model import us_latest
from .outputs import ProgramStatistics


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
                person_data[key] = [
                    0.0
                ] * n_people  # Default to 0 for numeric fields
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
    person_df = MicroDataFrame(
        pd.DataFrame(person_data), weights="person_weight"
    )
    household_df = MicroDataFrame(
        pd.DataFrame(household_data), weights="household_weight"
    )
    marital_unit_df = MicroDataFrame(
        pd.DataFrame(marital_unit_data), weights="marital_unit_weight"
    )
    family_df = MicroDataFrame(
        pd.DataFrame(family_data), weights="family_weight"
    )
    spm_unit_df = MicroDataFrame(
        pd.DataFrame(spm_unit_data), weights="spm_unit_weight"
    )
    tax_unit_df = MicroDataFrame(
        pd.DataFrame(tax_unit_data), weights="tax_unit_weight"
    )

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


class PolicyReformAnalysis(BaseModel):
    """Complete policy reform analysis result."""

    decile_impacts: OutputCollection[DecileImpact]
    program_statistics: OutputCollection[ProgramStatistics]


def economic_impact_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> PolicyReformAnalysis:
    """Perform comprehensive analysis of a policy reform.

    Returns:
        PolicyReformAnalysis containing decile impacts and program statistics
    """
    baseline_simulation.ensure()
    reform_simulation.ensure()

    assert len(baseline_simulation.dataset.data.household) > 100, (
        "Baseline simulation must have more than 100 households"
    )
    assert len(reform_simulation.dataset.data.household) > 100, (
        "Reform simulation must have more than 100 households"
    )

    # Decile impact (using household_net_income for US)
    decile_impacts = calculate_decile_impacts(
        dataset=baseline_simulation.dataset,
        tax_benefit_model_version=baseline_simulation.tax_benefit_model_version,
        baseline_policy=baseline_simulation.policy,
        reform_policy=reform_simulation.policy,
        dynamic=baseline_simulation.dynamic,
        income_variable="household_net_income",
    )

    # Major programs to analyse
    programs = {
        # Federal taxes
        "income_tax": {"entity": "tax_unit", "is_tax": True},
        "payroll_tax": {"entity": "person", "is_tax": True},
        # State and local taxes
        "state_income_tax": {"entity": "tax_unit", "is_tax": True},
        # Benefits
        "snap": {"entity": "spm_unit", "is_tax": False},
        "tanf": {"entity": "spm_unit", "is_tax": False},
        "ssi": {"entity": "person", "is_tax": False},
        "social_security": {"entity": "person", "is_tax": False},
        "medicare": {"entity": "person", "is_tax": False},
        "medicaid": {"entity": "person", "is_tax": False},
        "eitc": {"entity": "tax_unit", "is_tax": False},
        "ctc": {"entity": "tax_unit", "is_tax": False},
    }

    program_statistics = []

    for program_name, program_info in programs.items():
        entity = program_info["entity"]
        is_tax = program_info["is_tax"]

        stats = ProgramStatistics(
            baseline_simulation=baseline_simulation,
            reform_simulation=reform_simulation,
            program_name=program_name,
            entity=entity,
            is_tax=is_tax,
        )
        stats.run()
        program_statistics.append(stats)

    # Create DataFrame
    program_df = pd.DataFrame(
        [
            {
                "baseline_simulation_id": p.baseline_simulation.id,
                "reform_simulation_id": p.reform_simulation.id,
                "program_name": p.program_name,
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
            for p in program_statistics
        ]
    )

    program_collection = OutputCollection(
        outputs=program_statistics, dataframe=program_df
    )

    return PolicyReformAnalysis(
        decile_impacts=decile_impacts, program_statistics=program_collection
    )
