"""Calculate comparison statistics between two economic scenarios."""

import typing

from policyengine import Simulation

from pydantic import BaseModel
from policyengine.utils.calculations import get_change

from policyengine.outputs.macro.single import (
    _calculate_government_balance,
    FiscalSummary,
    _calculate_inequality,
    InequalitySummary,
)

from .decile import calculate_decile_impacts, DecileImpacts

from typing import Literal, List


class FiscalComparison(BaseModel):
    baseline: FiscalSummary
    reform: FiscalSummary
    change: FiscalSummary
    relative_change: FiscalSummary


class InequalityComparison(BaseModel):
    baseline: InequalitySummary
    reform: InequalitySummary
    change: InequalitySummary
    relative_change: InequalitySummary


class Headlines(BaseModel):
    budgetary_impact: float
    """The change in the (federal) government budget balance."""
    winner_share: float
    """The share of people that are better off in the reform scenario."""


class EconomyComparison(BaseModel):
    headlines: Headlines
    """Headline statistics for the comparison."""
    fiscal: FiscalComparison
    """Government budgets and other top-level fiscal statistics."""
    inequality: InequalityComparison
    """Inequality statistics for the household sector."""
    distributional: DecileImpacts
    """Distributional impacts of the reform."""


def calculate_economy_comparison(
    simulation: Simulation,
) -> EconomyComparison:
    """Calculate comparison statistics between two economic scenarios."""
    if not simulation.is_comparison:
        raise ValueError("Simulation must be a comparison simulation.")

    baseline = simulation.baseline_simulation
    reform = simulation.reform_simulation
    options = simulation.options

    baseline_balance = _calculate_government_balance(baseline, options)
    reform_balance = _calculate_government_balance(reform, options)
    balance_change = get_change(
        baseline_balance, reform_balance, relative=False
    )
    balance_rel_change = get_change(
        baseline_balance, reform_balance, relative=True
    )
    fiscal_comparison = FiscalComparison(
        baseline=baseline_balance,
        reform=reform_balance,
        change=balance_change,
        relative_change=balance_rel_change,
    )

    baseline_inequality = _calculate_inequality(baseline)
    reform_inequality = _calculate_inequality(reform)
    inequality_change = get_change(
        baseline_inequality, reform_inequality, relative=False
    )
    inequality_rel_change = get_change(
        baseline_inequality, reform_inequality, relative=True
    )
    inequality_comparison = InequalityComparison(
        baseline=baseline_inequality,
        reform=reform_inequality,
        change=inequality_change,
        relative_change=inequality_rel_change,
    )

    decile_impacts = calculate_decile_impacts(baseline, reform, options)

    # Headlines
    budgetary_impact = fiscal_comparison.change.federal_balance
    winner_share = decile_impacts.income.winners_and_losers.all.gain_share
    headlines = Headlines(
        budgetary_impact=budgetary_impact,
        winner_share=winner_share,
    )

    return EconomyComparison(
        headlines=headlines,
        fiscal=fiscal_comparison,
        inequality=inequality_comparison,
        distributional=decile_impacts,
    )
