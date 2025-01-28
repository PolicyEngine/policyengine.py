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


class PovertyRateMetricComparison(BaseModel):
    age_group: Literal["child", "working_age", "senior", "all"]
    racial_group: Literal["white", "black", "hispanic", "other", "all"]
    relative: bool
    poverty_rate: Literal[
        "uk_hbai_bhc", "uk_hbai_bhc_half", "us_spm", "us_spm_half"
    ]
    baseline: float
    reform: float
    change: float
    relative_change: float


class EconomyComparison(BaseModel):
    fiscal: FiscalComparison
    inequality: InequalityComparison
    distributional: DecileImpacts
    poverty: List[PovertyRateMetricComparison]


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
    poverty_metrics = []
    for baseline_metric, reform_metric in zip(
        baseline_poverty_metrics, reform_poverty_metrics
    ):
        change = reform_metric.value - baseline_metric.value
        rel_change = change / baseline_metric.value
        poverty_metrics.append(
            PovertyRateMetricComparison(
                age_group=baseline_metric.age_group,
                racial_group=baseline_metric.racial_group,
                relative=baseline_metric.relative,
                poverty_rate=baseline_metric.poverty_rate,
                baseline=baseline_metric.value,
                reform=reform_metric.value,
                change=change,
                relative_change=rel_change,
            )
        )

    return EconomyComparison(
        fiscal=fiscal_comparison,
        inequality=inequality_comparison,
        distributional=decile_impacts,
        poverty=poverty_metrics,
    )
