"""Microsimulation reform analysis for the US model.

The single-household calculator lives in :mod:`.household`; this module
holds the population-level reform-analysis helpers.
"""

from __future__ import annotations

from typing import Union

from pydantic import BaseModel, Field, computed_field

from policyengine.core import OutputCollection, Simulation
from policyengine.outputs import (
    CliffImpact,
    LaborSupplyResponse,
    ProgramStatistics,
    build_program_statistics,
    calculate_cliff_impact,
    calculate_labor_supply_response,
    configure_cliff_impact_variables,
    configure_labor_supply_response_variables,
    validate_program_statistics_config,
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

    ``total`` combines the reform-minus-baseline change in ``household_tax`` and
    ``household_benefits`` with the change in the government cost of the
    shared-funding health programs (Medicaid FMAP, CHIP eFMAP, and Medicare
    Savings Programs), which ``household_benefits`` excludes by default.
    ``federal`` and ``state`` hold only the pieces that are cleanly
    attributable to a level of government today; ``unattributed`` is the
    residual (``total - federal - state``) that carries everything not yet
    split. ``total`` is a computed field, so ``federal + state + unattributed``
    always equals it by construction. See :func:`calculate_budgetary_impact`
    for the exact variables behind each share.
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


def _include_health_benefits_in_net_income(simulation: Simulation) -> bool:
    """Whether ``household_benefits`` already includes Medicaid/CHIP/MSP.

    ``gov.simulation.include_health_benefits_in_net_income`` (default False in
    policyengine-us) controls whether the shared-funding health-program values
    are folded into ``household_benefits``. When False, those programs are
    excluded from ``household_benefits``, so :func:`calculate_budgetary_impact`
    adds their government cost from ``federal_benefit_cost`` /
    ``state_benefit_cost`` instead. The value is read from the baseline
    simulation at its dataset year; a missing parameter or year falls back to
    False (the default).
    """
    year = getattr(simulation.dataset, "year", None)
    if year is None:
        return False
    try:
        parameter = simulation.tax_benefit_model_version.get_parameter(
            "gov.simulation.include_health_benefits_in_net_income"
        )
    except ValueError:
        return False
    return bool(parameter._core_param(f"{year}-01-01"))


def calculate_budgetary_impact(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> BudgetaryImpact:
    """Partition a US reform's budgetary impact into federal, state, and
    unattributed shares.

    All figures are reform-minus-baseline weighted totals. Sign convention:
    positive means the government is better off (more tax revenue or lower
    benefit spending).

    ``total`` is the change in ``household_tax`` minus the change in
    ``household_benefits``, plus the change in the shared-funding health-program
    government cost (Medicaid FMAP, CHIP eFMAP, and Medicare Savings Programs)
    read from ``federal_benefit_cost`` / ``state_benefit_cost``. Those health
    programs are excluded from ``household_benefits`` by default
    (``gov.simulation.include_health_benefits_in_net_income`` is False), so
    their cost is added separately; when that parameter is True the values are
    already in ``household_benefits`` and the cost is not added again, avoiding
    a double count. ``total`` therefore covers taxes and every benefit the
    model counts, including shared-funding health-program cost.

    ``federal`` and ``state`` attribute only the cleanly-assignable pieces::

        federal = Δincome_tax + Δemployee_payroll_tax - Δfederal_benefit_cost
        state   = Δstate_income_tax                   - Δstate_benefit_cost

    where ``federal_benefit_cost`` / ``state_benefit_cost`` split the
    shared-funding health programs into their federal and state portions.

    ``unattributed`` is the residual, ``total - federal - state``. It carries
    everything not yet split by level of government — 100%-federal programs such
    as SSI and SNAP, 100%-state supplements, and any tax outside the three tax
    variables above — until finer attribution exists. Because ``total`` is
    measured from the household aggregates and health cost rather than summed
    from the attributed pieces, a reform to a shared-funding health program
    surfaces in ``total`` and the federal/state split (residual zero), while a
    reform to an unattributed program such as SSI surfaces in ``total`` and
    ``unattributed`` — neither silently reads as zero.

    ``federal_benefit_cost`` / ``state_benefit_cost`` are not in the default US
    output; :func:`economic_impact_analysis` calls
    :func:`configure_budgetary_impact_variables` to materialize them before the
    simulations run. Callers using this helper directly must do the same.
    """
    household_tax_change = _sum_change(
        baseline_simulation, reform_simulation, "household_tax"
    )
    household_benefits_change = _sum_change(
        baseline_simulation, reform_simulation, "household_benefits"
    )
    federal_benefit_cost_change = _sum_change(
        baseline_simulation, reform_simulation, "federal_benefit_cost"
    )
    state_benefit_cost_change = _sum_change(
        baseline_simulation, reform_simulation, "state_benefit_cost"
    )

    total = household_tax_change - household_benefits_change
    if not _include_health_benefits_in_net_income(baseline_simulation):
        # Medicaid/CHIP/MSP are excluded from household_benefits by default, so
        # add their government cost; when the parameter is True they are already
        # in household_benefits and adding the cost would double-count.
        total -= federal_benefit_cost_change + state_benefit_cost_change

    federal = (
        _sum_change(baseline_simulation, reform_simulation, "income_tax")
        + _sum_change(baseline_simulation, reform_simulation, "employee_payroll_tax")
        - federal_benefit_cost_change
    )
    state = (
        _sum_change(baseline_simulation, reform_simulation, "state_income_tax")
        - state_benefit_cost_change
    )

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


def _validate_program_statistics_config(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> None:
    """Validate US program-stat variables before running simulations."""
    validate_program_statistics_config(
        US_PROGRAMS,
        baseline_simulation,
        reform_simulation,
        "US",
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

    program_collection = build_program_statistics(
        US_PROGRAMS,
        baseline_simulation,
        reform_simulation,
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
