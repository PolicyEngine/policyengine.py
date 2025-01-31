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
    calculate_poverty,
)

from .decile import calculate_decile_impacts, DecileImpacts
from .labor_supply import (
    calculate_labor_supply_impact,
    LaborSupplyMetricImpact,
)

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
    poverty_impact: float
    """The relative change in the regular poverty rate."""
    winner_share: float
    """The share of people that are better off in the reform scenario."""


class PovertyRateMetricComparison(BaseModel):
    age_group: Literal["child", "working_age", "senior", "all"]
    """The age group of the population."""
    gender: Literal["male", "female", "all"]
    """The gender of the population."""
    racial_group: Literal["white", "black", "hispanic", "other", "all"]
    """The racial group of the population."""
    relative: bool
    """Whether the poverty rate is relative to the total population, or a headcount."""
    poverty_rate: Literal[
        "regular",
        "deep",
        "uk_hbai_bhc",
        "uk_hbai_bhc_half",
        "us_spm",
        "us_spm_half",
    ]
    """The poverty rate definition being calculated."""
    baseline: float
    """The poverty rate value in the baseline scenario."""
    reform: float
    """The poverty rate value in the reform scenario."""
    change: float
    """The change in the poverty rate value."""
    relative_change: float
    """The relative change in the poverty rate value."""


class EconomyComparison(BaseModel):
    headlines: Headlines
    """Headline statistics for the comparison."""
    fiscal: FiscalComparison
    """Government budgets and other top-level fiscal statistics."""
    inequality: InequalityComparison
    """Inequality statistics for the household sector."""
    distributional: DecileImpacts
    """Distributional impacts of the reform."""
    poverty: List[PovertyRateMetricComparison]
    """Poverty rates for different demographic groups and poverty definitions."""
    labor_supply: List[LaborSupplyMetricImpact]
    """Labor supply impacts for different demographic groups and labor supply metrics."""


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

    baseline_inequality = calculate_inequality(baseline)
    reform_inequality = calculate_inequality(reform)
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

    baseline_poverty_metrics = calculate_poverty(baseline, options)
    reform_poverty_metrics = calculate_poverty(reform, options)
    poverty_metrics: List[PovertyRateMetricComparison] = []
    for baseline_metric, reform_metric in zip(
        baseline_poverty_metrics, reform_poverty_metrics
    ):
        change = reform_metric.value - baseline_metric.value
        if baseline_metric.value == 0:
            rel_change = 0
        else:
            rel_change = change / baseline_metric.value
        poverty_metrics.append(
            PovertyRateMetricComparison(
                age_group=baseline_metric.age_group,
                gender=baseline_metric.gender,
                racial_group=baseline_metric.racial_group,
                relative=baseline_metric.relative,
                poverty_rate=baseline_metric.poverty_rate,
                baseline=baseline_metric.value,
                reform=reform_metric.value,
                change=change,
                relative_change=rel_change,
            )
        )

    labor_supply_metrics = calculate_labor_supply_impact(
        baseline, reform, options
    )

    # Headlines
    budgetary_impact = fiscal_comparison.change.federal_balance
    poverty_impact = next(
        filter(
            lambda metric: metric.age_group == "all"
            and metric.racial_group == "all"
            and metric.poverty_rate == "regular",
            poverty_metrics,
        )
    ).relative_change
    winner_share = decile_impacts.income.winners_and_losers.all.gain_share
    headlines = Headlines(
        budgetary_impact=budgetary_impact,
        poverty_impact=poverty_impact,
        winner_share=winner_share,
    )

    return EconomyComparison(
        headlines=headlines,
        fiscal=fiscal_comparison,
        inequality=inequality_comparison,
        distributional=decile_impacts,
        poverty=poverty_metrics,
        labor_supply=labor_supply_metrics,
    )
