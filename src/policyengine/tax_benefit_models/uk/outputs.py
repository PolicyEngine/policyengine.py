"""UK-specific output templates."""

from typing import TYPE_CHECKING

from pydantic import ConfigDict

from policyengine.core import Output
from policyengine.outputs.aggregate import Aggregate, AggregateType
from policyengine.outputs.change_aggregate import (
    ChangeAggregate,
    ChangeAggregateType,
)

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation


class ProgrammeStatistics(Output):
    """Single programme's statistics from a policy reform - represents one database row."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_simulation: "Simulation"
    reform_simulation: "Simulation"
    programme_name: str
    entity: str
    is_tax: bool = False

    # Results populated by run()
    baseline_total: float | None = None
    reform_total: float | None = None
    change: float | None = None
    baseline_count: float | None = None
    reform_count: float | None = None
    winners: float | None = None
    losers: float | None = None

    def run(self):
        """Calculate statistics for this programme."""
        # Baseline totals
        baseline_total = Aggregate(
            simulation=self.baseline_simulation,
            variable=self.programme_name,
            aggregate_type=AggregateType.SUM,
            entity=self.entity,
        )
        baseline_total.run()

        # Reform totals
        reform_total = Aggregate(
            simulation=self.reform_simulation,
            variable=self.programme_name,
            aggregate_type=AggregateType.SUM,
            entity=self.entity,
        )
        reform_total.run()

        # Count of recipients/payers (baseline)
        baseline_count = Aggregate(
            simulation=self.baseline_simulation,
            variable=self.programme_name,
            aggregate_type=AggregateType.COUNT,
            entity=self.entity,
            filter_variable=self.programme_name,
            filter_variable_geq=0.01,
        )
        baseline_count.run()

        # Count of recipients/payers (reform)
        reform_count = Aggregate(
            simulation=self.reform_simulation,
            variable=self.programme_name,
            aggregate_type=AggregateType.COUNT,
            entity=self.entity,
            filter_variable=self.programme_name,
            filter_variable_geq=0.01,
        )
        reform_count.run()

        # Winners and losers
        winners = ChangeAggregate(
            baseline_simulation=self.baseline_simulation,
            reform_simulation=self.reform_simulation,
            variable=self.programme_name,
            aggregate_type=ChangeAggregateType.COUNT,
            entity=self.entity,
            change_geq=0.01 if not self.is_tax else -0.01,
        )
        winners.run()

        losers = ChangeAggregate(
            baseline_simulation=self.baseline_simulation,
            reform_simulation=self.reform_simulation,
            variable=self.programme_name,
            aggregate_type=ChangeAggregateType.COUNT,
            entity=self.entity,
            change_leq=-0.01 if not self.is_tax else 0.01,
        )
        losers.run()

        # Populate results
        self.baseline_total = float(baseline_total.result)
        self.reform_total = float(reform_total.result)
        self.change = float(reform_total.result - baseline_total.result)
        self.baseline_count = float(baseline_count.result)
        self.reform_count = float(reform_count.result)
        self.winners = float(winners.result)
        self.losers = float(losers.result)
