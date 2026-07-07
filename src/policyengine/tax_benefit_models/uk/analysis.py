"""Microsimulation reform analysis for the UK model.

The single-household calculator lives in :mod:`.household`; this module
holds the population-level reform-analysis helpers.
"""

from __future__ import annotations

from pydantic import BaseModel

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
    cliff_impact: CliffImpact | None = None


def _validate_program_statistics_config(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> None:
    """Validate UK program-stat variables before running simulations."""
    validate_program_statistics_config(
        UK_PROGRAMS,
        baseline_simulation,
        reform_simulation,
        "UK",
    )


def economic_impact_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    include_cliff_impacts: bool = False,
) -> PolicyReformAnalysis:
    """Perform comprehensive analysis of a UK policy reform."""
    configure_labor_supply_response_variables(
        baseline_simulation,
        reform_simulation,
        country_code="uk",
    )
    if include_cliff_impacts:
        configure_cliff_impact_variables(baseline_simulation, reform_simulation)
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

    program_collection = build_program_statistics(
        UK_PROGRAMS,
        baseline_simulation,
        reform_simulation,
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
    cliff_impact = (
        calculate_cliff_impact(baseline_simulation, reform_simulation)
        if include_cliff_impacts
        else None
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
        cliff_impact=cliff_impact,
    )
