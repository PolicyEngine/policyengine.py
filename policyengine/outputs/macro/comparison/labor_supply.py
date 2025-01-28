import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation, SimulationOptions

from policyengine_core.simulations import Microsimulation

from pydantic import BaseModel
from typing import Literal, List
import numpy as np


class LaborSupplyMetricImpact(BaseModel):
    elasticity: Literal["income", "substitution", "all"]
    """Filter to the effects of a specific elasticity."""
    decile: Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "all"]
    """The income decile of the household, if filtering."""
    unit: Literal["earnings", "hours"]
    """The unit of the labor supply metric."""
    baseline: float
    """The labor supply metric value in the baseline scenario."""
    reform: float
    """The labor supply metric value in the reform scenario."""
    change: float
    """The change in the labor supply metric value."""
    relative_change: float
    """The relative change in the labor supply metric value."""


def calculate_labor_supply_impact(
    baseline: Microsimulation,
    reformed: Microsimulation,
    options: "SimulationOptions",
) -> List[LaborSupplyMetricImpact]:
    """Calculate labor supply impact statistics for a set of households."""
    if not _has_behavioral_response(reformed):
        return []

    lsr_metrics = []
    for elasticity in ["income", "substitution", "all"]:
        for decile in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "all"]:
            for unit in ["earnings", "hours"]:
                if options.country != "us" and unit == "hours":
                    # Hours not yet supported for the UK.
                    continue
                lsr_metrics.append(
                    calculate_specific_lsr_metric(
                        baseline,
                        reformed,
                        elasticity,
                        decile,
                        unit,
                    )
                )


def calculate_specific_lsr_metric(
    baseline: Microsimulation,
    reformed: Microsimulation,
    elasticity: Literal["income", "substitution", "all"],
    decile: Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "all"],
    unit: Literal["earnings", "hours"],
) -> LaborSupplyMetricImpact:
    """Calculate a specific labor supply metric for a set of households."""

    if unit == "earnings":
        baseline_variable = "employment_income"
        if elasticity == "income":
            variable = "income_elasticity_lsr"
        elif elasticity == "substitution":
            variable = "substitution_elasticity_lsr"
        else:
            variable = "employment_income_behavioral_response"
    else:
        baseline_variable = "weekly_hours_worked"
        if elasticity == "income":
            variable = (
                "weekly_hours_worked_behavioural_response_income_elasticity"
            )
        elif elasticity == "substitution":
            variable = "weekly_hours_worked_behavioural_response_substitution_elasticity"
        else:
            variable = "weekly_hours_worked"

    baseline_values = baseline.calculate(baseline_variable)
    reform_values = reformed.calculate(baseline_variable) + reformed.calculate(
        variable
    )

    if decile == "all":
        in_decile = np.ones_like(baseline_values, dtype=bool)
    else:
        in_decile = reformed.calculate("household_income_decile") == decile

    baseline_total = (baseline_values * in_decile).sum()
    reform_total = (reform_values * in_decile).sum()
    change = reform_total - baseline_total
    relative_change = change / baseline_total

    return LaborSupplyMetricImpact(
        elasticity=elasticity,
        decile=decile,
        unit=unit,
        baseline=baseline_total,
        reform=reform_total,
        change=change,
        relative_change=relative_change,
    )


def _has_behavioral_response(simulation: Microsimulation) -> bool:
    """Check if the simulation has a behavioral response to labor supply."""
    return (
        "employment_income_behavioral_response"
        in simulation.tax_benefit_system.variables
        and any(
            simulation.calculate("employment_income_behavioral_response") != 0
        )
    )
