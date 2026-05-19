"""Microsimulation reform analysis for the UK model.

The single-household calculator lives in :mod:`.household`; this module
holds the population-level reform-analysis helpers.
"""

from __future__ import annotations

import pandas as pd
from pydantic import BaseModel

from policyengine.core import OutputCollection, Simulation
from policyengine.outputs import (
    LaborSupplyResponse,
    ProgramStatistics,
    calculate_labor_supply_response,
    configure_labor_supply_response_variables,
)
from policyengine.outputs.decile_impact import (
    DecileImpact,
    calculate_decile_impacts,
)
from policyengine.outputs.inequality import (
    Inequality,
    calculate_uk_inequality,
)
from policyengine.outputs.intra_decile_impact import (
    IntraDecileImpact,
    compute_intra_decile_impacts,
)
from policyengine.outputs.poverty import (
    Poverty,
    calculate_uk_poverty_rates,
)
from policyengine.utils.errors import format_conditional_error_detail

# Map of UK program-statistics variable name -> program metadata. The
# entity for each program is derived from the variable's own metadata at
# runtime, so this list does not silently drift if policyengine-uk moves
# a variable between entities.
UK_PROGRAMS: dict[str, dict] = {
    "income_tax": {"is_tax": True},
    "national_insurance": {"is_tax": True},
    "vat": {"is_tax": True},
    "council_tax": {"is_tax": True},
    "fuel_duty": {"is_tax": True},
    "ni_employer": {"is_tax": True},
    "universal_credit": {"is_tax": False},
    "child_benefit": {"is_tax": False},
    "pension_credit": {"is_tax": False},
    "income_support": {"is_tax": False},
    # tax_credits overlaps with the separate working_tax_credit and
    # child_tax_credit rows. Downstream budget adapters should select the
    # row set they need rather than summing all program statistics.
    "tax_credits": {"is_tax": False},
    "working_tax_credit": {"is_tax": False},
    "child_tax_credit": {"is_tax": False},
    "state_pension": {"is_tax": False},
}


class PolicyReformAnalysis(BaseModel):
    """Complete policy reform analysis result."""

    decile_impacts: OutputCollection[DecileImpact]
    wealth_decile_impacts: OutputCollection[DecileImpact]
    intra_wealth_decile_impacts: OutputCollection[IntraDecileImpact]
    program_statistics: OutputCollection[ProgramStatistics]
    baseline_poverty: OutputCollection[Poverty]
    reform_poverty: OutputCollection[Poverty]
    baseline_inequality: Inequality
    reform_inequality: Inequality
    labor_supply_response: LaborSupplyResponse


def _format_missing_program_variables(missing_variables: set[str]) -> str | None:
    """Format the optional missing-variable detail for program statistics."""
    return format_conditional_error_detail(
        "Missing model variables",
        missing_variables,
    )


def _uk_program_statistics_config_error_message(
    missing_variables: set[str],
    missing_outputs: set[tuple[str, str]],
) -> str:
    lines = ["UK program statistics config is invalid:"]

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
    """Validate UK program-stat variables before running simulations."""
    missing_variables: set[str] = set()
    missing_outputs: set[tuple[str, str]] = set()

    simulations = (baseline_simulation, reform_simulation)
    for program_name in UK_PROGRAMS:
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

    raise ValueError(
        _uk_program_statistics_config_error_message(
            missing_variables,
            missing_outputs,
        ),
    )


def economic_impact_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> PolicyReformAnalysis:
    """Perform comprehensive analysis of a UK policy reform."""
    configure_labor_supply_response_variables(
        baseline_simulation,
        reform_simulation,
        country_code="uk",
    )
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
    )
    wealth_decile_impacts = calculate_decile_impacts(
        baseline_simulation=baseline_simulation,
        reform_simulation=reform_simulation,
        income_variable="household_net_income",
        decile_variable="household_wealth_decile",
        entity="household",
    )
    intra_wealth_decile_impacts = compute_intra_decile_impacts(
        baseline_simulation=baseline_simulation,
        reform_simulation=reform_simulation,
        income_variable="household_net_income",
        decile_variable="household_wealth_decile",
        entity="household",
    )

    model_version = baseline_simulation.tax_benefit_model_version
    program_statistics = []
    for program_name, program_info in UK_PROGRAMS.items():
        stats = ProgramStatistics(
            baseline_simulation=baseline_simulation,
            reform_simulation=reform_simulation,
            program_name=program_name,
            entity=model_version.get_variable(program_name).entity,
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

    baseline_poverty = calculate_uk_poverty_rates(baseline_simulation)
    reform_poverty = calculate_uk_poverty_rates(reform_simulation)
    baseline_inequality = calculate_uk_inequality(baseline_simulation)
    reform_inequality = calculate_uk_inequality(reform_simulation)
    labor_supply_response = calculate_labor_supply_response(
        baseline_simulation,
        reform_simulation,
        country_code="uk",
    )

    return PolicyReformAnalysis(
        decile_impacts=decile_impacts,
        wealth_decile_impacts=wealth_decile_impacts,
        intra_wealth_decile_impacts=intra_wealth_decile_impacts,
        program_statistics=program_collection,
        baseline_poverty=baseline_poverty,
        reform_poverty=reform_poverty,
        baseline_inequality=baseline_inequality,
        reform_inequality=reform_inequality,
        labor_supply_response=labor_supply_response,
    )
