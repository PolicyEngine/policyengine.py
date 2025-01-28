"""Calculate comparison statistics between two economic scenarios."""

import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation

from pydantic import BaseModel
from policyengine.utils.calculations import get_change

from .single import (
    calculate_government_balance,
    FiscalSummary,
    calculate_inequality,
    InequalitySummary,
)


class FiscalComparison(BaseModel):
    baseline: FiscalSummary
    reform: FiscalSummary
    change: FiscalSummary


class EconomyComparison(BaseModel):
    fiscal: FiscalComparison
    inequality: InequalitySummary


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
    change = get_change(baseline_balance, reform_balance)
    fiscal_comparison = FiscalComparison(
        baseline=baseline_balance, reform=reform_balance, change=change
    )

    baseline_inequality = calculate_inequality(baseline)
    reform_inequality = calculate_inequality(reform)
    inequality_comparison = get_change(baseline_inequality, reform_inequality)

    return EconomyComparison(
        fiscal=fiscal_comparison, inequality=inequality_comparison
    )
