from policyengine import Simulation
from microdf import MicroSeries
import numpy as np


def income_decile(simulation: Simulation):
    """Calculate the impact of the reform on income deciles.

    Args:
        simulation (Simulation): The simulation for which the impact is to be calculated.

    Returns:
        dict: A dictionary containing the impact details with the following keys:
            - deciles (dict): A dictionary with keys representing outcome labels and values as lists of percentages for each decile.
            - all (dict): A dictionary with keys representing outcome labels and values as overall percentages.
    """
    baseline = simulation.calculate("macro/baseline")
    reform = simulation.calculate("macro/reform")

    baseline_income = MicroSeries(
        baseline["household"]["finance"]["household_net_income"],
        weights=baseline["household"]["demographics"]["household_weight"],
    )
    reform_income = MicroSeries(
        reform["household"]["finance"]["household_net_income"],
        weights=baseline_income.weights,
    )
    people = MicroSeries(
        baseline["household"]["demographics"]["household_count_people"],
        weights=baseline_income.weights,
    )
    decile = MicroSeries(
        baseline["household"]["finance"]["household_income_decile"]
    ).values
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

    outcome_groups = {}
    all_outcomes = {}
    BOUNDS = [-np.inf, -0.05, -1e-3, 1e-3, 0.05, np.inf]
    LABELS = [
        "Lose more than 5%",
        "Lose less than 5%",
        "No change",
        "Gain less than 5%",
        "Gain more than 5%",
    ]
    for lower, upper, label in zip(BOUNDS[:-1], BOUNDS[1:], LABELS):
        outcome_groups[label] = []
        for i in range(1, 11):
            in_decile = decile == i
            in_group = (income_change > lower) & (income_change <= upper)
            in_both = in_decile & in_group
            outcome_groups[label].append(
                float(people[in_both].sum() / people[in_decile].sum())
            )
        all_outcomes[label] = sum(outcome_groups[label]) / 10
    return dict(deciles=outcome_groups, all=all_outcomes)
