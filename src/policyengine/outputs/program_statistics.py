"""Shared `ProgramStatistics` for reform-impact tables (US + UK)."""

from typing import Optional

from pydantic import ConfigDict

from policyengine.core import Output, Simulation
from policyengine.outputs.aggregate import Aggregate, AggregateType
from policyengine.outputs.change_aggregate import (
    ChangeAggregate,
    ChangeAggregateType,
)


class ProgramStatistics(Output):
    """Single program's statistics from a policy reform.

    Count fields are reported in the configured entity's units. For example,
    a tax-unit variable reports tax-unit recipient/winner/loser counts, while
    a person variable reports person counts.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_simulation: Simulation
    reform_simulation: Simulation
    program_name: str
    entity: str
    is_tax: bool = False

    # Results populated by run()
    baseline_total: Optional[float] = None
    reform_total: Optional[float] = None
    change: Optional[float] = None
    baseline_count: Optional[float] = None
    reform_count: Optional[float] = None
    winners: Optional[float] = None
    losers: Optional[float] = None

    def run(self):
        """Calculate statistics for this program."""
        # Baseline totals
        baseline_total = Aggregate(
            simulation=self.baseline_simulation,
            variable=self.program_name,
            aggregate_type=AggregateType.SUM,
            entity=self.entity,
        )
        baseline_total.run()

        # Reform totals
        reform_total = Aggregate(
            simulation=self.reform_simulation,
            variable=self.program_name,
            aggregate_type=AggregateType.SUM,
            entity=self.entity,
        )
        reform_total.run()

        # Count of recipients/payers (baseline)
        baseline_count = Aggregate(
            simulation=self.baseline_simulation,
            variable=self.program_name,
            aggregate_type=AggregateType.COUNT,
            entity=self.entity,
            filter_variable=self.program_name,
            filter_variable_geq=0.01,
        )
        baseline_count.run()

        # Count of recipients/payers (reform)
        reform_count = Aggregate(
            simulation=self.reform_simulation,
            variable=self.program_name,
            aggregate_type=AggregateType.COUNT,
            entity=self.entity,
            filter_variable=self.program_name,
            filter_variable_geq=0.01,
        )
        reform_count.run()

        # Winners and losers
        winners = ChangeAggregate(
            baseline_simulation=self.baseline_simulation,
            reform_simulation=self.reform_simulation,
            variable=self.program_name,
            aggregate_type=ChangeAggregateType.COUNT,
            entity=self.entity,
            change_geq=0.01 if not self.is_tax else -0.01,
        )
        winners.run()

        losers = ChangeAggregate(
            baseline_simulation=self.baseline_simulation,
            reform_simulation=self.reform_simulation,
            variable=self.program_name,
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
