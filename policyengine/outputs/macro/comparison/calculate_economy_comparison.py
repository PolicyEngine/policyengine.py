"""Calculate comparison statistics between two economic scenarios."""

import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation

from pydantic import BaseModel
from policyengine.utils.calculations import get_change

from policyengine.outputs.macro.single import (
    calculate_government_balance,
    FiscalSummary,
    calculate_inequality,
    InequalitySummary,
)

from .decile import calculate_decile_impacts, DecileImpacts


class FiscalComparison(BaseModel):
    baseline: FiscalSummary
    reform: FiscalSummary
    change: FiscalSummary

class InequalityComparison(BaseModel):
    baseline: InequalitySummary
    reform: InequalitySummary
    change: InequalitySummary


class EconomyComparison(BaseModel):
    fiscal: FiscalComparison
    inequality: InequalityComparison
    distributional: DecileImpacts


def calculate_economy_comparison(
    simulation: "Simulation",
) -> EconomyComparison:
    """Calculate comparison statistics between two economic scenarios."""
    if not simulation.is_comparison:
        raise ValueError("Simulation must be a comparison simulation.")

    baseline = simulation.baseline_simulation
    reform = simulation.reform_simulation
    options = simulation.options

    baseline_balance = calculate_government_balance(baseline, options)
    reform_balance = calculate_government_balance(reform, options)
    balance_change = get_change(baseline_balance, reform_balance)
    fiscal_comparison = FiscalComparison(
        baseline=baseline_balance, reform=reform_balance, change=balance_change
    )

    baseline_inequality = calculate_inequality(baseline)
    reform_inequality = calculate_inequality(reform)
    inequality_change = get_change(baseline_inequality, reform_inequality)
    inequality_comparison = InequalityComparison(
        baseline=baseline_inequality, reform=reform_inequality, change=inequality_change
    )

    decile_impacts = calculate_decile_impacts(baseline, reform, options)

    return EconomyComparison(
        fiscal=fiscal_comparison, 
        inequality=inequality_comparison,
        distributional=decile_impacts
    )
