from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from pydantic import ConfigDict

from policyengine.core import Output, OutputCollection, Simulation
from policyengine.core.dataset import Dataset
from policyengine.core.dynamic import Dynamic
from policyengine.core.policy import Policy
from policyengine.core.tax_benefit_model_version import TaxBenefitModelVersion
from policyengine.outputs.decile_analysis import (
    _prepare_decile_analysis,
    _PreparedDecileAnalysis,
    _weighted_mean,
)

_DECILE_RESULT_COLUMNS = [
    "baseline_mean",
    "reform_mean",
    "absolute_change",
    "relative_change",
    "count_better_off",
    "count_worse_off",
    "count_no_change",
]


@dataclass(frozen=True)
class _DecileImpactValues:
    """Calculated values for one reported decile."""

    baseline_mean: Optional[float]
    reform_mean: Optional[float]
    absolute_change: Optional[float]
    relative_change: Optional[float]
    count_better_off: float
    count_worse_off: float
    count_no_change: float


def _calculate_decile_impact_values(
    analysis: _PreparedDecileAnalysis,
    *,
    decile: int,
) -> _DecileImpactValues:
    """Calculate household-weighted statistics for one decile."""
    in_decile = analysis.included & analysis.groups.eq(decile).fillna(False).to_numpy(
        dtype=bool
    )
    weights = analysis.analysis_weight[in_decile]
    baseline_mean = _weighted_mean(
        analysis.baseline_income[in_decile],
        weights,
    )
    reform_mean = _weighted_mean(
        analysis.reform_income[in_decile],
        weights,
    )
    if baseline_mean is None or reform_mean is None:
        return _DecileImpactValues(
            baseline_mean=None,
            reform_mean=None,
            absolute_change=None,
            relative_change=None,
            count_better_off=0.0,
            count_worse_off=0.0,
            count_no_change=0.0,
        )

    income_change = (
        analysis.reform_income[in_decile] - analysis.baseline_income[in_decile]
    )
    absolute_change = reform_mean - baseline_mean
    relative_change = (
        None if baseline_mean == 0 else float(100 * absolute_change / baseline_mean)
    )
    return _DecileImpactValues(
        baseline_mean=baseline_mean,
        reform_mean=reform_mean,
        absolute_change=absolute_change,
        relative_change=relative_change,
        count_better_off=float(np.sum(weights[income_change > 0])),
        count_worse_off=float(np.sum(weights[income_change < 0])),
        count_no_change=float(np.sum(weights[income_change == 0])),
    )


class DecileImpact(Output):
    """Single decile's impact from a policy reform - represents one database row."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_simulation: Simulation
    reform_simulation: Simulation
    income_variable: str = "household_net_income"
    decile_variable: Optional[str] = None  # If set, use pre-computed grouping variable
    entity: Optional[str] = None
    decile: int
    quantiles: int = 10

    # Results populated by run()
    baseline_mean: Optional[float] = None
    reform_mean: Optional[float] = None
    absolute_change: Optional[float] = None
    relative_change: Optional[float] = None
    count_better_off: Optional[float] = None
    count_worse_off: Optional[float] = None
    count_no_change: Optional[float] = None

    def run(self) -> None:
        """Calculate impact for this specific decile."""
        analysis = _prepare_decile_analysis(
            self.baseline_simulation,
            self.reform_simulation,
            income_variable=self.income_variable,
            decile_variable=self.decile_variable,
            entity=self.entity,
            quantiles=self.quantiles,
        )
        self._run_from_prepared(analysis)

    def _run_from_prepared(
        self,
        analysis: _PreparedDecileAnalysis,
    ) -> None:
        """Populate this output from already validated shared inputs."""
        values = _calculate_decile_impact_values(
            analysis,
            decile=self.decile,
        )
        self.baseline_mean = values.baseline_mean
        self.reform_mean = values.reform_mean
        self.absolute_change = values.absolute_change
        self.relative_change = values.relative_change
        self.count_better_off = values.count_better_off
        self.count_worse_off = values.count_worse_off
        self.count_no_change = values.count_no_change


def calculate_decile_impacts(
    dataset: Optional[Dataset] = None,
    tax_benefit_model_version: Optional[TaxBenefitModelVersion] = None,
    baseline_policy: Optional[Policy] = None,
    reform_policy: Optional[Policy] = None,
    dynamic: Optional[Dynamic] = None,
    income_variable: str = "household_net_income",
    decile_variable: Optional[str] = None,
    entity: Optional[str] = None,
    quantiles: int = 10,
    baseline_simulation: Optional[Simulation] = None,
    reform_simulation: Optional[Simulation] = None,
) -> OutputCollection[DecileImpact]:
    """Calculate decile-by-decile impact of a reform.

    By default, changes are measured in ``household_net_income`` and household
    deciles are computed from that variable using survey weights multiplied by
    household size. Households with negative values of the computed income
    concept are excluded from the reported deciles, matching country-package
    income-decile outputs. Pass ``decile_variable`` to group by a pre-computed
    decile variable while still measuring changes in ``income_variable``;
    values outside ``1..quantiles`` are excluded from the reported groups. For
    example, UK wealth deciles use
    ``income_variable="household_net_income"`` with
    ``decile_variable="household_wealth_decile"``.

    Returns:
        OutputCollection containing list of DecileImpact objects and a DataFrame.
        The DataFrame includes ``decile_variable`` so callers can distinguish
        income-derived deciles from pre-computed grouping variables.
    """
    if (baseline_simulation is None) != (reform_simulation is None):
        raise ValueError(
            "baseline_simulation and reform_simulation must be provided together"
        )

    if baseline_simulation is None:
        if dataset is None or tax_benefit_model_version is None:
            raise ValueError(
                "dataset and tax_benefit_model_version are required when simulations are not provided"
            )

        baseline_simulation = Simulation(
            dataset=dataset,
            tax_benefit_model_version=tax_benefit_model_version,
            policy=baseline_policy,
            dynamic=dynamic,
        )
        reform_simulation = Simulation(
            dataset=dataset,
            tax_benefit_model_version=tax_benefit_model_version,
            policy=reform_policy,
            dynamic=dynamic,
        )

    assert baseline_simulation is not None
    assert reform_simulation is not None
    baseline_simulation.ensure()
    reform_simulation.ensure()

    analysis = _prepare_decile_analysis(
        baseline_simulation,
        reform_simulation,
        income_variable=income_variable,
        decile_variable=decile_variable,
        entity=entity,
        quantiles=quantiles,
    )
    results = []
    for decile in range(1, quantiles + 1):
        impact = DecileImpact(
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

    # Create DataFrame
    df = pd.DataFrame(
        [
            {
                "baseline_simulation_id": r.baseline_simulation.id,
                "reform_simulation_id": r.reform_simulation.id,
                "income_variable": r.income_variable,
                "decile_variable": r.decile_variable,
                "decile": r.decile,
                "baseline_mean": r.baseline_mean,
                "reform_mean": r.reform_mean,
                "absolute_change": r.absolute_change,
                "relative_change": r.relative_change,
                "count_better_off": r.count_better_off,
                "count_worse_off": r.count_worse_off,
                "count_no_change": r.count_no_change,
            }
            for r in results
        ]
    )
    df[_DECILE_RESULT_COLUMNS] = df[_DECILE_RESULT_COLUMNS].astype("Float64")

    return OutputCollection(outputs=results, dataframe=df)
