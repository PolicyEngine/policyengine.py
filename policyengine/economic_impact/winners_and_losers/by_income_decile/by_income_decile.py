from policyengine.economic_impact.base_metric_calculator import BaseMetricCalculator
from policyengine_uk import Microsimulation
from microdf import MicroDataFrame, MicroSeries
import numpy as np

class ByIncomeDecile(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):
        baseline_income = MicroSeries(
            self.baseline.calculate("household_net_income"), weights=self.baseline.calculate("household_weight")
        )
        reform_income = MicroSeries(
            self.reformed.calculate("household_net_income"), weights=baseline_income.weights
        )
        people = MicroSeries(
            self.baseline.calculate("household_count_people"), weights=baseline_income.weights
        )
        decile = MicroSeries(self.baseline.calculate("household_income_decile")).values
        absolute_change = (reform_income - baseline_income).values
        capped_baseline_income = np.maximum(baseline_income.values, 1)
        capped_reform_income = (
            np.maximum(reform_income.values, 1) + absolute_change
        )
        income_change = (
            capped_reform_income - capped_baseline_income
        ) / capped_baseline_income

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
                    round(float(people[in_both].sum() / people[in_decile].sum()) * 100, 1)
                )
            all_outcomes[label] = round(sum(outcome_groups[label]) / 10, 1)

        return {
            "result": dict(deciles=outcome_groups, all=all_outcomes)
        }