"""Intra-decile impact output.

Computes the distribution of income change categories within each decile.
Each row represents one decile (1-10) or the overall average (decile=0),
with five proportion columns summing to ~1.0.

The five categories classify households by their percentage income change:
  - lose_more_than_5pct:  change <= -5%
  - lose_less_than_5pct:  -5% < change <= -0.1%
  - no_change:            -0.1% < change <= 0.1%
  - gain_less_than_5pct:  0.1% < change <= 5%
  - gain_more_than_5pct:  change > 5%

Proportions are people-weighted (using household_count_people *
household_weight) so they reflect the share of people, not households.
"""

import numpy as np
import pandas as pd
from pydantic import ConfigDict

from policyengine.core import Output, OutputCollection, Simulation

# The 5-category thresholds
BOUNDS = [-np.inf, -0.05, -1e-3, 1e-3, 0.05, np.inf]
CATEGORY_NAMES = [
    "lose_more_than_5pct",
    "lose_less_than_5pct",
    "no_change",
    "gain_less_than_5pct",
    "gain_more_than_5pct",
]


class IntraDecileImpact(Output):
    """Single decile's intra-decile impact — proportion of people in each
    income change category."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_simulation: Simulation
    reform_simulation: Simulation
    income_variable: str = "household_net_income"
    decile_variable: str | None = None  # If set, use pre-computed grouping
    entity: str = "household"
    decile: int  # 1-10 for individual deciles
    quantiles: int = 10

    # Results populated by run()
    lose_more_than_5pct: float | None = None
    lose_less_than_5pct: float | None = None
    no_change: float | None = None
    gain_less_than_5pct: float | None = None
    gain_more_than_5pct: float | None = None

    def run(self):
        """Calculate intra-decile proportions for this specific decile."""
        baseline_data = getattr(
            self.baseline_simulation.output_dataset.data, self.entity
        )
        reform_data = getattr(
            self.reform_simulation.output_dataset.data, self.entity
        )

        baseline_income = baseline_data[self.income_variable].values
        reform_income = reform_data[self.income_variable].values

        # Determine decile grouping
        if self.decile_variable:
            decile_series = baseline_data[self.decile_variable].values
        else:
            decile_series = (
                pd.qcut(
                    baseline_income,
                    self.quantiles,
                    labels=False,
                    duplicates="drop",
                )
                + 1
            )

        # People-weighted counts
        weights = baseline_data[f"{self.entity}_weight"].values
        if self.entity == "household":
            people_count = baseline_data["household_count_people"].values
            people = people_count * weights
        else:
            people = weights

        # Compute percentage income change
        capped_baseline = np.maximum(baseline_income, 1.0)
        income_change = (reform_income - baseline_income) / capped_baseline

        in_decile = decile_series == self.decile
        people_in_decile = float(np.sum(people[in_decile]))

        if people_in_decile == 0:
            self.lose_more_than_5pct = 0.0
            self.lose_less_than_5pct = 0.0
            self.no_change = 1.0
            self.gain_less_than_5pct = 0.0
            self.gain_more_than_5pct = 0.0
            return

        proportions = []
        for lower, upper in zip(BOUNDS[:-1], BOUNDS[1:]):
            in_category = (income_change > lower) & (income_change <= upper)
            in_both = in_decile & in_category
            proportions.append(float(np.sum(people[in_both]) / people_in_decile))

        self.lose_more_than_5pct = proportions[0]
        self.lose_less_than_5pct = proportions[1]
        self.no_change = proportions[2]
        self.gain_less_than_5pct = proportions[3]
        self.gain_more_than_5pct = proportions[4]


def compute_intra_decile_impacts(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    income_variable: str = "household_net_income",
    decile_variable: str | None = None,
    entity: str = "household",
    quantiles: int = 10,
) -> OutputCollection[IntraDecileImpact]:
    """Compute intra-decile proportions for all deciles + overall average.

    Returns:
        OutputCollection containing list of IntraDecileImpact objects
        (deciles 1-N plus overall average at decile=0) and DataFrame.
    """
    results = []
    for decile in range(1, quantiles + 1):
        impact = IntraDecileImpact(
            baseline_simulation=baseline_simulation,
            reform_simulation=reform_simulation,
            income_variable=income_variable,
            decile_variable=decile_variable,
            entity=entity,
            decile=decile,
            quantiles=quantiles,
        )
        impact.run()
        results.append(impact)

    # Overall average (decile=0): arithmetic mean of decile proportions
    overall = IntraDecileImpact(
        baseline_simulation=baseline_simulation,
        reform_simulation=reform_simulation,
        income_variable=income_variable,
        decile_variable=decile_variable,
        entity=entity,
        decile=0,
        quantiles=quantiles,
        lose_more_than_5pct=sum(r.lose_more_than_5pct for r in results) / quantiles,
        lose_less_than_5pct=sum(r.lose_less_than_5pct for r in results) / quantiles,
        no_change=sum(r.no_change for r in results) / quantiles,
        gain_less_than_5pct=sum(r.gain_less_than_5pct for r in results) / quantiles,
        gain_more_than_5pct=sum(r.gain_more_than_5pct for r in results) / quantiles,
    )
    results.append(overall)

    # Create DataFrame
    df = pd.DataFrame(
        [
            {
                "baseline_simulation_id": r.baseline_simulation.id,
                "reform_simulation_id": r.reform_simulation.id,
                "decile": r.decile,
                "lose_more_than_5pct": r.lose_more_than_5pct,
                "lose_less_than_5pct": r.lose_less_than_5pct,
                "no_change": r.no_change,
                "gain_less_than_5pct": r.gain_less_than_5pct,
                "gain_more_than_5pct": r.gain_more_than_5pct,
            }
            for r in results
        ]
    )

    return OutputCollection(outputs=results, dataframe=df)
