"""Microsimulation reform analysis for the US model.

The single-household calculator lives in :mod:`.household`; this module
holds the population-level reform-analysis helpers.
"""

from __future__ import annotations

from typing import Union

import pandas as pd
from pydantic import BaseModel

from policyengine.core import OutputCollection, Simulation
from policyengine.outputs import ProgramStatistics
from policyengine.outputs.decile_impact import (
    DecileImpact,
    calculate_decile_impacts,
)
from policyengine.outputs.inequality import (
    Inequality,
    USInequalityPreset,
    calculate_us_inequality,
)
from policyengine.outputs.poverty import (
    Poverty,
    calculate_us_poverty_rates,
)
from policyengine.utils.errors import (
    create_error,
    format_conditional_error_detail,
)

US_PROGRAMS = {
    "income_tax": {"entity": "tax_unit", "is_tax": True},
    "employee_payroll_tax": {"entity": "tax_unit", "is_tax": True},
    "state_income_tax": {"entity": "tax_unit", "is_tax": True},
    "snap": {"entity": "spm_unit", "is_tax": False},
    "tanf": {"entity": "spm_unit", "is_tax": False},
    "ssi": {"entity": "person", "is_tax": False},
    "social_security": {"entity": "person", "is_tax": False},
    "medicare_cost": {"entity": "person", "is_tax": False},
    "medicaid": {"entity": "person", "is_tax": False},
    "eitc": {"entity": "tax_unit", "is_tax": False},
    "ctc": {"entity": "tax_unit", "is_tax": False},
}


class PolicyReformAnalysis(BaseModel):
    """Complete policy reform analysis result."""

    decile_impacts: OutputCollection[DecileImpact]
    program_statistics: OutputCollection[ProgramStatistics]
    baseline_poverty: OutputCollection[Poverty]
    reform_poverty: OutputCollection[Poverty]
    baseline_inequality: Inequality
    reform_inequality: Inequality


def _format_missing_program_variables(missing_variables: set[str]) -> str | None:
    """Format the optional missing-variable detail for program statistics."""
    return format_conditional_error_detail(
        "Missing model variables",
        missing_variables,
    )


def _program_statistics_config_error_message(
    missing_variables: set[str],
    missing_outputs: set[tuple[str, str]],
) -> str:
    lines = ["US program statistics config is invalid:"]

    missing_variables_message = _format_missing_program_variables(missing_variables)
    if missing_variables_message is not None:
        lines.append(missing_variables_message)

    if missing_outputs:
        formatted = ", ".join(
            f"{program_name} on {entity}"
            for program_name, entity in sorted(missing_outputs)
        )
        lines.append("Variables not materialized in simulation outputs: " + formatted)
        lines.append(
            "Add them to the model version's entity_variables or pass them "
            "via Simulation.extra_variables before running the simulation."
        )

    return "\n".join(lines)


def _validate_program_statistics_config(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> None:
    """Validate US program-stat variables before running simulations."""
    missing_variables: set[str] = set()
    missing_outputs: set[tuple[str, str]] = set()

    simulations = (baseline_simulation, reform_simulation)
    for program_name, program_info in US_PROGRAMS.items():
        for simulation in simulations:
            model_version = simulation.tax_benefit_model_version
            try:
                variable = model_version.get_variable(program_name)
            except ValueError:
                missing_variables.add(program_name)
                continue

            resolved_variables = model_version.resolve_entity_variables(simulation)
            if program_name not in resolved_variables.get(variable.entity, []):
                missing_outputs.add((program_name, variable.entity))

    if not missing_variables and not missing_outputs:
        return

    raise create_error(
        ValueError,
        _program_statistics_config_error_message(
            missing_variables,
            missing_outputs,
        ),
    )


def economic_impact_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    inequality_preset: Union[USInequalityPreset, str] = USInequalityPreset.STANDARD,
) -> PolicyReformAnalysis:
    """Perform comprehensive analysis of a US policy reform.

    Args:
        baseline_simulation: Baseline simulation.
        reform_simulation: Reform simulation.
        inequality_preset: Preset for the inequality output.

    Returns:
        ``PolicyReformAnalysis`` with decile impacts, program
        statistics, baseline and reform poverty, and inequality.
    """
    _validate_program_statistics_config(baseline_simulation, reform_simulation)

    baseline_simulation.ensure()
    reform_simulation.ensure()

    assert len(baseline_simulation.dataset.data.household) > 100, (
        "Baseline simulation must have more than 100 households"
    )
    assert len(reform_simulation.dataset.data.household) > 100, (
        "Reform simulation must have more than 100 households"
    )

    decile_impacts = calculate_decile_impacts(
        baseline_simulation=baseline_simulation,
        reform_simulation=reform_simulation,
        income_variable="household_net_income",
    )

    program_statistics = []
    for program_name, program_info in US_PROGRAMS.items():
        stats = ProgramStatistics(
            baseline_simulation=baseline_simulation,
            reform_simulation=reform_simulation,
            program_name=program_name,
            entity=program_info["entity"],
            is_tax=program_info["is_tax"],
        )
        stats.run()
        program_statistics.append(stats)

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

    baseline_poverty = calculate_us_poverty_rates(baseline_simulation)
    reform_poverty = calculate_us_poverty_rates(reform_simulation)
    baseline_inequality = calculate_us_inequality(
        baseline_simulation, preset=inequality_preset
    )
    reform_inequality = calculate_us_inequality(
        reform_simulation, preset=inequality_preset
    )

    return PolicyReformAnalysis(
        decile_impacts=decile_impacts,
        program_statistics=program_collection,
        baseline_poverty=baseline_poverty,
        reform_poverty=reform_poverty,
        baseline_inequality=baseline_inequality,
        reform_inequality=reform_inequality,
    )
