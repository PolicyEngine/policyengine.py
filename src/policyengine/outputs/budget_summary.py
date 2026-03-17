"""Budget summary output — totals for key budget variables under baseline and reform."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
from pydantic import ConfigDict

from policyengine.core import Output, OutputCollection
from policyengine.outputs.aggregate import Aggregate, AggregateType

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation


class BudgetSummaryItem(Output):
    """One row of the budget summary — totals for a single variable."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_simulation: Simulation
    reform_simulation: Simulation
    variable_name: str
    entity: str

    # Results populated by run()
    baseline_total: float | None = None
    reform_total: float | None = None
    change: float | None = None

    def run(self):
        baseline_agg = Aggregate(
            simulation=self.baseline_simulation,
            variable=self.variable_name,
            aggregate_type=AggregateType.SUM,
            entity=self.entity,
        )
        baseline_agg.run()

        reform_agg = Aggregate(
            simulation=self.reform_simulation,
            variable=self.variable_name,
            aggregate_type=AggregateType.SUM,
            entity=self.entity,
        )
        reform_agg.run()

        self.baseline_total = float(baseline_agg.result)
        self.reform_total = float(reform_agg.result)
        self.change = self.reform_total - self.baseline_total


def compute_budget_summary(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    variables: dict[str, str],
) -> OutputCollection[BudgetSummaryItem]:
    """Compute budget totals for each variable under baseline and reform.

    Args:
        baseline_simulation: Already-run baseline simulation.
        reform_simulation: Already-run reform simulation.
        variables: Mapping of variable name to entity,
            e.g. ``{"household_tax": "household"}``.

    Returns:
        OutputCollection of BudgetSummaryItem objects with a DataFrame.
    """
    results: list[BudgetSummaryItem] = []
    for var_name, entity in variables.items():
        item = BudgetSummaryItem(
            baseline_simulation=baseline_simulation,
            reform_simulation=reform_simulation,
            variable_name=var_name,
            entity=entity,
        )
        item.run()
        results.append(item)

    df = pd.DataFrame(
        [
            {
                "variable_name": r.variable_name,
                "entity": r.entity,
                "baseline_total": r.baseline_total,
                "reform_total": r.reform_total,
                "change": r.change,
            }
            for r in results
        ]
    )

    return OutputCollection(outputs=results, dataframe=df)
