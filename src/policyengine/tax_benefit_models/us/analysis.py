"""Microsimulation reform analysis for the US model.

The single-household calculator lives in :mod:`.household`; this module
holds the population-level reform-analysis helpers.
"""

from __future__ import annotations

from typing import Union

import pandas as pd
from pydantic import BaseModel, Field, computed_field

from policyengine.core import OutputCollection, Simulation
from policyengine.outputs import (
    CliffImpact,
    LaborSupplyResponse,
    ProgramStatistics,
    calculate_cliff_impact,
    calculate_labor_supply_response,
    configure_cliff_impact_variables,
    configure_labor_supply_response_variables,
)
from policyengine.outputs.change_aggregate import (
    ChangeAggregate,
    ChangeAggregateType,
)
from policyengine.outputs.decile_impact import (
    DecileImpact,
    calculate_decile_impacts,
)
from policyengine.outputs.extra_variables import add_extra_variables
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
    """Federal/state/unattributed partition of a US reform's budgetary impact.

    Sign convention: positive means the government is better off (more tax
    revenue or lower benefit spending); negative means revenue lost or
    spending incurred.

    ``total`` is measured directly from the reform-minus-baseline change in
    ``household_tax`` minus the change in ``household_benefits``, so it covers
    every tax and benefit the model computes. ``federal`` and ``state`` hold
    only the pieces that are cleanly attributable to a level of government
    today; ``unattributed`` is the residual (``total - federal - state``) that
    carries everything not yet split. ``total`` is a computed field, so
    ``federal + state + unattributed`` always equals it by construction. See
    :func:`calculate_budgetary_impact` for the exact variables behind each
    share.
    """

    federal: float = Field(
        ...,
        description="Federal budgetary impact, USD (positive = government gain).",
    )
    state: float = Field(
        ...,
        description="State budgetary impact, USD (positive = government gain).",
    )
    unattributed: float = Field(
        ...,
        description=(
            "Budgetary impact not yet attributed to a level of government, "
            "USD. Residual of total minus federal minus state."
        ),
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> float:
        """Total budgetary impact, USD: federal + state + unattributed."""
        return self.federal + self.state + self.unattributed


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


# Budgetary-impact variables that are not in the default US output
# (household_tax, household_benefits, and the three tax variables are). They
# must be materialized before the reform simulations run.
_BUDGETARY_IMPACT_EXTRA_VARIABLES: dict[str, list[str]] = {
    "person": ["federal_benefit_cost", "state_benefit_cost"],
}


def configure_budgetary_impact_variables(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> None:
    """Materialize the budgetary-impact aggregates in the reform outputs.

    ``federal_benefit_cost`` / ``state_benefit_cost`` are not in the default US
    output, so they are added as extra output variables before the simulations
    run. Call this before :meth:`Simulation.ensure` so the aggregates are
    present when :func:`calculate_budgetary_impact` reads them;
    :func:`economic_impact_analysis` does this automatically.
    """
    add_extra_variables(baseline_simulation, _BUDGETARY_IMPACT_EXTRA_VARIABLES)
    add_extra_variables(reform_simulation, _BUDGETARY_IMPACT_EXTRA_VARIABLES)


def calculate_budgetary_impact(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> BudgetaryImpact:
    """Partition a US reform's budgetary impact into federal, state, and
    unattributed shares.

    All figures are reform-minus-baseline weighted totals. Sign convention:
    positive means the government is better off (more tax revenue or lower
    benefit spending).

    ``total`` is measured directly from the model's household aggregates::

        total = Δhousehold_tax - Δhousehold_benefits

    so it captures *every* tax and benefit the model computes, regardless of
    whether the affected program can be attributed to a level of government.

    ``federal`` and ``state`` attribute only the cleanly-assignable pieces::

        federal = Δincome_tax + Δemployee_payroll_tax - Δfederal_benefit_cost
        state   = Δstate_income_tax                   - Δstate_benefit_cost

    where ``federal_benefit_cost`` / ``state_benefit_cost`` are the
    policyengine-us aggregates that split shared-funding programs (Medicaid
    FMAP, CHIP eFMAP) into their federal and state portions.

    ``unattributed`` is the residual, ``total - federal - state``. It carries
    everything not yet split by level of government — 100%-federal programs
    such as SSI and SNAP, 100%-state supplements, and any tax outside the
    three tax variables above — until finer attribution exists. Because
    ``total`` is measured from ``household_tax`` / ``household_benefits``
    rather than summed from the attributed pieces, a reform to an
    unattributed program (for example SSI) surfaces in ``total`` and
    ``unattributed`` instead of silently reading as zero.

    ``federal_benefit_cost`` / ``state_benefit_cost`` are not in the default US
    output; :func:`economic_impact_analysis` calls
    :func:`configure_budgetary_impact_variables` to materialize them before the
    simulations run. Callers using this helper directly must do the same.
    """
    total = _sum_change(
        baseline_simulation, reform_simulation, "household_tax"
    ) - _sum_change(baseline_simulation, reform_simulation, "household_benefits")

    federal = (
        _sum_change(baseline_simulation, reform_simulation, "income_tax")
        + _sum_change(baseline_simulation, reform_simulation, "employee_payroll_tax")
        - _sum_change(baseline_simulation, reform_simulation, "federal_benefit_cost")
    )
    state = _sum_change(
        baseline_simulation, reform_simulation, "state_income_tax"
    ) - _sum_change(baseline_simulation, reform_simulation, "state_benefit_cost")

    unattributed = total - federal - state
    return BudgetaryImpact(federal=federal, state=state, unattributed=unattributed)


class PolicyReformAnalysis(BaseModel):
    """Complete policy reform analysis result."""

    decile_impacts: OutputCollection[DecileImpact]
    program_statistics: OutputCollection[ProgramStatistics]
    budgetary_impact: BudgetaryImpact
    baseline_poverty: OutputCollection[Poverty]
    reform_poverty: OutputCollection[Poverty]
    baseline_inequality: Inequality
    reform_inequality: Inequality
    labor_supply_response: LaborSupplyResponse
    cliff_impact: CliffImpact | None = None


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
    include_cliff_impacts: bool = False,
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
    configure_labor_supply_response_variables(
        baseline_simulation,
        reform_simulation,
        country_code="us",
    )
    if include_cliff_impacts:
        configure_cliff_impact_variables(baseline_simulation, reform_simulation)
    configure_budgetary_impact_variables(baseline_simulation, reform_simulation)
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
    labor_supply_response = calculate_labor_supply_response(
        baseline_simulation,
        reform_simulation,
        country_code="us",
    )
    cliff_impact = (
        calculate_cliff_impact(baseline_simulation, reform_simulation)
        if include_cliff_impacts
        else None
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
        labor_supply_response=labor_supply_response,
        cliff_impact=cliff_impact,
    )
