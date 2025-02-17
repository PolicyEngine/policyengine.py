"""Calculate comparison statistics between two economic scenarios."""

import typing

from policyengine import PolicyEngine

from pydantic import BaseModel
from policyengine.utils.calculations import get_change
from policyengine.constants import DEFAULT_DATASETS_BY_COUNTRY

from policyengine.outputs.macro.single import (
    _calculate_government_balance,
    FiscalSummary,
    _calculate_inequality,
    InequalitySummary,
)

from .decile import calculate_decile_impacts, DecileImpacts

from typing import Literal, List
from policyengine.utils.types import *
from pydantic import Field

class EconomyComparisonOptions(BaseModel):
    country: CountryType = Field(..., description="The country to simulate.")
    data: DataType = Field(None, description="The data to simulate.")
    time_period: TimePeriodType = Field(
        2025, description="The time period to simulate.", ge=2024, le=2035
    )
    reform: PolicyType = Field(None, description="The reform to simulate.")
    baseline: PolicyType = Field(None, description="The baseline to simulate.")
    region: RegionType = Field(
        None, description="The region to simulate within the country."
    )
    subsample: SubsampleType = Field(
        None,
        description="How many, if a subsample, households to randomly simulate.",
    )

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
    engine: PolicyEngine,
    **options,
) -> EconomyComparison:
    """Calculate comparison statistics between two economic scenarios."""

    options = EconomyComparisonOptions(**options)

    if options.data is None:
        options.data = DEFAULT_DATASETS_BY_COUNTRY[
            options.country
        ]

    baseline = engine.expect_simulation(
        name="baseline",
        country=options.country,
        scope="macro",
        policy=options.baseline,
        data=options.data,
        time_period=options.time_period,
        region=options.region,
    )

    reform = engine.expect_simulation(
        name="reform",
        country=options.country,
        scope="macro",
        policy=options.reform,
        data=options.data,
        time_period=options.time_period,
        region=options.region,
    )

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
