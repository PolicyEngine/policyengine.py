"""Intra-decile impact output.

Computes the distribution of income change categories within each decile.
Each row represents one decile (1-10) or the overall result (decile=0),
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

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from pydantic import ConfigDict

from policyengine.core import Output, OutputCollection, Simulation
from policyengine.outputs.decile_analysis import (
    _prepare_decile_analysis,
    _PreparedDecileAnalysis,
)

# The 5-category thresholds
BOUNDS = [-np.inf, -0.05, -1e-3, 1e-3, 0.05, np.inf]
CATEGORY_NAMES = [
    "lose_more_than_5pct",
    "lose_less_than_5pct",
    "no_change",
    "gain_less_than_5pct",
    "gain_more_than_5pct",
]


@dataclass(frozen=True)
class _IntraDecileImpactValues:
    """People-weighted category proportions for one selected population."""

    lose_more_than_5pct: Optional[float]
    lose_less_than_5pct: Optional[float]
    no_change: Optional[float]
    gain_less_than_5pct: Optional[float]
    gain_more_than_5pct: Optional[float]


def _calculate_intra_decile_values(
    analysis: _PreparedDecileAnalysis,
    *,
    decile: Optional[int],
) -> _IntraDecileImpactValues:
    """Calculate category proportions for a decile or the full population."""
    selected = analysis.included.copy()
    if decile is not None:
        selected &= analysis.groups.eq(decile).fillna(False).to_numpy(dtype=bool)

    selected_weights = analysis.effective_weight[selected]
    total_weight = float(np.sum(selected_weights))
    if total_weight == 0:
        return _IntraDecileImpactValues(
            lose_more_than_5pct=None,
            lose_less_than_5pct=None,
            no_change=None,
            gain_less_than_5pct=None,
            gain_more_than_5pct=None,
        )

    baseline_income = analysis.baseline_income[selected]
    reform_income = analysis.reform_income[selected]
    income_change = (reform_income - baseline_income) / np.maximum(
        baseline_income,
        1.0,
    )
    proportions = []
    for lower, upper in zip(BOUNDS[:-1], BOUNDS[1:]):
        in_category = (income_change > lower) & (income_change <= upper)
        proportions.append(float(np.sum(selected_weights[in_category]) / total_weight))

    return _IntraDecileImpactValues(
        lose_more_than_5pct=proportions[0],
        lose_less_than_5pct=proportions[1],
        no_change=proportions[2],
        gain_less_than_5pct=proportions[3],
        gain_more_than_5pct=proportions[4],
    )


class IntraDecileImpact(Output):
    """Single decile's intra-decile impact — proportion of people in each
    income change category."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_simulation: Simulation
    reform_simulation: Simulation
    income_variable: str = "household_net_income"
    decile_variable: Optional[str] = None  # If set, use pre-computed grouping
    entity: str = "household"
    decile: int  # 1-10 for individual deciles
    quantiles: int = 10

    # Results populated by run()
    lose_more_than_5pct: Optional[float] = None
    lose_less_than_5pct: Optional[float] = None
    no_change: Optional[float] = None
    gain_less_than_5pct: Optional[float] = None
    gain_more_than_5pct: Optional[float] = None

    def run(self) -> None:
        """Calculate intra-decile proportions for this specific decile."""
        analysis = _prepare_decile_analysis(
            self.baseline_simulation,
            self.reform_simulation,
            income_variable=self.income_variable,
            decile_variable=self.decile_variable,
            entity=self.entity,
            quantiles=self.quantiles,
            require_effective_weight=True,
        )
        self._run_from_prepared(analysis)

    def _run_from_prepared(
        self,
        analysis: _PreparedDecileAnalysis,
    ) -> None:
        """Populate this output from already validated shared inputs."""
        values = _calculate_intra_decile_values(
            analysis,
            decile=None if self.decile == 0 else self.decile,
        )
        self.lose_more_than_5pct = values.lose_more_than_5pct
        self.lose_less_than_5pct = values.lose_less_than_5pct
        self.no_change = values.no_change
        self.gain_less_than_5pct = values.gain_less_than_5pct
        self.gain_more_than_5pct = values.gain_more_than_5pct


def compute_intra_decile_impacts(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    income_variable: str = "household_net_income",
    decile_variable: Optional[str] = None,
    entity: str = "household",
    quantiles: int = 10,
) -> OutputCollection[IntraDecileImpact]:
    """Compute intra-decile proportions for all deciles and the population.

    Returns:
        OutputCollection containing list of IntraDecileImpact objects
        (deciles 1-N plus the direct overall result at decile=0) and DataFrame.
    """
    analysis = _prepare_decile_analysis(
        baseline_simulation,
        reform_simulation,
        income_variable=income_variable,
        decile_variable=decile_variable,
        entity=entity,
        quantiles=quantiles,
        require_effective_weight=True,
    )
    results = []
    for decile in range(1, quantiles + 1):
        impact = IntraDecileImpact.model_construct(
            baseline_simulation=baseline_simulation,
            reform_simulation=reform_simulation,
            income_variable=income_variable,
            decile_variable=decile_variable,
            entity=entity,
            decile=decile,
            quantiles=quantiles,
        )
        impact._run_from_prepared(analysis)
        results.append(impact)

    overall = IntraDecileImpact.model_construct(
        baseline_simulation=baseline_simulation,
        reform_simulation=reform_simulation,
        income_variable=income_variable,
        decile_variable=decile_variable,
        entity=entity,
        decile=0,
        quantiles=quantiles,
    )
    overall._run_from_prepared(analysis)
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
