"""Microsimulation reform analysis for the US model.

The single-household calculator lives in :mod:`.household`; this module
holds the population-level reform-analysis helpers.
"""

from __future__ import annotations

from typing import Union

import pandas as pd
from pydantic import BaseModel, Field

from policyengine.core import OutputCollection, Simulation
from policyengine.outputs import ProgramStatistics
from policyengine.outputs.change_aggregate import (
    ChangeAggregate,
    ChangeAggregateType,
)
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
from policyengine.utils.errors import format_conditional_error_detail

# Map of US program-statistics variable name -> program metadata. The
# entity for each program is derived from the variable's own metadata
# at runtime (see ``_validate_program_statistics_config`` and
# ``economic_impact_analysis``), so this list cannot silently drift
# when policyengine-us moves a variable between entities.
US_PROGRAMS: dict[str, dict] = {
    "income_tax": {"is_tax": True},
    "employee_payroll_tax": {"is_tax": True},
    "state_income_tax": {"is_tax": True},
    "snap": {"is_tax": False},
    "tanf": {"is_tax": False},
    "ssi": {"is_tax": False},
    "social_security": {"is_tax": False},
    "medicare_cost": {"is_tax": False},
    "medicaid": {"is_tax": False},
    "eitc": {"is_tax": False},
    "ctc": {"is_tax": False},
}


class BudgetaryImpact(BaseModel):
    """Federal/state partition of a reform's budgetary impact.

    Sign convention: a negative value is revenue the government loses
    (or spending it incurs). Symmetric to the change in `income_tax`:
    reform tax revenue minus baseline tax revenue, with benefit spending
    subtracted.
    """

    federal: float = Field(..., description="Federal budgetary impact, USD.")
    state: float = Field(..., description="State budgetary impact, USD.")
    total: float = Field(..., description="Total budgetary impact, USD.")


def _sum_change(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    variable: str,
) -> float:
    """Reform minus baseline total for a variable."""
    agg = ChangeAggregate(
        baseline_simulation=baseline_simulation,
        reform_simulation=reform_simulation,
        variable=variable,
        aggregate_type=ChangeAggregateType.SUM,
    )
    agg.run()
    return float(agg.result)


def calculate_budgetary_impact(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> BudgetaryImpact:
    """Partition a reform's budgetary impact into federal and state shares.

    Federal share = change in federal tax revenue (income_tax + payroll_tax)
    minus change in federal benefit spending (`federal_benefit_cost`, which
    sums the federal portion of shared-funding benefit programs — currently
    Medicaid and CHIP).

    State share = change in state tax revenue (state_income_tax) minus
    change in state benefit spending (`state_benefit_cost`).

    Programs that are 100% federal (SNAP benefits pre-FY2028, SSI, LIHEAP,
    WIC, Section 8, school meals) and 100% state (state supplements via
    `household_state_benefits`) are not yet folded in; this partitions only
    the shared-funding programs exposed through
    `federal_benefit_cost` / `state_benefit_cost` in policyengine-us.
    """
    federal_tax_change = _sum_change(
        baseline_simulation, reform_simulation, "income_tax"
    ) + _sum_change(baseline_simulation, reform_simulation, "payroll_tax")
    state_tax_change = _sum_change(
        baseline_simulation, reform_simulation, "state_income_tax"
    )
    federal_benefit_change = _sum_change(
        baseline_simulation, reform_simulation, "federal_benefit_cost"
    )
    state_benefit_change = _sum_change(
        baseline_simulation, reform_simulation, "state_benefit_cost"
    )

    federal = federal_tax_change - federal_benefit_change
    state = state_tax_change - state_benefit_change
    return BudgetaryImpact(federal=federal, state=state, total=federal + state)


class PolicyReformAnalysis(BaseModel):
    """Complete policy reform analysis result."""

    decile_impacts: OutputCollection[DecileImpact]
    program_statistics: OutputCollection[ProgramStatistics]
    budgetary_impact: BudgetaryImpact
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
    for program_name in US_PROGRAMS:
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

    model_version = baseline_simulation.tax_benefit_model_version
    program_statistics = []
    for program_name, program_info in US_PROGRAMS.items():
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

    baseline_poverty = calculate_us_poverty_rates(baseline_simulation)
    reform_poverty = calculate_us_poverty_rates(reform_simulation)
    baseline_inequality = calculate_us_inequality(
        baseline_simulation, preset=inequality_preset
    )
    reform_inequality = calculate_us_inequality(
        reform_simulation, preset=inequality_preset
    )

    budgetary_impact = calculate_budgetary_impact(
        baseline_simulation, reform_simulation
    )

    return PolicyReformAnalysis(
        decile_impacts=decile_impacts,
        program_statistics=program_collection,
        budgetary_impact=budgetary_impact,
        baseline_poverty=baseline_poverty,
        reform_poverty=reform_poverty,
        baseline_inequality=baseline_inequality,
        reform_inequality=reform_inequality,
    )
