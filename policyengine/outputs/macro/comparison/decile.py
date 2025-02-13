import typing

from policyengine import Simulation, SimulationOptions

from policyengine_core.simulations import Microsimulation

from pydantic import BaseModel
from typing import Dict
import numpy as np


class IncomeMeasureSpecificDecileIncomeChange(BaseModel):
    relative: Dict[int, float]
    """Relative impacts by income decile."""
    average: Dict[int, float]
    """Average impacts by income decile."""


class IncomeMeasureSpecificDecileWinnersLosersGroupOutcomes(BaseModel):
    lose_more_than_5_percent_share: float
    """Share of households losing more than 5% of net income."""
    lose_less_than_5_percent_share: float
    """Share of households losing less than 5% of net income."""
    lose_share: float
    """Share of households losing net income."""
    no_change_share: float
    """Share of households with no change in net income."""
    gain_share: float
    """Share of households gaining net income."""
    gain_less_than_5_percent_share: float
    """Share of households gaining less than 5% of net income."""
    gain_more_than_5_percent_share: float
    """Share of households gaining more than 5% of net income."""


class IncomeMeasureSpecificDecileWinnersLosers(BaseModel):
    deciles: Dict[int, IncomeMeasureSpecificDecileWinnersLosersGroupOutcomes]
    """Winners and losers by income decile."""
    all: IncomeMeasureSpecificDecileWinnersLosersGroupOutcomes
    """Winners and losers for all households."""


class IncomeMeasureSpecificDecileImpacts(BaseModel):
    income_change: IncomeMeasureSpecificDecileIncomeChange
    """Income change by income decile."""
    winners_and_losers: IncomeMeasureSpecificDecileWinnersLosers
    """Winners and losers by income decile."""


class DecileImpacts(BaseModel):
    income: IncomeMeasureSpecificDecileImpacts
    """Impacts by income decile."""
    wealth: IncomeMeasureSpecificDecileImpacts | None
    """Impacts by wealth decile, if available."""


def calculate_decile_impacts(
    baseline: Microsimulation,
    reform: Microsimulation,
    options: "SimulationOptions",
) -> DecileImpacts:
    """Calculate changes to households by income and wealth deciles."""
    income_impacts = calculate_income_specific_decile_impacts(
        baseline, reform, by_wealth_decile=False
    )
    if options.country == "uk":
        wealth_impacts = calculate_income_specific_decile_impacts(
            baseline, reform, by_wealth_decile=True
        )
    else:
        wealth_impacts = None
    return DecileImpacts(income=income_impacts, wealth=wealth_impacts)


def calculate_income_specific_decile_impacts(
    baseline: Microsimulation,
    reform: Microsimulation,
    by_wealth_decile: bool,
) -> IncomeMeasureSpecificDecileImpacts:
    """Calculate changes to households by income and wealth deciles."""
    income_impacts = calculate_income_specific_decile_income_changes(
        baseline, reform, by_wealth_decile
    )
    winners_losers = calculate_income_specific_decile_winners_losers(
        baseline, reform, by_wealth_decile
    )
    return IncomeMeasureSpecificDecileImpacts(
        income_change=income_impacts, winners_and_losers=winners_losers
    )


def calculate_income_specific_decile_winners_losers(
    baseline: Microsimulation,
    reform: Microsimulation,
    by_wealth_decile: bool,
) -> dict:
    """Calculate winners and losers by income and wealth deciles."""
    baseline_income = baseline.calculate("household_net_income")
    reform_income = reform.calculate("household_net_income")
    people_per_household = baseline.calculate("household_count_people")
    if not by_wealth_decile:
        decile = baseline.calculate("household_income_decile")
    else:
        wealth = baseline.calculate("total_wealth")
        household_count_people = baseline.calculate("household_count_people")
        wealth.weights *= household_count_people
        decile = wealth.decile_rank().clip(1, 10).astype(int)
    # Filter out negative decile values due to negative incomes
    absolute_change = (reform_income - baseline_income).values
    capped_baseline_income = np.maximum(baseline_income.values, 1)
    capped_reform_income = (
        np.maximum(reform_income.values, 1) + absolute_change
    )
    income_change = (
        capped_reform_income - capped_baseline_income
    ) / capped_baseline_income

    # Within each decile, calculate the percentage of people who:
    # 1. Gained more than 5% of their income
    # 2. Gained between 0% and 5% of their income
    # 3. Had no change in income
    # 3. Lost between 0% and 5% of their income
    # 4. Lost more than 5% of their income

    BOUNDS = [
        (-np.inf, -0.05),
        (-0.05, -1e-3),
        (-np.inf, -1e-3),
        (-1e-3, 1e-3),
        (1e-3, np.inf),
        (1e-3, 0.05),
        (0.05, np.inf),
    ]
    LABELS = [
        "lose_more_than_5_percent_share",
        "lose_less_than_5_percent_share",
        "lose_share",
        "no_change_share",
        "gain_share",
        "gain_less_than_5_percent_share",
        "gain_more_than_5_percent_share",
    ]

    deciles = {}
    all = {}

    for i in range(len(BOUNDS)):
        lower, upper = BOUNDS[i]
        label = LABELS[i]

        # First, add the 'all' group

        total_people = people_per_household.sum()
        in_group = (income_change >= lower) & (income_change < upper)
        people_in_group = people_per_household[in_group].sum()
        share_in_group = people_in_group / total_people
        all[label] = share_in_group

        # Next, add the decile-specific groups

        for d in range(1, 11):
            in_group = (income_change[decile == d] >= lower) & (
                income_change[decile == d] < upper
            )
            people_in_group = people_per_household[decile == d][in_group].sum()
            people_in_decile = people_per_household[decile == d].sum()
            share_in_group = people_in_group / people_in_decile
            if d not in deciles:
                deciles[d] = {}
            deciles[d][label] = share_in_group

    return IncomeMeasureSpecificDecileWinnersLosers(deciles=deciles, all=all)


def calculate_income_specific_decile_income_changes(
    baseline: Microsimulation,
    reform: Microsimulation,
    by_wealth_decile: bool,
) -> dict:
    """Calculate changes to households by income and wealth deciles."""
    baseline_income = baseline.calculate("household_net_income")
    reform_income = reform.calculate("household_net_income")
    if not by_wealth_decile:
        decile = baseline.calculate("household_income_decile")
    else:
        wealth = baseline.calculate("total_wealth")
        household_count_people = baseline.calculate("household_count_people")
        wealth.weights *= household_count_people
        decile = wealth.decile_rank().clip(1, 10).astype(int)
    # Filter out negative decile values due to negative incomes
    baseline_income_filtered = baseline_income[decile >= 0]
    reform_income_filtered = reform_income[decile >= 0]

    income_change = reform_income_filtered - baseline_income_filtered
    rel_income_change_by_decile = (
        income_change.groupby(decile).sum()
        / baseline_income_filtered.groupby(decile).sum()
    )
    avg_income_change_by_decile = (
        income_change.groupby(decile).sum()
        / baseline_income_filtered.groupby(decile).count()
    )
    rel_decile_dict = rel_income_change_by_decile.to_dict()
    avg_decile_dict = avg_income_change_by_decile.to_dict()
    per_decile_changes = dict(
        relative={int(k): v for k, v in rel_decile_dict.items()},
        average={int(k): v for k, v in avg_decile_dict.items()},
    )
    return IncomeMeasureSpecificDecileIncomeChange(**per_decile_changes)
